"""Standard logical knowledge spaces and copies of approved native templates."""
import copy
import hashlib
import hmac
import json
import secrets

import frappe

from .errors import KnowledgeError
from .maintenance_access import ROLE, require
from .maintenance_contract import DEPARTMENTS,normalized_department
from .service_http import canonical
from .shared_reference import configuration

FIELDS = ['name', 'title', 'required_role', 'enabled', 'maintenance_department',
          'maintenance_template', 'template_json', 'parent_space', 'space_admission_json']


def space_admission(row,cfg):
    key=cfg.get('fingerprint_key')
    if not isinstance(key,str) or len(key)<16:raise KnowledgeError('POLICY_UNAVAILABLE')
    body={name:row[name] for name in ('name','required_role','maintenance_department','parent_space')}
    return {**body,'signature':hmac.new(key.encode(),canonical(body).encode(),hashlib.sha256).hexdigest()}


def _roles():
    # Role revocation is effective immediately; do not reuse a browser profile.
    return {row[0] for row in frappe.db.sql('SELECT role FROM `tabHas Role` '
            'WHERE parent=%s AND parenttype=%s', (frappe.session.user, 'User'))}


def _space(space_id):
    row = frappe.db.get_value('HBOS Knowledge Space', space_id, FIELDS, as_dict=True)
    if not row or not row.get('enabled'):
        raise KnowledgeError('SCOPE_REJECTED')
    all_rows=frappe.get_all('HBOS Knowledge Space',filters={'enabled':1},fields=FIELDS,limit_page_length=100)
    if space_id not in approved_child_spaces(all_rows,configuration()):raise KnowledgeError('SCOPE_REJECTED')
    return row


def _department(row):
    explicit = row.get('maintenance_department')
    raw=row['name'].removeprefix('DEPT_')
    normalized=normalized_department(raw)
    return explicit or (normalized if normalized in DEPARTMENTS else raw.lower())


def can_manage_spaces(cfg, user, roles):
    managers = cfg.get('maintenance_space_manager_users')
    return (cfg.get('maintenance_space_creation_enabled') is True
            and isinstance(managers,list) and user in managers
            and ROLE in roles and cfg['reader_role'] in roles)


def _admin():
    require()
    if not can_manage_spaces(configuration(),frappe.session.user,_roles()):
        raise KnowledgeError('SCOPE_REJECTED')


def catalog():
    require()
    roles = _roles()
    rows = frappe.get_all('HBOS Knowledge Space', filters={'enabled': 1},
                         fields=FIELDS, order_by='title asc', limit_page_length=100)
    cfg=configuration()
    allowed=approved_child_spaces(rows,cfg)
    return {'can_manage_spaces':can_manage_spaces(cfg,frappe.session.user,roles),
            'spaces': [{'space_id': row['name'], 'title': row['title'],
                        'department': _department(row),
                        'template': row.get('maintenance_template') or 'auto',
                        'parent_space': row.get('parent_space')}
                       for row in rows if row['name'] in allowed and row['required_role'] in roles and _department(row) in DEPARTMENTS]}


def _templates(row, cfg):
    from .maintenance_native_upload import _profiles
    current = _profiles(cfg)
    if current is None:
        raise KnowledgeError('POLICY_UNAVAILABLE')
    try:
        selected = json.loads(row.get('template_json') or '{}') or current
    except ValueError:
        raise KnowledgeError('POLICY_UNAVAILABLE') from None
    # A copied template can only select an already locked approved profile.
    if selected != current:
        raise KnowledgeError('POLICY_UNAVAILABLE')
    return copy.deepcopy(selected)


def create(title, source_space_id):
    _admin()
    if not isinstance(title, str) or not 2 <= len(title.strip()) <= 120:
        raise KnowledgeError('INVALID_REQUEST')
    from .public_strings import safe_string
    title = safe_string(title.strip(), 120)
    parent = _space(source_space_id)
    if (parent['required_role'] not in _roles() or _department(parent) not in DEPARTMENTS
            or parent['required_role']!=configuration().get('reader_role')):
        raise KnowledgeError('SCOPE_REJECTED')
    profiles = _templates(parent, configuration())
    identifier = 'KBSPACE_' + secrets.token_hex(12)
    row = frappe.get_doc({'doctype': 'HBOS Knowledge Space', 'space_id': identifier,
        'title': title, 'required_role': parent['required_role'], 'enabled': 1,
        'maintenance_department': _department(parent),
        'maintenance_template': parent.get('maintenance_template') or 'auto',
        'template_json': canonical(profiles), 'parent_space': source_space_id})
    row.space_admission_json=canonical(space_admission({'name':identifier,'required_role':parent['required_role'],
        'maintenance_department':_department(parent),'parent_space':source_space_id},configuration()))
    row.insert(ignore_permissions=True)
    frappe.db.commit()
    return {'space_id': identifier, 'title': title, 'template_copied': True,
            'existing_write_dataset_reused': True, 'new_dataset_created': False,
            'required_role_changed': False}


def copy_template(space_id, source_space_id):
    _admin()
    target, source = _space(space_id), _space(source_space_id)
    if (target['required_role'] not in _roles() or source['required_role'] not in _roles()
            or _department(target) != _department(source)):
        raise KnowledgeError('SCOPE_REJECTED')
    profiles = _templates(source, configuration())
    frappe.db.set_value('HBOS Knowledge Space', space_id, {
        'maintenance_template': source.get('maintenance_template') or 'auto',
        'template_json': canonical(profiles)})
    frappe.db.commit()
    return {'space_id': space_id, 'template_copied': True,
            'applies_to': 'FUTURE_UPLOADS', 'existing_documents_reparsed': False}


def intake_space(cfg, space_id, department):
    require()
    selected = _space(space_id)
    if selected['required_role'] not in _roles() or _department(selected) != department:
        raise KnowledgeError('SCOPE_REJECTED')
    _templates(selected, cfg)
    return selected


def assign_space(planned, cfg, space_id, department):
    intake_space(cfg,space_id,department)
    for item in planned['items']:
        # A duplicate keeps the old logical identity and ACL; selecting another
        # space cannot copy an existing document into a different audience.
        if item['disposition'] != 'SAME_CONTENT_SKIP':
            item['space_id'] = space_id
    from knowledge_service.ingestion import canonical as native_canonical
    planned['batch_sha256'] = hashlib.sha256(native_canonical(
        {k: v for k, v in planned.items() if k != 'batch_sha256'})).hexdigest()


def approved_child_spaces(rows, cfg):
    """A standard clone retains its approved parent's role and template.

    This only admits a logical space. Source sharing, quality, current version,
    and publication still pass the ordinary fresh backend binding checks.
    """
    allowed=set(cfg['approved_space_ids'])
    if cfg.get('maintenance_space_creation_enabled') is not True:
        return allowed
    for _ in range(20):
        before=len(allowed)
        for row in rows:
            try:
                admission=json.loads(row.get('space_admission_json') or 'null')
                expected=space_admission(row,cfg)
                exact=isinstance(admission,dict) and admission.keys()==expected.keys() and all(
                    hmac.compare_digest(str(admission[k]),str(v)) for k,v in expected.items())
            except (ValueError,TypeError,KeyError,KnowledgeError):exact=False
            if (str(row.get('name','')).startswith('KBSPACE_')
                    and row.get('parent_space') in allowed
                    and row.get('required_role')==cfg['reader_role']
                    and row.get('maintenance_department') in DEPARTMENTS and exact):
                allowed.add(row['name'])
        if before==len(allowed):break
    return allowed
