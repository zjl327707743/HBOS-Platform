"""从运行态 Stock 工作台生成 hb_stock_app 的「海滨库存」工作台 fixture。

用法：
    # 1. 在 backend 容器内导出原生 Stock 工作台
    docker exec hbos-m0-r3a-backend-1 bash -lc 'cd /home/frappe/frappe-bench && \
      bench --site frontend execute frappe.client.get \
      --kwargs "{\\"doctype\\":\\"Workspace\\",\\"name\\":\\"Stock\\"}" > /tmp/stock_ws.json'
    # 2. 拷回宿主机
    docker cp hbos-m0-r3a-backend-1:/tmp/stock_ws.json /tmp/stock_ws.json
    # 3. 生成 fixture
    PYTHONPATH=apps/hb_stock_app python3 tools/gen_stock_workspace_fixture.py /tmp/stock_ws.json
"""

import json
import sys
from pathlib import Path

from hb_stock_app.hbos_stock.workspace_builder import (
	TARGET_WORKSPACE,
	build_workspace_payload,
)

FIXTURE = (Path(__file__).resolve().parent.parent / "apps" / "hb_stock_app"
           / "hb_stock_app" / "hbos_stock" / "workspace" / TARGET_WORKSPACE
           / f"{TARGET_WORKSPACE}.json")


def extract_json(raw):
	"""bench execute 输出会夹带日志行，截取首个 { 到末个 }。"""
	start, end = raw.find("{"), raw.rfind("}")
	if start == -1 or end == -1:
		raise SystemExit("未在输入中找到 JSON 对象")
	return json.loads(raw[start:end + 1])


def main():
	if len(sys.argv) != 2:
		raise SystemExit("用法: python3 tools/gen_stock_workspace_fixture.py <stock_ws.json>")
	source = extract_json(Path(sys.argv[1]).read_text())
	payload = build_workspace_payload(source)
	FIXTURE.parent.mkdir(parents=True, exist_ok=True)
	FIXTURE.write_text(json.dumps(payload, ensure_ascii=False, indent=1, sort_keys=True))
	print(f"已写入 {FIXTURE}")
	print(f"links={len(payload['links'])} charts={len(payload['charts'])} "
	      f"number_cards={len(payload['number_cards'])}")


if __name__ == "__main__":
	main()
