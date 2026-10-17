"""Idempotent migration of four lifecycle state fields, never password data."""
from __future__ import annotations


def migrate():
    import frappe
    from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
    definitions = [
        {'fieldname': 'hbos_initial_password_pending', 'label': 'Initial password pending', 'fieldtype': 'Check', 'default': '0'},
        {'fieldname': 'hbos_temporary_password', 'label': 'Temporary password state', 'fieldtype': 'Check', 'default': '0'},
        {'fieldname': 'hbos_temporary_password_expires_at', 'label': 'Temporary password expires at', 'fieldtype': 'Datetime'},
        {'fieldname': 'hbos_password_generation', 'label': 'Password generation', 'fieldtype': 'Int', 'default': '0'},
    ]
    for definition in definitions:
        definition.update(hidden=1, read_only=1, no_copy=1, allow_on_submit=0)
    create_custom_fields({'User': definitions}, update=True)
    if frappe.db.table_exists('HBOS IAM Policy'):
        frappe.db.add_unique('HBOS IAM Policy', ['subject_type', 'subject_name'], constraint_name='hbos_iam_subject_unique')
    if frappe.db.table_exists('HBOS IAM Rule'):
        frappe.db.add_index('HBOS IAM Rule', ['parent', 'app_id', 'operation_id'], index_name='hbos_iam_rule_lookup')
    if frappe.db.table_exists('Employee'):
        # Current reads must target account/department ranges rather than scan
        # and next-key-lock the whole native Employee primary index. These are
        # non-unique: no existing identity association or empty value is changed.
        frappe.db.add_index('Employee', ['user_id'], index_name='hbos_iam_employee_user_lookup')
        frappe.db.add_index('Employee', ['department'], index_name='hbos_iam_employee_department_lookup')
    frappe.clear_cache(doctype='User')
