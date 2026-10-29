"""RC13 batch import: read-only preview, idempotent submit, fenced progress.

Scope of this round (owner decision, honest boundary): a manifest names source
files whose bytes are already registered in the maintenance registry as uploaded
originals (the 122-item priority queue). Each item also carries its verified
page-level text and page evidence, so the preview can classify it without
touching the database, and submit can freeze a local-full-text derivative batch
with the same semantics RC12 used: one immutable batch per department/dataset
group, at most four documents per native job, state.dataset_id preserved from
the existing uploaded original.

An item whose source hash is not a known uploaded original is reported as
``NEW_UPLOAD_REQUIRED`` (the single-file upload flow stays the supported path for
new files in this round). A business replacement still needs the original parse
flow and a technical repair still needs the native prepare flow; both are shown
in the preview with ``submittable: false`` and a reason instead of being queued.

Lease fencing: ``job_json.lease_generation`` is incremented by every claim and
every expired-lease reclaim. ``progress`` must echo the current generation, so a
worker that lost its lease can never write into a reclaimed batch. Reclaim never
rewrites item states in bulk - it only requeues that one batch.

Retrieval receipts: a real employee search writes a ``History`` activity row and
issuing evidence puts a short-lived evidence id in the server cache. The
``record_retrieval_verified`` endpoint verifies those two server-side facts (it
never trusts a browser checkbox) and then writes
``quality_json[version].retrieval_verified``. Withdrawal or a newer current
version invalidates the display without deleting the historical receipt.
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import secrets
import shutil
import time
from contextlib import contextmanager
from pathlib import Path, PurePosixPath

import frappe

from .errors import KnowledgeError
from .maintenance_contract import (DEPARTMENTS, configured_max_source_bytes,
                                   normalized_department, require_source_size,
                                   source_size_budget)
from .service_http import canonical
from . import maintenance as m

TABLE = m.TABLE
PLAN_SCHEMA = 'rc13-batch-plan-v1'
SUBMIT_SCHEMA = 'rc13-batch-submit-v1'
VERIFICATION_SCHEMA = 'rc13-retrieval-verified-v1'
DERIVATIVE_SCOPE = 'EXACT_SHA_PAGE_COMPLETE_LOCAL_FULLTEXT_V1'
MANIFEST_SCHEMA = 2
MAX_ITEMS = 64
MAX_LABEL = 160
MAX_APPROVAL = 200
MAX_PAGE_METHODS = 200
MAX_PAGE_TEXT = 20000
MAX_TOTAL_TEXT = 8_000_000
MAX_PLAN_MANIFEST_BYTES = 32 * 1024 * 1024
MAX_ITEM_PAGES = 10000
LEASE_SECONDS = 1800
MAX_RECLAIM_HISTORY = 20
VERIFICATION_WINDOW_SECONDS = 1800
HEX64 = re.compile(r'[0-9a-f]{64}')
PHYSICAL_ID = re.compile(r'[0-9a-f]{32}')
DOCUMENT_ID = re.compile(r'DOC_[0-9a-f]{24}')
VERSION_ID = re.compile(r'VER_[0-9a-f]{24}')
BATCH_ID = re.compile(r'IMP_[0-9a-f]{32}')
SOURCE_EXTENSIONS = {'.doc', '.docx', '.pdf', '.xlsx', '.pptx', '.txt', '.md'}
DERIVATIVE_EXTENSIONS = {'.doc', '.docx', '.pdf', '.xlsx', '.pptx', '.md'}
PAGE_METHODS = {'native', 'cached_ocr', 'cached_ocr_sparse', 'local_fulltext',
                'local_ocr', 'office_text', 'symbol_normalized', 'ocr'}
PAGE_CHECK_KEYS = {'quality_pass', 'visual_review', 'sparse_pages', 'gap_pages'}
HINTS = {'NEW', 'BUSINESS_UPDATE', 'TECHNICAL_REPAIR'}
PUBLISHED_OUTCOMES = {'PUBLISHED', 'REPLACED', 'RESTORED', 'REPAIRED'}
SAFE_ITEM_ERRORS = {'PARSE_FAILED', 'SOURCE_CHANGED', 'EXECUTOR_STOPPED',
                    'RECONCILIATION_REQUIRED', 'UNKNOWN_ENQUEUE_OUTCOME_REQUIRES_TASK_RECONCILIATION'}
MANIFEST_KEYS = {'schema_version', 'department', 'label', 'sharing_confirmed', 'items'}
ITEM_KEYS = {'source_sha256', 'canonical_source_path', 'relative_path', 'department',
             'pages', 'page_methods', 'page_checks', 'disposition_hint', 'replace', 'repair'}
REPLACE_KEYS = {'canonical_document_id', 'expected_current_version'}
REPAIR_KEYS = {'parent_batch_id', 'parent_version_id', 'reason'}
DISPOSITION_KEYS = {'NEW': 'new', 'DUPLICATE': 'duplicate', 'BUSINESS_UPDATE': 'business_update',
                    'TECHNICAL_REPAIR': 'technical_repair',
                    'NEW_UPLOAD_REQUIRED': 'new_upload_required', 'ANOMALY': 'anomaly'}


# ---------------------------------------------------------------- configuration
def _config():
    from .shared_reference import configuration
    return configuration()


def _batch_root(cfg):
    raw = cfg.get('maintenance_batch_root')
    if not raw:
        upload = cfg.get('maintenance_upload_root')
        if not isinstance(upload, str) or not upload:
            raise KnowledgeError('POLICY_UNAVAILABLE')
        raw = str(Path(upload) / 'batch')
    if not isinstance(raw, str) or not raw:
        raise KnowledgeError('POLICY_UNAVAILABLE')
    base = Path(raw)
    if not base.is_absolute() or base.is_symlink():
        raise KnowledgeError('POLICY_UNAVAILABLE')
    base.mkdir(parents=True, exist_ok=True, mode=0o700)
    return base


def _derivative_root(cfg):
    """Host-shared directory: source copies + derivatives for the native worker.

    It must be the same directory the host controller uses as ``private_work`` so
    the controller finds ``<batch_id>/derivatives/<version_id>.txt`` next to its
    own ``state.json``. Submitting without it must fail, never pretend success.
    """
    raw = cfg.get('maintenance_derivative_root')
    if not isinstance(raw, str) or not raw:
        raise KnowledgeError('BATCH_DERIVATIVE_ROOT_UNCONFIGURED')
    base = Path(raw)
    if not base.is_absolute() or base.is_symlink() or not base.is_dir():
        raise KnowledgeError('BATCH_DERIVATIVE_ROOT_UNCONFIGURED')
    if not os.access(base, os.W_OK):
        raise KnowledgeError('BATCH_DERIVATIVE_ROOT_UNCONFIGURED')
    return base


def _approved_roots(cfg):
    raw = cfg.get('maintenance_batch_source_roots')
    if not isinstance(raw, list) or not 1 <= len(raw) <= 8:
        raise KnowledgeError('POLICY_UNAVAILABLE')
    roots = []
    for value in raw:
        if not isinstance(value, str) or not value:
            raise KnowledgeError('POLICY_UNAVAILABLE')
        path = Path(value)
        if not path.is_absolute() or path.is_symlink() or not path.is_dir():
            raise KnowledgeError('POLICY_UNAVAILABLE')
        roots.append(path.resolve())
    return roots


def batch_available():
    """True when the private preview/derivative roots are configured (read-only)."""
    try:
        cfg = _config()
    except (KnowledgeError, OSError):
        return False
    roots = cfg.get('maintenance_batch_source_roots')
    where = cfg.get('maintenance_batch_root') or cfg.get('maintenance_upload_root')
    derivative = cfg.get('maintenance_derivative_root')
    return (isinstance(roots, list) and 1 <= len(roots) <= 8
            and all(isinstance(value, str) and value for value in roots)
            and isinstance(where, str) and bool(where)
            and isinstance(derivative, str) and bool(derivative))


# ---------------------------------------------------------------------- helpers
def require_manifest_source_budget(total, cfg):
    budget = source_size_budget(cfg)
    if type(total) is not int or total < 0:
        raise KnowledgeError('INVALID_REQUEST')
    if total > budget['per_manifest']:
        raise KnowledgeError('BATCH_SOURCE_SIZE_LIMIT_EXCEEDED')
    return total


def _require(condition, code='INVALID_REQUEST'):
    if not condition:
        raise KnowledgeError(code)


def _canonical_bytes(value):
    # service_http.canonical is a compact JSON string (ingestion.canonical is
    # bytes); hashing and the plan digest always use its UTF-8 encoding here.
    return canonical(value).encode('utf-8')


def _digest_bytes(value):
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _sha256_file(path):
    hasher = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            hasher.update(block)
    return hasher.hexdigest()


def _bounded_text(value, maximum, *, minimum=1):
    if not isinstance(value, str):
        raise KnowledgeError('INVALID_REQUEST')
    value = value.strip()
    if not minimum <= len(value) <= maximum:
        raise KnowledgeError('INVALID_REQUEST')
    if any(ord(c) < 32 for c in value) or '\x7f' in value:
        raise KnowledgeError('INVALID_REQUEST')
    return value


def _save_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = path.with_name(path.name + '.tmp-' + secrets.token_hex(4))
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=1) + '\n')
    temporary.chmod(0o600)
    os.replace(temporary, path)
    return path


def _load_json(path, code='POLICY_UNAVAILABLE'):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError) as error:
        raise KnowledgeError(code) from error


def _stage_file(source, destination, expected_sha256, *, expected_size=None):
    """Private copy/hardlink; the digest is verified before the rename."""
    source = Path(source)
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if destination.is_symlink():
        raise KnowledgeError('POLICY_UNAVAILABLE')
    if destination.exists():
        _require(_sha256_file(destination) == expected_sha256, 'BATCH_PLAN_STALE')
        return destination
    temporary = destination.with_name(destination.name + '.tmp-' + secrets.token_hex(4))
    copied = False
    try:
        os.link(source, temporary)
    except OSError:
        shutil.copyfile(source, temporary)
        copied = True
    if copied:
        temporary.chmod(0o600)
    size = temporary.stat().st_size
    if _sha256_file(temporary) != expected_sha256 or (expected_size is not None and size != expected_size):
        temporary.unlink(missing_ok=True)
        raise KnowledgeError('INVALID_REQUEST')
    os.replace(temporary, destination)
    return destination


@contextmanager
def _plan_lock(plan_dir):
    """Serialize submit/reclaim attempts on one immutable plan."""
    path = Path(plan_dir) / '.plan.lock'
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT, 0o600)
    try:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            raise KnowledgeError('IMPORT_BUSY') from None
        yield
    finally:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
        finally:
            os.close(descriptor)


def _plan_dir(plan_sha256):
    _require(isinstance(plan_sha256, str) and HEX64.fullmatch(plan_sha256) is not None)
    root = _batch_root(_config())
    directory = root / 'plans' / plan_sha256
    _require(directory.is_dir() and not directory.is_symlink(), 'BATCH_PLAN_STALE')
    return directory


# ------------------------------------------------------------------- identities
def _version_identity(source_sha256, text_sha256, department):
    """Stable version identity: source bytes + full text + department."""
    return 'VER_' + hashlib.sha256(_canonical_bytes(
        ['RC13_BATCH_VERSION_V1', source_sha256, text_sha256, department])).hexdigest()[:24]


def _binding_identity(version_id, parser_config):
    return 'BR_' + hashlib.sha256(_canonical_bytes(
        [version_id, 'ragflow-v0.27.0', parser_config])).hexdigest()[:24]


def _frozen_digest(frozen):
    """Frozen batch hash uses the ingestion canonical form (the same one
    ``maintenance_contract.registered`` re-verifies); ours is only a helper."""
    from knowledge_service.ingestion import canonical as ingestion_canonical, digest
    value = dict(frozen)
    value.pop('batch_sha256', None)
    return digest(ingestion_canonical(value))


def _page_source_text(pages):
    return '\n\n'.join(f'【原件物理第{i + 1}页】\n{text}' for i, text in enumerate(pages))


# -------------------------------------------------------------- manifest input
def _safe_relative_path(value):
    if not isinstance(value, str) or not 1 <= len(value) <= 512 or '\\' in value:
        raise KnowledgeError('INVALID_REQUEST')
    if any(ord(c) < 32 for c in value) or ':' in value:
        raise KnowledgeError('INVALID_REQUEST')
    path = PurePosixPath(value)
    if path.is_absolute() or not path.parts:
        raise KnowledgeError('INVALID_REQUEST')
    if any(part in ('', '.', '..') or part.startswith('.') for part in path.parts):
        raise KnowledgeError('INVALID_REQUEST')
    if path.suffix.lower() not in SOURCE_EXTENSIONS:
        raise KnowledgeError('INVALID_REQUEST')
    return path.as_posix()


def _symlink_free(real, relative):
    current = real.parents[len(relative.parts) - 1]
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise KnowledgeError('INVALID_REQUEST')


def _resolve_source(value, roots, max_bytes):
    """Resolve one owner path inside the configured approved roots only."""
    if not isinstance(value, str) or not 1 <= len(value) <= 4096 or '\x00' in value:
        raise KnowledgeError('INVALID_REQUEST')
    candidate = Path(value)
    matches = []
    for index, root in enumerate(roots):
        entries = [candidate] if candidate.is_absolute() else [root / candidate]
        for entry in entries:
            if not entry.exists() or entry.is_symlink():
                continue
            real = entry.resolve(strict=True)
            try:
                relative = real.relative_to(root)
            except ValueError:
                continue
            if not real.is_file() or not relative.parts:
                continue
            _symlink_free(real, relative)
            matches.append((index, real, relative))
    unique = {}
    for index, real, relative in matches:
        unique[str(real)] = (index, real, relative)
    _require(len(unique) == 1)
    index, real, relative = next(iter(unique.values()))
    size = real.stat().st_size
    require_source_size(size, max_bytes)
    return index, real, relative


def _validate_page_checks(value, page_count):
    if not isinstance(value, dict) or set(value) - PAGE_CHECK_KEYS:
        raise KnowledgeError('INVALID_REQUEST')
    _require(isinstance(value.get('quality_pass'), bool))
    visual = value.get('visual_review')
    if visual is not None:
        _require(isinstance(visual, dict) and set(visual) <= {'reviewer', 'pages', 'notes'})
        _bounded_text(visual.get('reviewer'), 80)
        notes = visual.get('notes')
        if notes is not None:
            _bounded_text(notes, 500)
        pages = visual.get('pages')
        if pages is not None:
            _require(isinstance(pages, list) and 1 <= len(pages) <= 10)
            _require(all(type(page) is int and 1 <= page <= page_count for page in pages))
    for key in ('sparse_pages', 'gap_pages'):
        pages = value.get(key)
        if pages is not None:
            _require(isinstance(pages, list) and len(pages) <= page_count)
            _require(all(type(page) is int and 1 <= page <= page_count for page in pages))
    return value


def _normalize_manifest(raw, cfg):
    if isinstance(raw, str):
        if len(raw) > MAX_PLAN_MANIFEST_BYTES:
            raise KnowledgeError('MANIFEST_SIZE_LIMIT_EXCEEDED')
        try:
            raw = json.loads(raw)
        except ValueError:
            raise KnowledgeError('INVALID_REQUEST') from None
    _require(isinstance(raw, dict))
    if len(canonical(raw)) > MAX_PLAN_MANIFEST_BYTES:
        raise KnowledgeError('MANIFEST_SIZE_LIMIT_EXCEEDED')
    budget = source_size_budget(cfg)
    _require(set(raw) <= MANIFEST_KEYS)
    if 'schema_version' in raw:
        _require(type(raw.get('schema_version')) is int and raw['schema_version'] == MANIFEST_SCHEMA)
    _require(raw.get('sharing_confirmed') is True)
    default_department = raw.get('department')
    if default_department is not None:
        default_department = normalized_department(default_department)
        _require(default_department in DEPARTMENTS)
    label = raw.get('label')
    if label is not None:
        label = _bounded_text(label, MAX_LABEL)
    items = raw.get('items')
    _require(isinstance(items, list) and 1 <= len(items) <= MAX_ITEMS)
    roots = _approved_roots(cfg)
    normalized_items = []
    runtime_items = []
    seen_relative = set()
    total_text = 0
    total_source_bytes = 0
    for index, item in enumerate(items):
        _require(isinstance(item, dict))
        _require(set(item) <= ITEM_KEYS)
        source_sha256 = item.get('source_sha256')
        _require(isinstance(source_sha256, str) and HEX64.fullmatch(source_sha256) is not None)
        source_sha256 = source_sha256.lower()
        root_index, real, source_relative = _resolve_source(
            item.get('canonical_source_path'), roots, budget['per_file'])
        relative_value = item.get('relative_path')
        relative_path = (_safe_relative_path(source_relative.as_posix()) if relative_value is None
                         else _safe_relative_path(relative_value))
        _require(PurePosixPath(relative_path).suffix.lower() == real.suffix.lower())
        _require(real.suffix.lower() in DERIVATIVE_EXTENSIONS)
        department = item.get('department') or default_department
        _require(department is not None)
        department = normalized_department(department)
        _require(department in DEPARTMENTS)
        _require((department, relative_path) not in seen_relative)
        seen_relative.add((department, relative_path))
        pages = item.get('pages')
        _require(isinstance(pages, list) and 1 <= len(pages) <= MAX_ITEM_PAGES)
        for text in pages:
            _require(isinstance(text, str) and len(text) <= MAX_PAGE_TEXT)
        page_methods = item.get('page_methods')
        _require(isinstance(page_methods, list) and len(page_methods) == len(pages))
        _require(all(isinstance(method, str) and method in PAGE_METHODS for method in page_methods))
        page_checks = _validate_page_checks(item.get('page_checks'), len(pages))
        source_text = _page_source_text(pages)
        text_characters = len(source_text)
        _require(4 <= text_characters <= 5_000_000)
        total_text += text_characters
        _require(total_text <= MAX_TOTAL_TEXT)
        text_sha256 = hashlib.sha256(source_text.encode()).hexdigest()
        hint = item.get('disposition_hint') or 'NEW'
        _require(hint in HINTS)
        replace = item.get('replace')
        repair = item.get('repair')
        if hint == 'BUSINESS_UPDATE':
            _require(isinstance(replace, dict) and set(replace) == REPLACE_KEYS)
            _require(isinstance(replace.get('canonical_document_id'), str)
                     and DOCUMENT_ID.fullmatch(replace['canonical_document_id']) is not None)
            _require(isinstance(replace.get('expected_current_version'), str)
                     and VERSION_ID.fullmatch(replace['expected_current_version']) is not None)
        else:
            _require(replace is None)
        if hint == 'TECHNICAL_REPAIR':
            _require(isinstance(repair, dict) and set(repair) == REPAIR_KEYS)
            _require(isinstance(repair.get('parent_batch_id'), str)
                     and BATCH_ID.fullmatch(repair['parent_batch_id']) is not None)
            _require(isinstance(repair.get('parent_version_id'), str)
                     and VERSION_ID.fullmatch(repair['parent_version_id']) is not None)
            _bounded_text(repair.get('reason'), 500, minimum=3)
        else:
            _require(repair is None)
        _require(_sha256_file(real) == source_sha256)
        total_source_bytes += real.stat().st_size
        require_manifest_source_budget(total_source_bytes, cfg)
        version_id = _version_identity(source_sha256, text_sha256, department)
        source_ref = f'{root_index}:{PurePosixPath(source_relative.as_posix())}'
        normalized = {'source_sha256': source_sha256, 'source_ref': source_ref,
                      'relative_path': relative_path, 'department': department,
                      'text_sha256': text_sha256, 'version_id': version_id,
                      'pages': list(pages), 'page_methods': list(page_methods),
                      'page_checks': page_checks}
        if hint != 'NEW':
            normalized['disposition_hint'] = hint
        if replace is not None:
            normalized['replace'] = dict(replace)
        if repair is not None:
            normalized['repair'] = {**repair, 'reason': _bounded_text(repair['reason'], 500, minimum=3)}
        normalized_items.append(normalized)
        runtime_items.append({'index': index, 'source_sha256': source_sha256,
                              'source_ref': source_ref, 'source_path': str(real),
                              'source_size': real.stat().st_size,
                              'relative_path': relative_path, 'department': department,
                              'text_sha256': text_sha256, 'version_id': version_id,
                              'pages': list(pages), 'page_methods': list(page_methods),
                              'page_checks': page_checks, 'hint': hint,
                              'replace': replace, 'repair': repair})
    normalized_manifest = {'schema_version': MANIFEST_SCHEMA, 'sharing_confirmed': True,
                           'label': label, 'items': normalized_items}
    if default_department is not None:
        normalized_manifest['department'] = default_department
    plan_sha256 = _digest_bytes(normalized_manifest)
    return {'plan_sha256': plan_sha256, 'normalized': normalized_manifest,
            'items': runtime_items, 'label': label,
            'departments': sorted({item['department'] for item in runtime_items})}


# ---------------------------------------------------------------- classification
def _uploaded_original(entry):
    return (isinstance(entry.get('dataset_id'), str) and PHYSICAL_ID.fullmatch(entry['dataset_id']) is not None
            and isinstance(entry.get('ragflow_document_id'), str)
            and PHYSICAL_ID.fullmatch(entry['ragflow_document_id']) is not None)


def _registry_entry(entry):
    return {'document_id': entry.get('canonical_document_id'),
            'version_id': entry.get('version_id'),
            'sha256': entry.get('sha256'),
            'dataset_id': entry.get('dataset_id'),
            'ragflow_document_id': entry.get('ragflow_document_id'),
            'binding_revision': entry.get('binding_revision'),
            'relative_path': entry.get('relative_path'),
            'title': entry.get('title'),
            'size_bytes': entry.get('size_bytes'),
            'status': entry.get('status'),
            'source_type': entry.get('source_type'),
            'authority_status': entry.get('authority_status'),
            'document_number': entry.get('document_number'),
            'business_version': entry.get('business_version'),
            'embedding_model': entry.get('embedding_model'),
            'embedding_dimensions': entry.get('embedding_dimensions'),
            'department_key': normalized_department(entry.get('department_key'))}


def _publication(entry_document_id):
    return frappe.db.get_value('HBOS Knowledge Document', entry_document_id,
                               ['current_version', 'withdrawn', 'ingestion_status'], as_dict=True)


def _result(item, disposition, *, submittable, reason=None, pages=None, page_methods=None,
            document_id=None, version_id=None, expected_current_version=None,
            candidate=None, detail=None, reprocess=False):
    return {'index': item['index'], 'source_sha256': item['source_sha256'],
            'disposition': disposition, 'submittable': submittable,
            'conflict_reason': reason, 'detail': detail, 'reprocess': bool(reprocess),
            'pages': len(item['pages']) if pages is None else pages,
            'page_methods': page_methods if page_methods is not None else list(item['page_methods']),
            'text_sha256': item['text_sha256'],
            'document_id': document_id, 'version_id': version_id,
            'expected_current_version': expected_current_version,
            'candidate': candidate}


def _classify_item(item, index):
    department = item['department']
    version_id = item['version_id']
    page_methods = list(item['page_methods'])
    page_count = len(item['pages'])
    if not item['page_checks'].get('quality_pass'):
        return _result(item, 'ANOMALY', submittable=False, reason='QUALITY_CHECK_FAILED',
                       page_methods=page_methods)
    same_version = [entry for entry in (index['by_version'].get(version_id) or [])
                    if entry.get('sha256') == item['source_sha256']]
    if same_version:
        entry = same_version[0]
        document_id = entry.get('canonical_document_id')
        published = _publication(document_id)
        available = bool(published) and not published.get('withdrawn') \
            and published.get('current_version') == version_id \
            and published.get('ingestion_status') == 'published'
        if entry.get('status') == 'parsed/indexed' and available:
            return _result(item, 'DUPLICATE', submittable=True, page_methods=page_methods,
                           document_id=document_id, version_id=entry.get('version_id'),
                           candidate=_registry_entry(entry),
                           detail='该版本全文已处理且文档当前可用；提交只登记重复记录，不会重新解析。')
        if entry.get('status') in ('parse_queued', 'parse_intent', 'upload_intent'):
            return _result(item, 'ANOMALY', submittable=False, reason='PARSE_IN_FLIGHT',
                           page_methods=page_methods, document_id=document_id,
                           candidate=_registry_entry(entry))
        if (published and not published.get('withdrawn')
                and published.get('ingestion_status') == 'published'
                and published.get('current_version') != version_id):
            # A different current version is live; re-driving this old version
            # would create a publication conflict, not a recovery.
            return _result(item, 'ANOMALY', submittable=False,
                           reason='CANDIDATE_ALREADY_PUBLISHED', page_methods=page_methods,
                           document_id=document_id, candidate=_registry_entry(entry))
        candidate = entry if _uploaded_original(entry) else next(
            (other for other in index['by_sha_dept'].get((item['source_sha256'], department), [])
             if _uploaded_original(other)), None)
        if candidate is None:
            return _result(item, 'NEW_UPLOAD_REQUIRED', submittable=False,
                           reason='ORIGINAL_ASSET_REQUIRED', page_methods=page_methods,
                           document_id=document_id, version_id=entry.get('version_id'),
                           detail='该版本曾未成功或未发布，但缺少可用于重处理的已上传原件。')
        return _result(item, 'NEW', submittable=True, page_methods=page_methods,
                       document_id=document_id, version_id=entry.get('version_id'),
                       candidate=_registry_entry(candidate), reprocess=True,
                       detail='该版本曾处理失败或尚未发布；本次复用同一逻辑文档/版本重新处理，'
                              '不触碰其它已成功项，也不伪造审批。')
    if item['hint'] == 'TECHNICAL_REPAIR':
        repair = item['repair']
        try:
            parent_row, parent_frozen, parent_state = m._row(repair['parent_batch_id'])
        except KnowledgeError:
            return _result(item, 'ANOMALY', submittable=False, reason='REPAIR_PARENT_MISSING',
                           page_methods=page_methods)
        matching = [entry for entry in parent_state.get('items', [])
                    if entry.get('sha256') == item['source_sha256']
                    and entry.get('version_id') == repair['parent_version_id']
                    and entry.get('disposition') not in ('SAME_CONTENT_SKIP', 'ALIAS')]
        if len(matching) != 1:
            return _result(item, 'ANOMALY', submittable=False, reason='REPAIR_PARENT_MISMATCH',
                           page_methods=page_methods)
        return _result(item, 'TECHNICAL_REPAIR', submittable=False,
                       reason='REPAIR_USES_EXISTING_NATIVE_PREPARE_FLOW',
                       page_methods=page_methods,
                       detail='技术修复依赖 native prepare/派生证明，请走既有修复流程；本批次不编排。')
    if item['hint'] == 'BUSINESS_UPDATE':
        relation = item['replace']
        matches = [entry for entry in index['by_document'].get(relation['canonical_document_id'], [])
                   if normalized_department(entry.get('department_key')) == department]
        if len(matches) != 1:
            return _result(item, 'ANOMALY', submittable=False, reason='RELATION_NOT_TRACEABLE',
                           page_methods=page_methods)
        published = _publication(relation['canonical_document_id'])
        if (not published or published.get('withdrawn')
                or published.get('current_version') != relation['expected_current_version']
                or published.get('ingestion_status') != 'published'):
            return _result(item, 'ANOMALY', submittable=False, reason='RELATION_NOT_CURRENT',
                           page_methods=page_methods)
        candidates = [entry for entry in index['by_sha_dept'].get((item['source_sha256'], department), [])
                      if _uploaded_original(entry)]
        if not candidates:
            return _result(item, 'BUSINESS_UPDATE', submittable=False,
                           reason='NEW_UPLOAD_REQUIRED', page_methods=page_methods,
                           document_id=relation['canonical_document_id'],
                           version_id=version_id,
                           expected_current_version=relation['expected_current_version'],
                           detail='业务换版需先按单文件上传流程登记当前新原件，再走原件解析流程。')
        return _result(item, 'BUSINESS_UPDATE', submittable=False,
                       reason='BUSINESS_UPDATE_REQUIRES_ORIGINAL_PARSE_FLOW',
                       page_methods=page_methods,
                       document_id=relation['canonical_document_id'], version_id=version_id,
                       expected_current_version=relation['expected_current_version'],
                       detail='换版需保留原件解析语义；本批次只做已登记原件的全文派生。')
    candidates = [entry for entry in index['by_sha_dept'].get((item['source_sha256'], department), [])
                  if _uploaded_original(entry)]
    distinct = {entry.get('canonical_document_id') for entry in candidates}
    if len(distinct) > 1:
        return _result(item, 'ANOMALY', submittable=False, reason='AMBIGUOUS_CANDIDATE',
                       page_methods=page_methods)
    if not candidates:
        return _result(item, 'NEW_UPLOAD_REQUIRED', submittable=False,
                       reason='SINGLE_FILE_UPLOAD_REQUIRED', page_methods=page_methods,
                       version_id=version_id,
                       detail='该来源尚未登记上传原件；本轮请使用单文件新增资料上传，再处理全文。')
    candidate = candidates[0]
    status = candidate.get('status')
    if not (isinstance(candidate.get('upload_sha256'), str) and candidate.get('upload_sha256')):
        pass  # upload_sha256 is optional evidence here; the native stage re-verifies bytes.
    if status in ('parse_queued', 'parse_intent', 'upload_intent'):
        return _result(item, 'ANOMALY', submittable=False, reason='PARSE_IN_FLIGHT',
                       page_methods=page_methods, candidate=_registry_entry(candidate))
    if status not in ('uploaded', 'parse_failed'):
        return _result(item, 'ANOMALY', submittable=False, reason='CANDIDATE_STATE_UNSUPPORTED',
                       page_methods=page_methods, candidate=_registry_entry(candidate))
    document_id = candidate.get('canonical_document_id')
    published = _publication(document_id)
    if published and not published.get('withdrawn') and published.get('ingestion_status') == 'published':
        return _result(item, 'ANOMALY', submittable=False, reason='CANDIDATE_ALREADY_PUBLISHED',
                       page_methods=page_methods, candidate=_registry_entry(candidate))
    return _result(item, 'NEW', submittable=True, page_methods=page_methods,
                   document_id=document_id, version_id=version_id,
                   candidate=_registry_entry(candidate))


def _build_index(registry):
    index = {'by_version': {}, 'by_document': {}, 'by_sha_dept': {}}
    for entry in registry.get('documents') or []:
        if not isinstance(entry, dict):
            continue
        department = normalized_department(entry.get('department_key'))
        sha = entry.get('sha256')
        if isinstance(sha, str):
            index['by_sha_dept'].setdefault((sha, department), []).append(entry)
        version = entry.get('version_id')
        if isinstance(version, str) and version.startswith('VER_'):
            index['by_version'].setdefault(version, []).append(entry)
        document = entry.get('canonical_document_id')
        if isinstance(document, str):
            index['by_document'].setdefault(document, []).append(entry)
    return index


def _classify(cfg, normalized, registry):
    index = _build_index(registry)
    results = []
    for item in normalized['items']:
        results.append(_classify_item(item, index))
    results.sort(key=lambda entry: entry['index'])
    return results


def plan_batch(manifest):
    """Read-only preview. Writes only the private plan cache, never a DB row."""
    cfg = _config()
    normalized = _normalize_manifest(manifest, cfg)
    plan_sha256 = normalized['plan_sha256']
    root = _batch_root(cfg)
    plan_dir = root / 'plans' / plan_sha256
    plan_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    registry = m._registry()
    results = _classify(cfg, normalized, registry)
    seen_manifest = {}
    for item in normalized['items']:
        key = (item['source_sha256'], item['text_sha256'], item['department'])
        if key in seen_manifest:
            results[item['index']] = _result(item, 'ANOMALY', submittable=False,
                                             reason='DUPLICATE_IN_MANIFEST')
        else:
            seen_manifest[key] = item['index']
    departments = normalized['departments']
    public_items = []
    for item in normalized['items']:
        classified = {key: value for key, value in results[item['index']].items()
                      if key != 'candidate'}
        public_items.append({**classified,
                             'filename': PurePosixPath(item['relative_path']).name,
                             'title': PurePosixPath(item['relative_path']).stem,
                             'department': item['department'],
                             'target': {'space_id': cfg.get('department_space_map', {}).get(
                                            item['department'], 'DEPT_' + item['department'].upper()),
                                        'title': DEPARTMENTS[item['department']],
                                        'department': item['department']},
                             'evidence': {'source_sha256': item['source_sha256'],
                                          'page_count': len(item['pages']),
                                          'text_sha256': item['text_sha256'],
                                          'page_methods': item['page_methods'],
                                          'page_checks': item['page_checks'],
                                          'sharing_confirmed': True}})
    counts = {'total': len(public_items), 'new': 0, 'duplicate': 0, 'business_update': 0,
              'technical_repair': 0, 'new_upload_required': 0, 'anomaly': 0}
    for entry in public_items:
        counts[DISPOSITION_KEYS[entry['disposition']]] += 1
    blocking = sum(1 for entry in public_items if not entry['submittable'])
    groups = []
    for department in departments:
        members = [entry for entry in public_items if entry['department'] == department]
        active = [entry for entry in members if entry['disposition'] == 'NEW']
        duplicates = [entry for entry in members if entry['disposition'] == 'DUPLICATE']
        groups.append({'department': department,
                       'documents': len(members),
                       'jobs': (len(active) + 3) // 4 if active else 0,
                       'duplicate_documents': len(duplicates)})
    result = {'schema': PLAN_SCHEMA, 'plan_sha256': plan_sha256, 'readonly': True,
              'label': normalized['label'],
              'department': normalized['normalized'].get('department'),
              'departments': departments, 'sharing_confirmed': True,
              'items': public_items, 'counts': counts, 'groups': groups,
              'blocking_anomalies': blocking,
              'submittable': blocking == 0,
              'next_action': 'submit_import' if blocking == 0 else 'fix_manifest'}
    _save_json(plan_dir / 'plan-input.json', normalized['normalized'])
    _save_json(plan_dir / 'sources.json', {'items': [
        {'index': item['index'], 'source': item['source_path'],
         'source_size': item['source_size']} for item in normalized['items']]})
    _save_json(plan_dir / 'plan.json', result)
    return result


# ------------------------------------------------------------------- submission
def _runtime_items_from_input(plan_dir, plan_input):
    sources = _load_json(plan_dir / 'sources.json', 'BATCH_PLAN_STALE')
    paths = {entry.get('index'): entry for entry in sources.get('items') or []
             if isinstance(entry, dict) and type(entry.get('index')) is int}
    runtime = []
    for index, item in enumerate(plan_input.get('items') or []):
        source = paths.get(index)
        _require(isinstance(source, dict) and isinstance(source.get('source'), str), 'BATCH_PLAN_STALE')
        runtime.append({'index': index, 'source_sha256': item['source_sha256'],
                        'source_ref': item['source_ref'], 'source_path': source['source'],
                        'source_size': source.get('source_size'),
                        'relative_path': item['relative_path'],
                        'department': item['department'],
                        'text_sha256': item['text_sha256'], 'version_id': item['version_id'],
                        'pages': item['pages'], 'page_methods': item['page_methods'],
                        'page_checks': item['page_checks'],
                        'hint': item.get('disposition_hint') or 'NEW',
                        'replace': item.get('replace'), 'repair': item.get('repair')})
    return runtime


def _drift_check(stored, fresh):
    """Registry drift between preview and submit must never freeze stale decisions."""
    if len(stored) != len(fresh):
        raise KnowledgeError('BATCH_PLAN_STALE')
    for public, current in zip(sorted(stored, key=lambda entry: entry['index']),
                               sorted(fresh, key=lambda entry: entry['index'])):
        for key in ('disposition', 'document_id', 'version_id', 'expected_current_version'):
            if public.get(key) != current.get(key):
                raise KnowledgeError('BATCH_PLAN_STALE')


def _parser_profile():
    from knowledge_service.ingestion import LOCAL_FULLTEXT_NEWLINE_PROFILE, parser_config_for_profile
    return LOCAL_FULLTEXT_NEWLINE_PROFILE, parser_config_for_profile(LOCAL_FULLTEXT_NEWLINE_PROFILE)


def _derivation_receipt(item):
    return {'source_sha256': item['source_sha256'], 'full_source_processed': True,
            'pages': len(item['pages']), 'page_methods': list(item['page_methods']),
            'source_pages_sha256': hashlib.sha256(_canonical_bytes(item['pages'])).hexdigest(),
            'text_sha256': item['text_sha256'],
            'visual_review': item['page_checks'].get('visual_review'),
            'quality_pass': True,
            'sparse_pages': item['page_checks'].get('sparse_pages'),
            'gap_pages': item['page_checks'].get('gap_pages')}


def _derivative_item(item, classification, approval_ref):
    """Exact RC12 shape: existing uploaded original + verified page-complete text."""
    from knowledge_service.ingestion import RUNTIME_ITEM_FIELDS
    candidate = classification['candidate']
    _require(isinstance(candidate, dict), 'BATCH_PLAN_STALE')
    profile, parser_config = _parser_profile()
    receipt = _derivation_receipt(item)
    receipt_sha256 = hashlib.sha256(_canonical_bytes(receipt)).hexdigest()
    source_text = _page_source_text(item['pages'])
    title = candidate.get('title') or PurePosixPath(item['relative_path']).stem
    department = item['department']
    base = {key: value for key, value in candidate.items()
            if key in ('source_type', 'authority_status', 'document_number', 'business_version',
                       'embedding_model', 'embedding_dimensions', 'legal_metadata',
                       'source_identity_number') and value is not None}
    return {**base,
            'source_ref': item['source_ref'], 'relative_path': item['relative_path'],
            'original_filename': PurePosixPath(item['relative_path']).name,
            'media_type': None, 'extension': PurePosixPath(item['relative_path']).suffix.lower(),
            'size_bytes': item['source_size'], 'sha256': item['source_sha256'],
            'title': title, 'department_key': department,
            'department_title': DEPARTMENTS[department],
            'space_id': 'DEPT_' + department.upper(),
            'canonical_document_id': candidate['document_id'],
            'version_id': item['version_id'],
            'binding_revision': _binding_identity(item['version_id'], parser_config),
            'disposition': 'NEW', 'expected_current_version': None, 'identity_relation': None,
            'dataset_id': candidate['dataset_id'],
            # The generated local-full-text derivative is a NEW physical asset:
            # it must be uploaded and parsed. Reusing the uploaded original's
            # native id here makes ingestion.apply() skip the upload and then
            # fail with "Stored original checksum mismatch". The original asset
            # remains only in native_text_preflight.original_asset below.
            'ragflow_document_id': None,
            'status': 'planned', 'parser_config': parser_config,
            'parser_input': 'VERIFIED_LOCAL_FULL_TEXT',
            'native_display_original_filename': False,
            'technical_admission': 'ADMIT_INTERNAL_REFERENCE',
            'quality_gate_holds': [],
            'owner_inclusion_confirmed': True, 'internal_sharing_confirmed': True,
            'owner_processing_confirmed': True, 'approval_ref': approval_ref,
            'native_text_preflight': {
                'method': 'local-fulltext-derivative-v1',
                'source_sha256': item['source_sha256'], 'full_source_processed': True,
                'text_characters': len(source_text), 'text_sha256': item['text_sha256'],
                'derivation_receipt_sha256': receipt_sha256,
                'original_asset': {'dataset_id': candidate['dataset_id'],
                                   'document_id': candidate['ragflow_document_id'],
                                   'source_sha256': item['source_sha256']}}}


def _duplicate_item(item, classification, approval_ref):
    candidate = classification['candidate']
    _require(isinstance(candidate, dict), 'BATCH_PLAN_STALE')
    department = item['department']
    return {'source_ref': item['source_ref'], 'relative_path': item['relative_path'],
            'original_filename': PurePosixPath(item['relative_path']).name,
            'media_type': None, 'extension': PurePosixPath(item['relative_path']).suffix.lower(),
            'size_bytes': item['source_size'], 'sha256': item['source_sha256'],
            'title': candidate.get('title') or PurePosixPath(item['relative_path']).stem,
            'department_key': department, 'department_title': DEPARTMENTS[department],
            'space_id': 'DEPT_' + department.upper(),
            'canonical_document_id': candidate['document_id'],
            'version_id': candidate['version_id'],
            'binding_revision': candidate.get('binding_revision') or
            _binding_identity(candidate['version_id'], {'legacy': True}),
            'disposition': 'SAME_CONTENT_SKIP', 'expected_current_version': None,
            'identity_relation': None, 'dataset_id': None, 'ragflow_document_id': None,
            'status': 'planned', 'parser_config': None,
            'owner_inclusion_confirmed': True, 'internal_sharing_confirmed': True,
            'owner_processing_confirmed': True, 'approval_ref': approval_ref}


def _chunk_groups(normalized, results):
    """Group derivative work by department+dataset, at most four documents per job."""
    groups = []
    duplicate_groups = {}
    for item in normalized['items']:
        classification = results[item['index']]
        if classification['disposition'] == 'DUPLICATE':
            duplicate_groups.setdefault(item['department'], []).append((item, classification))
            continue
        _require(classification['disposition'] == 'NEW', 'BATCH_PLAN_BLOCKED')
        candidate = classification['candidate']
        key = (item['department'], candidate['dataset_id'])
        if not groups or groups[-1]['key'] != key or len(groups[-1]['items']) == 4:
            groups.append({'key': key, 'items': []})
        groups[-1]['items'].append((item, classification))
    batches = [{'kind': 'derivative', 'department': entry['key'][0],
                'dataset_id': entry['key'][1], 'items': entry['items']}
               for entry in groups]
    for department, entries in duplicate_groups.items():
        batches.append({'kind': 'duplicate', 'department': department, 'dataset_id': None,
                        'items': entries})
    return batches


def _content_key(plan_sha256, group):
    identity = [entry[0]['index'] for entry in group['items']]
    return 'RC13-' + hashlib.sha256(_canonical_bytes(
        ['RC13_BATCH_CONTENT', plan_sha256, group['department'],
         group.get('dataset_id'), identity])).hexdigest()[:24]


def _job_id(plan_sha256, group):
    identity = [entry[0]['index'] for entry in group['items']]
    return 'JOB_' + hashlib.sha256(_canonical_bytes(
        ['RC13_BATCH_JOB', plan_sha256, group['department'],
         group.get('dataset_id'), identity])).hexdigest()[:24]


def _embedding_model(cfg, group):
    """Exact model string expected by the controller's ingestion.apply().

    Resolution order: the private candidate config (required when the registry
    evidence predates this field) then the registered uploaded item's frozen
    model. A batch is one department/dataset; mixed evidence is unusable.
    """
    configured = cfg.get('maintenance_embedding_model')
    if isinstance(configured, str) and configured.strip():
        return _bounded_text(configured, 200, minimum=3)
    values = set()
    for _item, classification in group['items']:
        candidate = classification.get('candidate') or {}
        value = candidate.get('embedding_model')
        if isinstance(value, str) and value.strip():
            values.add(value.strip())
    if len(values) == 1:
        value = next(iter(values))
        _require(3 <= len(value) <= 200)
        return value
    raise KnowledgeError('POLICY_UNAVAILABLE')


def _write_dataset_map(derivative_root, batch_id, frozen, embedding_model):
    """Write the exact map ingestion.apply() reads next to its state file.

    Layout: <maintenance_derivative_root>/<batch_id>/dataset-map.json. The host
    controller's private_work is the same directory, so one batch's map can
    never overwrite another's.
    """
    dataset_id = frozen.get('expected_dataset_id')
    if not (isinstance(dataset_id, str) and PHYSICAL_ID.fullmatch(dataset_id)):
        raise KnowledgeError('BATCH_PLAN_STALE')
    payload = {'dataset_id': dataset_id,
               'department_key': frozen['department_key'],
               'embedding_model': embedding_model,
               'batch_sha256': frozen['batch_sha256']}
    folder = derivative_root / batch_id
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = folder / 'dataset-map.json'
    if path.is_symlink():
        raise KnowledgeError('POLICY_UNAVAILABLE')
    if path.exists():
        _require(_load_json(path, 'BATCH_PLAN_STALE') == payload, 'BATCH_PLAN_STALE')
        return path
    _save_json(path, payload)
    return path


def _write_derivatives(derivative_root, batch_id, items):
    """Write <private_work>/<batch_id>/derivatives/<version_id>.txt exactly once."""
    folder = derivative_root / batch_id / 'derivatives'
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    for item in items:
        content = _page_source_text(item['pages']).encode('utf-8')
        if hashlib.sha256(content).hexdigest() != item['text_sha256']:
            raise KnowledgeError('BATCH_PLAN_STALE')
        path = folder / (item['version_id'] + '.txt')
        if path.is_symlink():
            raise KnowledgeError('POLICY_UNAVAILABLE')
        if not path.exists():
            temporary = path.with_name(path.name + '.tmp-' + secrets.token_hex(4))
            temporary.write_bytes(content)
            temporary.chmod(0o600)
            os.replace(temporary, path)
        _require(hashlib.sha256(path.read_bytes()).hexdigest() == item['text_sha256'],
                 'BATCH_PLAN_STALE')


def _freeze_group(plan_dir, plan_sha256, normalized, group, approval_ref, context):
    derivative_root = context['derivative_root']
    registry = context['registry']
    content_key = _content_key(plan_sha256, group)
    batch_dir = plan_dir / 'batches' / content_key
    frozen_path = batch_dir / 'frozen.json'
    signature = [(entry[0]['source_sha256'], entry[0]['relative_path']) for entry in group['items']]
    if frozen_path.exists():
        frozen = _load_json(frozen_path, 'BATCH_PLAN_STALE')
        _require([(entry.get('sha256'), entry.get('relative_path')) for entry in frozen.get('items') or []]
                 == signature, 'BATCH_PLAN_STALE')
        state = _load_json(batch_dir / 'state.json', 'BATCH_PLAN_STALE')
        return frozen, state, batch_dir
    if group['kind'] == 'duplicate':
        items = [_duplicate_item(item, classification, approval_ref)
                 for item, classification in group['items']]
        source_root = None
        expected_dataset = None
    else:
        budget = source_size_budget(context['cfg'])
        batch_source_bytes = sum(int(item.get('source_size') or 0)
                                 for item, _classification in group['items'])
        if batch_source_bytes > budget['per_batch']:
            raise KnowledgeError('BATCH_SOURCE_SIZE_LIMIT_EXCEEDED')
        source_root = derivative_root / 'sources' / content_key / 'source'
        for item, _classification in group['items']:
            staged = _stage_file(item['source_path'], source_root / item['relative_path'],
                                 item['source_sha256'], expected_size=item.get('source_size'))
            item['source_size'] = staged.stat().st_size
        items = [_derivative_item(item, classification, approval_ref)
                 for item, classification in group['items']]
        expected_dataset = group['dataset_id']
    frozen = {'schema_version': 3, 'source_root': str(source_root) if source_root else None,
              'department_key': group['department'],
              'department_title': DEPARTMENTS[group['department']],
              'approval_ref': None, 'approval_status': 'OWNER_APPROVED',
              'instruction_ref': 'RC13_BATCH_SUBMIT:' + plan_sha256[:16],
              'registry_sha256': hashlib.sha256(_canonical_bytes(registry)).hexdigest(),
              'source_scope': DERIVATIVE_SCOPE, 'items': items, 'excluded': []}
    if expected_dataset is not None:
        frozen['expected_dataset_id'] = expected_dataset
    frozen['batch_sha256'] = _frozen_digest(frozen)
    from .maintenance_contract import initial_state
    state = initial_state(frozen)
    if expected_dataset is not None:
        state['dataset_id'] = expected_dataset
    if group['kind'] == 'derivative':
        from knowledge_service.ingestion import verify_frozen
        try:
            verify_frozen(frozen)
        except (ValueError, KeyError, TypeError) as error:
            raise KnowledgeError('BATCH_PLAN_STALE') from error
    _save_json(batch_dir / 'frozen.json', frozen)
    _save_json(batch_dir / 'state.json', state)
    _save_json(batch_dir / 'approval.json', {'approval_ref': approval_ref,
                                             'plan_sha256': plan_sha256,
                                             'source_scope': DERIVATIVE_SCOPE})
    return frozen, state, batch_dir


def _submit_group(plan_dir, plan_sha256, normalized, group, approval_ref, context):
    frozen, state, _ = _freeze_group(plan_dir, plan_sha256, normalized, group, approval_ref, context)
    batch_id = 'IMP_' + frozen['batch_sha256'][:32]
    job_id = _job_id(plan_sha256, group)
    if group['kind'] == 'derivative':
        _write_derivatives(context['derivative_root'], batch_id,
                           [item for item, _classification in group['items']])
        _write_dataset_map(context['derivative_root'], batch_id, frozen,
                           _embedding_model(context['cfg'], group))
    m.register_batch(frozen, state, context['label'], frappe.session.user)
    row, current_frozen, current_state = m._row(batch_id, True)
    _require(current_frozen.get('batch_sha256') == frozen['batch_sha256'])
    job = m._json(row, 'job_json', {})
    queued_documents = ([] if group['kind'] == 'duplicate'
                        else [frozen_item for frozen_item in frozen['items']
                              if frozen_item.get('disposition') != 'SAME_CONTENT_SKIP'])
    if job.get('id') and job.get('id') != job_id:
        if job.get('status') in ('Queued', 'Running', 'Paused'):
            raise KnowledgeError('IMPORT_BUSY')
        raise KnowledgeError('BATCH_PLAN_STALE')
    if job.get('id') == job_id:
        if job.get('status') in ('Queued', 'Running', 'Paused'):
            return {'batch_id': batch_id, 'department': group['department'],
                    'documents': len(frozen['items']), 'queued_documents': len(queued_documents),
                    'job_id': job_id, 'status': row.get('status'),
                    'active_job': job.get('status'), 'kind': group['kind']}
        job['status'] = 'Queued'
        job['pause_requested'] = False
        job['requested_at'] = job.get('requested_at') or time.time()
        frappe.db.set_value(TABLE, batch_id, {'job_json': canonical(job), 'status': 'Queued',
                                              'last_error': None})
        return {'batch_id': batch_id, 'department': group['department'],
                'documents': len(frozen['items']), 'queued_documents': len(queued_documents),
                'job_id': job_id, 'status': 'Queued', 'active_job': 'Queued',
                'kind': group['kind']}
    if not queued_documents:
        return {'batch_id': batch_id, 'department': group['department'],
                'documents': len(frozen['items']), 'queued_documents': 0,
                'job_id': None, 'status': row.get('status'), 'active_job': None,
                'kind': group['kind']}
    job = {'id': job_id, 'status': 'Queued', 'operation': 'parse',
           'document_ids': [entry['canonical_document_id'] for entry in queued_documents],
           'requested_by': frappe.session.user, 'requested_at': time.time(),
           'lease_generation': 0, 'nonce': None, 'lease_expires_at': None,
           'pause_requested': False, 'plan_sha256': plan_sha256,
           'approval_ref': approval_ref, 'reclaims': [],
           'source_scope': DERIVATIVE_SCOPE}
    frappe.db.set_value(TABLE, batch_id, {'job_json': canonical(job), 'status': 'Queued',
                                          'last_error': None})
    return {'batch_id': batch_id, 'department': group['department'],
            'documents': len(frozen['items']), 'queued_documents': len(queued_documents),
            'job_id': job_id, 'status': 'Queued', 'active_job': 'Queued',
            'kind': group['kind']}


def submit_batch(plan_sha256, approval_ref, label):
    _require(isinstance(plan_sha256, str) and HEX64.fullmatch(plan_sha256) is not None)
    approval_ref = _bounded_text(approval_ref, MAX_APPROVAL, minimum=3)
    cfg = _config()
    derivative_root = _derivative_root(cfg)
    plan_dir = _plan_dir(plan_sha256)
    with _plan_lock(plan_dir):
        plan_input = _load_json(plan_dir / 'plan-input.json', 'BATCH_PLAN_STALE')
        if _digest_bytes(plan_input) != plan_sha256:
            raise KnowledgeError('BATCH_PLAN_STALE')
        normalized = {'plan_sha256': plan_sha256, 'normalized': plan_input,
                      'items': _runtime_items_from_input(plan_dir, plan_input),
                      'label': plan_input.get('label'),
                      'departments': sorted({item['department'] for item in plan_input['items']})}
        if not normalized['items']:
            raise KnowledgeError('BATCH_PLAN_STALE')
        plan_public = _load_json(plan_dir / 'plan.json', 'BATCH_PLAN_STALE')
        if plan_public.get('plan_sha256') != plan_sha256:
            raise KnowledgeError('BATCH_PLAN_STALE')
        receipt_path = plan_dir / 'submitted.json'
        if receipt_path.exists():
            receipt = _load_json(receipt_path, 'BATCH_PLAN_STALE')
            if receipt.get('approval_ref') != approval_ref:
                raise KnowledgeError('BATCH_PLAN_STALE')
            return {**receipt, 'replayed': True}
        if plan_public.get('blocking_anomalies'):
            raise KnowledgeError('BATCH_PLAN_BLOCKED')
        registry = m._registry()
        results = _classify(cfg, normalized, registry)
        _drift_check(plan_public.get('items') or [], results)
        label_value = (_bounded_text(label, MAX_LABEL) if label
                       else (plan_public.get('label') or 'RC13 批量入库'))
        groups = _chunk_groups(normalized, results)
        context = {'derivative_root': derivative_root, 'registry': registry,
                   'label': label_value, 'cfg': cfg}
        submitted = [_submit_group(plan_dir, plan_sha256, normalized, group, approval_ref, context)
                     for group in groups]
        frappe.db.commit()
        receipt = {'schema': SUBMIT_SCHEMA, 'plan_sha256': plan_sha256,
                   'approval_ref': approval_ref, 'label': label_value,
                   'submitted_at': time.time(),
                   'actor_hash': hashlib.sha256(str(frappe.session.user).encode()).hexdigest()[:16],
                   'source_scope': DERIVATIVE_SCOPE,
                   'batches': submitted, 'replayed': False}
        _save_json(receipt_path, receipt)
        return receipt


# -------------------------------------------------------------------- progress
def _verification_view(receipt, published, version_id):
    if not isinstance(receipt, dict):
        return None
    status = receipt.get('status')
    base = {'status': 'VERIFIED' if status == 'VERIFIED' else 'PENDING',
            'at': receipt.get('at'),
            'query_sha256': receipt.get('query_sha256'),
            'evidence_id_hash': receipt.get('evidence_id_hash'),
            'receipt_sha256': receipt.get('receipt_sha256')}
    if status != 'VERIFIED':
        return base
    if not published or published.get('withdrawn'):
        return {**base, 'status': 'INVALIDATED', 'reason': 'WITHDRAWN'}
    if published.get('current_version') != version_id:
        return {**base, 'status': 'INVALIDATED', 'reason': 'VERSION_SUPERSEDED'}
    if published.get('ingestion_status') != 'published':
        return {**base, 'status': 'INVALIDATED', 'reason': 'UNPUBLISHED'}
    return base


def _item_error(item):
    status = item.get('status')
    if status == 'quarantined':
        attempt = item.get('attempt_error')
        return attempt if isinstance(attempt, str) and attempt in SAFE_ITEM_ERRORS \
            else 'IDENTITY_REVIEW_REQUIRED'
    # A previous failure stays on the item as history; it is not the current
    # execution state once the item has succeeded or is being re-driven.
    if status in ('parsed/indexed', 'skipped_duplicate'):
        return None
    attempt = item.get('attempt_error')
    if (isinstance(attempt, str) and attempt in SAFE_ITEM_ERRORS
            and status in ('quarantined', 'parse_failed', 'parse_intent')):
        return attempt
    if status == 'parse_failed':
        return 'PARSE_FAILED'
    return None


def _publication_state(published, version_id):
    if not published:
        return 'Unpublished'
    if published.get('withdrawn'):
        return 'Withdrawn'
    if published.get('current_version') == version_id and published.get('ingestion_status') == 'published':
        return 'Published'
    return 'Unpublished'


def progress_batch(batch_id, page=1, limit=20):
    from .reference_admin import _page_number
    page = _page_number(page, 100000)
    limit = _page_number(limit, 50)
    row, frozen, state = m._row(batch_id)
    job = m._json(row, 'job_json', {})
    quality = m._json(row, 'quality_json', {})
    now = time.time()
    counts = {'parsed': 0, 'failed': 0, 'queued': 0, 'verified': 0, 'invalidated': 0}
    for item in state['items']:
        status = item.get('status')
        if status == 'parsed/indexed':
            counts['parsed'] += 1
        elif status == 'parse_failed':
            counts['failed'] += 1
        elif status in ('parse_queued', 'parse_intent', 'upload_intent'):
            counts['queued'] += 1
    window = state['items'][(page - 1) * limit:page * limit]
    items = []
    for item in window:
        document_id = item['canonical_document_id']
        version_id = item['version_id']
        published = frappe.db.get_value('HBOS Knowledge Document', document_id,
                                        ['current_version', 'withdrawn', 'ingestion_status'], as_dict=True)
        verification = _verification_view(quality.get(version_id, {}).get('retrieval_verified'),
                                          published, version_id)
        if isinstance(verification, dict):
            if verification['status'] == 'VERIFIED':
                counts['verified'] += 1
            elif verification['status'] == 'INVALIDATED':
                counts['invalidated'] += 1
        items.append({'document_id': document_id, 'version_id': version_id,
                      'title': str(item.get('title') or '')[:240],
                      'filename': PurePosixPath(str(item.get('relative_path') or '')).name[:240],
                      'department': normalized_department(item.get('department_key')),
                      'status': item.get('status'),
                      'progress': max(0.0, min(1.0, float(item.get('progress') or 0))),
                      'chunk_count': int(item.get('chunk_count') or 0),
                      'error_code': _item_error(item),
                      'publication_status': _publication_state(published, version_id),
                      'retrieval_verified': verification})
    lease = job.get('lease_expires_at')
    expired = isinstance(lease, (int, float)) and float(lease) < now
    return {'schema': PLAN_SCHEMA, 'batch_id': row['name'], 'label': row.get('label'),
            'department': row.get('department_key'), 'status': row.get('status'),
            'last_error': row.get('last_error'),
            'job': {'id': job.get('id'), 'status': job.get('status'),
                    'operation': job.get('operation'),
                    'lease_generation': int(job.get('lease_generation') or 0),
                    'lease_expires_at': lease, 'lease_expired': expired,
                    'pause_requested': bool(job.get('pause_requested')),
                    'requested_at': job.get('requested_at'),
                    'reclaims': len(job.get('reclaims') or []),
                    'recoveries': len(job.get('recoveries') or []),
                    'retry_id': job.get('retry_id'),
                    'document_ids': list(job.get('document_ids') or []),
                    'source_scope': job.get('source_scope')},
            'items': items, 'total': len(state['items']), 'page': page, 'limit': limit,
            'counts': counts}


# -------------------------------------------------------------------- pause/resume
def pause_batch(batch_id):
    row, frozen, state = m._row(batch_id, True)
    job = m._json(row, 'job_json', {})
    status = row.get('status')
    if job.get('status') == 'Running' and status == 'Running':
        job['pause_requested'] = True
        job['paused_at'] = time.time()
        frappe.db.set_value(TABLE, row['name'], {'job_json': canonical(job)})
        frappe.db.commit()
        return {'batch_id': row['name'], 'status': 'Running', 'pause_requested': True,
                'note': 'Controller stops at the next safe point; no in-flight parse is killed.'}
    if job.get('status') == 'Queued' and status == 'Queued':
        job['status'] = 'Paused'
        job['pause_requested'] = False
        job['paused_at'] = time.time()
        frappe.db.set_value(TABLE, row['name'], {'job_json': canonical(job), 'status': 'Paused'})
        frappe.db.commit()
        return {'batch_id': row['name'], 'status': 'Paused', 'pause_requested': False}
    raise KnowledgeError('IMPORT_BUSY')


def resume_batch(batch_id):
    row, frozen, state = m._row(batch_id, True)
    job = m._json(row, 'job_json', {})
    if job.get('status') == 'Running' and job.get('pause_requested'):
        job['pause_requested'] = False
        frappe.db.set_value(TABLE, row['name'], {'job_json': canonical(job)})
        frappe.db.commit()
        return {'batch_id': row['name'], 'status': 'Running', 'pause_requested': False}
    if job.get('status') == 'Queued' and row.get('status') == 'Queued':
        raise KnowledgeError('IMPORT_BUSY')
    resumable = [item for item in state['items'] if item.get('status') in
                 ('planned', 'uploaded', 'parse_queued', 'parse_intent', 'upload_intent')]
    _require(resumable, 'INVALID_REQUEST')
    was_claimed = bool(job.get('claimed_at'))
    job['status'] = 'Queued'
    job['operation'] = 'resume' if was_claimed or job.get('operation') == 'resume' else 'parse'
    job['pause_requested'] = False
    job['resume_requested_at'] = time.time()
    frappe.db.set_value(TABLE, row['name'], {'job_json': canonical(job), 'status': 'Queued',
                                             'last_error': None})
    frappe.db.commit()
    return {'batch_id': row['name'], 'status': 'Queued', 'operation': job['operation']}


# -------------------------------------------------------------- quarantine retry
ACTIVE_JOB_STATUSES = ('Queued', 'Running', 'Paused')
MAX_RECOVERY_HISTORY = 20


def retry_batch(batch_id, document_ids, reason):
    """Audited technical recovery of quarantined items in one registered batch.

    Only the exact quarantined selection is re-driven from ``planned``; a
    successful item is never re-uploaded or re-embedded. The prior status,
    safe attempt error and native diagnostics stay on the item, and the request
    itself is appended to ``job_json.recoveries``. Repeating the same request
    while its job is still active is idempotent; once the item is processed the
    request is a no-op rejection instead of a second recovery.
    """
    _require(isinstance(batch_id, str) and BATCH_ID.fullmatch(batch_id) is not None)
    _require(isinstance(document_ids, list) and 1 <= len(document_ids) <= 50
             and len(set(document_ids)) == len(document_ids)
             and all(isinstance(value, str) and DOCUMENT_ID.fullmatch(value) is not None
                     for value in document_ids))
    reason = _bounded_text(reason, 200, minimum=3)
    row, frozen, state = m._row(batch_id, True)
    job = m._json(row, 'job_json', {})
    selection = sorted(document_ids)
    recovery_id = 'RCV_' + hashlib.sha256(_canonical_bytes(
        ['RC13_QUARANTINE_RETRY', batch_id, selection, reason])).hexdigest()[:24]
    if job.get('status') in ACTIVE_JOB_STATUSES:
        if job.get('retry_id') == recovery_id:
            return {'batch_id': batch_id, 'status': job.get('status'),
                    'job_id': job.get('id'), 'retry_id': recovery_id,
                    'retried_documents': len(selection), 'replayed': True}
        raise KnowledgeError('IMPORT_BUSY')
    chosen = set(selection)
    items = [item for item in state['items']
             if item.get('canonical_document_id') in chosen
             and item.get('disposition') not in ('SAME_CONTENT_SKIP', 'ALIAS')]
    _require(len(items) == len(selection))
    _require(all(item.get('status') == 'quarantined' for item in items))
    now = time.time()
    prior_statuses = {item['canonical_document_id']: item.get('status') for item in items}
    prior_attempts = {item['canonical_document_id']: item.get('attempt_error')
                      for item in items if isinstance(item.get('attempt_error'), str)}
    previous_job_status = job.get('status')
    for item in items:
        # Historical failure facts (attempt_error, private_parse_message,
        # actual_run, chunk_count) stay untouched; only the execution state is
        # reset so apply() uploads/parses the generated derivative again.
        item['status'] = 'planned'
        item['ragflow_document_id'] = None
        item['upload_sha256'] = None
        item['upload_name'] = None
        item['progress'] = 0
    job.update(status='Queued', operation='parse', document_ids=selection,
               requested_by=frappe.session.user, requested_at=now,
               lease_generation=int(job.get('lease_generation') or 0),
               nonce=None, lease_expires_at=None, pause_requested=False,
               retry_id=recovery_id)
    audit = {'id': recovery_id, 'kind': 'QUARANTINE_RETRY', 'at': now,
             'actor_hash': hashlib.sha256(str(frappe.session.user).encode()).hexdigest()[:16],
             'reason': reason, 'document_ids': selection,
             'prior_statuses': prior_statuses, 'prior_attempt_errors': prior_attempts,
             'previous_job_status': previous_job_status}
    job['recoveries'] = (list(job.get('recoveries') or []) + [audit])[-MAX_RECOVERY_HISTORY:]
    frappe.db.set_value(TABLE, batch_id, {'state_json': canonical(state),
                                          'job_json': canonical(job),
                                          'status': 'Queued', 'last_error': None})
    frappe.db.commit()
    return {'batch_id': batch_id, 'status': 'Queued', 'job_id': job.get('id'),
            'retry_id': recovery_id, 'retried_documents': len(items),
            'replayed': False}


# ---------------------------------------------------------------------- reclaim
def _expired_batches(batch_id=None):
    if batch_id is not None:
        _require(isinstance(batch_id, str) and batch_id.startswith('IMP_'))
        rows = frappe.db.sql(
            'SELECT name FROM `tabHBOS Knowledge Import Batch` WHERE name=%s AND status=%s '
            'FOR UPDATE', (batch_id, 'Running'), as_dict=True)
    else:
        rows = frappe.db.sql(
            'SELECT name FROM `tabHBOS Knowledge Import Batch` WHERE status=%s '
            'ORDER BY modified ASC LIMIT 20 FOR UPDATE', ('Running',), as_dict=True)
    return [row['name'] for row in rows]


def _reclaim_one(batch_id, actor, reason, now):
    row, frozen, state = m._row(batch_id, True)
    job = m._json(row, 'job_json', {})
    if job.get('status') != 'Running':
        return None
    lease = job.get('lease_expires_at')
    if isinstance(lease, (int, float)) and float(lease) >= now:
        return None
    previous_generation = int(job.get('lease_generation') or 0)
    nonce = job.get('nonce')
    entry = {'at': now,
             'actor_hash': hashlib.sha256(str(actor or '').encode()).hexdigest()[:16],
             'reason': reason,
             'previous_generation': previous_generation,
             'new_generation': previous_generation + 1,
             'previous_lease_expires_at': lease,
             'previous_nonce_sha256': hashlib.sha256(str(nonce).encode()).hexdigest() if nonce else None}
    job['lease_generation'] = previous_generation + 1
    job['nonce'] = None
    job['lease_expires_at'] = None
    job['status'] = 'Queued'
    job['pause_requested'] = False
    job['reclaims'] = (list(job.get('reclaims') or []) + [entry])[-MAX_RECLAIM_HISTORY:]
    frappe.db.set_value(TABLE, row['name'], {'job_json': canonical(job), 'status': 'Queued',
                                             'last_error': None})
    return {'batch_id': row['name'], 'new_lease_generation': job['lease_generation'],
            'previous_lease_generation': previous_generation,
            'previous_lease_expires_at': lease, 'reason': reason}


def reclaim_expired(actor=None, now=None, batch_id=None, reason=None):
    """Requeue only batches whose own lease has expired. Item states untouched."""
    now = time.time() if now is None else now
    reclaimed = []
    for name in _expired_batches(batch_id):
        entry = _reclaim_one(name, actor, reason or 'LEASE_EXPIRED', now)
        if entry is not None:
            reclaimed.append(entry)
    return reclaimed


def reclaim_batch(batch_id=None, reason=None):
    safe_reason = _bounded_text(reason, 200, minimum=3) if reason else 'MAINTAINER_RECLAIM'
    if batch_id:
        rows = _expired_batches(batch_id)
        if not rows:
            raise KnowledgeError('IMPORT_BUSY')
    reclaimed = reclaim_expired(actor=frappe.session.user, batch_id=batch_id, reason=safe_reason)
    frappe.db.commit()
    return {'reclaimed': reclaimed, 'total': len(reclaimed)}


# ------------------------------------------------------- retrieval verification
def mark_retrieval_pending(batch_id, publish_result):
    """Best-effort persistent 'awaiting employee verification' receipt."""
    if not isinstance(publish_result, dict):
        return {'pending': 0}
    row, frozen, state = m._row(batch_id, True)
    quality = m._json(row, 'quality_json', {})
    by_document = {item['canonical_document_id']: item for item in state['items']
                   if item.get('disposition') not in ('SAME_CONTENT_SKIP', 'ALIAS')}
    pending = 0
    for result in publish_result.get('results') or []:
        if not isinstance(result, dict) or result.get('outcome') not in PUBLISHED_OUTCOMES:
            continue
        item = by_document.get(result.get('document_id'))
        if item is None:
            continue
        record = quality.setdefault(item['version_id'], {})
        existing = record.get('retrieval_verified')
        if isinstance(existing, dict) and existing.get('status') in ('PENDING', 'VERIFIED'):
            continue
        record['retrieval_verified'] = {
            'schema': VERIFICATION_SCHEMA, 'status': 'PENDING', 'at': time.time(),
            'document_id': item['canonical_document_id'], 'version_id': item['version_id'],
            'publication_receipt_id': result.get('receipt_id'),
            'binding': {'space_id': item.get('space_id'), 'dataset_id': item.get('dataset_id'),
                        'binding_revision': item.get('binding_revision')},
            'note': 'Published; wait for a real employee search + evidence resolution receipt.'}
        pending += 1
    if pending:
        frappe.db.set_value(TABLE, batch_id, 'quality_json', canonical(quality))
        frappe.db.commit()
    return {'pending': pending}


def _history_verification(owner_user, query_sha256, document_id, version_id):
    """Server-side cross-check: a real employee search row must exist."""
    rows = frappe.get_all('HBOS Knowledge Activity',
                          filters={'kind': 'History', 'owner_user': owner_user},
                          fields=['name', 'payload_json', 'creation'],
                          order_by='creation desc', limit_page_length=20)
    cutoff = time.time() - VERIFICATION_WINDOW_SECONDS
    for row in rows:
        created = row.get('creation')
        if isinstance(created, str):
            try:
                created = time.mktime(time.strptime(created[:19], '%Y-%m-%d %H:%M:%S'))
            except ValueError:
                created = None
        stamp = created.timestamp() if hasattr(created, 'timestamp') else (
            float(created) if isinstance(created, (int, float)) else None)
        if stamp is not None and stamp < cutoff:
            continue
        try:
            payload = json.loads(row.get('payload_json') or '{}')
        except (ValueError, TypeError):
            continue
        if not isinstance(payload, dict):
            continue
        query = payload.get('query')
        if not isinstance(query, str) or hashlib.sha256(query.encode()).hexdigest() != query_sha256:
            continue
        references = payload.get('references') or []
        for reference in references:
            if (isinstance(reference, list) and len(reference) >= 2
                    and reference[0] == document_id and reference[1] == version_id):
                return row.get('name')
    return None


def _evidence_verification(evidence_id, document_id, version_id):
    """Server-side cross-check: the evidence id must be a live issued binding."""
    if not isinstance(evidence_id, str) or not 1 <= len(evidence_id) <= 128:
        raise KnowledgeError('EVIDENCE_UNAVAILABLE')
    from .runtime import load_runtime
    from . import evidence as evidence_module
    runtime = load_runtime()
    cache = getattr(runtime, 'cache', None)
    if cache is None:
        raise KnowledgeError('POLICY_UNAVAILABLE')
    payload = cache.get_value(evidence_module._evidence_key(evidence_id), expires=True)
    if not isinstance(payload, dict) or payload.get('schema') != evidence_module.EVIDENCE_SCHEMA:
        raise KnowledgeError('EVIDENCE_UNAVAILABLE')
    reference_id = payload.get('reference_id')
    if not isinstance(reference_id, str) or not reference_id:
        raise KnowledgeError('EVIDENCE_UNAVAILABLE')
    reference = runtime.references.get(reference_id)
    if reference is None:
        raise KnowledgeError('EVIDENCE_UNAVAILABLE')
    binding = reference.binding
    if (binding.canonical_document_id != document_id or binding.version_id != version_id):
        raise KnowledgeError('EVIDENCE_UNAVAILABLE')
    if reference.actor is None or not getattr(reference.actor, 'user_ref', None):
        raise KnowledgeError('EVIDENCE_UNAVAILABLE')
    now = runtime.provider.clock()
    if not isinstance(reference.expires_at, (int, float)) or now >= reference.expires_at:
        raise KnowledgeError('EVIDENCE_UNAVAILABLE')
    return {'reference': reference, 'binding': binding, 'actor_user': reference.actor.user_ref}


def record_verification(batch_id, document_id, version_id, evidence_id, query_sha256):
    """Persist a receipt only when the server can verify the employee evidence.

    A browser checkbox cannot reach this path: the caller must present the
    opaque evidence id that a real signed employee search returned, plus the
    hash of that search query. The server then re-reads (a) the short-lived
    evidence cache entry bound to this exact document/version and (b) that
    employee's persisted History row carrying the same query hash and the exact
    reference. No approval or publication row is created here.
    """
    _require(isinstance(batch_id, str) and BATCH_ID.fullmatch(batch_id) is not None)
    _require(isinstance(document_id, str) and DOCUMENT_ID.fullmatch(document_id) is not None)
    _require(isinstance(version_id, str) and VERSION_ID.fullmatch(version_id) is not None)
    _require(isinstance(query_sha256, str) and HEX64.fullmatch(query_sha256) is not None)
    row, frozen, state = m._row(batch_id, True)
    items = [item for item in state['items']
             if item.get('canonical_document_id') == document_id
             and item.get('version_id') == version_id
             and item.get('disposition') not in ('SAME_CONTENT_SKIP', 'ALIAS')]
    _require(len(items) == 1)
    item = items[0]
    if item.get('status') != 'parsed/indexed':
        raise KnowledgeError('QUALITY_REQUIRED')
    published = frappe.db.get_value('HBOS Knowledge Document', document_id,
                                    ['current_version', 'withdrawn', 'ingestion_status'], as_dict=True)
    if (not published or published.get('withdrawn')
            or published.get('current_version') != version_id
            or published.get('ingestion_status') != 'published'):
        raise KnowledgeError('SOURCE_VERSION_STALE')
    verified = _evidence_verification(evidence_id, document_id, version_id)
    activity = _history_verification(verified['actor_user'], query_sha256, document_id, version_id)
    if not activity:
        raise KnowledgeError('EVIDENCE_UNAVAILABLE')
    evidence_id_hash = hashlib.sha256(evidence_id.encode()).hexdigest()
    quality = m._json(row, 'quality_json', {})
    record = quality.setdefault(version_id, {})
    existing = record.get('retrieval_verified')
    if (isinstance(existing, dict) and existing.get('status') == 'VERIFIED'
            and existing.get('query_sha256') == query_sha256
            and existing.get('evidence_id_hash') == evidence_id_hash):
        return {'batch_id': batch_id, 'document_id': document_id, 'version_id': version_id,
                'receipt': existing, 'replayed': True}
    receipt = {'schema': VERIFICATION_SCHEMA, 'status': 'VERIFIED', 'result': 'VERIFIED',
               'at': time.time(),
               'actor_hash': hashlib.sha256(str(verified['actor_user']).encode()).hexdigest()[:16],
               'query_sha256': query_sha256, 'evidence_id_hash': evidence_id_hash,
               'activity_ref': hashlib.sha256(str(activity).encode()).hexdigest()[:16],
               'document_id': document_id, 'version_id': version_id,
               'binding': {'space_id': item.get('space_id'), 'dataset_id': item.get('dataset_id'),
                           'binding_revision': item.get('binding_revision')},
               'published_current_version': published.get('current_version')}
    receipt['receipt_sha256'] = hashlib.sha256(_canonical_bytes(receipt)).hexdigest()
    history = list(record.get('retrieval_verified_history') or [])
    if isinstance(existing, dict):
        history = (history + [existing])[-5:]
    if history:
        record['retrieval_verified_history'] = history
    record['retrieval_verified'] = receipt
    frappe.db.set_value(TABLE, batch_id, 'quality_json', canonical(quality))
    frappe.db.commit()
    return {'batch_id': batch_id, 'document_id': document_id, 'version_id': version_id,
            'receipt': receipt, 'replayed': False}


# --------------------------------------------------------------------- API entry
def _action(method, fields, fn):
    from .api import _maintenance_action
    return _maintenance_action(method, fields, fn)


@frappe.whitelist(methods=['POST'])
def plan_import(manifest=None, **fields):
    return _action('plan_import', fields, lambda: plan_batch(manifest))


@frappe.whitelist(methods=['POST'])
def submit_import(plan_sha256=None, approval_ref=None, label=None, **fields):
    return _action('submit_import', fields,
                   lambda: submit_batch(plan_sha256, approval_ref, label))


@frappe.whitelist(methods=['GET'])
def batch_progress(batch_id=None, page=1, limit=20, page_size=None, **fields):
    effective = limit if page_size in (None, 20) else page_size
    return _action('batch_progress', fields,
                   lambda: progress_batch(batch_id, page, effective))


@frappe.whitelist(methods=['POST'])
def pause_import(batch_id=None, **fields):
    return _action('pause_import', fields, lambda: pause_batch(batch_id))


@frappe.whitelist(methods=['POST'])
def resume_import(batch_id=None, **fields):
    return _action('resume_import', fields, lambda: resume_batch(batch_id))


@frappe.whitelist(methods=['POST'])
def retry_import(batch_id=None, document_ids=None, reason=None, **fields):
    return _action('retry_import', fields,
                   lambda: retry_batch(batch_id, document_ids, reason))


@frappe.whitelist(methods=['POST'])
def reclaim_import(batch_id=None, reason=None, **fields):
    return _action('reclaim_import', fields, lambda: reclaim_batch(batch_id, reason))


@frappe.whitelist(methods=['POST'])
def record_retrieval_verified(batch_id=None, document_id=None, version_id=None,
                              evidence_id=None, query_sha256=None, **fields):
    return _action('record_retrieval_verified', fields,
                   lambda: record_verification(batch_id, document_id, version_id,
                                               evidence_id, query_sha256))
