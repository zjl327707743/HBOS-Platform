import pytest
from hb_knowledge_app.hb_knowledge.public_strings import safe_string
from hb_knowledge_app.hb_knowledge.quota import InMemoryQuota
from hb_knowledge_app.hb_knowledge.errors import KnowledgeError

def test_chinese_ocr_slash_is_not_an_original_file_address():
    text='\n/火，手机）和电子设备等进入生产区）'
    assert safe_string(text)==text
    for locator in ['/etc/private', '/材料/员工手册', '/员工手册.pdf', 'https://storage.invalid/original',
                    'file:///员工手册.pdf', '../原文.pdf', '/run/secrets/key']:
        with pytest.raises(KnowledgeError):safe_string(locator)

def test_bounded_normal_queries_fit_without_removing_the_extraction_or_request_limit():
    quota=InMemoryQuota(clock=lambda:100)
    for i in range(12):
        quota.reserve_request('synthetic',str(i),str(i))
        quota.reserve_output('synthetic',2500)
    with pytest.raises(KnowledgeError) as request_error:
        quota.reserve_request('synthetic','thirteenth','thirteenth')
    assert request_error.value.code=='RATE_LIMITED'
    with pytest.raises(KnowledgeError) as output_error:
        quota.reserve_output('synthetic',1)
    assert output_error.value.code=='EXTRACTION_LIMITED'
