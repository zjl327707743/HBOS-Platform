app_name = "hb_attendance_app"
app_title = "海滨考勤"
app_icon = "assets/hb_attendance_app/hbos-attendance-logo.svg"
app_publisher = "HBOS"
app_description = "海滨考勤：考勤机数据导入、中文报表、月度对账与异常处理"
app_email = "admin@example.com"
app_license = "MIT"
required_apps = ["frappe", "erpnext", "hrms"]
after_migrate = "hb_attendance_app.hbos_attendance.setup.after_migrate"

# HBOS 业务页面共享样式层。所有规则限定在 `.hbos-surface` 下，只影响显式加了该
# class 的容器；Desk 的侧边栏、顶栏与原生控件不受影响（EA-4 §38 要求 Management
# Console 保留自身身份）。样式只此一份——6 个页面各抄一遍色值必然漂移。
app_include_css = "hbos_attendance.bundle.css"

# 报表与 DocType 列表页不是我们的代码（Frappe 的视图工厂生成），不会自己挂
# `.hbos-surface`。这个小脚本按路由给「本 App 的报表 / 列表」补上挂载点，
# 于是上面那份 CSS 自然生效，无需在 bundle 里再抄一遍报表样式。
# 其余 app 的页面不受影响。
app_include_js = "hbos_attendance.bundle.js"

scheduler_events = {
    "cron": {
        # 考勤通知：北京时间 09:00（Frappe 系统时区为 Asia/Shanghai，cron 按本地时区判定，
        # 已实测 "0 10 * * *" 的下次执行为本地 10:00）。
        # 只挂一条：Scheduled Job Type 以 method 为唯一键，同一方法挂多条会互相覆盖，
        # 谁胜出取决于遍历顺序——若被覆盖成非 9 点的时刻，守卫会拒发且悄无声息。
        "0 9 * * *": [
            "hb_attendance_app.hbos_attendance.attendance_notify.send_daily_report"
        ],
        "0 10 * * *": [
            "hb_attendance_app.hbos_attendance.daily_feishu_sync.daily_sync_to_feishu"
        ],
        "*/10 * * * *": [
            "hb_attendance_app.hbos_attendance.api.sync_delicloud_checkin"
        ],
        "*/30 * * * *": [
            "hb_attendance_app.hbos_attendance.api.sync_from_bitable",
            "hb_attendance_app.hbos_attendance.api.sync_overtime_from_bitable",
            # 调休三段：同步 → LLM 解析加班日 → 核实（顺序固定，解析依赖同步刚落的记录）
            "hb_attendance_app.hbos_attendance.sync_rest_leave.sync_rest_leave_from_bitable",
            "hb_attendance_app.hbos_attendance.sync_rest_leave.parse_pending_rest_leaves",
            "hb_attendance_app.hbos_attendance.sync_rest_leave.verify_pending_rest_leaves",
        ],
    }
}


# HBOS Portal experience provider.
# Attendance owns access and implementation routing; Portal only consumes the contract.
hbos_portal_provider = [
    "hb_attendance_app.hbos_attendance.portal.provider.get_provider",
]
