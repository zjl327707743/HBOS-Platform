"""MC-1: the maintenance rows carry server-derived allowed actions and an overview.

The client must never infer an action: the server offers one only when its own
state proves it is legal. These are synthetic checks over the pure helpers.
"""
import sys
from types import ModuleType

if 'frappe' not in sys.modules:
    sys.modules['frappe'] = ModuleType('frappe')
sys.modules.setdefault('pymysql', ModuleType('pymysql'))
_cipher = ModuleType('cryptography.fernet'); _cipher.Fernet = lambda *a, **k: None
sys.modules.setdefault('cryptography', ModuleType('cryptography'))
sys.modules.setdefault('cryptography.fernet', _cipher)

from hb_knowledge_app.hb_knowledge.maintenance import _allowed_actions, overview_counts  # noqa: E402


def test_unpublished_clean_shared_row_can_publish():
    actions = _allowed_actions('Unpublished', 'Passed', True)
    assert actions == ['open', 'view', 'publish']


def test_unpublished_unverified_row_must_check_quality_and_sharing():
    actions = _allowed_actions('Unpublished', 'Pending', False)
    assert actions == ['open', 'view', 'quality_check', 'approve_sharing']
    assert 'publish' not in actions


def test_published_row_offers_withdraw_and_replace_but_not_publish():
    actions = _allowed_actions('Published', 'Passed', True)
    assert actions == ['open', 'view', 'withdraw', 'replace']


def test_withdrawn_row_offers_restore_and_replace():
    actions = _allowed_actions('Withdrawn', 'Passed', True)
    assert actions == ['open', 'view', 'restore', 'replace']


def test_pending_quality_and_pending_sharing_are_both_offered():
    actions = _allowed_actions('Unpublished', 'Failed', False)
    assert 'quality_check' in actions and 'approve_sharing' in actions and 'publish' not in actions


def test_actions_are_deduplicated_and_ordered():
    actions = _allowed_actions('Published', 'Pending', False)
    assert actions == ['open', 'view', 'quality_check', 'approve_sharing', 'withdraw', 'replace']
    assert len(actions) == len(set(actions))


def test_overview_is_counts_only_and_tolerates_none():
    assert overview_counts(None, None, None, None) == {
        'published_total': 0, 'pending_quality_check': 0, 'sharing_pending': 0, 'feedback_pending': 0}
    assert overview_counts(1103, 12, 7, 3) == {
        'published_total': 1103, 'pending_quality_check': 12, 'sharing_pending': 7, 'feedback_pending': 3}
