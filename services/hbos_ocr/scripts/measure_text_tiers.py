"""按「大字 / 小字 / 手写」分档测 OCR 质量。

## 为什么这么测

`compare_accuracy.py` 给的是**字段级**准确率，而它衡量的 5 个字段里 4 个是数字
（批号 / 物料代码 / 两个日期），只有品名是汉字。所以那个数字**对「汉字读得准不准」
几乎没有说明力**，而标签上的信息大半是汉字。

## 分档口径与真值从哪来

| 档 | 真值来源 | 说明 |
| --- | --- | --- |
| 大字 | `真值表.csv` 的 5 个字段 | 有真值，逐张比 |
| 小字 | **模板恒定串**（`模板锚点.json`，仓库外） | 50 张是同一模板、同一公司，公司名 / 字段名 / 运输注意事项这些**印刷内容恒定**，等于免费的现成真值 |
| 手写 | 人工转写（另见抽验记录） | 无自动真值 |

**为什么不收「编码 / 执行标准 / 储存条件 / 登记号」当小字真值**：它们逐张不同，
而 OCR 的错读会长出看起来合法的变体（`...01/2.0` 读成 `...02/4.0`），
无法区分「这张真印的是 02」还是「读错了」。用它们当真值会**把错的算成对的**。

## 比对方式：整段归一化后找子串

OCR 会把一行切碎（`品` 与 `名：` 分成两行），所以**不能按行比**。
做法是先把整段原文的空白全部去掉拼成一个串，再判断锚点是否为它的子串——
这样切碎也能对上。找不到时再用等长滑窗取最相似片段，算字符级相似度。

用法：
    python scripts/measure_text_tiers.py --samples-dir ~/Documents/M3R6样本 \
        --anchors ~/Documents/M3R6样本/模板锚点.json \
        --tier small --raw-dir 结果_small/识别原文
"""

from __future__ import annotations

import argparse
import csv
import difflib
import json
import os
import re
import sys

# 全部空白 + 常见分隔噪声。OCR 的换行/空格位置不稳定，比之前先去干净。
_WS = re.compile(r"\s+")


def norm(s: str) -> str:
    return _WS.sub("", s or "")


def best_similarity(haystack: str, needle: str) -> float:
    """``needle`` 与 ``haystack`` 里最相似等长片段的字符相似度（0~1）。

    整串找不到时才用——找不到往往是**读错了几个字**而不是整句没有，
    所以要给出「错了多少」而不只是「没命中」。
    """
    n = len(needle)
    if n == 0 or not haystack:
        return 0.0
    if n >= len(haystack):
        return difflib.SequenceMatcher(None, haystack, needle).ratio()
    sm = difflib.SequenceMatcher()
    sm.set_seq2(needle)
    best = 0.0
    for i in range(len(haystack) - n + 1):
        sm.set_seq1(haystack[i : i + n])
        r = sm.ratio()
        if r > best:
            best = r
            if best == 1.0:
                break
    return best


