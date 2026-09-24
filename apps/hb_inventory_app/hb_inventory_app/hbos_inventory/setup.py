"""HBOS Inventory 主数据同步（幂等）

由 hooks.after_migrate 调用，声明式创建：
  1. 计量单位（盘存表实测 11 种中 KG 之外的 10 种）
  2. 六车间 8 个库位 Warehouse
  3. 海滨产品分类树（Item Group）
  4. Item / Batch 自定义字段

全部按"存在即跳过"处理，可重复执行。
"""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

COMPANY = "hb"
WAREHOUSE_ROOT = "All Warehouses - HB"

# 盘存表实测单位：KG（原生已有）、个、套、瓶、支、双、卷、张、L、BT，
# 另加「件」用于原料药 / 中间体的双单位计数。
UOMS = ["个", "套", "瓶", "支", "双", "卷", "张", "L", "BT", "件"]

# 六车间 8 个库位。3904 由 M3-R1 货位树改名而来（16号楼产品库 = 3904），
# 此处只确保存在；其余 7 个新建。3904 含子节点故为 group，其余为叶子。
WAREHOUSES = [
    ("3902 六车间退货库", 0),
    ("3903 六车间不合格品库", 0),
    ("3904 六车间中间库", 1),
    ("3906 六车间液体库", 0),
    ("3907 六车间冷藏库", 0),
    ("3908 六车间包材库", 0),
    ("3914 六车间物料库", 0),
    ("3915 六车间备品备库", 0),
]

# 海滨产品分类树。注意：SAP 代码前缀不等于业务分类
# （对外发货的最终产品业务上是成品，但代码为 1300），故分类独立维护。
#
# `is_group = 0`（叶子）——物料要**直接**放进这 5 个节点。M3-R2 初建时误设为 1
# （分组节点），导致物料无处可放：`sync_item_groups` 补了纠偏逻辑，见下。
ITEM_GROUPS = [
    ("原料药", 0),
    ("包材", 0),
    ("辅助用品", 0),
    ("中间体", 0),
    ("成品", 0),
]


def _log(tag, *args):
    print(tag, *args)


def sync_uoms():
    created = []
    for name in UOMS:
        if not frappe.db.exists("UOM", name):
            frappe.get_doc({"doctype": "UOM", "uom_name": name}).insert(ignore_permissions=True)
            created.append(name)
    _log("UOM", "新建", len(created), created)


def sync_warehouses():
    abbr = frappe.get_cached_value("Company", COMPANY, "abbr")
    created = []
    for short, is_group in WAREHOUSES:
        name = f"{short} - {abbr}"
        if frappe.db.exists("Warehouse", name):
            continue
        frappe.get_doc(
            {
                "doctype": "Warehouse",
                "warehouse_name": short,
                "company": COMPANY,
                "parent_warehouse": WAREHOUSE_ROOT,
                "is_group": is_group,
            }
        ).insert(ignore_permissions=True)
        created.append(name)
    _log("Warehouse", "新建", len(created), created)


def sync_item_groups():
    """建海滨分类树，并把已存在节点的 `is_group` **纠偏**。

    纠偏是必需的：`sync_*` 一律「存在即跳过」，所以光改上面的 `ITEM_GROUPS`
    对库里已有的节点无效——`bench migrate` 跑一百遍也不会把 M3-R2 误设的
    `is_group = 1` 改回来。而只要它还是 1，物料就放不进去（分类树形同虚设）。

    只对**没有子节点**的节点纠偏，避免把一个真正的分组节点改坏。
    """
    created, fixed = [], []
    for short, is_group in ITEM_GROUPS:
        if not frappe.db.exists("Item Group", short):
            frappe.get_doc(
                {
                    "doctype": "Item Group",
                    "item_group_name": short,
                    "parent_item_group": "All Item Groups",
                    "is_group": is_group,
                }
            ).insert(ignore_permissions=True)
            created.append(short)
            continue

        cur = frappe.db.get_value("Item Group", short, "is_group")
        if cur == is_group:
            continue
        has_children = frappe.db.exists("Item Group", {"parent_item_group": short})
        if has_children:
            continue
        frappe.db.set_value("Item Group", short, "is_group", is_group, update_modified=False)
        fixed.append(f"{short}:{cur}->{is_group}")

    _log("Item Group", "新建", len(created), created)
    if fixed:
        _log("Item Group", "纠偏 is_group", len(fixed), fixed)


