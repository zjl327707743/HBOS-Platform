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
        "",
        f"【员工】{emp.get('name','')} 工号{emp.get('num','')} 部门{emp.get('dept','')}",
        f"【班次规则】{rule_line}",
        f"【打卡流水】\n{checkin_lines}",
        "",
        "待复核异常（每行一条）：",
    ]
    for d, t in anomaly_items:
        lines.append(f"{d}|{t}")
    lines.append("输出：")
    return "\n".join(lines)


def parse_review(text, anomaly_keys):
    """解析 LLM 输出。返回 {date_str: "结论：理由"}。

    - 只保留 date 在 anomaly_keys 中的行
    - 跳过无 | 的行；结论非法时回落「存疑」
    - 输出行数截断到 anomaly_keys 数内
    """
    if not text:
        return {}
    out = {}
    for line in text.splitlines():
        line = line.strip()
        if "|" not in line:
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 4:
            continue
        date_str, typ, verdict, reason = parts[0], parts[1], parts[2], "".join(parts[3:])
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
        "max_tokens": 1200,
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
