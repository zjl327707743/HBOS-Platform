"""端到端链路冒烟测试（进程内，**不启动服务器**）。

目的：验证「上传 → 后端识别 → 约束校验 → 响应」整条链路是通的，
**不依赖任何真实标签样本、不依赖 ML 依赖、不联网**。

用 FastAPI 的 TestClient 在进程内驱动应用，因此**不需要真的把服务跑起来**。

运行：
    cd services/hbos_ocr && python scripts/smoke_test.py
"""

from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

# 用一张**纯色图片**即可——stub 后端不读图像内容。
# 这里直接构造一个最小合法 PNG（1x1 像素），避免引入图片库依赖。
TINY_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
    "890000000a49444154789c6360000002000100ffff03000006000557bfabd400"
    "00000049454e44ae426082"
)

failures: list[str] = []


def check(label: str, condition: bool, detail: str = "") -> None:
    mark = "PASS" if condition else "FAIL"
    print(f"{mark}  {label}" + (f"  | {detail}" if detail else ""))
    if not condition:
        failures.append(label)


def main() -> int:
    try:
        from fastapi.testclient import TestClient
    except Exception:
        print("缺少 fastapi / httpx。请先：")
        print("    uv venv && source .venv/bin/activate && uv pip install -r requirements.txt")
        return 2

    from app.main import app

    client = TestClient(app)

    # --- 1. 健康检查与后端可用性 ---
    r = client.get("/health")
    check("/health 200", r.status_code == 200, f"status={r.status_code}")
    body = r.json()
    check("健康检查返回 ok", body.get("ok") is True)
    backends = body.get("backends", {})
    check("stub 后端可用", backends.get("stub", {}).get("available") is True)
    print("    后端状态：", {k: v["available"] for k, v in backends.items()})

    # --- 2. 正常识别（stub 默认值） ---
    r = client.post(
        "/api/v1/recognize",
        files={"image": ("label.jpg", TINY_PNG, "image/jpeg")},
        data={"backend": "stub", "source_type": "自产"},
    )
    check("识别 200", r.status_code == 200, f"status={r.status_code}")
    payload = r.json()
    check("返回 ok", payload.get("ok") is True)
    check("返回 backend 标识", payload.get("backend") == "stub", str(payload.get("backend")))
    fields = payload.get("fields", {})
    check("五个字段齐全", all(k in fields for k in (
        "product_name", "item_code", "batch_no", "manufacturing_date", "expiry_date")),
        str(sorted(fields)))
    check("响应含 raw_fields（可追溯 AI 读到了什么）", "raw_fields" in payload)
    check("响应含 elapsed_ms", isinstance(payload.get("elapsed_ms"), int))

    # --- 3. 约束校验层生效：形近字母被纠正 ---
    r = client.post(
        "/api/v1/recognize",
        files={"image": ("label.jpg", TINY_PNG, "image/jpeg")},
        data={
            "backend": "stub",
            "source_type": "自产",
            # OCR 把数字 0 认成字母 O —— 校验层应把它纠正回来
            "hints": '{"item_code": "13OOO215", "batch_no": "B2609503"}',
        },
    )
    check("带 hints 的识别 200", r.status_code == 200, f"status={r.status_code}")
    payload = r.json()
    check(
        "物料代码形近字母已纠正",
        payload["fields"]["item_code"] == "13000215",
        f"got {payload['fields']['item_code']!r}",
    )
    check(
        "纠正产生 hints 提示",
        any("形近" in h for h in payload.get("hints", {}).get("item_code", [])),
        str(payload.get("hints", {}).get("item_code")),
    )
    check("needs_review 为真（有提示即需复核）", payload.get("needs_review") is True)

    # --- 4. 幂等：同一 request_id 命中缓存 ---
    rid = "smoke-idem-001"
    r1 = client.post(
        "/api/v1/recognize",
        files={"image": ("a.jpg", TINY_PNG, "image/jpeg")},
        data={"backend": "stub", "request_id": rid},
    )
    r2 = client.post(
        "/api/v1/recognize",
        files={"image": ("b.jpg", TINY_PNG, "image/jpeg")},
        data={"backend": "stub", "request_id": rid},
    )
    check("幂等：两次请求均 200", r1.status_code == 200 and r2.status_code == 200)
    check("幂等：结果一致", r1.json()["fields"] == r2.json()["fields"])

    # --- 5. 失败路径：未知后端 / 空图 / 不可用后端 ---
    r = client.post(
        "/api/v1/recognize",
        files={"image": ("a.jpg", TINY_PNG, "image/jpeg")},
        data={"backend": "no_such_backend"},
    )
    check("未知后端返回 400", r.status_code == 400, f"status={r.status_code}")

    r = client.post(
        "/api/v1/recognize",
        files={"image": ("a.jpg", b"", "image/jpeg")},
        data={"backend": "stub"},
    )
    check("空图返回 400", r.status_code == 400, f"status={r.status_code}")

    r = client.post(
        "/api/v1/recognize",
        files={"image": ("a.jpg", TINY_PNG, "image/jpeg")},
        data={"backend": "c1_local_vlm"},
    )
    # C1 依赖未装时应是 400（后端不可用），不应是 500
    check(
        "未装依赖的后端返回 400 而非 500",
        r.status_code == 400,
        f"status={r.status_code}",
    )

    print()
    if failures:
        print(f"{len(failures)} 项失败：" + "; ".join(failures))
        return 1
    print("冒烟测试全部通过——链路通。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
