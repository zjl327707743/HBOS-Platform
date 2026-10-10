"""Fixed managed fact commands, closed without the trusted HTTP WSGI boundary."""
import frappe

from hbos_portal.organization.management_http import execute_request
from hbos_portal.organization.management_query_http import execute_query


@frappe.whitelist(methods=["POST"])
def create_position(**kwargs):
    return execute_request("create_position")


@frappe.whitelist(methods=["POST"])
def update_position(**kwargs):
    return execute_request("update_position")


@frappe.whitelist(methods=["POST"])
def create_assignment(**kwargs):
    return execute_request("create_assignment")


@frappe.whitelist(methods=["POST"])
def update_assignment(**kwargs):
    return execute_request("update_assignment")


@frappe.whitelist(methods=["GET"])
def get_management_context(**kwargs):
    return execute_query("get_management_context")


@frappe.whitelist(methods=["GET"])
def list_positions(**kwargs):
    return execute_query("list_positions")


@frappe.whitelist(methods=["GET"])
def get_person_assignments(**kwargs):
    return execute_query("get_person_assignments")


@frappe.whitelist(methods=["GET"])
def lookup_people(**kwargs):
    return execute_query("lookup_people")
