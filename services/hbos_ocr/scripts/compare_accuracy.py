"""C1 / C2 识别准确率比对脚本。

用途
----
用**真实标签照片**测出「拍一张 → 读到什么 → 对不对」，为选定识别后端提供依据。
标准见 `docs/milestones/M3_R6_入库拍照识别服务方案.md` 第七节。

数据边界（必须遵守）
--------------------
真实标签照片含真实批号与产品名，**不得进入仓库**。

因此本脚本：

- **脚本本身在仓库内**，不含任何真实数据；
- 样本目录与结果目录**都在仓库外**，由 ``--samples-dir`` / ``--out-dir`` 指定；
- 结果只写本地磁盘，不上传任何地方。

用法
----
先起服务（另开一个终端）：

    HBOS_OCR_BACKEND=c2_ocr uvicorn app.main:app --host 127.0.0.1 --port 8100

再跑比对：

    python scripts/compare_accuracy.py \
        --samples-dir ~/Documents/M3R6样本 \
        --backend c2_ocr

判定口径（重要）
----------------
标签上日期的**印刷粒度不一致**——实测 50 张里有 34 张的有效期只印到月
（如「2028年7月」），另外 6 张印到日（如「2028年6月24日」）。

所以日期**按真值的粒度比对**：

- 真值只到月 → 只比 年+月；模型多给了一个日，不算错，但单独记为「过细」；
- 真值到日 → 比 年+月+日。

若拿「2028年7月」去硬比模型的「2028-07-31」，会把对的说成错的。
"""

from __future__ import annotations

import argparse
import csv
import json
import mimetypes
import os
import re
import sys
import time
import urllib.error
import urllib.request
import uuid

# ``--reextract`` 要直接调用服务端代码，所以把服务根目录挂到 sys.path。
# 正常跑（走 HTTP）用不到，装了也无副作用。
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ---------------------------------------------------------------------------
# 日期规范化
# ---------------------------------------------------------------------------

_CN_DATE = re.compile(r"(\d{4})\s*年\s*(\d{1,2})\s*月(?:\s*(\d{1,2})\s*日)?")
_NUM_DATE = re.compile(r"(\d{4})\s*[.\-/]\s*(\d{1,2})\s*[.\-/]\s*(\d{1,2})")
_NUM_MONTH = re.compile(r"^\s*(\d{4})\s*[.\-/]\s*(\d{1,2})\s*$")


def parse_truth_date(raw: str) -> tuple[int, int, int | None] | None:
    """把真值表里的日期写法解析为 ``(年, 月, 日 或 None)``。

    真值表里三种写法并存，且月粒度与日粒度混用：

        2025年6月25日   日粒度
        2028年7月       月粒度
        2024.08.01      日粒度（点分）
        2027.06         月粒度（点分）← 这一种最容易漏，漏了会低估样本量
    """
    if not raw:
        return None
    text = str(raw).strip()
    if not text:
        return None

    # 先试「日粒度」，再试「月粒度」——顺序不能反，
    # 否则 2024.08.01 会被 _NUM_MONTH 之外的规则误判。
    m = _CN_DATE.search(text)
    if m:
        day = int(m.group(3)) if m.group(3) else None
        return int(m.group(1)), int(m.group(2)), day

    m = _NUM_DATE.search(text)
    if m:
        return int(m.group(1)), int(m.group(2)), int(m.group(3))

    m = _NUM_MONTH.match(text)
    if m:
        return int(m.group(1)), int(m.group(2)), None

    return None


def parse_pred_date(raw: str | None) -> tuple[int, int, int | None] | None:
    """解析识别结果里的日期（校验层已规范为 ISO ``YYYY-MM-DD``）。"""
    if not raw:
        return None
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", str(raw).strip())
    if not m:
        return None
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


def is_month_only(truth_raw: str) -> bool:
    """真值是否只到月（标签上没印日）。"""
    t = parse_truth_date(truth_raw)
    return t is not None and t[2] is None


def score_date(truth_raw: str, pred_raw: str | None) -> str:
    """按真值粒度比对日期。判定取值：``✓`` / ``✓月`` / ``✗`` / ``空`` / ``—``

    只到月的真值只比 年+月。校验层会把这种值补成**当月最后一天**
    （标签没印日，不补的话 ERPNext 的 Date 字段存不下），
    所以拿补出来的日去比是没意义的——比分时按真值粒度。
    """
    t = parse_truth_date(truth_raw)
    if t is None:
        return "—"  # 真值本就没填，不参与评分

    p = parse_pred_date(pred_raw)
    if p is None:
        return "空"

    ty, tm, td = t
    py, pm, pd = p

    if (ty, tm) != (py, pm):
        return "✗"

    if td is None:
        return "✓月"  # 真值只到月，月对即对

    return "✓" if td == pd else "✗"


