import unittest
from hb_knowledge_app.hb_knowledge.followup import conversation_history,validate_followup_scope
from hb_knowledge_app.hb_knowledge.errors import KnowledgeError


class FollowupTests(unittest.TestCase):
    def test_previous_turn_is_passed_as_real_dialogue_not_a_query_prefix(self):
        previous={'query':'水质监控需要哪些项目','answer':'需要监测pH和电导率。[C1]'}
        self.assertEqual(conversation_history(previous),(
            {'role':'user','content':'水质监控需要哪些项目'},
            {'role':'assistant','content':'需要监测pH和电导率。[C1]'}))

    def test_two_turns_are_bounded_and_keep_the_newest(self):
        older={'query':'培养箱怎么用','answer':'按规程检查密封性。[C1]'}
        previous={'query':'温度条件是什么','answer':'低于25℃不得启动。[C2]'}
        turns=conversation_history(previous,older=older)
        self.assertEqual([t['role'] for t in turns],['user','assistant','user','assistant'])
        self.assertEqual(turns[-1]['content'],'低于25℃不得启动。[C2]')

    def test_history_is_bounded_in_size(self):
        previous={'query':'前'*3000,'answer':'答'*3000}
        turns=conversation_history(previous)
        self.assertTrue(turns)
        self.assertLessEqual(sum(len(t['content']) for t in turns),12000)
        self.assertLessEqual(max(len(t['content']) for t in turns),2000)

    def test_missing_answer_text_contributes_no_fabricated_turn(self):
        self.assertEqual(conversation_history({'query':'问','answer':''}),())

    def test_followup_cannot_carry_question_across_scope_or_context(self):
        prior={'space_ids':['A','B'],'context':{'equipment_id':'SYNTHETIC_MACHINE'}}
        validate_followup_scope(prior,('B','A'),(('equipment_id','SYNTHETIC_MACHINE'),))
        with self.assertRaises(KnowledgeError):validate_followup_scope(prior,('A',),prior['context'])
        with self.assertRaises(KnowledgeError):validate_followup_scope(prior,('A','B'),{})
        with self.assertRaises(KnowledgeError):validate_followup_scope({'space_ids':['A']},('A',),{'equipment_id':'UNKNOWN_OLD_CONTEXT'})


if __name__=='__main__':unittest.main()


# ---------------------------------------------------------------------------
# Retrieval query for referential follow-ups.
#
# A bare "上一条是什么意思" has no topic words, so using it as the retrieval
# query returned unrelated documents (an incubator question followed by
# "上一条是什么意思" retrieved 安全生产法). Retrieval now reuses the previous
# question verbatim; the displayed question and the stored history stay raw.
# ---------------------------------------------------------------------------

def test_a_bare_reference_reuses_the_previous_question_for_retrieval():
    from hb_knowledge_app.hb_knowledge.followup import retrieval_query
    previous = {'query': '培养箱使用前需要检查哪些项目？'}
    for follow_up in ('上一条是什么意思', '用三句话总结', '展开说说', '这条要求由谁负责？'):
        query = retrieval_query(follow_up, previous)
        assert '培养箱' in query, follow_up
        assert follow_up in query, follow_up


def test_a_self_contained_follow_up_is_not_rewritten():
    from hb_knowledge_app.hb_knowledge.followup import retrieval_query
    previous = {'query': '培养箱使用前需要检查哪些项目？'}
    for question in ('那培养箱的灭菌要求呢？', 'SOP-MP-3-B-063 是什么', '灭菌器维护周期是多少'):
        assert retrieval_query(question, previous) == question


def test_the_first_turn_is_never_rewritten():
    from hb_knowledge_app.hb_knowledge.followup import retrieval_query
    assert retrieval_query('上一条是什么意思', None) == '上一条是什么意思'
    assert retrieval_query('上一条是什么意思', {'query': ''}) == '上一条是什么意思'
