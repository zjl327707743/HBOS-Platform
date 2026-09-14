"""M3-R1 货位主数据建树脚本（幂等）

用途：按 Owner 提供的货位清单，在 ERPNext 中建立
      `16号楼产品库 → 03区 → 五个层 → 货位` 的 Warehouse 树。

运行方式（在仓库根目录）：
    docker compose cp "scripts/M3R1_货位清单.json"        backend:/tmp/M3R1_货位清单.json
    docker compose cp "scripts/M3R1_建立货位主数据.py"     backend:/tmp/M3R1_建立货位主数据.py
    docker compose exec -T backend bench --site frontend console \
        <<< 'exec(open("/tmp/M3R1_建立货位主数据.py").read())'

注意：必须用 `exec(open(...).read())` 整体执行，不要把脚本直接重定向进 bench console。
bench console 是 REPL，多行缩进块会被拆成多个单元分别执行，
导致 for 循环只跑一次就被中断（本轮已踩过该坑）。

幂等性：按完整 Warehouse 名称判存，已存在则跳过，可重复执行。
量级：7 个分组节点 + 203 个货位 + 2 个非货位区域 = 212 个节点。
"""

import json
import frappe

DATA_PATH = "/tmp/M3R1_货位清单.json"

with open(DATA_PATH, encoding="utf-8") as fh:
    data = json.load(fh)

company = data["company"]
root_parent = data["root_parent"]
abbr = frappe.get_cached_value("Company", company, "abbr")

created, skipped = [], []
for node in data["nodes"]:
    short = node["warehouse_name"]
    full_name = f"{short} - {abbr}"
    if frappe.db.exists("Warehouse", full_name):
        skipped.append(full_name)
        continue

    parent_short = node["parent"]
    parent = root_parent if parent_short is None else f"{parent_short} - {abbr}"

    doc = frappe.get_doc(
        {
            "doctype": "Warehouse",
            "warehouse_name": short,
            "company": company,
            "parent_warehouse": parent,
            "is_group": node["is_group"],
        }
    )
    doc.insert(ignore_permissions=True)
    created.append(doc.name)

frappe.db.commit()

print(f"新建 {len(created)} 个，跳过（已存在）{len(skipped)} 个")

# 建树后校验：层分布与总数
expected = data["layer_counts"]
total = 0
print("层分布校验：")
for layer, want in expected.items():
    got = frappe.db.count("Warehouse", {"parent_warehouse": f"{layer} - {abbr}"})
    total += got
    flag = "OK" if got == want else "!! 不符"
    print(f"  {layer}: 期望 {want}，实际 {got}  {flag}")

special = [n["warehouse_name"] for n in data["nodes"] if n["parent"] == "03区" and not n["is_group"]]
print("非货位区域:", special)
print(f"货位合计 {total}（期望 {sum(expected.values())}）")
print("层节点 is_group:", frappe.db.get_value("Warehouse", f"第一层 - {abbr}", "is_group"))
