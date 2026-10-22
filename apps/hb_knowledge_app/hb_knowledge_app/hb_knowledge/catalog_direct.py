"""Authorized directory statistics, answered without the knowledge gateway.

A question such as 知识库共有多少份文件 is a request for metadata, not for a
document answer. It used to travel the full ask path: the gateway was called,
the service classified it, rebuilt the catalogue and returned it, which measured
about four seconds of the five-and-a-half second request for an answer that is
just a count over the authorized bindings this request already holds.

This module renders that answer from the same authorized plan the ask path
builds, so the identity, department scope, publication state, withdrawal and
current-version rules are exactly those of the plan. It never reads a global
total: every number counts bindings the caller is authorized to see. Portal and
MCP both reach it through api.ask, so the business rule stays single.
"""
from __future__ import annotations
import time

# Same cap the service catalogue uses, so a long directory does not turn into a
# wall of text and the header/body can never disagree.
PER_SPACE=15

def counts_by_space(plan):
    """(space_id -> [title, ...]) for the authorized bindings of this plan."""
    out={}
    for b in getattr(plan,'bindings',()) or ():
        space=getattr(b,'space_id',None)
        if not space:continue
        title=getattr(b,'title',None) or getattr(b,'document_number',None) or ''
        out.setdefault(space,[]).append(title)
    return out

def render(plan,titles,query,now=None):
    """The statistics answer for the bindings this caller is authorized to see."""
    grouped=counts_by_space(plan)
    total=sum(len(v) for v in grouped.values())
    as_of=(now or time.strftime('%Y-%m-%d %H:%M',time.localtime()))
    ordered=sorted(grouped.items(),key=lambda kv:(-len(kv[1]),kv[0]))
    name=lambda s:(titles or {}).get(s,s)
    scope='、'.join(name(s) for s,_ in ordered) or '全部已共享范围'
    head=(f'截至本次查询（{as_of}），你可以查阅 {total} 份已发布资料。'
          f'统计口径：已发布且为当前版本、且你有权查阅的资料；分类为：{scope}。')
    lines=[]
    for space,titles_in_space in ordered:
        shown=titles_in_space[:PER_SPACE]
        block=[f'【{name(space)}】共 {len(titles_in_space)} 份']
        block+= [f'- 《{t}》' for t in shown if t]
        if len(titles_in_space)>PER_SPACE:
            block.append(f'- …等其余 {len(titles_in_space)-PER_SPACE} 份')
        lines.append('\n'.join(block))
    answer=head+'\n\n已为你整理已共享资料的分类目录，共 %d 份：\n\n'%total+'\n\n'.join(lines)
    answer+='\n\n如需逐条查看，请打开“资料目录”，或选择部门后继续提问。'
    return answer[:2000]
