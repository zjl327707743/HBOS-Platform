import unittest
from hb_knowledge_app.hb_knowledge.publication import PublicationConflict,decide,receipt_id


class PublicationTests(unittest.TestCase):
    def current(self,version='OLD',withdrawn=0,status='published'):
        return {'current_version':version,'withdrawn':withdrawn,'ingestion_status':status}

    def test_first_publish_and_replay(self):
        self.assertEqual(decide(None,'OLD'),'PUBLISHED')
        self.assertEqual(decide(self.current(),'OLD'),'NOOP')

    def test_withdrawn_replay_never_restores(self):
        for operation in ['publish','replace']:
            self.assertEqual(decide(self.current(withdrawn=1,status='retired'),'OLD',operation,'OLD'),'SKIPPED_WITHDRAWN')

    def test_old_batch_cannot_replace_new_version(self):
        with self.assertRaises(PublicationConflict):decide(self.current('NEW'),'OLD')

    def test_replace_has_compare_and_swap(self):
        self.assertEqual(decide(self.current(),'NEW','replace','OLD'),'REPLACED')
        with self.assertRaises(PublicationConflict):decide(self.current('OTHER'),'NEW','replace','OLD')
        with self.assertRaises(PublicationConflict):decide(self.current(),'NEW','replace')

    def test_restore_is_explicit_and_only_same_version(self):
        self.assertEqual(decide(self.current(withdrawn=1,status='retired'),'OLD','restore','OLD'),'RESTORED')
        with self.assertRaises(PublicationConflict):decide(self.current(withdrawn=1),'NEW','restore','OLD')
        with self.assertRaises(PublicationConflict):decide(self.current(),'OLD','restore','OTHER')

    def test_prior_receipt_is_never_permanent_authority(self):
        self.assertEqual(decide(self.current('NEW'),'NEW','replace','OLD'),'RECEIPT_REQUIRED')
        with self.assertRaises(PublicationConflict):decide(self.current('OTHER'),'NEW','replace','OLD')
        self.assertEqual(decide(self.current('NEW',1),'NEW','replace','OLD'),'SKIPPED_WITHDRAWN')

    def test_receipt_binds_batch_item_operation_expected_target(self):
        item={'canonical_document_id':'D','version_id':'V','sha256':'a'*64,'binding_revision':'R'}
        r=receipt_id('B',item,'publish',None)
        for batch,entry,op,expected in [('OTHER',item,'publish',None),('B',{**item,'version_id':'V2'},'publish',None),('B',item,'replace','V0'),('B',item,'restore','V')]:
            self.assertNotEqual(r,receipt_id(batch,entry,op,expected))
