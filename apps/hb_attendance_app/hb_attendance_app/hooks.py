app_name = "hb_attendance_app"
app_title = "海滨考勤"
app_icon = "assets/hb_attendance_app/hbos-attendance-logo.svg"
app_publisher = "HBOS"
app_description = "海滨考勤：考勤机数据导入、中文报表、月度对账与异常处理"
app_email = "admin@example.com"
app_license = "MIT"
required_apps = ["frappe", "erpnext", "hrms"]
after_migrate = "hb_attendance_app.hbos_attendance.setup.after_migrate"

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
