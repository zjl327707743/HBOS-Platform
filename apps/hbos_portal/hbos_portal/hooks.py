app_name = "hbos_portal"
app_title = "HBOS Portal"
app_publisher = "HBOS"
app_description = "HBOS workspace and portal platform shell"
app_email = "admin@example.com"
app_license = "MIT"

after_migrate = [
    "hbos_portal.auth.migration.migrate_identity_constraints",
    "hbos_portal.auth.export_policy.enforce_sensitive_export_boundary",
]
after_install = [
    "hbos_portal.auth.migration.migrate_identity_constraints",
    "hbos_portal.auth.export_policy.enforce_sensitive_export_boundary",
]
on_login = ["hbos_portal.auth.accounts.check_login"]
on_session_creation = ['hbos_portal.auth.security.on_session_creation']
auth_hooks = ['hbos_portal.auth.accounts.check_request']
before_request = ["hbos_portal.auth.accounts.check_request"]
on_logout = ["hbos_portal.auth.accounts.on_logout"]
doc_events = {
    "User": {"before_validate": "hbos_portal.auth.accounts.guard_document_password", "on_update": "hbos_portal.auth.accounts.user_updated"},
    "Social Login Key": {"validate": "hbos_portal.auth.migration.guard_social_login"},
    # UserType.on_update regenerates Custom DocPerm without writing `export`,
    # so saved rows fall back to that field's default of "1" and an ordinary
    # User Type save would re-open the bulk-export door between two migrations.
    # Re-assert the boundary as the last writer on every save.
    "User Type": {"on_update": "hbos_portal.auth.export_policy.on_user_type_update"},
}
override_whitelisted_methods = {
    "frappe.core.doctype.user.user.update_password": "hbos_portal.auth.accounts.update_password",
    "frappe.core.doctype.user.user.reset_password": "hbos_portal.auth.accounts.request_reset",
}
website_route_rules = [{"from_route": "/hbos/<path:app_path>", "to_route": "hbos"}]
scheduler_events = {"cron": {"*/5 * * * *": ["hbos_portal.auth.lifecycle.sync_disabled_members", 'hbos_portal.auth.operations.expire_operations']}}

# Business applications register their adapters through this custom hook:
#
# hbos_portal_provider = [
#     "some_app.portal.provider.get_provider"
# ]
#
# hbos_portal itself intentionally registers no business provider.