# ---------------------------------------------------------------------------
# 其它字段
# ---------------------------------------------------------------------------


def score_item_code(truth: str, pred: str | None, raw: str | None) -> str:
    """比对物料代码。

    额外区分「**纠错后对**」——原始识别含形近字母、被校验层纠正后才对的。
    这个数字直接量化了校验层的价值。
    """
    truth = (truth or "").strip()
    if not truth:
        return "—"
    if not pred:
        return "空"
    if str(pred).strip() == truth:
        raw_s = (raw or "").strip()
        if raw_s and raw_s != truth:
            return "✓纠错"
        return "✓"
    return "✗"


def score_batch(truth: str, pred: str | None) -> str:
    """比对批号（忽略大小写与空白）。"""
    truth = (truth or "").strip()
    if not truth:
        return "—"
    if not pred:
        return "空"
    a = re.sub(r"\s", "", truth).upper()
    b = re.sub(r"\s", "", str(pred)).upper()
    return "✓" if a == b else "✗"


def score_name(truth: str, pred: str | None) -> str:
    """比对产品名称。

    品名是最软的一个字段：OCR 抽的是"最长的中文行"，容易带上别的内容。
    因此除完全一致外，**互相包含**也记为部分命中（△）。
    """
    truth = (truth or "").strip()
    if not truth:
        return "—"
    if not pred:
        return "空"
    a = re.sub(r"\s", "", truth)
    b = re.sub(r"\s", "", str(pred))
    if a == b:
        return "✓"
    if a and (a in b or b in a):
        return "△"
    return "✗"


# ---------------------------------------------------------------------------
# HTTP（stdlib，不引第三方依赖）
# ---------------------------------------------------------------------------


