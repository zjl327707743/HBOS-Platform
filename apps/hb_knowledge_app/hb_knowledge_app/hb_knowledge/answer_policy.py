"""Closed aliases and deterministic, conservative question routing. No model calls."""
import re, unicodedata
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

# ---------------------------------------------------------------------------
# Intent classification: CATALOG / KNOWLEDGE / GENERAL / CLARIFICATION.
# Deterministic and conservative; the service decides what each intent means.
# ---------------------------------------------------------------------------

_FOLLOWUP_MARKERS=re.compile(r'(?:上一条|上面|前面|刚才|之前|这个|那个|它|它们|再|继续|接着|三句话|总结一下|什么意思|是什么含义|展开|详细说|举个例子|进一步|追问)',re.I)

def _looks_like_catalog(question):
    """A request to find/list/dir documents, regulations or where-to-find."""
    q=question
    doc_nouns=r'(?:资料|文件|文档|法规|法律|条例|办法|规定|规程|制度|标准|sop|手册|台账|目录|证书|预案|报告|图纸|记录)'
    find_verbs=r'(?:列表|清单|目录|一览|有哪些|都有哪些|有什么|在哪里|在哪儿|在哪个|去哪|如何找到|怎么找|找一下|查找|查询|列出|列一下|枚举|分一下类|分类)'
    if re.search(doc_nouns+r'.{0,16}?'+find_verbs,q,re.I):return True
    if re.search(find_verbs+r'.{0,16}?'+doc_nouns,q,re.I):return True
    # Standalone catalogue titles: "法律法规", "新乡海滨法规列表", "安全培训资料"
    if re.fullmatch(r'[\s，,。.、]*((?:新乡|海滨|公司|厂|公共)?(?:法律)?法规|安全培训资料|岗位安全培训资料|培训资料|工程资料|设备资料)[\s，,。.、]*',q):
        return True
    return False

_CLARIFY_FILLERS=re.compile(r'^(?:嗯+|哦+|啊+|呃+|唉+|哈+|好+|行+|是+|对+|对的对的|知道了|明白|随便|什么|为啥|为什么|然后|还有|那|那么|吧|吗|呢|呀|嘛|喂|hi|hello|hey|nihao|你好|您好)[\s，,。.、!！?？~～]*$',re.I)

def _looks_like_clarification(question):
    stripped=re.sub(r'[\s，,。.、;；:：!！?？~～"“”\'‘’()（）\[\]【】{}<>《》*#@$%^&+=|\\/_-]+','',question)
    if not stripped:return True
    if len(stripped)<=1:return True
    if _CLARIFY_FILLERS.fullmatch(question):return True
    # Only digits / symbols with no words: "123", "!!!", "a b c" fragments.
    if re.fullmatch(r'[\d\W_]+',stripped):return True
    if re.fullmatch(r'[a-z]{1,3}',stripped,re.I):return True
    return False

_COMPANY_MARKERS=re.compile(r'公司|本厂|我厂|海滨|内部|制度|规程|工艺|参数|培养箱|岗位|员工|人事|考勤|奖金|工资|薪|补贴|津贴|未公布|未发布|保密|机密|生产|质量|包装|药|安全培训|生效|sop|gmp|\bf\d+\b|our\s|hbos|company|internal|confidential|payroll|salary|salaries|employee|bonus|attendance',re.I)

def _looks_like_company_question(question):
    """A company/internal subject must never be answered as general knowledge."""
    return bool(_COMPANY_MARKERS.search(unicodedata.normalize('NFKC',question)))

def route_question(question,*,knowledge_only=False,context=(),history=()):
    """Classify a user question into one of the four supported intents.

    - knowledge_only/context force KNOWLEDGE (a knowledge-scoped request).
    - history marks a conversational follow-up; follow-up phrasing must stay in
      the knowledge path so the generation model can resolve references.
    - catalog intent is checked before the company-subject guard so that
      "岗位安全培训资料在哪里" stays a directory request.
    - any company/internal subject is never downgraded to a general answer.
    """
    q=unicodedata.normalize('NFKC',question).casefold().strip()
    if knowledge_only or context:return 'KNOWLEDGE'
    if history and _FOLLOWUP_MARKERS.search(q):return 'KNOWLEDGE'
    if _looks_like_catalog(question):return 'CATALOG'
    if _looks_like_company_question(question):return 'KNOWLEDGE'
    # General knowledge: greetings, definitions, arithmetic, code writing.
    if re.fullmatch(r'(?:你好|您好|nihao|hello|hi|hey|早上好|晚上好|谢谢|再见)[!！。,.，\s]*',q):return 'GENERAL'
    if re.match(r'(?:什么是|解释|请解释|介绍|请介绍|what is|explain)\s*(?:ai\b|人工智能|机器学习|深度学习|大语言模型|python\b|javascript\b|计算机|互联网|算法|数学|概率|物理|光合作用)',q):return 'GENERAL'
    if re.match(r'(?:计算|请计算)\s*[\d()+*/.\s-]+[?？。]*$',q):return 'GENERAL'
    if re.match(r'(?:写|请写|帮我写|如何写|how to write)\s*(?:一个|一段|a\s)?(?:python|javascript|typescript|sql|正则)',q):return 'GENERAL'
    if _looks_like_clarification(question):return 'CLARIFICATION'
    return 'KNOWLEDGE'


def answer_presentation(answer,has_citations,general=False,*,state=None):
    """Explicit wire presentation for the service answer state.

    The main generation path always carries an explicit ``state``; the old
    inference (text-prefix based) remains only as a compatibility fallback.
    """
    from .r1_contract import REFERENCE_TEXT,LEGACY_REFERENCE_TEXT
    explicit={
        'GENERATED_WITH_SOURCES':{'mode':'internal_reference_generation','answer_status':'GENERATED_WITH_SOURCES','answerable':True},
        'CATALOG_RESULTS':{'mode':'catalog_results','answer_status':'CATALOG_RESULTS','answerable':True},
        'GENERAL_ANSWER':{'mode':'general_generation','answer_status':'GENERAL_ANSWERED','answerable':True},
        'CLARIFICATION':{'mode':'clarification','answer_status':'CLARIFIED','answerable':False},
        'REFERENCE_EXCERPTS':{'mode':'reference_excerpts','answer_status':'REFERENCE_EXCERPTS','answerable':False},
        'FAILED':{'mode':'failed','answer_status':'FAILED','answerable':False},
        'INSUFFICIENT_EVIDENCE':{'mode':'authorized_generation','answer_status':'INSUFFICIENT_EVIDENCE','answerable':False},
    }
    if state in explicit:return explicit[state]
    if general:return {'mode':'general_generation','answer_status':'GENERAL_ANSWERED','answerable':True}
    if has_citations and answer in (REFERENCE_TEXT,LEGACY_REFERENCE_TEXT):
        return {'mode':'reference_only','answer_status':'REFERENCE_ONLY','answerable':False}
    if has_citations:return {'mode':'internal_reference_generation','answer_status':'REFERENCE_ANSWERED','answerable':True}
    return {'mode':'authorized_generation','answer_status':'INSUFFICIENT_EVIDENCE','answerable':False}
