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

from .document_assets import MAX_DOWNLOAD_BYTES, MAX_FILE_BYTES, disposition, unavailable
from .document_reader_contract import normalize_document_read
from .errors import KnowledgeError

# Short-lived by design; the client renews it silently when it lapses, so a
# reader never has to understand a ticket. The whole fetch starts well inside
# this window and a stream is never cut off by it.
TICKET_SECONDS = 60
_TICKET = re.compile(r'[A-Za-z0-9_-]{40,64}')
CONTENT_PATH = '/api/method/hb_knowledge_app.hb_knowledge.api.document_content'
_LOG = logging.getLogger('hbos.knowledge.document_delivery')


@dataclass(frozen=True)
class Content:
    body: bytes | None
    status: int
    headers: dict
    stream: object | None = None


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
                # The check is structural only: hashing a 400 MB original just
                # to answer "can this be downloaded" would stall the reader.
                # A file that is served to the browser may be larger than the
                # in-memory preview cap: previews and originals share the wider
                # delivery limit, and both are still verified before sending.
                original.probe(limit=MAX_DOWNLOAD_BYTES)
                if asset.path != original.path:
                    asset.probe(limit=MAX_DOWNLOAD_BYTES)
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
        original.probe(limit=MAX_DOWNLOAD_BYTES)
        if asset.path != original.path:
            asset.probe(limit=MAX_DOWNLOAD_BYTES)
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
            # A derived preview never replaces source verification: the original
            # is still hashed on every content request. The hash reads the whole
            # file, so it carries the delivery ceiling - the preview of a large
            # original was refused here with the in-memory 32 MiB cap.
            original.read('bytes=0-0', limit=MAX_DOWNLOAD_BYTES)
        size = asset.probe(limit=MAX_DOWNLOAD_BYTES)
        if range_header is not None or size <= MAX_FILE_BYTES:
            # A bounded range or a normally sized file is verified and returned
            # in one piece; the range path still verifies the whole file first
            # and still re-checks the current authorization before any byte.
            body, status, start, end, size = asset.read(range_header, limit=MAX_DOWNLOAD_BYTES)
            self.runtime.checkpoint('document_delivery_before_final')
            self.runtime.provider.revalidate(plan)
            if purpose == 'download' and not self._download_allowed(actor, binding, original.sha256):
                raise unavailable('DOWNLOAD_NOT_AUTHORIZED')
            if record['expires_at'] <= self.clock():
                raise unavailable('TICKET_EXPIRED')
            self._deliver_log(actor, record, purpose, size, streamed=False)
            headers = self._headers(asset, purpose, status, size)
            if status == 206:
                headers['Content-Range'] = f'bytes {start}-{end}/{size}'
            return Content(body, status, headers)
        # A full file is verified in one pass and then streamed, so a large
        # published standard never sits in the worker's memory.
        stream, size = asset.open_stream()
        self.runtime.checkpoint('document_delivery_before_final')
        self.runtime.provider.revalidate(plan)
        if purpose == 'download' and not self._download_allowed(actor, binding, original.sha256):
            stream.close()
            raise unavailable('DOWNLOAD_NOT_AUTHORIZED')
        # An expiry crossed during the verified read does not extend a ticket.
        if record['expires_at'] <= self.clock():
            stream.close()
            raise unavailable('TICKET_EXPIRED')
        self._deliver_log(actor, record, purpose, size, streamed=True)
        headers = self._headers(asset, purpose, 200, size)
        headers['Accept-Ranges'] = 'none'
        return Content(None, 200, headers, stream=stream)

    def _deliver_log(self, actor, record, purpose, size, *, streamed):
        action = 'document.preview' if purpose == 'preview' else 'document.download'
        self.runtime.audit.record(actor.user_ref, action.replace('.', '_'), 'SUCCESS', 1)
        _LOG.info(json.dumps({'event': 'DOCUMENT_DELIVERED', 'action': action,
                             'document_sha256': hashlib.sha256(record['document_id'].encode()).hexdigest(),
                             'bytes': size, 'streamed': streamed}))

    @staticmethod
    def _headers(asset, purpose, status, size):
        return {'Content-Type': asset.content_type,
                'Content-Disposition': disposition(asset.filename, purpose == 'preview'),
                'X-Content-Type-Options': 'nosniff',
                'Cache-Control': 'private, no-store, max-age=0', 'Pragma': 'no-cache',
                'Referrer-Policy': 'no-referrer', 'X-Frame-Options': 'SAMEORIGIN',
                'Cross-Origin-Resource-Policy': 'same-origin',
                'Content-Security-Policy': "sandbox; default-src 'none'; frame-ancestors 'self'",
                'Accept-Ranges': 'bytes', 'Content-Length': str(size)}


def build_delivery(runtime, cfg, state):
    from .document_assets import LocalDocumentAssets, current_source_hash
    return DocumentDelivery(runtime, LocalDocumentAssets(
        cfg.get('document_asset_manifest'), cfg.get('document_asset_roots'), current_source_hash), state)
