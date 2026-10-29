import copy,unittest
from hb_knowledge_app.hb_knowledge.source_reindex import validate_same_source_reindex,metadata_digest
from hb_knowledge_app.hb_knowledge.publication import PublicationConflict

class SameSourceReindexTest(unittest.TestCase):
    def fixture(self):
        parent={'sha256':'a'*64,'upload_sha256':'a'*64,'document_number':'SAMPLE-001','business_version':'1',
                'source_type':'ORDINARY_INTERNAL_KNOWLEDGE','authority_status':'INTERNAL_REFERENCE_REVIEWED'}
        binding={'canonical_document_id':'DOC_SAMPLE','version_id':'VER_'+'a'*24,'binding_revision':'BR_'+'a'*24,
                 'dataset_id':'a'*32,'document_id':'b'*32,'space_id':'DEPT_PRODUCTION','title':'合成资料',
                 **{k:parent[k] for k in ('document_number','business_version','source_type','authority_status')}}
        current={'document_id':'DOC_SAMPLE','current_version':binding['version_id'],'source_hash':'a'*64,
                 'dataset_id':'a'*32,'ingestion_status':'published','withdrawn':0}
        item={**parent,**binding,'version_id':'VER_'+'b'*24,'binding_revision':'BR_'+'b'*24,
              'ragflow_document_id':'c'*32,'disposition':'REPLACE_CURRENT','expected_current_version':binding['version_id'],
              'parser_input':'VERIFIED_LOCAL_FULL_TEXT','upload_sha256':'c'*64,
              'owner_inclusion_confirmed':True,'internal_sharing_confirmed':True,'approval_ref':'OWNER_EXACT_SOURCE',
              'native_text_preflight':{'text_sha256':'c'*64,'original_asset':{'dataset_id':'a'*32,'document_id':'b'*32,'source_sha256':'a'*64},
               'same_source_reindex':{'parent_version_id':binding['version_id'],'parent_binding_revision':binding['binding_revision'],
                  'parent_document_id':binding['document_id'],'parent_metadata_sha256':metadata_digest(parent),'source_sha256':'a'*64}}}
        return item,current,parent,binding

    def check(self,item,current,parent,binding):
        return validate_same_source_reindex(item,current,parent,binding,'VER_'+'a'*24,'DEPT_PRODUCTION')

    def test_atomic_replacement_and_current_committed_receipt_replay(self):
        args=self.fixture();self.check(*args);args[1]['current_version']=args[0]['version_id'];self.check(*args)

    def test_fact_or_authority_change_is_rejected(self):
        for field in ('sha256','document_number','business_version','source_type','authority_status','title'):
            with self.subTest(field=field):
                args=self.fixture();args[0][field]='changed'
                with self.assertRaises(PublicationConflict):self.check(*args)

    def test_stale_withdrawn_or_moved_publication_is_rejected(self):
        for field,value in [('current_version','VER_OTHER'),('withdrawn',1),('dataset_id','other'),('source_hash','other'),('ingestion_status','retired')]:
            with self.subTest(field=field):
                args=self.fixture();args[1][field]=value
                with self.assertRaises(PublicationConflict):self.check(*args)

    def test_parent_and_new_physical_index_are_not_interchangeable(self):
        for field,value in [('ragflow_document_id','b'*32),('binding_revision','BR_'+'a'*24),('expected_current_version','VER_OTHER')]:
            args=self.fixture();args[0][field]=value
            with self.assertRaises(PublicationConflict):self.check(*args)
        args=self.fixture();args[2]['upload_sha256']='d'*64
        with self.assertRaises(PublicationConflict):self.check(*args)

    def test_parent_metadata_space_and_original_asset_must_still_match(self):
        for change in ['parent_metadata','space','asset','proof','text_hash','sharing']:
            args=self.fixture();item,current,parent,binding=args
            if change=='parent_metadata':parent['extra']='changed'
            if change=='space':binding['space_id']='OTHER'
            if change=='asset':item['native_text_preflight']['original_asset']['document_id']='d'*32
            if change=='proof':item['native_text_preflight']['same_source_reindex']['extra']='value'
            if change=='text_hash':item['native_text_preflight']['text_sha256']='d'*64
            if change=='sharing':item['internal_sharing_confirmed']=False
            with self.assertRaises(PublicationConflict):self.check(*args)

if __name__=='__main__':unittest.main()
