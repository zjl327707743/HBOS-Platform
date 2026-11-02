"""Gate A2: native session age must be measured in the site's own timezone.

``tabSessions.lastupdate`` is written by Frappe's ``now()``, which is
``datetime.now(site_time_zone).replace(tzinfo=None)`` - a naive timestamp
already converted to the System Settings time zone. Attaching an optional
config value (defaulting to UTC) only computes the right age when the site
happens to be UTC. The site is Asia/Shanghai in the reference profile, so the
naive instant is eight hours ahead of UTC and the idle-expiry check never
fires for an abandoned session.
"""
import sys
from datetime import datetime, timedelta, timezone as dt_timezone
from types import ModuleType, SimpleNamespace
from zoneinfo import ZoneInfo

import pytest

from hb_knowledge_app.hb_knowledge.errors import KnowledgeError

SESSION_EXPIRY = 3600


class Row(dict):
    pass


def _load_module(monkeypatch):
    monkeypatch.setitem(sys.modules, 'pymysql', ModuleType('pymysql'))
    cipher = ModuleType('cryptography.fernet')
    cipher.Fernet = lambda *args: SimpleNamespace()
    monkeypatch.setitem(sys.modules, 'cryptography', ModuleType('cryptography'))
    monkeypatch.setitem(sys.modules, 'cryptography.fernet', cipher)

    portal_services = ModuleType('hbos_portal.services')
    internal = ModuleType('hbos_portal.services.internal_users')
    internal.classify_internal_user = lambda *a, **k: SimpleNamespace(allowed=True)
    monkeypatch.setitem(sys.modules, 'hbos_portal', ModuleType('hbos_portal'))
    monkeypatch.setitem(sys.modules, 'hbos_portal.services', portal_services)
    monkeypatch.setitem(sys.modules, 'hbos_portal.services.internal_users', internal)

    frappe_pkg = ModuleType('frappe')
    sessions = ModuleType('frappe.sessions')
    sessions.get_expiry_in_seconds = lambda value: SESSION_EXPIRY
    monkeypatch.setitem(sys.modules, 'frappe', frappe_pkg)
    monkeypatch.setitem(sys.modules, 'frappe.sessions', sessions)

    from hb_knowledge_app.hb_knowledge import frappe_authority
    # ``_native`` imports frappe lazily; bind the stub where the test can set
    # the site time zone reader on it.
    frappe_authority.frappe = frappe_pkg
    return frappe_authority


class Cur:
    """Answers the three SELECTs ``_native`` issues, keyed by the table."""

    def __init__(self, *, lastupdate, status='Active', enabled=1, blocked=0, version=0):
        self.lastupdate = lastupdate
        self.status = status
        self.enabled = enabled
        self.blocked = blocked
        self.version = version

    def execute(self, sql, args=()):
        text = ' '.join(sql.split())
        if 'FROM `tabSessions`' in text:
            if self.lastupdate is None:
                self._rows = []
            else:
                self._rows = [Row(user=args[1], sessiondata='{"creation":"C","hbos_security_version":0}',
                                  lastupdate=self.lastupdate, status=self.status)]
        elif 'FROM `tabUser`' in text:
            self._rows = [Row(enabled=self.enabled, user_type='System User')]
        elif 'FROM `tabHas Role`' in text:
            self._rows = [Row(role='HBOS Knowledge Reader')]
        elif 'FROM `tabHBOS Account Security`' in text:
            self._rows = [Row(security_version=self.version, blocked=self.blocked)]
        else:
            self._rows = []

    def fetchall(self):
        return self._rows


def _proofs(module, monkeypatch, *, now, site_zone, lastupdate, config_timezone='Asia/Shanghai',
            **row):
    """SessionProofs wired to a fixed clock and a site time zone."""
    monkeypatch.setattr(module.time, 'time', lambda: now)
    monkeypatch.setattr(module.frappe, 'get_system_settings',
                        lambda key: site_zone if key == 'time_zone' else None, raising=False)
    config = {'proof_key': 'K' * 32, 'sid_encryption_key': 'S' * 32, 'site': 'knowledge.test',
              'run_id': 'RUN_1', 'reader_role': 'HBOS Knowledge Reader', 'timezone': config_timezone,
              'internal_user_config': {}}
    proofs = module.SessionProofs(SimpleNamespace(), config)
    cur = Cur(lastupdate=lastupdate, **row)
    return proofs, cur


