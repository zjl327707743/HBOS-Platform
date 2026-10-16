import unittest
from hb_knowledge_app.hb_knowledge.followup import followup_query,validate_followup_scope
from hb_knowledge_app.hb_knowledge.errors import KnowledgeError


class FollowupTests(unittest.TestCase):
    def test_missing_answer_structure_is_not_reconstructed(self):
        for q in ['前一回答第二点是什么','上一回答第2条能再解释吗','上面第二条呢','前面第三步是什么','那一步的限制呢','这一步呢']:
            self.assertIsNone(followup_query('前一问题',q))

    def test_explicit_followup_retains_question_context(self):
        self.assertEqual(followup_query('水质监控需要哪些项目','请概括监控责任'),'前一问题：水质监控需要哪些项目\n追问：请概括监控责任')

    def test_full_length_followup_does_not_overflow_request_contract(self):
        self.assertEqual(followup_query('前文'*100,'问'*500),'问'*500)
        self.assertLessEqual(len(followup_query('前文'*100,'问'*400)),500)

    def test_followup_cannot_carry_question_across_scope_or_context(self):
        prior={'space_ids':['A','B'],'context':{'equipment_id':'SYNTHETIC_MACHINE'}}
        validate_followup_scope(prior,('B','A'),(('equipment_id','SYNTHETIC_MACHINE'),))
        with self.assertRaises(KnowledgeError):validate_followup_scope(prior,('A',),prior['context'])
        with self.assertRaises(KnowledgeError):validate_followup_scope(prior,('A','B'),{})
        with self.assertRaises(KnowledgeError):validate_followup_scope({'space_ids':['A']},('A',),{'equipment_id':'UNKNOWN_OLD_CONTEXT'})
