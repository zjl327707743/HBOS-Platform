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
