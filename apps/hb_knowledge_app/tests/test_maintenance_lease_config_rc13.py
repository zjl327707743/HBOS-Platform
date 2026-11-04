"""RC13: the controller lease length is a bounded private config value.

The default remains 30 minutes. Drills and legitimately slow parsers may set a
different bound, but a malformed value must never silently shorten the lease.
"""
import sys
from types import ModuleType

_frappe = ModuleType('frappe')
def _whitelist(*a, **k):
    def decorator(fn):
        return fn
    return decorator
_frappe.whitelist = _whitelist
_frappe._ = lambda text: text
sys.modules['frappe'] = _frappe
sys.modules.setdefault('pymysql', ModuleType('pymysql'))
_cipher = ModuleType('cryptography.fernet'); _cipher.Fernet = lambda *a, **k: None
sys.modules.setdefault('cryptography', ModuleType('cryptography'))
sys.modules.setdefault('cryptography.fernet', _cipher)

from hb_knowledge_app.hb_knowledge.maintenance_api import (  # noqa: E402
    DEFAULT_LEASE_SECONDS, MAX_LEASE_SECONDS, MIN_LEASE_SECONDS, lease_seconds)


def test_default_is_thirty_minutes():
    assert DEFAULT_LEASE_SECONDS == 1800
    assert lease_seconds({}) == 1800
    assert lease_seconds({'maintenance_lease_seconds': None}) == 1800


def test_configured_lease_is_returned_within_bounds():
    assert lease_seconds({'maintenance_lease_seconds': MIN_LEASE_SECONDS}) == MIN_LEASE_SECONDS
    assert lease_seconds({'maintenance_lease_seconds': 15}) == 15
    assert lease_seconds({'maintenance_lease_seconds': MAX_LEASE_SECONDS}) == MAX_LEASE_SECONDS


def test_malformed_or_out_of_range_values_fall_back_to_default():
    for value in (0, 4, MAX_LEASE_SECONDS + 1, -5, '60', 60.0, True):
        assert lease_seconds({'maintenance_lease_seconds': value}) == DEFAULT_LEASE_SECONDS
