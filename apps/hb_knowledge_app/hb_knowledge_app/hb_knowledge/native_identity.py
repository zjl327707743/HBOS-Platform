"""Native PDF outline is harmless parser metadata, never an identity override."""
IDENTITY=('canonical_document_id','version_id','binding_revision')
def identity_metadata_matches(actual,expected):
    if not isinstance(actual,dict) or set(expected)!=set(IDENTITY):return False
    if any(actual.get(k)!=expected[k] for k in IDENTITY):return False
    if set(actual)-set(IDENTITY)-{'outline'}:return False
    if 'outline' not in actual:return True
    outline=actual['outline']
    return (isinstance(outline,list) and len(outline)<=512 and
            all(isinstance(v,dict) and set(v)=={'depth','title'} and
                type(v['depth']) is int and 0<=v['depth']<=20 and
                isinstance(v['title'],str) and len(v['title'])<=1000 for v in outline))
