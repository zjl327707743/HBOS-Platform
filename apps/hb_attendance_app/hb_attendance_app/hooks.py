app_name = "hb_attendance_app"
app_title = "HBOS Attendance"
app_publisher = "HBOS"
app_description = "Lightweight HBOS attendance import app"
app_email = "admin@example.com"
app_license = "MIT"
required_apps = ["frappe", "erpnext", "hrms"]
after_migrate = "hb_attendance_app.hbos_attendance.setup.after_migrate"
