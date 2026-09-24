"""HBOS Inventory schema/UI migration.

Company-specific UOM / Warehouse / Item Group data is business master data and is
not mutated by bench migrate.  Apply an administrator-controlled profile explicitly
through hbos_inventory.business_seed.apply_profile().
"""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


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
