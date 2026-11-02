from dataclasses import replace
import pytest
from hb_knowledge_app.hb_knowledge.execution_plan import Binding,validate_admission
from hb_knowledge_app.hb_knowledge.errors import KnowledgeError
from hb_knowledge_app.hb_knowledge.public_strings import safe_string


def test_reference_inclusion_does_not_manufacture_effective_gmp_approval():
    b=Binding('PRODUCTION','DOC_A','VER_A',None,'dataset','document','PRODUCTION','BIND_A','REV_A','COMPANY_CONTROLLED','CONTROLLED_REFERENCE_REVIEWED','2026-10-08T00:00:00Z')
    validate_admission(b,'production',1791424800)
    with pytest.raises(KnowledgeError):validate_admission(replace(b,authority_status='CONTROLLED_APPROVED'),'production',1791424800)


def test_numeric_comparators_survive_projection_but_links_and_html_do_not():
    assert safe_string('温度 < 25℃；压力 > 0.1MPa',500)
    for value in ['<img src=x>','https://example.invalid/original','/private/files/original.docx']:
        with pytest.raises(KnowledgeError):safe_string(value,500)