NOW = datetime(2026, 10, 23, 12, 0, tzinfo=dt_timezone.utc)


def test_idle_session_expires_when_the_site_is_ahead_of_utc(monkeypatch):
    module = _load_module(monkeypatch)
    site = ZoneInfo('Asia/Shanghai')
    # Session last touched 2h20m ago in site-local wall time; naive in the DB.
    stale = (NOW.astimezone(site) - timedelta(minutes=140)).replace(tzinfo=None)
    proofs, cur = _proofs(module, monkeypatch, now=NOW.timestamp(), site_zone='Asia/Shanghai',
                          lastupdate=stale)
    with pytest.raises(KnowledgeError) as caught:
        proofs._native(cur, 'SID', 'reader@example.test')
    assert caught.value.code == 'AUTHENTICATION_REQUIRED'


def test_active_session_inside_the_expiry_window_is_accepted(monkeypatch):
    module = _load_module(monkeypatch)
    site = ZoneInfo('Asia/Shanghai')
    fresh = (NOW.astimezone(site) - timedelta(minutes=5)).replace(tzinfo=None)
    proofs, cur = _proofs(module, monkeypatch, now=NOW.timestamp(), site_zone='Asia/Shanghai',
                          lastupdate=fresh)
    roles, generation = proofs._native(cur, 'SID', 'reader@example.test')
    assert roles == ('HBOS Knowledge Reader',)
    assert generation


def test_a_utc_site_keeps_the_same_boundary(monkeypatch):
    module = _load_module(monkeypatch)
    stale = (NOW - timedelta(minutes=62)).replace(tzinfo=None)
    proofs, cur = _proofs(module, monkeypatch, now=NOW.timestamp(), site_zone='UTC', lastupdate=stale)
    with pytest.raises(KnowledgeError):
        proofs._native(cur, 'SID', 'reader@example.test')


def test_missing_site_timezone_uses_frappes_own_default_not_the_config(monkeypatch):
    module = _load_module(monkeypatch)
    # Frappe's get_system_timezone() falls back to Asia/Kolkata when the site
    # has no time zone; the reader must make the same assumption.
    kolkata = ZoneInfo('Asia/Kolkata')
    stale = (NOW.astimezone(kolkata) - timedelta(minutes=140)).replace(tzinfo=None)
    proofs, cur = _proofs(module, monkeypatch, now=NOW.timestamp(), site_zone=None,
                          lastupdate=stale, config_timezone='UTC')
    with pytest.raises(KnowledgeError) as caught:
        proofs._native(cur, 'SID', 'reader@example.test')
    assert caught.value.code == 'AUTHENTICATION_REQUIRED'


def test_config_timezone_never_overrides_the_site(monkeypatch):
    module = _load_module(monkeypatch)
    site = ZoneInfo('Asia/Shanghai')
    stale = (NOW.astimezone(site) - timedelta(minutes=140)).replace(tzinfo=None)
    proofs, cur = _proofs(module, monkeypatch, now=NOW.timestamp(), site_zone='Asia/Shanghai',
                          lastupdate=stale, config_timezone='UTC')
    with pytest.raises(KnowledgeError):
        proofs._native(cur, 'SID', 'reader@example.test')


def test_blocked_account_is_rejected_regardless_of_session_age(monkeypatch):
    module = _load_module(monkeypatch)
    site = ZoneInfo('Asia/Shanghai')
    fresh = (NOW.astimezone(site) - timedelta(seconds=5)).replace(tzinfo=None)
    proofs, cur = _proofs(module, monkeypatch, now=NOW.timestamp(), site_zone='Asia/Shanghai',
                          lastupdate=fresh, blocked=1)
    with pytest.raises(KnowledgeError):
        proofs._native(cur, 'SID', 'reader@example.test')
