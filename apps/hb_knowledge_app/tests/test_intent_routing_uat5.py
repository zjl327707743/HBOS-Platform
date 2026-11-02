"""Intent routing: a content question must never be answered with a catalogue.

The routing table had no test coverage, which is how a real defect survived: a
question about a *named document's* contents matched a doc noun (规程) plus a
find verb (有什么) and was answered with a 210-item catalogue instead of the
rule being asked about. These cases pin both directions — content questions stay
in the knowledge path, and genuine directory requests still get the catalogue.
"""
import pytest

from hb_knowledge_app.hb_knowledge.answer_policy import route_question

# Questions about what a specific document says. Every one of these was, or
# would have been, misrouted to CATALOG before the content-ask guard.
CONTENT_QUESTIONS = [
    '录像监控系统的标准操作规程里，对录像保存时间有什么要求？',
    'SOP-MP-3-B-074（晶种结晶）和 SOP-MP-3-B-081（美罗培南结晶）这两份规程，主题上有什么区别？',
    '蒸汽灭菌器（SGLH-A-650D）维护规程里，哪些维护项目是有周期要求的？',
    '《使用有毒物品作业场所劳动保护条例》对用人单位规定了哪些主要义务？',
    '河南省电动车停放充电场所消防管理规范适用于我们公司吗？',
    'SOP-MP-3-B-074 这份规程主要讲什么？',
    '员工手册对试用期是怎么规定的？',
    '这个规程由谁负责监督执行？',
    '灭菌器维护规程多久检查一次？',
]

# Genuine directory requests. These must keep returning a catalogue.
CATALOG_QUESTIONS = [
    '法律法规',
    '新乡海滨法规列表',
    '岗位安全培训资料在哪里',
    '在哪里查找岗位安全培训资料',
    '安全生产方面的资料都有哪些？',
    '设备工程方面的资料有哪些',
    '把安全资料列一下',
    '规程有哪些',
]


@pytest.mark.parametrize('question', CONTENT_QUESTIONS)
def test_a_named_document_content_question_is_not_a_catalogue_request(question):
    assert route_question(question) == 'KNOWLEDGE'


@pytest.mark.parametrize('question', CATALOG_QUESTIONS)
def test_a_directory_request_still_returns_a_catalogue(question):
    assert route_question(question) == 'CATALOG'


def test_an_explicit_set_request_wins_over_content_wording():
    # "有哪些规程" asks for the set even though it contains a content verb.
    assert route_question('灭菌器维护规程有哪些') == 'CATALOG'


def test_a_follow_up_stays_in_the_knowledge_path():
    assert route_question('上一条是什么意思', history=(('user', '灭菌器怎么维护'),)) == 'KNOWLEDGE'


def test_knowledge_only_scope_forces_the_knowledge_path():
    assert route_question('法律法规', knowledge_only=True) == 'KNOWLEDGE'