def sync_custom_fields():
    create_custom_fields(
        {
            "Item": [
                {
                    "fieldname": "hbos_product_kind",
                    "label": "HBOS 业务分类",
                    "fieldtype": "Select",
                    "options": "原料药\n包材\n辅助用品\n中间体\n成品",
                    "insert_after": "item_group",
                    "description": "业务口径分类，独立于 SAP 代码前缀",
                },
                {
                    "fieldname": "hbos_workshop",
                    "label": "HBOS 生产车间",
                    "fieldtype": "Data",
                    "insert_after": "hbos_product_kind",
                },
                {
                    "fieldname": "hbos_shelf_life_type",
                    "label": "HBOS 效期类型",
                    "fieldtype": "Select",
                    "options": "复检期\n有效期",
                    "insert_after": "has_expiry_date",
                },
                {
                    "fieldname": "hbos_shelf_life_months",
                    "label": "HBOS 效期期限（月）",
                    "fieldtype": "Int",
                    "insert_after": "hbos_shelf_life_type",
                    "description": "与原生 shelf_life_in_days 二选一使用",
                },
                {
                    "fieldname": "hbos_storage_condition",
                    "label": "HBOS 储存条件",
                    "fieldtype": "Small Text",
                    "insert_after": "hbos_shelf_life_months",
                },
            ],
            "Batch": [
                {
                    "fieldname": "hbos_source_type",
                    "label": "HBOS 来源类型",
                    "fieldtype": "Select",
                    "options": "自产\n外购",
                    "default": "自产",
                    "insert_after": "batch_id",
                    "description": "决定打印时使用自产货位卡还是外购货位卡",
                },
                {
                    "fieldname": "hbos_release_status",
                    "label": "HBOS 放行状态",
                    "fieldtype": "Select",
                    "options": "待检\n已放行\n不放行",
                    "default": "待检",
                    "insert_after": "hbos_source_type",
                    "read_only": 1,
                    "description": "出库门禁依据：须为「已放行」且有合格证",
                },
                {
                    "fieldname": "hbos_release_date",
                    "label": "HBOS 放行日期",
                    "fieldtype": "Date",
                    "insert_after": "hbos_release_status",
                    "read_only": 1,
                },
                {
                    "fieldname": "hbos_certificate_no",
                    "label": "HBOS 合格证编号",
                    "fieldtype": "Data",
                    "insert_after": "hbos_release_date",
                    "read_only": 1,
                },
                {
                    "fieldname": "hbos_certificate_file",
                    "label": "HBOS 合格证附件",
                    "fieldtype": "Attach",
                    "insert_after": "hbos_certificate_no",
                    "read_only": 1,
                },
                {
                    "fieldname": "hbos_lims_reference",
                    "label": "HBOS LIMS 放行引用",
                    "fieldtype": "Data",
                    "insert_after": "hbos_certificate_file",
                    "read_only": 1,
                    "description": "LIMS 放行记录/样品/COA 的稳定引用；Warehouse 只读",
                },
                {
                    "fieldname": "hbos_release_source",
                    "label": "HBOS 放行来源",
                    "fieldtype": "Data",
                    "insert_after": "hbos_lims_reference",
                    "read_only": 1,
                    "description": "质量放行投影来源；正式放行固定为 LIMS",
                },
                {
                    "fieldname": "hbos_supplier_batch_no",
                    "label": "HBOS 原厂批号",
                    "fieldtype": "Data",
                    "insert_after": "manufacturing_date",
                    "description": "外购物料的供应商批号；batch_id 存进厂批号",
                },
                {
                    "fieldname": "hbos_supplier_name",
                    "label": "HBOS 供货单位",
                    "fieldtype": "Data",
                    "insert_after": "hbos_supplier_batch_no",
                    "description": (
                        "照标签填写的供货单位名称（自由文本）。"
                        "待检证的「供货单位」优先取本字段，为空才回落到标准 supplier 链接——"
                        "标准字段是只读的 Supplier 链接，库里供应商档案远少于实际供货单位。"
                    ),
                },
                {
                    "fieldname": "hbos_manufacturer",
                    "label": "HBOS 生产单位",
                    "fieldtype": "Data",
                    "insert_after": "hbos_supplier_name",
                },
                {
                    "fieldname": "hbos_packaging",
                    "label": "HBOS 包装构成",
                    "fieldtype": "Table",
                    "options": "HBOS Packaging Detail",
                    "insert_after": "hbos_manufacturer",
                },
                {
                    "fieldname": "hbos_label_text",
                    "label": "HBOS 标签原文（人工校对后）",
                    "fieldtype": "Long Text",
                    "insert_after": "hbos_packaging",
                    "description": (
                        "入库拍照识别读到的标签全文，**经操作员逐行校对后**留存。"
                        "照片是原始凭证（挂在入库单上），这段文字是可检索的转录件——"
                        "照片没法搜，文字可以。**不参与打印**。"
                    ),
                },
            ],
            "Stock Entry": [
                {
                    "fieldname": "hbos_intake_batch",
                    "label": "HBOS 识别入库批次",
                    "fieldtype": "Link",
                    "options": "Batch",
                    "insert_after": "remarks",
                    "read_only": 1,
                    "description": (
                        "由「入库拍照识别」建的草稿会写入此字段，指向本批的批次。"
                        "**非空即代表来源是拍照识别**——提交后据此提示去批次取货位卡 / 待检证。"
                        "用专用字段而不是靠 remarks 的中文文案匹配，避免改一句话就失效。"
                    ),
                },
            ],
        }
    )
    _log("Custom Field", "同步完成")


def after_migrate():
    """Schema/UI migration only.

    Company-specific UOM/Warehouse/Item Group data is intentionally excluded.
    Use hbos_inventory.business_seed.apply_profile(...) explicitly for business seed.
    """
    sync_custom_fields()
    from hb_inventory_app.hbos_inventory.workspace_setup import sync_inventory_workspace

    sync_inventory_workspace()
    frappe.db.commit()
    _log("HBOS Inventory", "after_migrate schema/UI 完成")
