"""Local trusted-operator commands for HBOS IAM operability.

Run with the bench CLI, for example::

    bench --site owner-uat.localhost init-roles \
        --company "UAT-测试公司" --actor "ops:agent" --reason "初始化考勤三角色定义"

    bench --site owner-uat.localhost delegate-admin \
        --user uat-iam-admin@example.invalid --company "UAT-测试公司" \
        --actor "ops:agent" --reason "为合成 UAT 管理账号建立首个受限委派"

Both commands are preview-only unless ``--apply`` is passed. They never
publish roles, assign roles to employees, grant native ERPNext/HRMS roles, or
change feature flags. The CLI boundary is separate from a browser session: the
audit entry records the local operator and reason, not a completed web MFA.
"""
from __future__ import annotations

import json

import click
import frappe

from frappe.commands import pass_context


def _site(context) -> str:
    sites = getattr(context, "sites", None) or []
    if len(sites) != 1:
        raise click.UsageError("必须用 --site 指定且只指定一个目标 Site。")
    return sites[0]


def _run(context, callback):
    site = _site(context)
    frappe.init(site=site)
    frappe.connect()
    try:
        frappe.set_user("Administrator")
        result = callback()
        click.echo(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    finally:
        frappe.destroy()


@click.command("init-roles")
@click.option("--company", "companies", multiple=True, required=True, help="明确允许的角色管理公司；可重复。")
@click.option("--role", "role_keys", multiple=True, default=("staff", "clerk", "admin"), help="考勤角色 key；默认三种全部。")
@click.option("--actor", required=True, help="本机操作者标识，写入审计。")
@click.option("--reason", required=True, help="执行原因，写入审计。")
@click.option("--apply", is_flag=True, default=False, help="真正执行；不加时只输出预览计划。")
@pass_context
def init_roles(context, companies, role_keys, actor, reason, apply):
    """Create missing attendance role definitions (draft only)."""

    def callback():
        from hbos_portal.iam import role_init

        return role_init.initialize(companies, role_keys, actor=actor, reason=reason, dry_run=not apply)

    _run(context, callback)


@click.command("delegate-admin")
@click.option("--user", "user", required=True, help="具名、非 Administrator 的合成管理账号。")
@click.option("--company", "company", required=True, help="该委派明确覆盖的一个公司。")
@click.option("--actor", required=True, help="本机操作者标识，写入审计。")
@click.option("--reason", required=True, help="执行原因，写入审计。")
@click.option("--apply", is_flag=True, default=False, help="真正执行；不加时只输出预览计划。")
@pass_context
def delegate_admin(context, user, company, actor, reason, apply):
    """Grant the first company-scoped IAM management delegation to one user."""

    def callback():
        from hbos_portal.iam import role_init

        return role_init.delegate_admin(user, company, actor=actor, reason=reason, dry_run=not apply)

    _run(context, callback)


commands = [init_roles, delegate_admin]
