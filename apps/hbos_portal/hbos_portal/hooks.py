app_name = "hbos_portal"
app_title = "HBOS Portal"
app_publisher = "HBOS"
app_description = "HBOS workspace and portal platform shell"
app_email = "admin@example.com"
app_license = "MIT"

after_migrate = ["hbos_portal.auth.migration.migrate_identity_constraints"]
after_install = "hbos_portal.auth.migration.migrate_identity_constraints"
on_login = ["hbos_portal.auth.accounts.check_login"]
before_request = ["hbos_portal.auth.accounts.check_request"]
on_logout = ["hbos_portal.auth.accounts.on_logout"]
doc_events = {
    "User": {"before_validate": "hbos_portal.auth.accounts.guard_document_password", "on_update": "hbos_portal.auth.accounts.user_updated"},
    "Social Login Key": {"validate": "hbos_portal.auth.migration.guard_social_login"},
}
override_whitelisted_methods = {
    "frappe.core.doctype.user.user.update_password": "hbos_portal.auth.accounts.update_password",
    "frappe.core.doctype.user.user.reset_password": "hbos_portal.auth.accounts.request_reset",
}
website_route_rules = [{"from_route": "/hbos/<path:app_path>", "to_route": "hbos"}]
scheduler_events = {"cron": {"*/5 * * * *": ["hbos_portal.auth.lifecycle.sync_disabled_members"]}}

# Business applications register their adapters through this custom hook:
#
# hbos_portal_provider = [
#     "some_app.portal.provider.get_provider"
# ]
#
# hbos_portal itself intentionally registers no business provider.
