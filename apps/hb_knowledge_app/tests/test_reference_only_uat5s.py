"""A source-only response is a successful query, never a supported answer."""
import pytest
from hb_knowledge_app.hb_knowledge.answer_policy import answer_presentation
from hb_knowledge_app.hb_knowledge.r1_contract import REFERENCE_TEXT,LEGACY_REFERENCE_TEXT,validate_ask_data
from hb_knowledge_app.hb_knowledge.errors import KnowledgeError

@pytest.mark.parametrize('text',[REFERENCE_TEXT,LEGACY_REFERENCE_TEXT])
def test_current_and_historical_source_only_answers_retain_false_answerability(text):
    p=answer_presentation(text,True)
    assert p=={'mode':'reference_only','answer_status':'REFERENCE_ONLY','answerable':False}
    citation={'document_id':'SYNTHETIC_DOC','title':None,'version':None,'status_note':None,'section':None,'page_number':None,'excerpt':'合成资料要点。','evidence_id':'SYNTHETIC_EVIDENCE','citation_label':'C1','space_id':'SYNTHETIC_SPACE','source_type':'ORDINARY_INTERNAL_KNOWLEDGE'}
    data={'request_id':'SYNTHETIC','turn_id':'SYNTHETIC_TURN',**p,'answer':text,'citations':[citation],'answer_origin':'KNOWLEDGE','model_alias':'deepseek-flash'}
    validate_ask_data(data,environment='production')
    for override in ({'answer':'合成未获支持的模型结论。'},{'citations':[]},{'answerable':True}):
        with pytest.raises(KnowledgeError):validate_ask_data({**data,**override},environment='production')

def test_empty_sources_and_general_answers_remain_distinct():
    assert answer_presentation('没有依据',False)['answer_status']=='INSUFFICIENT_EVIDENCE'
    assert answer_presentation('合成一般知识',False,True)['answer_status']=='GENERAL_ANSWERED'
    assert answer_presentation('合成资料原句。[C1]',True)['answer_status']=='REFERENCE_ANSWERED'
