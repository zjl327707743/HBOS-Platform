"""Authorized PDF layout preview and separately granted original delivery.

An opaque short-lived ticket names an immutable logical version. It is not an
authorization: every content/range request obtains a new native actor, current
read plan, download decision (when applicable), original digest, and final
policy revalidation before returning bytes. No RAGFlow credential or physical
identifier enters the public contract.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import logging
import re
import secrets
import time

from .document_assets import disposition, unavailable
from .document_reader_contract import normalize_document_read
from .errors import KnowledgeError

TICKET_SECONDS = 60
_TICKET = re.compile(r'[A-Za-z0-9_-]{40,64}')
CONTENT_PATH = '/api/method/hb_knowledge_app.hb_knowledge.api.document_content'
_LOG = logging.getLogger('hbos.knowledge.document_delivery')


@dataclass(frozen=True)
class Content:
    body: bytes
    status: int
    headers: dict


class DocumentDelivery:
    def __init__(self, runtime, assets, state, *, clock=time.time):
        self.runtime, self.assets, self.state, self.clock = runtime, assets, state, clock

    def _authorize(self, document_id, version_id, request_id):
        raw = {'document_id': document_id}
        if version_id is not None:
            raw['version_id'] = version_id
        request = normalize_document_read(raw)
        actor = self.runtime.actor()
        plan = self.runtime.provider.evaluate(actor, self.runtime.client, 'document.read',
                                             request, request_id)
        if (plan.action != 'document.read' or len(plan.bindings) != 1
                or plan.bindings[0].canonical_document_id != document_id
                or version_id is not None and plan.bindings[0].version_id != version_id):
            raise KnowledgeError('SCOPE_REJECTED')
        return actor, plan, plan.bindings[0]

    def _download_allowed(self, actor, binding, source_sha256):
        decide = getattr(self.runtime.provider, 'authorize_download', None)
        return callable(decide) and decide(actor, self.runtime.client, binding, source_sha256) is True

    def capabilities(self, document_id, version_id, request_id):
        actor, plan, binding = self._authorize(document_id, version_id, request_id)
        data = {'document_id': document_id, 'version_id': binding.version_id,
                'can_read': True, 'can_preview': False, 'can_download': False,
                'preview_kind': None, 'preview_reason': 'PREVIEW_UNAVAILABLE',
                'download_reason': 'DOWNLOAD_NOT_AUTHORIZED'}
        for purpose in ('download', 'preview'):
            try:
                asset, original = self.assets.resolve(binding, purpose)
                allowed = purpose == 'preview' or self._download_allowed(actor, binding, original.sha256)
                if not allowed:
                    continue
                # A capability is truthful about the mapped bytes at this
                # moment, while the content request will check everything again.
                original.read('bytes=0-0')
                if asset.path != original.path:
                    asset.read('bytes=0-0')
                data['can_' + purpose] = True
                data[purpose + '_reason'] = None
                if purpose == 'preview':
                    data['preview_kind'] = asset.kind
            except KnowledgeError as error:
                if error.code != 'DOCUMENT_DELIVERY_UNAVAILABLE':
                    raise
                data[purpose + '_reason'] = error.state
        self.runtime.provider.revalidate(plan)
        # Check the independent action again after file inspection as well.
        if data['can_download'] and not self._download_allowed(actor, binding, self.assets.resolve(binding, 'download')[0].sha256):
            data['can_download'], data['download_reason'] = False, 'DOWNLOAD_NOT_AUTHORIZED'
        return data

    def prepare(self, document_id, version_id, purpose, request_id):
        if purpose not in {'preview', 'download'} or version_id is None:
            raise KnowledgeError('INVALID_REQUEST')
        actor, plan, binding = self._authorize(document_id, version_id, request_id)
        asset, original = self.assets.resolve(binding, purpose)
        if purpose == 'download' and not self._download_allowed(actor, binding, original.sha256):
            raise unavailable('DOWNLOAD_NOT_AUTHORIZED')
        original.read('bytes=0-0')
        if asset.path != original.path:
            asset.read('bytes=0-0')
        self.runtime.provider.revalidate(plan)
        if purpose == 'download' and not self._download_allowed(actor, binding, original.sha256):
            raise unavailable('DOWNLOAD_NOT_AUTHORIZED')
        ticket = secrets.token_urlsafe(32)
        expires = int(self.clock()) + TICKET_SECONDS
        record = {'subject': actor.user_ref, 'session': actor.session_ref,
                  'session_revision': actor.session_revision, 'client': self.runtime.client.client_id,
                  'document_id': document_id, 'version_id': binding.version_id,
                  'purpose': purpose, 'source_sha256': original.sha256,
                  'asset_sha256': asset.sha256, 'expires_at': expires}
        if not self.state.set(self._key(ticket), json.dumps(record), ex=TICKET_SECONDS, nx=True):
            raise KnowledgeError('SERVICE_ERROR')
        return {'content_url': CONTENT_PATH + '?ticket=' + ticket,
                'expires_at': expires, 'filename': asset.filename,
                'content_type': asset.content_type, 'sha256': asset.sha256, 'kind': asset.kind}

    @staticmethod
    def _key(ticket):
        return 'document-delivery:' + hashlib.sha256(ticket.encode()).hexdigest()

    def content(self, ticket, range_header, request_id):
        if not isinstance(ticket, str) or not _TICKET.fullmatch(ticket):
            raise KnowledgeError('INVALID_REQUEST')
        actor = self.runtime.actor()  # Guest must fail even for a random ticket.
        raw = self.state.get(self._key(ticket))
        try:
            record = json.loads(raw) if raw else None
            if not isinstance(record, dict) or record['expires_at'] <= self.clock():
                raise unavailable('TICKET_EXPIRED')
            if (record['subject'], record['session'], record['session_revision'], record['client']) != (
                    actor.user_ref, actor.session_ref, actor.session_revision,
                    self.runtime.client.client_id):
                raise KnowledgeError('SCOPE_REJECTED')
        except KnowledgeError:
            raise
        except (ValueError, KeyError, TypeError):
            raise unavailable('TICKET_EXPIRED') from None
        actor, plan, binding = self._authorize(record['document_id'], record['version_id'], request_id)
        purpose = record['purpose']
        if purpose not in {'preview', 'download'}:
            raise KnowledgeError('SCOPE_REJECTED')
        asset, original = self.assets.resolve(binding, purpose)
        if (asset.sha256 != record['asset_sha256'] or original.sha256 != record['source_sha256']):
            raise unavailable('ASSET_HASH_MISMATCH')
        if purpose == 'download' and not self._download_allowed(actor, binding, original.sha256):
            raise unavailable('DOWNLOAD_NOT_AUTHORIZED')
        if asset.path != original.path:
            original.read('bytes=0-0')
        body, status, start, end, size = asset.read(range_header)
        self.runtime.checkpoint('document_delivery_before_final')
        self.runtime.provider.revalidate(plan)
        if purpose == 'download' and not self._download_allowed(actor, binding, original.sha256):
            raise unavailable('DOWNLOAD_NOT_AUTHORIZED')
        # An expiry crossed during a bounded file read does not extend a ticket.
        if record['expires_at'] <= self.clock():
            raise unavailable('TICKET_EXPIRED')
        action = 'document.preview' if purpose == 'preview' else 'document.download'
        self.runtime.audit.record(actor.user_ref, action.replace('.', '_'), 'SUCCESS', 1)
        _LOG.info(json.dumps({'event': 'DOCUMENT_DELIVERED', 'action': action,
                             'document_sha256': hashlib.sha256(record['document_id'].encode()).hexdigest(),
                             'bytes': len(body), 'partial': status == 206}))
        headers = {'Content-Type': asset.content_type,
                   'Content-Disposition': disposition(asset.filename, purpose == 'preview'),
                   'X-Content-Type-Options': 'nosniff',
                   'Cache-Control': 'private, no-store, max-age=0', 'Pragma': 'no-cache',
                   'Referrer-Policy': 'no-referrer', 'X-Frame-Options': 'SAMEORIGIN',
                   'Cross-Origin-Resource-Policy': 'same-origin',
                   'Content-Security-Policy': "sandbox; default-src 'none'; frame-ancestors 'self'",
                   'Accept-Ranges': 'bytes', 'Content-Length': str(len(body))}
        if status == 206:
            headers['Content-Range'] = f'bytes {start}-{end}/{size}'
        return Content(body, status, headers)


def build_delivery(runtime, cfg, state):
    from .document_assets import LocalDocumentAssets, current_source_hash
    return DocumentDelivery(runtime, LocalDocumentAssets(
        cfg.get('document_asset_manifest'), cfg.get('document_asset_roots'), current_source_hash), state)
