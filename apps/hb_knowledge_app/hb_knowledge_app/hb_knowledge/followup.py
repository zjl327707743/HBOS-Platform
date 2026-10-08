"""History stores logical sources, so unrecorded answer structure stays unknown."""
import re

UNRESOLVED_FOLLOWUP = '无法可靠定位前一回答中的具体条目。请指出步骤名称或关键词后再问；当前资料不足以直接回答这个追问。'


def followup_query(previous_query, question):
    if (re.search(r'(?:前一|上一|刚才).{0,4}(?:回答|答复).{0,6}第[一二三四五六七八九十\d]+[点步项条]', question)
            or re.search(r'[那这](?:一)?步', question)):
        return None
    budget = 500 - len(question) - len('前一问题：\n追问：')
    if budget <= 0:
        return question
    return '前一问题：' + previous_query[-min(180, budget):] + '\n追问：' + question
