"""Ask citation projection with per-record isolation for curated answers."""
from .errors import KnowledgeError
from .gateway import EvidenceRecord


def project_ask_results(raw_results,raw_labels,selected_bindings,*,answer_status):
    """Project the ask citations, isolating an unprojectable record only for
    REFERENCE_EXCERPTS answers.

    A REFERENCE_EXCERPTS answer has no generated claims of its own: the visible
    payload is the curated citation list. One citation whose excerpt cannot be
    projected safely must not fail the whole answer, or the employee loses the
    other safe sources. Generated answers keep the strict behaviour (any bad
    citation fails the answer) because their claim labels must stay complete.
    """
    from knowledge_service.hbos_gateway.response_projection import public_evidence
    records=[];labels=[];isolated=[]
    for item in raw_results:
        if not isinstance(item,dict) or set(item)!={'binding_ref','version_id','chunk_id','excerpt','page_number','score','citation_label'}:raise KnowledgeError('UPSTREAM_INVALID_RESULT')
        b=selected_bindings.get(item['binding_ref']);label=item['citation_label']
        if not b or b.version_id!=item['version_id'] or label not in {'C1','C2','C3','C4','C5'} or label in labels:raise KnowledgeError('UPSTREAM_SCOPE_VIOLATION')
        r=EvidenceRecord(b.canonical_document_id,b.title,b.business_version,'内部参考／有效性待核',b.section,item['page_number'],item['excerpt'],item['chunk_id'],b.dataset_alias,b.space_id,b.version_id,b.binding_ref,b)
        try:
            public_evidence(r,'ASK_PROJECTION_CHECK',environment='production')
        except KnowledgeError as error:
            if answer_status!='REFERENCE_EXCERPTS' or error.code!='UPSTREAM_INVALID_RESULT':raise
            isolated.append({'citation_label':label,'chunk_id':item['chunk_id'],'reason':error.code});continue
        records.append(r);labels.append(label)
    if not records and raw_results:raise KnowledgeError('UPSTREAM_INVALID_RESULT')
    if answer_status!='REFERENCE_EXCERPTS' and set(labels)!=set(raw_labels):raise KnowledgeError('UPSTREAM_INVALID_RESULT')
    return records,labels,isolated
