"""Native organization preparation for the explicitly named isolated UAT Site.

No HTTP import endpoint, employee matcher, account creator or authorization
provider is registered here. Source rows and the reviewed mapping stay private.
"""
from __future__ import annotations

import hashlib
import json
import re

import frappe
from hbos_portal.iam import guards, policy
from hbos_portal.iam.demo_provider import require_isolated_site


def _root():
    require_isolated_site()
    if frappe.session.user != 'Administrator' or getattr(frappe.local, 'request', None):
        frappe.throw('组织准备只能由隔离站点的本机受控命令执行。', frappe.PermissionError)


def technical_ids(doctype, conf=None):
    conf = frappe.conf if conf is None else conf
    if conf.get('hbos_iam_test_site') not in (True, 1, '1'):
        return []
    key = {'Employee': 'hbos_iam_technical_employee_ids', 'Department': 'hbos_iam_technical_department_ids'}.get(doctype)
    values = conf.get(key) if key else None
    if not isinstance(values, list) or len(values) > 5000 or any(not isinstance(item, str) or not item or len(item) > 140 for item in values):
        return []
    return sorted(set(values))


def group_filter(doctype, group, conf=None):
    if group not in {'daily', 'technical', 'all'}:
        frappe.throw('请选择日常员工、技术验证夹具或全部。', frappe.ValidationError)
    ids = technical_ids(doctype, conf)
    return ids, bool(ids)


def filter_rows(rows, doctype, group='daily', name_field='name', conf=None):
    ids, available = group_filter(doctype, group, conf)
    if not available or group == 'all':
        return rows
    return [row for row in rows if (policy.value(row, name_field) in ids) == (group == 'technical')]


def validate_source_plan(company, nodes, source_sha256):
    if not re.fullmatch(r'[a-f0-9]{64}', str(source_sha256)):
        frappe.throw('缺少原件指纹。', frappe.ValidationError)
    if not isinstance(company, dict) or set(company) != {'name', 'abbr', 'country', 'default_currency'} or any(not isinstance(v, str) or not v.strip() for v in company.values()):
        frappe.throw('公司来源和原生必填配置不完整。', frappe.ValidationError)
    if not isinstance(nodes, list) or not 1 <= len(nodes) <= 200:
        frappe.throw('请提交已核对的有限组织树。', frappe.ValidationError)
    seen, labels = set(), set()
    for node in nodes:
        if not isinstance(node, dict) or set(node) != {'key', 'name', 'parent', 'is_group', 'source_rows'}:
            frappe.throw('组织节点字段不正确。', frappe.ValidationError)
        key, parent, label = node['key'], node['parent'], node['name']
        if not isinstance(key, str) or not isinstance(label, str) or not label.strip() or key in seen or label in labels or (parent and parent not in seen) or node['is_group'] not in {0, 1} or not isinstance(node['source_rows'], list) or not node['source_rows'] or any(not isinstance(row, int) or row < 3 for row in node['source_rows']):
            frappe.throw('组织节点存在重复、歧义或未确认的父级/源行。', frappe.ValidationError)
        seen.add(key); labels.add(label)
    for node in nodes:
        has_children = any(other['parent'] == node['key'] for other in nodes)
        if bool(node['is_group']) != has_children:
            frappe.throw('组织层级与叶子标记不一致。', frappe.ValidationError)


def native_organization_revision():
    payload = [frappe.get_all('Company', fields=['name', 'abbr', 'modified'], order_by='name'), frappe.get_all('Department', fields=['name', 'department_name', 'parent_department', 'company', 'is_group', 'modified'], order_by='name')]
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()


def apply_source_organization(company, nodes, source_sha256, expected_revision):
    _root(); validate_source_plan(company, nodes, source_sha256)
    from hbos_portal.auth.onboarding import serialize
    with serialize('iam-organization', 'site'):
        if native_organization_revision() != expected_revision:
            frappe.throw('原生组织已变化，请重新核对私有导入计划。', frappe.TimestampMismatchError)
        frappe.db.savepoint('iam_source_organization')
        try:
            matches = frappe.get_all('Company', filters={'name': company['name']}, fields=['name', 'abbr', 'country', 'default_currency'], limit_page_length=2)
            if len(matches) > 1 or matches and any(matches[0][key] != company[key] for key in ('abbr', 'country', 'default_currency')):
                frappe.throw('公司原生对象与已核对计划存在冲突。', frappe.ValidationError)
            if not matches:
                if frappe.db.exists('Company', {'abbr': company['abbr']}):
                    frappe.throw('公司缩写已被其他原生对象使用。', frappe.ValidationError)
                frappe.get_doc(dict(doctype='Company', company_name=company['name'], abbr=company['abbr'], country=company['country'], default_currency=company['default_currency'])).insert(ignore_permissions=True)
            mapping, created, reused = {}, [], []
            for node in nodes:
                parent = mapping[node['parent']] if node['parent'] else 'All Departments'
                rows = frappe.get_all('Department', filters={'company': company['name'], 'department_name': node['name']}, fields=['name', 'parent_department', 'is_group'], limit_page_length=2)
                if len(rows) > 1 or rows and (rows[0].parent_department != parent or bool(rows[0].is_group) != bool(node['is_group'])):
                    frappe.throw('部门原生对象存在同名或层级冲突，未改写已有对象。', frappe.ValidationError)
                if rows:
                    name = rows[0].name; reused.append(name)
                else:
                    doc = frappe.get_doc(dict(doctype='Department', department_name=node['name'], company=company['name'], parent_department=parent, is_group=node['is_group']))
                    doc.insert(ignore_permissions=True); name = doc.name; created.append(name)
                mapping[node['key']] = name
            return dict(mapping=mapping, created=created, reused=reused, company=company['name'], source_sha256=source_sha256)
        except Exception:
            frappe.db.rollback(save_point='iam_source_organization')
            raise
