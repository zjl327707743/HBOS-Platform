"""月度考勤汇总 AI 复核：事实包/prompt/返回解析（纯函数，无顶层 frappe 依赖可离线测试）。

LLM 走 OpenAI 兼容协议，配置走 env（HBOS_AI_BASE_URL / HBOS_AI_API_KEY /
HBOS_AI_MODEL / HBOS_AI_TIMEOUT），不入 git 不入库。
AI 只生成复核意见文本，不改写考勤结果、不落库。
结论枚举：属实 / 存疑 / 非异常。
"""
import os

CONCLUSIONS = ("属实", "存疑", "非异常")

# 单批复核上限（人）：同步逐人调 LLM 放进单次报表请求，须限制在代理/浏览器
# 可接受耗时内（PROXY_READ_TIMEOUT=120s）。超出提示分批/缩小范围。
AI_BATCH = 20

# 单批总时间预算（秒）：串行逐人调用若每人 ≤60s，20 人最坏 1200s 远超代理
# 120s。此预算防止整个请求超时被切断——累计超预算后不再发起新调用，
# 剩余员工标记未复核（不产生费用、请求可正常返回）。
AI_BATCH_SECONDS = 100

# 单次调用的输出预算（token）。
#
# **必须给推理留余量**：当前模型 deepseek-flash 是推理模型，它的 thinking
# 计入 max_tokens。实测——缺勤类 prompt 下 reasoning 会烧掉全部 1200 token
# （finish_reason=length），content 返回空串，复核结果变成「无有效返回」。
# 提到 4096 给推理留出空间；prompt 本身已尽量去掉诱发长推理的因素
# （见 build_prompt 里写死星期的那段）。
AI_MAX_TOKENS = 4096

# 中文星期，用于把「目标日期是星期几」直接写进 prompt
_WEEKDAYS = ("星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日")


def weekday_cn(date_str):
    """YYYY-MM-DD → 「2026-10-07（星期三）」。非法输入原样返回。

    为什么要把星期写进 prompt：班次规则里会出现「周末双休」这类表述，
    模型于是**自己去推算目标日期是星期几**——实测它在 prompt 里反复演算
    「2026 年 1 月 1 日是星期几」，把输出预算全部耗在推理上，正文返回空。
    这是模型最不该花力气的地方：日期与其星期是给定事实，直接喂给它即可。
    """
    from datetime import date

    try:
        y, m, d = (int(x) for x in str(date_str).split("-")[:3])
        return f"{date_str}（{_WEEKDAYS[date(y, m, d).weekday()]}）"
    except Exception:
        return str(date_str)


def env_config():
    """读取 AI 配置。缺失项为空字符串，由调用方判断并 throw。"""
    try:
        timeout = int(os.environ.get("HBOS_AI_TIMEOUT", "60"))
    except ValueError:
        timeout = 60
    return {
        "base_url": (os.environ.get("HBOS_AI_BASE_URL") or "").rstrip("/"),
        "api_key": os.environ.get("HBOS_AI_API_KEY") or "",
        "model": os.environ.get("HBOS_AI_MODEL") or "",
        "timeout": timeout,
    }


def build_prompt(emp, anomaly_items, checkin_lines, rule_line):
    """构造发给 LLM 的复核 prompt。

    emp: {"name","num","dept"}
    anomaly_items: [(date_str, "迟到|早退|缺勤"), ...]
    checkin_lines / rule_line: 字符串（含换行的事实文本）
    """
    lines = [
        "你是海滨考勤审核助手。对每条被系统判为异常的考勤记录给复核结论。",
        "逐条输出，格式严格为：日期|类型|结论|理由",
        "结论取值仅限：属实 / 存疑 / 非异常（非异常=系统误判，须给出依据）。",
        "类型取值：迟到 / 早退 / 缺勤。",
        "日历事实已在下文给出，无需推算。直接逐条作答，不要展开推理过程。",
        "",
        f"【员工】{emp.get('name','')} 工号{emp.get('num','')} 部门{emp.get('dept','')}",
        f"【班次规则】{rule_line}",
        f"【打卡流水】\n{checkin_lines}",
        "",
        "待复核异常（每行一条，日期后已注明星期）：",
    ]
    # 日期与星期一并给出：模型自己推星期会烧光输出预算（见 weekday_cn 的说明）。
    for d, t in anomaly_items:
        lines.append(f"{weekday_cn(d)}|{t}")
    lines.append("输出：")
    return "\n".join(lines)


def parse_review(text, anomaly_keys):
    """解析 LLM 输出。返回 {date_str: "结论：理由"}。

    - 只保留 date 在 anomaly_keys 中的行
    - 跳过无 | 的行；结论非法时回落「存疑」
    - 输出行数截断到 anomaly_keys 数内

    **日期要做归一化**：prompt 里给的是「2026-10-07（星期三）」，模型可能
    原样回抄也可能只回 `2026-10-07`，还可能回 `10-07`。三种都要能对上
    anomaly_keys（那里是 `YYYY-MM-DD`），否则整批结果全被当成「不在待复核集里」
    而丢弃——那是静默丢结果，比报错更难查。
    """
    if not text:
        return {}

    def norm(value):
        raw = str(value).strip()
        # 先砍掉「（星期三）」「(周三)」这类后缀
        for sep in ("（", "("):
            if sep in raw:
                raw = raw.split(sep, 1)[0]
        raw = raw.strip()
        if raw in anomaly_keys:
            return raw
        # 只回 MM-DD 时，用 anomaly_keys 里的年份补全（同一次复核必属同一区间）
        if len(raw) == 5 and raw[2] == "-":
            for key in anomaly_keys:
                if key.endswith("-" + raw):
                    return key
        return raw

    out = {}
    for line in text.splitlines():
        line = line.strip()
        if "|" not in line:
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 4:
            continue
        date_str = norm(parts[0])
        typ, verdict, reason = parts[1], parts[2], "".join(parts[3:])
        if date_str not in anomaly_keys:
            continue
        if verdict not in CONCLUSIONS:
            verdict = "存疑"
        out[date_str] = f"{verdict}：{reason}"
        if len(out) >= len(anomaly_keys):
            break
    return out


def call_llm(cfg, prompt):
    """调用 OpenAI 兼容接口，返回模型文本。失败抛中文异常。"""
    import frappe
    if not (cfg["base_url"] and cfg["api_key"] and cfg["model"]):
        frappe.throw("未配置 AI（HBOS_AI_BASE_URL / HBOS_AI_API_KEY / HBOS_AI_MODEL）")
    import requests
    url = f"{cfg['base_url']}/chat/completions"
    headers = {"Authorization": f"Bearer {cfg['api_key']}", "Content-Type": "application/json"}
    body = {
        "model": cfg["model"],
        "messages": [{"role": "system", "content": "你是海滨考勤审核助手，输出严格按用户要求格式。"},
                     {"role": "user", "content": prompt}],
        "temperature": 0,
        # 推理模型的 thinking 计入 max_tokens；预算过小会让正文返回空串
        # （实测 1200 时 reasoning 吃满、content 为空）。见 AI_MAX_TOKENS。
        "max_tokens": AI_MAX_TOKENS,
    }
    try:
        resp = requests.post(url, json=body, headers=headers, timeout=cfg["timeout"])
    except Exception as e:
        frappe.throw(f"AI 调用失败：{e}")
    if resp.status_code != 200:
        frappe.throw(f"AI 返回异常：HTTP {resp.status_code} {resp.text[:200]}")
    try:
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    except Exception:
        frappe.throw("AI 返回格式无法解析")
