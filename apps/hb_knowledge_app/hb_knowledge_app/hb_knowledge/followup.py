"""Real conversation history, and a retrieval query for referential follow-ups.

Two different needs, deliberately kept apart:

* the *generation* model receives the previous user/assistant turns as
  ``history``, so it can resolve "上一条" against real dialogue;
* *retrieval* still needs a query that names the topic. A bare follow-up such
  as "上一条是什么意思" contains no topic words at all, so using it verbatim
  retrieved unrelated documents (observed: an incubator question followed by
  "上一条是什么意思" retrieved 安全生产法, and the answer had to degrade).

``retrieval_query`` therefore rewrites only when the follow-up carries a
reference and no topic of its own, and only by *reusing the previous question
verbatim* — never by inventing words. The raw question is what the user sees and
what the history stores.
"""
import re

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


# A follow-up that points at the previous turn instead of naming a topic.
_REFERENTIAL=re.compile(
    r'(?:上一条|上一条回答|上面(?:那|这)?条?|前面(?:那|这)?(?:条|个|句)?|刚才(?:那|说)?|'
    r'它|其|该(?:条|项|要求|规程|文件)|这条|那条|'
    r'用三句话|三句话|总结一下|再总结|简要总结|什么意思|是什么含义|展开说说|详细说说|举个例子)')
# Topic words that make the follow-up self-contained; then no rewrite is needed.
_TOPIC=re.compile(
    r'(?:SOP|GB|TSD|URS|[A-Z]{2,6}-[A-Z0-9]|规程|条例|办法|规定|标准|手册|制度|'
    r'培养箱|灭菌|分装|结晶|洁净|纯化水|注射用水|压力|温度|时间|记录|培训|法规)')


def retrieval_query(question, previous):
    """The query retrieval should use for this turn.

    Returns ``question`` unchanged unless it is a bare reference. When it is,
    the previous question is prepended so the topic is present; the follow-up's
    own words are kept after it so an explicit narrowing still applies.
    """
    value=(question or '').strip()
    if not value or previous is None:return value
    if not _REFERENTIAL.search(value):return value
    if _TOPIC.search(value):return value
    prior=(previous.get('query') or '').strip()
    if not prior:return value
    return f'{prior[:200]} {value}'[:500]
