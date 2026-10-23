"""Authorized directory statistics, answered without the knowledge gateway.

A question such as 知识库共有多少份文件 asks for metadata, not a document
answer. It used to pay the full ask path: the BFF called the service, the
service classified it and rebuilt the catalogue, and about four seconds of a
five-and-a-half second request went into that round trip for a count over the
bindings this request already holds.

This module renders that answer from the plan the ask path already built, so
identity, department scope, publication state, withdrawal and current-version
rules are exactly the plan's. It never reads a global total: every number counts
bindings the caller is authorized to see. Portal and MCP both reach it through
``api.ask``, so there is one business rule.

The phase path is the one the BFF already uses for its own metadata reads
(``activity.restore``): ``introspect`` → ``cache_read`` → ``pre_projection`` →
``final_publish``. It is completed through the same decision store and the same
principal as the normal path - nothing here fabricates a phase.
"""
from __future__ import annotations

import time

# Same caps the service catalogue uses, so the web and MCP answers to the same
# question stay recognisably the same and the header can never disagree with
# the body.
PER_SPACE = 15
ANSWER_MAX = 1800

# The service's subject matcher, kept identical: a named subject narrows the
# directory instead of dumping every space.
SUBJECTS = (
    (('法律', '法规', '条例', '办法', '规定', '标准', 'GMP', '药典', '环保', '安全法', '消防', '计量'), '法律法规',
     ('DEPT_PUBLIC_LAW',), ('法', '条例', '办法', '规定', '标准', '准则', '规范')),
    (('安全培训', '安全资料', '安全教育', '培训资料'), '安全培训资料',
     ('DEPT_SAFETY',), ('培训', '安全', '教育', '演练', '应急')),
    (('人事', '员工手册', '考勤', '薪酬', '招聘', '劳动合同'), '人事资料',
     ('DEPT_HR',), ('人事', '员工', '考勤', '薪', '招聘', '劳动', '手册')),
    (('设备', '工程', '图纸', '建模', 'CAD', '图号'), '设备工程资料',
     ('DEPT_ENGINEERING',), ('设备', '图纸', '图号', '工程', '建模', '清单')),
    (('无菌', '洁净区', '无菌车间'), '无菌车间资料',
     ('DEPT_PRODUCTION',), ('无菌', '洁净', '车间')),
    (('生产', '工艺', '规程', 'SOP'), '生产部门资料',
     ('DEPT_PRODUCTION',), ('生产', '工艺', '规程', '操作')),
)


def focus(query, titles):
    """The spaces a directory question names, and its title matcher."""
    q = (query or '').casefold()
    for words, label, spaces, title_words in SUBJECTS:
        if any(word.casefold() in q for word in words):
            lowered = tuple(word.casefold() for word in title_words)
            return {'kind': label, 'label': label, 'spaces': tuple(spaces),
                    'match': lambda binding, lowered=lowered: any(
                        word in (getattr(binding, 'title', None) or '').casefold()
                        for word in lowered)}
    return {'kind': 'ALL', 'label': None, 'spaces': (), 'match': lambda binding: True}


def counts(plan, titles, query):
    """(space_id, items) groups for the authorized bindings of this plan.

    One entry per document: a second version of the same document is not a
    second document, and the service counts it the same way.
    """
    chosen = focus(query, titles)
    by_space = {}
    for binding in getattr(plan, 'bindings', ()) or ():
        space = getattr(binding, 'space_id', None)
        if not space:
            continue
        by_space.setdefault(space, {})[binding.canonical_document_id] = binding
    allowed = set(getattr(plan, 'space_ids', ()) or ()) or set(by_space)
    observed = chosen['spaces'] if chosen['spaces'] else sorted(by_space)
    groups = []
    for space in observed:
        if space not in by_space or space not in allowed:
            continue
        items = [b for b in by_space[space].values() if chosen['match'](b)]
        if items:
            groups.append((space, items))
    return groups, chosen


def render(plan, titles, query, *, now=None):
    """The statistics answer for the bindings this caller is authorized to see."""
    titles = dict(titles or {})
    groups, chosen = counts(plan, titles, query)
    total = sum(len(items) for _, items in groups)
    if not groups:
        scope = '、'.join(titles.get(s, s) for s in
                         (getattr(plan, 'space_ids', ()) or ())) or '全部已共享范围'
        return (f'在已共享资料（{scope}）中没有找到与“{query}”匹配的目录项。'
                '可以尝试更具体的关键词或文号，或打开“资料目录”按部门浏览。'), False
    as_of = time.strftime('%Y-%m-%d %H:%M', time.localtime(now))
    lines, shown, omitted = [], [], 0
    for index, (space, items) in enumerate(groups):
        items.sort(key=lambda b: (getattr(b, 'title', None) or ''))
        block = [f'【{titles.get(space, space)}】共 {len(items)} 份']
        block += [f'- 《{getattr(b, "title", None)}》' +
                  (f'（文号 {b.document_number}）' if getattr(b, 'document_number', None) else '')
                  for b in items[:PER_SPACE]]
        if len(items) > PER_SPACE:
            block.append(f'- …等其余 {len(items) - PER_SPACE} 份')
        text = '\n'.join(block)
        # Leave room for the omission note; the answer is sliced to a fixed
        # size, so a full budget pushes the note off the end.
        if len('\n'.join(lines)) + len(text) + 200 > ANSWER_MAX:
            omitted = len(groups) - index
            break
        lines.append(text)
        shown.append(space)
    if omitted:
        rest = sum(len(items) for _, items in groups[len(shown):])
        lines.append(f'（另有 {omitted} 个部门共 {rest} 份未在此展开，可打开“资料目录”按部门查看）')
    scope_names = '、'.join(titles.get(s, s) for s in shown) or '全部已共享范围'
    head = (f'截至本次查询（{as_of}），你可以查阅 {total} 份已发布资料。'
            f'统计口径：已发布且为当前版本、且你有权查阅的资料；分类为：{scope_names}。')
    if chosen['spaces']:
        header = head + f'\n\n已按“{chosen["label"] or query}”整理，共 {total} 份：'
    else:
        header = head + f'\n\n已为你整理已共享资料的分类目录，共 {total} 份：'
    answer = header + '\n\n' + '\n\n'.join(lines)
    answer += '\n\n如需逐条查看，请打开“资料目录”，或选择部门后继续提问。'
    return answer[:2000], True


def is_catalog_question(question, *, knowledge_only=False, context=(), history=()):
    """Whether this question is the directory case, under the shared router.

    Delegates to the same classifier the gateway uses, so Portal and MCP agree
    and a content question that merely mentions a document noun is not
    downgraded to a count.
    """
    from .answer_policy import route_question
    return route_question(question, knowledge_only=knowledge_only,
                          context=context, history=history) == 'CATALOG'
