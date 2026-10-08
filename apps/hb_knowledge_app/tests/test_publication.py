import unittest
from hb_knowledge_app.hb_knowledge.publication import PublicationConflict,decide,receipt_id,verify_frozen_target,FROZEN_PUBLICATION_FIELDS


class PublicationTests(unittest.TestCase):
    def frozen(self):
        item={k:'synthetic' for k in FROZEN_PUBLICATION_FIELDS}
        item.update(department_key='DEMO',business_version=None,document_number=None,
                    owner_inclusion_confirmed=True,internal_sharing_confirmed=True)
        return item

    def test_complete_frozen_target_is_accepted(self):
        item=self.frozen();verify_frozen_target(item,dict(item),'DEMO')

    def test_hash_only_approval_is_rejected(self):
        item=self.frozen()
        with self.assertRaises(PublicationConflict):verify_frozen_target(item,{'sha256':item['sha256']},'DEMO')

    def test_source_classification_cannot_be_upgraded_in_execution_state(self):
        item=self.frozen()
        for field in ['source_type','authority_status']:
            with self.subTest(field=field),self.assertRaises(PublicationConflict):
                verify_frozen_target({**item,field:'unapproved-controlled'},item,'DEMO')

    def test_owner_approval_fields_cannot_drift(self):
        item=self.frozen()
        for field in ['owner_inclusion_confirmed','internal_sharing_confirmed','approval_ref']:
            with self.subTest(field=field),self.assertRaises(PublicationConflict):
                verify_frozen_target({**item,field:False},item,'DEMO')

    def test_title_number_and_business_version_are_frozen(self):
        item=self.frozen()
        for field in ['title','document_number','business_version']:
            with self.subTest(field=field),self.assertRaises(PublicationConflict):
                verify_frozen_target({**item,field:'unapproved-metadata'},item,'DEMO')

    def test_frozen_department_cannot_publish_into_another_space(self):
        item=self.frozen()
        with self.assertRaises(PublicationConflict):verify_frozen_target(item,item,'OTHER')

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
