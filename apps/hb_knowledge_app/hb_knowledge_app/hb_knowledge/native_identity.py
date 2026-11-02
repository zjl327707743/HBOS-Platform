"""Native PDF outline is harmless parser metadata, never an identity override."""
IDENTITY=('canonical_document_id','version_id','binding_revision')
MAX_OUTLINE_ENTRIES=4096
MAX_OUTLINE_TITLE_CHARACTERS=131072
def identity_metadata_matches(actual,expected):
    if not isinstance(actual,dict) or set(expected)!=set(IDENTITY):return False
    if any(actual.get(k)!=expected[k] for k in IDENTITY):return False
    if set(actual)-set(IDENTITY)-{'outline'}:return False
    if 'outline' not in actual:return True
    outline=actual['outline']
    # Long, otherwise valid PDFs can have more than 512 real bookmark entries.
    # The outline never grants access or supplies a protected identity. Bound
    # both its structure and total text, rather than confusing length with an
    # identity mismatch after the native parser has already indexed the file.
    return (isinstance(outline,list) and len(outline)<=MAX_OUTLINE_ENTRIES and
            all(isinstance(v,dict) and set(v)=={'depth','title'} and
                type(v['depth']) is int and 0<=v['depth']<=20 and
                isinstance(v['title'],str) and len(v['title'])<=1000 for v in outline)
            and sum(len(v['title']) for v in outline)<=MAX_OUTLINE_TITLE_CHARACTERS)
