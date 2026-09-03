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
        "0 10 * * *": [
            "hb_attendance_app.hbos_attendance.daily_feishu_sync.daily_sync_to_feishu"
        ],
        "*/10 * * * *": [
            "hb_attendance_app.hbos_attendance.api.sync_delicloud_checkin"
        ],
        "*/30 * * * *": [
            "hb_attendance_app.hbos_attendance.api.sync_from_bitable",
            "hb_attendance_app.hbos_attendance.api.sync_overtime_from_bitable",
        ],
    }
}
