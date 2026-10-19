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
# class 的容器；Desk 的侧边栏、顶栏与原生控件不受影响。样式只此一份。
app_include_css = "hbos_attendance.bundle.css"

# 给「本 App 的报表 / 列表」补上 `.hbos-surface` 挂载点，使上面那份 CSS 生效。
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
        "*/10 * * * *": [
            "hb_attendance_app.hbos_attendance.api.sync_delicloud_checkin"
        ],
        "*/30 * * * *": [
            "hb_attendance_app.hbos_attendance.api.sync_from_bitable",
            "hb_attendance_app.hbos_attendance.api.sync_overtime_from_bitable",
            # 调休业务有严格先后依赖，统一由单一编排入口顺序执行。
            "hb_attendance_app.hbos_attendance.sync_rest_leave.sync_rest_leave_pipeline",
        ],
    }
}


# HBOS Portal experience provider.
# Attendance owns access and implementation routing; Portal only consumes the contract.
hbos_portal_provider = [
    "hb_attendance_app.hbos_attendance.portal.provider.get_provider",
]

# IAM is an explicit Site rollout. With its flag off, existing native HR
# boundaries remain unchanged; no ordinary IAM reader receives an HR role.
permission_query_conditions = {
    "Employee Checkin": "hb_attendance_app.hbos_attendance.portal.permissions.query_conditions",
    "Attendance": "hb_attendance_app.hbos_attendance.portal.permissions.query_conditions",
    "Prepared Report": "hb_attendance_app.hbos_attendance.portal.permissions.prepared_report_query_conditions",
    "File": "hb_attendance_app.hbos_attendance.portal.permissions.file_query_conditions",
}
has_permission = {
    "Employee Checkin": "hb_attendance_app.hbos_attendance.portal.permissions.has_permission",
    "Attendance": "hb_attendance_app.hbos_attendance.portal.permissions.has_permission",
    "Prepared Report": "hb_attendance_app.hbos_attendance.portal.permissions.prepared_report_has_permission",
    "File": "hb_attendance_app.hbos_attendance.portal.permissions.file_has_permission",
}
doc_events = {
    "Prepared Report": {
        "before_insert": "hb_attendance_app.hbos_attendance.portal.permissions.guard_prepared_report",
        "before_validate": "hb_attendance_app.hbos_attendance.portal.permissions.guard_prepared_report",
        "on_trash": "hb_attendance_app.hbos_attendance.portal.permissions.guard_prepared_report",
    },
    "File": {
        "before_insert": "hb_attendance_app.hbos_attendance.portal.permissions.guard_file",
        "before_validate": "hb_attendance_app.hbos_attendance.portal.permissions.guard_file",
        "on_trash": "hb_attendance_app.hbos_attendance.portal.permissions.guard_file",
    },
}
before_request = ["hb_attendance_app.hbos_attendance.portal.permissions.check_request"]
before_job = ["hb_attendance_app.hbos_attendance.portal.permissions.check_background_job"]
