app_name = "hb_attendance_app"
app_title = "HBOS Attendance"
app_icon = "assets/hb_attendance_app/hbos-attendance-logo.svg"
app_publisher = "HBOS"
app_description = "HBOS attendance import and workspace"
app_email = "admin@example.com"
app_license = "MIT"
required_apps = ["frappe", "erpnext", "hrms"]
after_migrate = "hb_attendance_app.hbos_attendance.setup.after_migrate"

scheduler_events = {
    "cron": {
        "0 10 * * *": [
            "hb_attendance_app.hb_attendance_app.hbos_attendance.daily_feishu_sync.daily_sync_to_feishu"
        ]
    }
}
