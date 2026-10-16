"""Closed aliases and deterministic, conservative question routing. No model calls."""
import re,unicodedata
from .errors import KnowledgeError
ALIASES=('gpt-6-luna','deepseek-flash','gemini-3.8-flash','kimi-k3')
DEFAULT_MODEL='gpt-6-luna'
COMPANY_INSUFFICIENT='没有可核验的企业依据。请提供已发布且有权查阅的资料。'
def guard_restricted_request(question):
    q=unicodedata.normalize('NFKC',question)
    if re.search(r'(?:未授权|隔离)[\s的]*(?:资料|文档|个人|SOP)|(?:个人薪资|个人工资)原件|(?:下载|导出|提供|给我).{0,24}(?:原件|企业全文|公司全文)|全文枚举|(?:unauthori[sz]ed|isolated)\s+(?:documents|records|files)|(?:download|export|provide).{0,32}(?:original|company\s+full\s+text)',q,re.I):
        raise KnowledgeError('ORIGINAL_ACCESS_DENIED')
def model_alias(value):
    if value not in ALIASES:raise KnowledgeError('MODEL_NOT_APPROVED')
    return value
def route_question(question,*,knowledge_only=False,context=()):
    q=unicodedata.normalize('NFKC',question).casefold().strip()
    if knowledge_only or context:return 'KNOWLEDGE'
    if re.search(r'公司|本厂|我厂|海滨|内部|制度|规程|工艺|参数|培养箱|岗位|员工|人事|考勤|奖金|工资|薪|补贴|津贴|未公布|未发布|保密|机密|生产|质量|包装|药|安全培训|生效|sop|gmp|\bf\d+\b|our\s|hbos|company|internal|confidential|payroll|salary|salaries|employee|bonus|attendance',q):return 'KNOWLEDGE'
    if re.fullmatch(r'(?:你好|您好|nihao|hello|hi|hey|早上好|晚上好|谢谢|再见)[!！。,.，\s]*',q):return 'GENERAL'
    if re.match(r'(?:什么是|解释|请解释|介绍|请介绍|what is|explain)\s*(?:ai\b|人工智能|机器学习|深度学习|大语言模型|python\b|javascript\b|计算机|互联网|算法|数学|概率|物理|光合作用)',q):return 'GENERAL'
    if re.match(r'(?:计算|请计算)\s*[\d()+*/.\s-]+[?？。]*$',q):return 'GENERAL'
    if re.match(r'(?:写|请写|帮我写|如何写|how to write)\s*(?:一个|一段|a\s)?(?:python|javascript|typescript|sql|正则)',q):return 'GENERAL'
    return 'KNOWLEDGE'


def answer_presentation(answer,has_citations,general=False):
    from .r1_contract import REFERENCE_TEXT,LEGACY_REFERENCE_TEXT
    if general:return {'mode':'general_generation','answer_status':'GENERAL_ANSWERED','answerable':True}
    if has_citations and answer in (REFERENCE_TEXT,LEGACY_REFERENCE_TEXT):
        return {'mode':'reference_only','answer_status':'REFERENCE_ONLY','answerable':False}
    if has_citations:return {'mode':'internal_reference_generation','answer_status':'REFERENCE_ANSWERED','answerable':True}
    return {'mode':'authorized_generation','answer_status':'INSUFFICIENT_EVIDENCE','answerable':False}
