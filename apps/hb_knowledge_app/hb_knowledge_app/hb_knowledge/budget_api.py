"""Candidate budget authority over the existing private signed BFF transport."""

import frappe

from .errors import KnowledgeError
from .frappe_factory import _authority_envelope, _service_request, configuration


RESERVE_FIELDS = {'operation_id', 'attempt_id', 'request_id', 'model', 'request_sha256', 'input_bound', 'output_bound'}
SETTLE_FIELDS = {'attempt_id', 'result'}


@frappe.whitelist(allow_guest=True, methods=['POST'])
def checkpoint(**ignored):
    def run():
        from knowledge_service.provider_budget import BudgetStopped
        from knowledge_service.provider_epoch import HARNESS_LANE, local_epoch

        raw, principal, _ = _service_request(max_body=8192)
        if not isinstance(raw, dict) or set(raw) != {'action', 'lane', 'args'} or not isinstance(raw['args'], dict):
            raise KnowledgeError('INVALID_REQUEST')
        caller = frappe.request.headers.get('X-HBOS-Caller')
        admitted = configuration().get('provider_epoch_callers', {}).get(caller) or {}
        lane, action, args = raw['lane'], raw['action'], raw['args']
        if (admitted.get('origin') != principal.client.client_id or not isinstance(lane, str)
                or lane not in admitted.get('lanes', ())):
            raise KnowledgeError('CLIENT_AUTH_FAILED')
        epoch = local_epoch()
        if epoch is None:
            raise KnowledgeError('ANSWER_BUDGET_BLOCKED')
        budget = {'owner': caller}
        if lane == HARNESS_LANE:
            budget['harness_grant'] = admitted.get('harness_child')
        try:
            if action == 'status' and not args:
                return {'status': epoch.status(lane, **budget)}
            fields = set(args)
            if action == 'reserve' and RESERVE_FIELDS <= fields <= RESERVE_FIELDS | {'parent_attempt_id', 'retry_reason'}:
                allowed_requests = admitted.get('reserve_request_ids')
                if allowed_requests is not None and args['request_id'] not in allowed_requests.get(lane, ()):
                    raise KnowledgeError('CLIENT_AUTH_FAILED')
                return {'attempt_id': epoch.reserve(lane, **budget, **args)}
            if action == 'settle' and SETTLE_FIELDS <= fields <= SETTLE_FIELDS | {
                    'provider_request_id', 'input_tokens', 'output_tokens'}:
                epoch.settle(lane_name=lane, owner=caller, **args)
                return {'settled': True}
        except BudgetStopped:
            raise KnowledgeError('ANSWER_BUDGET_BLOCKED') from None
        raise KnowledgeError('INVALID_REQUEST')

    return _authority_envelope(run)
