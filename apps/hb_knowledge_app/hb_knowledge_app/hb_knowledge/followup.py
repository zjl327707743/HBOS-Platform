"""Real conversation history for the generation model.

The old path concatenated ``前一问题；追问：...`` into one query string.
That conflated retrieval rewriting with dialogue context. The BFF now keeps
the raw follow-up question as the retrieval query and passes the previous
user/assistant turns separately through the signed request (``history``),
so the generation model can resolve references without altering retrieval.
"""
from .errors import KnowledgeError

UNRESOLVED_FOLLOWUP = '无法可靠定位前一回答中的具体条目。请指出步骤名称或关键词后再问；当前资料不足以直接回答这个追问。'

MAX_TURNS = 2          # Previous turn plus the turn before it, bounded.
MAX_TOTAL_CHARS = 12000
MAX_TURN_CHARS = 2000


def validate_followup_scope(previous,space_ids,context):
    if (sorted(previous.get('space_ids') or [])!=sorted(space_ids or [])
            or dict(previous.get('context') or {})!=dict(context or {})):
        raise KnowledgeError('INVALID_REQUEST')


def _turn(role,text):
    value=(text or '').strip()
    if not value:return None
    if len(value)>MAX_TURN_CHARS:value=value[-MAX_TURN_CHARS:]
    return {'role':role,'content':value}


def conversation_history(previous, *, older=None):
    """Bounded dialogue turns (user/assistant) in chronological order.

    ``previous`` is the last stored History row (query + answer). ``older``
    may supply the turn before it. Answers that are not real answers
    (REFERENCE_ONLY / INSUFFICIENT_EVIDENCE placeholders) are still useful
    dialogue context, so they are kept; the generation model treats history
    as context, never as authority.
    """
    history=[]
    if older is not None:
        user=_turn('user',older.get('query'));assistant=_turn('assistant',older.get('answer'))
        if user is not None and assistant is not None:
            history.append(user);history.append(assistant)
    user=_turn('user',previous.get('query'));assistant=_turn('assistant',previous.get('answer'))
    if user is not None and assistant is not None:
        history.append(user);history.append(assistant)
    total=sum(len(t['content']) for t in history)
    # Keep the newest turns first when the budget is exceeded.
    while total>MAX_TOTAL_CHARS and history:
        removed=history.pop(0);total-=len(removed['content'])
    return tuple(history)
