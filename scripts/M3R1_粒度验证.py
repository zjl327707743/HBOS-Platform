"""M3-R1 货位 × 批次粒度抽样验证（虚构 TEST 数据）

目的：用 TEST- 前缀虚构数据，验证 ERPNext 原生 Bin / Stock Ledger Entry
      在「货位 × 批次」粒度上的实际行为，为 M3-R2 入库登记去风险。

覆盖场景：
  1. 两个批次分别入到不同货位
  2. 同一批次移库到第二个货位（一批散放多货位）
  3. 按批号反查货位及数量（批号 → 货位）
  4. 按货位反查全部批号（货位 → 批号）

运行方式：
    docker compose cp scripts/M3R1_粒度验证.py backend:/tmp/M3R1_粒度验证.py
    docker compose exec -T backend bench --site frontend console \
        <<< 'exec(open("/tmp/M3R1_粒度验证.py", encoding="utf-8").read())'

数据可清理：全部对象以 TEST-M3R1- 前缀，与 M1 阶段 TEST 数据同约定。
"""

import frappe

COMPANY = "hb"
ITEM = "TEST-M3R1-虚构产品"
B1, B2 = "TEST-M3R1-B001", "TEST-M3R1-B002"
BIN_A, BIN_B, BIN_C = "16-03-221 - HB", "16-03-222 - HB", "16-03-223 - HB"


def log(tag, *args):
    print(tag, *args)


# ---------- 0. 前置设置：ERPNext v16 批次开关 ----------
# v16 默认关闭；不开启则无法按批次记账，也无法建 Serial and Batch Bundle。
if not frappe.db.get_single_value("Stock Settings", "enable_serial_and_batch_no_for_item"):
    ss = frappe.get_single("Stock Settings")
    ss.enable_serial_and_batch_no_for_item = 1
    ss.save(ignore_permissions=True)
    frappe.db.commit()
    log("S0 已开启批次功能")
else:
    log("S0 批次功能已开启")

log("S1 出库批次选取规则",
    frappe.db.get_single_value("Stock Settings", "pick_serial_and_batch_based_on"))


# ---------- 1. 主数据 ----------
if not frappe.db.exists("Item", ITEM):
    frappe.get_doc(
        {
            "doctype": "Item",
            "item_code": ITEM,
            "item_name": "TEST-M3R1-虚构产品",
            "item_group": "Products",
            "stock_uom": "Kg",
            "is_stock_item": 1,
            "has_batch_no": 1,
            "has_serial_no": 0,
        }
    ).insert(ignore_permissions=True)

for b, mfg, exp in ((B1, "2026-09-01", "2028-09-01"), (B2, "2026-08-01", "2028-08-01")):
    if not frappe.db.exists("Batch", b):
        frappe.get_doc(
            {
                "doctype": "Batch",
                "batch_id": b,
                "item": ITEM,
                "manufacturing_date": mfg,
                "expiry_date": exp,
            }
        ).insert(ignore_permissions=True)

log("M1 主数据", "Item", bool(frappe.db.exists("Item", ITEM)), "Batches", frappe.db.count("Batch"))


# ---------- 2. 收货入库：两批次 → 两个货位 ----------
def receipt(batch, qty, warehouse):
    se = frappe.get_doc(
        {
            "doctype": "Stock Entry",
            "stock_entry_type": "Material Receipt",
            "company": COMPANY,
            "to_warehouse": warehouse,
            "items": [
                {
                    "item_code": ITEM,
                    "qty": qty,
                    "t_warehouse": warehouse,
                    "use_serial_batch_fields": 1,
                    "batch_no": batch,
                    "allow_zero_valuation_rate": 1,
                }
            ],
        }
    )
    se.insert(ignore_permissions=True)
    se.submit()
    return se.name


def transfer(batch, qty, src, dst):
    se = frappe.get_doc(
        {
            "doctype": "Stock Entry",
            "stock_entry_type": "Material Transfer",
            "company": COMPANY,
            "from_warehouse": src,
            "to_warehouse": dst,
            "items": [
                {
                    "item_code": ITEM,
                    "qty": qty,
                    "s_warehouse": src,
                    "t_warehouse": dst,
                    "use_serial_batch_fields": 1,
                    "batch_no": batch,
                    "allow_zero_valuation_rate": 1,
                }
            ],
        }
    )
    se.insert(ignore_permissions=True)
    se.submit()
    return se.name


# 幂等：该虚构物料已有库存流水则不再重复建单据
if not frappe.db.exists("Stock Ledger Entry", {"item_code": ITEM}):
    r1 = receipt(B1, 100, BIN_A)
    r2 = receipt(B2, 50, BIN_B)
    log("M2 收货", "B001→", BIN_A, r1, "|", "B002→", BIN_B, r2)
    mv = transfer(B1, 40, BIN_A, BIN_C)
    log("M3 移库", "B001", BIN_A, "→", BIN_C, mv)
    frappe.db.commit()
    log("M4 committed")
else:
    log("M4 已存在流水，跳过建单据")

# ---------- 3. 验证：Bin 粒度 ----------
log("V1 Bin 行数", frappe.db.count("Bin"))
for row in frappe.db.sql(
    "SELECT name, item_code, warehouse, actual_qty FROM tabBin WHERE item_code=%s ORDER BY warehouse",
    ITEM,
    as_dict=True,
):
    log("V2 Bin", row["warehouse"], row["actual_qty"], "| has_batch_field:",
        "batch_no" in [f.fieldname for f in frappe.get_meta("Bin").fields])

# ---------- 4. 验证：SLE 粒度（批次 → 货位） ----------
log("V3 批号→货位→数量（聚合 Stock Ledger Entry）")
for row in frappe.db.sql(
    """SELECT batch_no, warehouse, SUM(actual_qty) AS qty, COUNT(*) AS n
       FROM `tabStock Ledger Entry`
       WHERE item_code=%s AND is_cancelled=0
       GROUP BY batch_no, warehouse ORDER BY batch_no, warehouse""",
    ITEM,
    as_dict=True,
):
    log("V4", row["batch_no"], row["warehouse"], row["qty"], "sle_rows", row["n"])

# ---------- 5. 验证：货位 → 全部批号 ----------
log("V5 货位→批号清单")
for row in frappe.db.sql(
    """SELECT warehouse, GROUP_CONCAT(DISTINCT batch_no) AS batches, SUM(actual_qty) AS qty
       FROM `tabStock Ledger Entry`
       WHERE item_code=%s AND is_cancelled=0
       GROUP BY warehouse ORDER BY warehouse""",
    ITEM,
    as_dict=True,
):
    log("V6", row["warehouse"], "batches=", row["batches"], "qty=", row["qty"])