def load_truth(path: str) -> dict[str, dict]:
    """真值表 → {文件名: {字段: 真值}}。只取有大字真值的 5 列。"""
    out = {}
    with open(path, encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            out[row["文件名"].strip()] = row
    return out


def measure_small(raw_dir: str, anchors: list[dict]) -> dict:
    """小字：拿模板恒定串当真值，逐张比。"""
    files = sorted(os.listdir(raw_dir), key=lambda x: int(x.split(".")[0]))
    per_anchor = {a["key"]: {"hit": 0, "sim": []} for a in anchors}
    for fn in files:
        text = norm(open(os.path.join(raw_dir, fn), encoding="utf-8").read())
        for a in anchors:
            want = norm(a["text"])
            if want in text:
                per_anchor[a["key"]]["hit"] += 1
                per_anchor[a["key"]]["sim"].append(1.0)
            else:
                per_anchor[a["key"]]["sim"].append(best_similarity(text, want))
    return {"n": len(files), "per_anchor": per_anchor}


def measure_big(raw_dir: str, truth: dict[str, dict]) -> dict:
    """大字：5 个结构化字段，按真值表比（与 compare_accuracy 同口径）。"""
    from app.backends.c2_ocr import PaddleOCRBackend

    files = sorted(os.listdir(raw_dir), key=lambda x: int(x.split(".")[0]))
    fields = ("品名", "物料代码", "批号", "生产日期", "有效期至")
    stat = {f: {"hit": 0, "n": 0} for f in fields}
    rows = []
    for fn in files:
        key = fn.split(".")[0]
        t = truth.get(key)
        if not t:
            continue
        lines = open(os.path.join(raw_dir, fn), encoding="utf-8").read().split("\n")
        got = PaddleOCRBackend._extract(lines)
        # _extract 的键名 → 真值表的列名
        got_map = {
            "品名": got.get("product_name"),
            "物料代码": got.get("item_code"),
            "批号": got.get("batch_no"),
            "生产日期": got.get("manufacturing_date"),
            "有效期至": got.get("expiry_date"),
        }
        row = {"文件": key}
        for f in fields:
            tv, gv = (t.get(f) or "").strip(), (got_map[f] or "").strip()
            row[f] = f"{tv} | {gv}"
            if tv in ("", "—", "/"):
                continue
            stat[f]["n"] += 1
            if _date_like(tv) and _date_like(gv):
                ok = _ymd(tv)[: _gran(tv)] == _ymd(gv)[: _gran(tv)]
            else:
                ok = tv == gv
            stat[f]["hit"] += int(ok)
        rows.append(row)
    return {"stat": stat, "rows": rows}


def _date_like(s: str) -> bool:
    return bool(re.search(r"\d{4}", s or ""))


def _ymd(s: str) -> tuple:
    return tuple(int(x) for x in re.findall(r"\d+", s or ""))


def _gran(s: str) -> int:
    """真值印刷粒度：印到「日」就是 3，只到月就是 2。

    按真值粒度比对——标签只印到月的不因模型多给日而判错（与 compare_accuracy 同口径）。
    """
    return 3 if "日" in (s or "") else 2


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples-dir", required=True)
    ap.add_argument("--anchors", required=True)
    ap.add_argument("--tier", required=True)
    ap.add_argument("--raw-dir", required=True, help="相对 samples-dir 的识别原文目录")
    args = ap.parse_args()

    base = os.path.expanduser(args.samples_dir)
    raw_dir = os.path.join(base, args.raw_dir)
    if not os.path.isdir(raw_dir):
        print(f"找不到：{raw_dir}", file=sys.stderr)
        return 2

    anchors = json.load(open(os.path.expanduser(args.anchors), encoding="utf-8"))["小字"]
    truth = load_truth(os.path.join(base, "真值表.csv"))

    print(f"===== 档位 {args.tier} | {raw_dir} =====")
    print("\n-- 大字（5 个结构化字段，有真值）--")
    big = measure_big(raw_dir, truth)
    for f, s in big["stat"].items():
        acc = s["hit"] / s["n"] * 100 if s["n"] else 0
        print(f"   {f:8s} {s['hit']:3d}/{s['n']:<3d} = {acc:5.1f}%")

    print("\n-- 小字（模板恒定串当免费真值）--")
    small = measure_small(raw_dir, anchors)
    tot_hit = sum(v["hit"] for v in small["per_anchor"].values())
    tot_sim = sum(sum(v["sim"]) for v in small["per_anchor"].values())
    tot_n = small["n"] * len(anchors)
    for a in anchors:
        v = small["per_anchor"][a["key"]]
        avg = sum(v["sim"]) / len(v["sim"]) * 100 if v["sim"] else 0
        print(f"   {a['key']:20s} 整串命中 {v['hit']:2d}/{small['n']:<3d} 字符相似 {avg:5.1f}%  「{a['text'][:28]}」")
    print(f"   {'合计':20s} 整串命中 {tot_hit}/{tot_n} = {tot_hit/tot_n*100:.1f}%  "
          f"字符相似 {tot_sim/tot_n*100:.1f}%")

    with open(os.path.join(base, f"分档_{args.tier}.json"), "w", encoding="utf-8") as fh:
        json.dump({"tier": args.tier, "big": big["stat"], "small": small},
                  fh, ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    raise SystemExit(main())
