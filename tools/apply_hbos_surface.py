"""给 6 个考勤 Desk 页面的根容器加上 hbos-surface class。

做法：在 make_app_page({...}); 之后插入一行 $(wrapper).addClass("hbos-surface")。
用脚本而非手改，是因为 6 个文件的插入点模式一致，手改容易漏。

幂等：已插入过就跳过。
"""
import pathlib
import re

BASE = pathlib.Path("apps/hb_attendance_app/hb_attendance_app/hbos_attendance/page")
PAGES = [
    "hbos_attendance_dashboard",
    "hbos_attendance_import",
    "hbos_department_board",
    "hbos_employee_management",
    "hbos_monthly_upload",
    "hbos_shift_management",
]
MARK = 'hbos-surface'
LINE = (
    '\n\t// HBOS 共享样式层的挂载点：只影响本容器内部，Desk 框架不受影响。\n'
    '\t$(wrapper).addClass("hbos-surface");\n'
)

for page in PAGES:
    js = next((BASE / page).glob("*.js"))
    src = js.read_text(encoding="utf-8")
    if MARK in src:
        print(f"  跳过（已有）: {page}")
        continue
    # 找到 make_app_page({ 的起止，插入到其后
    m = re.search(r"make_app_page\(\{(?:[^}]|\}(?!\);))*\}\);", src, re.S)
    if not m:
        print(f"  ⚠ 未找到插入点: {page}")
        continue
    src = src[: m.end()] + LINE + src[m.end():]
    js.write_text(src, encoding="utf-8")
    print(f"  ✓ 已插入: {page}")
