"""Opt-in Gunicorn factory; importing the module does not open a Site.

Only a deployment that explicitly selects this factory installs the query
wrapper. No default environment, site_config or previous-file fallback exists.
"""
from .management_runtime import create_management_query_application


def create_application(configuration_path=None):
    from frappe.app import application
    return create_management_query_application(application, configuration_path=configuration_path)
