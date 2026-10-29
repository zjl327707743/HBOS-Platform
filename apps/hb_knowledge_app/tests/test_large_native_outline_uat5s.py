"""Real long-document shape, without corporate source text or identities."""
import unittest
from hb_knowledge_app.hb_knowledge.native_identity import identity_metadata_matches

class LargeOutlineTest(unittest.TestCase):
    def setUp(self):
        self.expected={'canonical_document_id':'DOC_SAMPLE','version_id':'VER_SAMPLE','binding_revision':'BR_SAMPLE'}
        self.actual={**self.expected,'outline':[{'depth':n%4,'title':'Chapter '+str(n)} for n in range(551)]}

    def test_long_valid_native_outline_is_not_an_identity_change(self):
        self.assertTrue(identity_metadata_matches(self.actual,self.expected))

    def test_outline_cannot_override_identity_or_add_metadata(self):
        for key in self.expected:
            self.assertFalse(identity_metadata_matches({**self.actual,key:'changed'},self.expected))
        self.assertFalse(identity_metadata_matches({**self.actual,'other':'value'},self.expected))

    def test_structure_and_aggregate_bounds_remain_closed(self):
        for outline in ([{'depth':0,'title':'x'}]*4097,
                        [{'depth':0,'title':'x'*1000}]*132,
                        [{'depth':True,'title':'x'}],
                        [{'depth':21,'title':'x'}],
                        [{'depth':0,'title':'x','version_id':'changed'}],
                        [{'depth':0,'title':'x'*1001}]):
            self.assertFalse(identity_metadata_matches({**self.expected,'outline':outline},self.expected))

if __name__=='__main__':unittest.main()
