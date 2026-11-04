"""Allowlisted OAuth facts; never serialize provider payloads or credentials."""
from __future__ import annotations

import json
import os
import secrets
import stat
from datetime import datetime, timezone
from pathlib import Path

import frappe


def new_trace() -> dict:
    version = {}
    try:
        release = json.loads(Path('/opt/hbos-release/release.json').read_text())
        version = {k: release.get(k) for k in ('source_commit', 'build_id')}
    except (OSError, ValueError):
        pass
    return {'id': secrets.token_hex(8), 'at': datetime.now(timezone.utc).isoformat(),
        'site': frappe.local.site, **version, 'calls': [], 'facts': {}, 'result': 'pending'}


def safe_http(response, stage: str, trace: dict | None):
    if trace is not None:
        status = getattr(response, 'status_code', None)
        code = None
        try:
            value = response.json()
            raw = value.get('code') if isinstance(value, dict) else None
            code = str(raw) if raw is not None and str(raw).isdigit() and len(str(raw)) <= 12 else None
        except (ValueError, AttributeError):
            pass
        trace['calls'].append({'stage': stage, 'http': status if isinstance(status, int) else None, 'api_code': code})
    return response


def shape(value) -> dict:
    return {'present': value is not None, 'type': type(value).__name__,
        'judgement': 'true' if value is True else 'false' if value is False else 'unknown'}


def persist(trace: dict) -> None:
    # Callers add only fixed booleans/field shapes, never identity values.
    path = Path(frappe.get_site_path('private', 'hbos_feishu_diagnostics.jsonl'))
    try:
        if path.exists():
            info = path.lstat()
            if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077 or info.st_uid != os.geteuid():
                return
        fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT | getattr(os, 'O_NOFOLLOW', 0), 0o600)
        with os.fdopen(fd, 'w') as f:
            f.write(json.dumps(trace, ensure_ascii=False, separators=(',', ':')) + '\n')
    except OSError:
        # Diagnostic storage cannot create a permissive fallback or change auth.
        pass
