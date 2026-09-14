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
ITEM_GROUPS = [
    ("原料药", 1),
    ("包材", 1),
    ("辅助用品", 1),
    ("中间体", 1),
    ("成品", 1),
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
    created = []
    for short, is_group in ITEM_GROUPS:
        if frappe.db.exists("Item Group", short):
            continue
        frappe.get_doc(
            {
                "doctype": "Item Group",
                "item_group_name": short,
                "parent_item_group": "All Item Groups",
                "is_group": is_group,
            }
        ).insert(ignore_permissions=True)
        created.append(short)
    _log("Item Group", "新建", len(created), created)


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
                    "fieldname": "hbos_release_status",
                    "label": "HBOS 放行状态",
                    "fieldtype": "Select",
                    "options": "待检\n已放行\n不放行",
                    "default": "待检",
                    "insert_after": "batch_id",
                    "description": "出库门禁依据：须为「已放行」且有合格证",
                },
                {
                    "fieldname": "hbos_release_date",
                    "label": "HBOS 放行日期",
                    "fieldtype": "Date",
                    "insert_after": "hbos_release_status",
                },
                {
                    "fieldname": "hbos_certificate_no",
                    "label": "HBOS 合格证编号",
                    "fieldtype": "Data",
                    "insert_after": "hbos_release_date",
                },
                {
                    "fieldname": "hbos_certificate_file",
                    "label": "HBOS 合格证附件",
                    "fieldtype": "Attach",
                    "insert_after": "hbos_certificate_no",
                },
                {
                    "fieldname": "hbos_supplier_batch_no",
                    "label": "HBOS 原厂批号",
                    "fieldtype": "Data",
                    "insert_after": "manufacturing_date",
                    "description": "外购物料的供应商批号；batch_id 存进厂批号",
                },
                {
                    "fieldname": "hbos_manufacturer",
                    "label": "HBOS 生产单位",
                    "fieldtype": "Data",
                    "insert_after": "hbos_supplier_batch_no",
                },
                {
                    "fieldname": "hbos_packaging",
                    "label": "HBOS 包装构成",
                    "fieldtype": "Table",
                    "options": "HBOS Packaging Detail",
                    "insert_after": "hbos_manufacturer",
                },
            ],
        }
    )
    _log("Custom Field", "同步完成")


def after_migrate():
    sync_uoms()
    sync_warehouses()
    sync_item_groups()
    sync_custom_fields()
    from hb_inventory_app.hbos_inventory.workspace_setup import sync_inventory_workspace

    sync_inventory_workspace()
    frappe.db.commit()
    _log("HBOS Inventory", "after_migrate 完成")