def post_recognize(base_url: str, image_path: str, backend: str, source_type: str | None) -> dict:
    """把一张照片 POST 给识别服务，返回 JSON。"""
    boundary = "----hbos" + uuid.uuid4().hex
    filename = os.path.basename(image_path)
    ctype = mimetypes.guess_type(filename)[0] or "image/jpeg"

    with open(image_path, "rb") as fh:
        blob = fh.read()

    parts: list[bytes] = []

    def field(name: str, value: str) -> None:
        parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode()
        )

    parts.append(
        f'--{boundary}\r\nContent-Disposition: form-data; name="image"; filename="{filename}"\r\n'
        f"Content-Type: {ctype}\r\n\r\n".encode()
    )
    parts.append(blob)
    parts.append(b"\r\n")

    field("backend", backend)
    if source_type:
        field("source_type", source_type)

    parts.append(f"--{boundary}--\r\n".encode())
    body = b"".join(parts)

    req = urllib.request.Request(
        f"{base_url.rstrip('/')}/api/v1/recognize",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        return json.loads(resp.read().decode())


def check_health(base_url: str) -> dict:
    with urllib.request.urlopen(f"{base_url.rstrip('/')}/health", timeout=15) as resp:
        return json.loads(resp.read().decode())


# ---------------------------------------------------------------------------
# 逐张判定 + 汇总
# ---------------------------------------------------------------------------


def score_row(truth: dict, fields: dict, raw_fields: dict | None = None) -> dict:
    """把「真值行 + 识别结果」判成一条对照记录。

    单独抽成函数，是为了能**离线重判**——OCR 跑一次要半小时，
    而评分口径（比如日期的月粒度处理）可能还要改。
    """
    rawf = raw_fields or {}
    return {
        "来源": truth.get("来源", ""),
        "品名_真值": truth.get("品名", ""),
        "品名_识别": fields.get("product_name") or "",
        "品名判定": score_name(truth.get("品名", ""), fields.get("product_name")),
        "物料代码_真值": truth.get("物料代码", ""),
        "物料代码_识别": fields.get("item_code") or "",
        "物料代码_判定": score_item_code(
            truth.get("物料代码", ""), fields.get("item_code"), rawf.get("item_code")
        ),
        "批号_真值": truth.get("批号", ""),
        "批号_识别": fields.get("batch_no") or "",
        "批号判定": score_batch(truth.get("批号", ""), fields.get("batch_no")),
        "生产日期_真值": truth.get("生产日期", ""),
        "生产日期_识别": fields.get("manufacturing_date") or "",
        "生产日期判定": score_date(truth.get("生产日期", ""), fields.get("manufacturing_date")),
        "有效期_真值": truth.get("有效期至", ""),
        "有效期_识别": fields.get("expiry_date") or "",
        "有效期判定": score_date(truth.get("有效期至", ""), fields.get("expiry_date")),
    }


SUMMARY_FIELDS = (
    ("品名", "品名判定"),
    ("物料代码", "物料代码_判定"),
    ("批号", "批号判定"),
    ("生产日期", "生产日期判定"),
    ("有效期至", "有效期判定"),
)


def summarize(detail: list[dict], rows: list[dict], backend: str, samples: str) -> str:
    """生成准确率汇总（Markdown 文本）。"""

    def tally(key: str) -> dict[str, int]:
        c: dict[str, int] = {}
        for d in detail:
            v = str(d.get(key) or "").strip()
            if not v:
                continue
            c[v] = c.get(v, 0) + 1
        return c

    counts = {label: tally(key) for label, key in SUMMARY_FIELDS}
    month_only = sum(1 for r in rows if is_month_only(r.get("有效期至", "")))

    lines = [
        f"# 识别准确率（后端 {backend}）",
        "",
        f"- 样本：{len(detail)} 张，目录 `{samples}`",
        "- 判定口径：日期按**真值印刷粒度**比对；只到月的真值不因模型多给日而判错。",
        "- `空` = 没识别出来；`—` = 真值没填（不计入分母）。",
        "",
        "| 字段 | 命中 | 部分 | 未中 | 空 | 有效样本 | 准确率 |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]

    for label, key in SUMMARY_FIELDS:
        c = counts[label]
        hit = c.get("✓", 0) + c.get("✓月", 0) + c.get("✓纠错", 0)
        part = c.get("△", 0)
        miss = c.get("✗", 0)
        empty = c.get("空", 0)
        total = hit + part + miss + empty
        rate = f"{hit / total * 100:.0f}%" if total else "—"
        lines.append(f"| {label} | {hit} | {part} | {miss} | {empty} | {total} | **{rate}** |")

    corrected = counts["物料代码"].get("✓纠错", 0)
    lines += [
        "",
        f"其中物料代码靠**校验层纠错**才对的：**{corrected}** 张。",
        "",
        f"有效期只印到月的标签：**{month_only}** 张（这些的日是按**月末**推定的，非标签实印）。",
    ]

    return "\n".join(lines) + "\n"


def print_summary(detail: list[dict]) -> None:
    print()
    print("=" * 62)
    for label, key in SUMMARY_FIELDS:
        c: dict[str, int] = {}
        for d in detail:
            v = str(d.get(key) or "").strip()
            if v:
                c[v] = c.get(v, 0) + 1
        hit = c.get("✓", 0) + c.get("✓月", 0) + c.get("✓纠错", 0)
        part = c.get("△", 0)
        miss = c.get("✗", 0)
        empty = c.get("空", 0)
        total = hit + part + miss + empty
        rate = f"{hit / total * 100:5.1f}%" if total else "   —  "
        extra = f" 部分{part}" if part else ""
        print(f"  {label:<6} {rate}  (命中{hit}/{total}  空{empty}{extra})")
    print("=" * 62)


def rescore(compare_csv: str, truth_csv: str, out_dir: str, backend: str, samples: str) -> int:
    """用现有的逐张对照表重新判定，**不重跑 OCR**。

    只重算派生列（各字段的判定），识别结果本身照用。
    改了评分口径、或补了真值表之后用这个，省一次半小时的识别。
    """
    with open(compare_csv, encoding="utf-8-sig", newline="") as fh:
        got = {r["文件名"]: r for r in csv.DictReader(fh)}
    with open(truth_csv, encoding="utf-8-sig", newline="") as fh:
        rows = [r for r in csv.DictReader(fh) if (r.get("文件名") or "").strip()]

    detail: list[dict] = []
    for row in rows:
        fname = (row.get("文件名") or "").strip()
        prev = got.get(fname)
        if not prev:
            continue
        fields = {
            "product_name": prev.get("品名_识别") or None,
            "item_code": prev.get("物料代码_识别") or None,
            "batch_no": prev.get("批号_识别") or None,
            "manufacturing_date": prev.get("生产日期_识别") or None,
            "expiry_date": prev.get("有效期_识别") or None,
        }
        rec = {"文件名": fname}
        rec.update(score_row(row, fields, None))
        rec["耗时秒"] = prev.get("耗时秒", "")
        rec["需复核"] = prev.get("需复核", "")
        detail.append(rec)

    text = summarize(detail, rows, backend, samples)
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "准确率汇总.md"), "w", encoding="utf-8") as fh:
        fh.write(text)

    keys: list[str] = []
    for d in detail:
        for k in d:
            if k not in keys:
                keys.append(k)
    with open(os.path.join(out_dir, "逐张对照表.csv"), "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        w.writerows(detail)

    print(f"重判 {len(detail)} 张（未重跑识别）")
    print_summary(detail)
    print(text)
    return 0


def reextract(
    out_dir: str, truth_csv: str, backend: str, samples: str, photo_dir: str
) -> int:
    """从**已保存的识别原文**重跑抽取与校验，不重跑 OCR。

    什么时候用：改了 ``app/backends/c2_ocr.py`` 的抽取规则、或改了
    ``app/validate.py`` 的校验逻辑，而 **OCR 模型本身没换**。

    为什么等价：``识别原文/<文件名>.txt`` 存的正是后端当初拿到的文本行
    （``BackendResult.raw_text``）。后端对同一份文本行的处理是纯函数，
    因此离线重跑与重启服务重跑**结果完全一致**，但省掉半小时的识别。

    ⚠ 若换的是 OCR 模型（如改到 C1），必须重跑，不能用这个。
    """
    from app.backends.c2_ocr import PaddleOCRBackend  # noqa: PLC0415
    from app.validate import validate_fields  # noqa: PLC0415

    with open(truth_csv, encoding="utf-8-sig", newline="") as fh:
        rows = [r for r in csv.DictReader(fh) if (r.get("文件名") or "").strip()]

    text_dir = os.path.join(out_dir, "识别原文")
    detail: list[dict] = []
    missing: list[str] = []

    for row in rows:
        fname = (row.get("文件名") or "").strip()
        path = os.path.join(text_dir, f"{fname}.txt")
        if not os.path.exists(path):
            missing.append(fname)
            continue

        with open(path, encoding="utf-8") as fh:
            raw_text = fh.read()
        lines = raw_text.split("\n")

        raw_fields = PaddleOCRBackend._extract(lines)
        # raw_text 必须传——日期的**溯源校验**靠它判断模型有没有编日期
        report = validate_fields(
            raw_fields,
            source_type=(row.get("来源") or "").strip() or None,
            raw_text=raw_text,
        )

        rec = {"文件名": fname}
        rec.update(score_row(row, report.as_dict(), raw_fields))
        detail.append(rec)

    if missing:
        print(f"缺识别原文，已跳过：{missing}", file=sys.stderr)

    text = summarize(detail, rows, backend, samples)
    with open(os.path.join(out_dir, "准确率汇总.md"), "w", encoding="utf-8") as fh:
        fh.write(text)

    keys: list[str] = []
    for d in detail:
        for k in d:
            if k not in keys:
                keys.append(k)
    # 逐张对照表会被覆盖，先留一份旧的备查
    old = os.path.join(out_dir, "逐张对照表.csv")
    if os.path.exists(old):
        os.replace(old, os.path.join(out_dir, "逐张对照表.上次.csv"))
    with open(old, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        w.writerows(detail)

    print(f"从识别原文重跑抽取：{len(detail)} 张（未重跑 OCR）")
    print_summary(detail)
    return 0


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------


def main() -> int:
    ap = argparse.ArgumentParser(description="识别准确率比对")
    ap.add_argument("--samples-dir", required=True, help="含 照片/ 与 真值表.csv 的目录")
    ap.add_argument("--out-dir", default=None, help="结果输出目录，缺省为 <samples-dir>/结果")
    ap.add_argument("--base-url", default="http://127.0.0.1:8100")
    ap.add_argument("--backend", default="c2_ocr")
    ap.add_argument("--limit", type=int, default=0, help="只跑前 N 张（0=全部）")
    ap.add_argument(
        "--rescore",
        action="store_true",
        help="只按现有逐张对照表重判，不重跑抽取（改评分口径后用）",
    )
    ap.add_argument(
        "--reextract",
        action="store_true",
        help="从识别原文重跑抽取+校验，不重跑 OCR（改抽取规则后用）",
    )
    args = ap.parse_args()

    samples = os.path.expanduser(args.samples_dir)
    out_dir = os.path.expanduser(args.out_dir) if args.out_dir else os.path.join(samples, "结果")
    photo_dir = os.path.join(samples, "照片")
    truth_csv = os.path.join(samples, "真值表.csv")

    for p in (photo_dir, truth_csv):
        if not os.path.exists(p):
            print(f"找不到：{p}", file=sys.stderr)
            return 2

    if args.rescore:
        compare_csv = os.path.join(out_dir, "逐张对照表.csv")
        if not os.path.exists(compare_csv):
            print(f"找不到逐张对照表：{compare_csv}", file=sys.stderr)
            return 2
        return rescore(compare_csv, truth_csv, out_dir, args.backend, samples)

    if args.reextract:
        return reextract(out_dir, truth_csv, args.backend, samples, photo_dir)



    # 服务必须在跑——否则测的不是真实链路
    try:
        health = check_health(args.base_url)
    except Exception as exc:  # noqa: BLE001
        print(f"识别服务不可达（{args.base_url}）：{type(exc).__name__}", file=sys.stderr)
        print("请先起服务：HBOS_OCR_BACKEND=... uvicorn app.main:app --port 8100", file=sys.stderr)
        return 3

    backends = health.get("backends", {})
    # --backend 可以是 ``c2_ocr:small`` 这种带模型档位的写法；
    # 可用性按后端名查，档位交给服务端解析。
    base_backend = args.backend.split(":", 1)[0]
    if base_backend not in backends:
        print(f"未知后端 {args.backend}，服务报告可用：{list(backends)}", file=sys.stderr)
        return 3
    avail, reason = backends[base_backend].get("available"), backends[base_backend].get("reason", "")
    if not avail:
        print(f"后端 {args.backend} 不可用：{reason}", file=sys.stderr)
        return 3

    with open(truth_csv, encoding="utf-8-sig", newline="") as fh:
        rows = [r for r in csv.DictReader(fh) if (r.get("文件名") or "").strip()]
    if args.limit:
        rows = rows[: args.limit]

    os.makedirs(out_dir, exist_ok=True)

    print(f"后端 {args.backend}｜样本 {len(rows)} 张｜结果写到 {out_dir}")
    print()

    detail: list[dict] = []
    raw_text_dir = os.path.join(out_dir, "识别原文")
    os.makedirs(raw_text_dir, exist_ok=True)

    for i, row in enumerate(rows, 1):
        fname = (row.get("文件名") or "").strip()
        img = os.path.join(photo_dir, f"{fname}.jpg")
        if not os.path.exists(img):
            print(f"  [{i:2}/{len(rows)}] {fname} 缺照片，跳过")
            continue

        source = (row.get("来源") or "").strip() or None
        t0 = time.time()
        try:
            res = post_recognize(args.base_url, img, args.backend, source)
        except urllib.error.HTTPError as exc:
            body = exc.read().decode(errors="replace")[:200]
            print(f"  [{i:2}/{len(rows)}] {fname} 识别失败 HTTP {exc.code}: {body}")
            detail.append({"文件名": fname, "错误": f"HTTP {exc.code}"})
            continue
        except Exception as exc:  # noqa: BLE001
            print(f"  [{i:2}/{len(rows)}] {fname} 识别失败 {type(exc).__name__}")
            detail.append({"文件名": fname, "错误": type(exc).__name__})
            continue
        elapsed = round(time.time() - t0, 1)

        fields = res.get("fields") or {}
        rawf = res.get("raw_fields") or {}

        rec = {"文件名": fname}
        rec.update(score_row(row, fields, rawf))
        rec["耗时秒"] = elapsed
        rec["需复核"] = "是" if res.get("needs_review") else "否"
        detail.append(rec)

        # 识别原文单独落盘，便于逐张回看"读到了什么"
        with open(os.path.join(raw_text_dir, f"{fname}.txt"), "w", encoding="utf-8") as fh:
            fh.write(res.get("raw_text") or "")

        code_v = rec["物料代码_判定"]
        exp_v = rec["有效期判定"]
        flag = "" if (code_v.startswith("✓") and exp_v.startswith("✓")) else "  ←"
        print(
            f"  [{i:2}/{len(rows)}] {fname:>3}  "
            f"代码 {code_v:<5} 批号 {rec['批号判定']:<3} "
            f"生产 {rec['生产日期判定']:<4} 效期 {exp_v:<4} {elapsed:>5.1f}s{flag}"
        )

    text = summarize(detail, rows, args.backend, samples)
    with open(os.path.join(out_dir, "准确率汇总.md"), "w", encoding="utf-8") as fh:
        fh.write(text)

    if detail:
        keys: list[str] = []
        for d in detail:
            for k in d:
                if k not in keys:
                    keys.append(k)
        with open(os.path.join(out_dir, "逐张对照表.csv"), "w", encoding="utf-8-sig", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=keys)
            w.writeheader()
            w.writerows(detail)

    print_summary(detail)
    print(text)
    print(f"结果：{out_dir}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
