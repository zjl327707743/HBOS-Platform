"""Offline preview preparation. Never called on untrusted HTTP parameters.

PDFs are inspected structurally before original layout bytes can be embedded.
Active objects are removed from a separate preview copy. Office conversion is
local, with a disposable profile, macros disabled and OS network denial; failed
conversion leaves the existing indexed text reader available.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import zipfile
from xml.etree import ElementTree

# Published scanned books run well past two thousand pages (one in the corpus is
# 2032). The bound still exists; it is now above that, and the copy stays
# page-preserving so the physical page the browser shows is the printed one.
MAX_PAGES = 4000
LEGACY_OFFICE = frozenset({'.doc', '.xls', '.ppt', '.wps'})
# Some published technical reports carry a per-character structure tree and
# reach ~880k reachable objects. The walk is bounded and runs offline in the
# preview builder, so the ceiling is raised to admit them rather than treating a
# large but normal document as hostile.
MAX_OBJECTS = 1_000_000
MAX_OFFICE_EXPANDED = 64 * 1024 * 1024
ACTIVE_ACTIONS = frozenset({'/JavaScript','/Launch','/GoToR','/GoToE','/URI',
                            '/SubmitForm','/ImportData','/Rendition','/Sound',
                            '/Movie','/RichMediaExecute'})
# A catalog /Names entry is a name tree dictionary. Only some of its subtrees
# can execute or embed content; /Dests is pure in-document navigation and is
# written back by pypdf for ordinary internal links. Treating the whole /Names
# entry as active rejected every PDF with an internal link anchor - the source
# of 313 of the 384 preview failures - while the active subtrees below are what
# actually matter.
ACTIVE_NAME_TREES = frozenset({'/JavaScript','/EmbeddedFiles','/Renditions','/AP',
                               '/AlternatePresentations'})
NON_ACTIVE_NAME_TREES = frozenset({'/Dests','/Pages','/Templates','/IDS','/URLS','/EF'})


def file_sha256(path):
    value=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):value.update(block)
    return value.hexdigest()


def _walk(root, *, clean=False):
    from pypdf.generic import DictionaryObject, ArrayObject, IndirectObject
    def resolve(value):
        for _ in range(16):
            if not isinstance(value,IndirectObject):return value
            value=value.get_object()
        raise ValueError('PDF_REFERENCE_LIMIT')
    catalog=resolve(root.get('/Root')) if isinstance(root,DictionaryObject) and '/Root' in root else root
    def name_tree(value):
        """True when a catalog /Names dictionary holds an active subtree.

        The name tree is walked entry by entry: a pure /Dests tree is
        navigation inside the document (pypdf rewrites it for ordinary internal
        links) and stays, while script, embedded-file, rendition, appearance and
        presentation subtrees are removed - or, when only inspecting, reported as
        active. An unknown subtree counts as active.
        """
        node=resolve(value)
        if not isinstance(node,DictionaryObject):return False
        found=False
        for key in list(node):
            name=str(key)
            if name in ACTIVE_NAME_TREES or name not in NON_ACTIVE_NAME_TREES:
                found=True
                if clean:del node[key]
            else:stack.append(node.raw_get(key))
        return found
    stack=[root];seen=set();active=False
    while stack:
        obj=stack.pop()
        if isinstance(obj,IndirectObject):
            key=(id(obj.pdf),obj.idnum,obj.generation)
            if key in seen:continue
            seen.add(key)
            obj=obj.get_object()
        else:
            key=('direct',id(obj))
            if key in seen:continue
            seen.add(key)
        if len(seen)>MAX_OBJECTS:raise ValueError('PDF_OBJECT_LIMIT')
        if isinstance(obj,DictionaryObject):
            # /A and /JS can also be harmless resource names. Restrict removal
            # to PDF action semantics and catalog/page/annotation contexts so
            # font resources and page drawing instructions are preserved.
            kind='/Catalog' if obj is catalog else str(resolve(obj.get('/Type','')))
            blocked=set()
            if kind=='/Catalog':blocked.update({'/AA','/OpenAction','/AcroForm','/Collection','/AF'})
            if kind=='/Page':blocked.update({'/AA','/Annots','/AF'})
            if kind=='/Annot':blocked.update({'/A','/AA','/RichMediaContent','/RichMediaSettings'})
            if kind=='/Filespec':blocked.update({'/EF','/AF'})
            if str(resolve(obj.get('/S',''))) in ACTIVE_ACTIONS:
                blocked.update({'/S','/JS','/JavaScript','/URI','/F','/Next','/EF'})
            for key in list(obj):
                child=obj.raw_get(key)
                if kind=='/Catalog' and str(key)=='/Names':
                    if name_tree(child):active=True
                    continue
                resolved=resolve(child)
                is_action=isinstance(resolved,DictionaryObject) and str(resolve(resolved.get('/S',''))) in ACTIVE_ACTIONS
                if str(key) in blocked or is_action:
                    active=True
                    if clean:del obj[key]
                else:stack.append(child)
        elif isinstance(obj,ArrayObject):stack.extend(obj)
    return active


def prepare_pdf(source, destination):
    from pypdf.errors import PdfReadError
    try:return _prepare_pdf(source,destination,strict=True)
    except PdfReadError:
        # Old source PDFs may contain broken xref offsets. A recovered source
        # is always rebuilt as a clearly labeled derived preview, then parsed
        # strictly; its original bytes are never sent inline on that basis.
        return _prepare_pdf(source,destination,strict=False)


def _prepare_pdf(source, destination, *, strict):
    from pypdf import PdfReader, PdfWriter
    source,destination=Path(source),Path(destination)
    reader=PdfReader(source,strict=strict)
    if reader.is_encrypted:
        # An owner-password-only PDF opens with the empty user password, which is
        # the normal case for published standards and drawings. Anything that
        # really needs a user password stays refused rather than guessed.
        try:opened=reader.decrypt('')
        except Exception:opened=0
        if not opened:
            raise ValueError('PDF_USER_PASSWORD_REQUIRED')
    if not 1<=len(reader.pages)<=MAX_PAGES:
        raise ValueError('PDF_PAGE_LIMIT')
    # Trailer traversal includes catalog and pages. Names/action keys are not
    # allowed even when they occur in an indirect object or an annotation.
    active=_walk(reader.trailer)
    if not active and strict:
        return {'path':source,'kind':'ORIGINAL_PDF','sha256':file_sha256(source),
                'pages':len(reader.pages),'active_content_removed':False}
    destination.parent.mkdir(parents=True,exist_ok=True)
    writer=PdfWriter()
    dimensions=[]
    for page in reader.pages:
        dimensions.append(tuple(float(x) for x in page.mediabox))
        writer.add_page(page)
    _walk(writer._root_object,clean=True)
    temporary=destination.with_suffix('.tmp.pdf')
    with temporary.open('wb') as stream:writer.write(stream)
    verified=PdfReader(temporary,strict=True)
    if (_walk(verified.trailer) or len(verified.pages)!=len(dimensions)
            or not _same_boxes([tuple(float(x) for x in p.mediabox) for p in verified.pages],
                              dimensions)):
        temporary.unlink(missing_ok=True)
        raise ValueError('PDF_PREVIEW_VALIDATION_FAILED')
    temporary.replace(destination)
    return {'path':destination,'kind':'DERIVED_PDF','sha256':file_sha256(destination),
            'pages':len(dimensions),'active_content_removed':True}


def _same_boxes(actual, expected, tolerance=0.01):
    """Page geometry is unchanged within the 1/100 pt that PDF real numbers keep.

    A writer serialises a source value like 595.29998779 as 595.299988; refusing
    that as a changed page rejected otherwise perfect previews of ordinary
    documents. A real size change is far larger than a hundredth of a point.
    """
    if len(actual)!=len(expected):return False
    return all(len(a)==len(b) and all(abs(x-y)<=tolerance for x,y in zip(a,b))
               for a,b in zip(actual,expected))


def office_admitted(source, *, allow_external_links=False, allow_large_xml=False):
    """Admit an Office file for local conversion, or say exactly why not.

    The OOXML package is inspected first (macros, embedded objects, external
    relationships, active fields). Legacy binary formats (.doc/.xls/.ppt) and
    WPS files carry the same macro/embedded-object risk that this package scan
    cannot read, so they are converted only in the Owner's offline builder with
    macros disabled in the converter profile - never on a request path - and are
    labelled as a converted preview exactly like the OOXML ones.

    ``allow_external_links`` and ``allow_large_xml`` exist only for that offline
    builder: a hyperlink target or a large stylesheet cannot execute in a
    headless conversion with macros disabled and no network, and refusing them
    withheld a preview from ordinary published notices. Macros, embedded
    objects and active fields are refused in every mode.
    """
    source=Path(source)
    if source.suffix.lower() not in {'.docx','.xlsx','.pptx'}:
        raise ValueError('OFFICE_FORMAT_UNSUPPORTED')
    with zipfile.ZipFile(source) as archive:
        entries=archive.infolist()
        if len(entries)>10000 or sum(x.file_size for x in entries)>MAX_OFFICE_EXPANDED:
            raise ValueError('OFFICE_EXPANSION_LIMIT')
        for item in entries:
            name=item.filename.lower()
            if any(part in name for part in ('vba','activex','embeddings/','externallinks/')):
                raise ValueError('OFFICE_ACTIVE_CONTENT')
            if name.endswith('.rels'):
                if item.file_size>512*1024:raise ValueError('OFFICE_RELATIONSHIP_LIMIT')
                if allow_external_links:continue
                root=ElementTree.fromstring(archive.read(item))
                if any(node.attrib.get('TargetMode','').lower()=='external' for node in root):
                    raise ValueError('OFFICE_EXTERNAL_LINK')
            if name.endswith('.xml'):
                if item.file_size>8*1024*1024 and not allow_large_xml:raise ValueError('OFFICE_XML_LIMIT')
                text=archive.read(item).decode('utf-8','strict')
                if _active_field(text):
                    raise ValueError('OFFICE_ACTIVE_FIELD')


# A field code can fetch or run something: a Word field instruction, a
# spreadsheet formula or a defined name. Ordinary cell text cannot - and one
# published data-integrity workbook was refused only because a cell happened to
# contain the English word "database". So the scan reads field content, never
# the document's prose.
_FIELD = re.compile(r'<(?:\w+:)?instrText[^>]*>(.*?)</(?:\w+:)?instrText>'
                    r'|<(?:\w+:)?f(?:\s[^>]*)?>(.*?)</(?:\w+:)?f>'
                    r'|<(?:\w+:)?definedName[^>]*>(.*?)</(?:\w+:)?definedName>', re.S)
_ACTIVE_FIELD = re.compile(r'\b(?:DDEAUTO|DDE|INCLUDETEXT|INCLUDEPICTURE|WEBSERVICE|RTD)\b', re.I)


def _active_field(xml):
    return any(_ACTIVE_FIELD.search(next(group for group in match.groups() if group is not None))
               for match in _FIELD.finditer(xml))



def prepare_office(source, destination, *, soffice, allow_legacy=False, allow_external_links=False):
    source=Path(source)
    if allow_legacy and source.suffix.lower() in LEGACY_OFFICE:
        # Offline builder only: the binary format cannot be inspected as a
        # package, so the converter runs headless with macros disabled, in a
        # disposable profile, under the sandbox policy below - and its output is
        # labelled DERIVED_PDF, never presented as the original.
        pass
    elif allow_external_links:
        office_admitted(source, allow_external_links=True, allow_large_xml=True)
    else:
        office_admitted(source)
    destination=Path(destination);destination.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='rc14-office-',dir=destination.parent) as temp:
        work=Path(temp);original=work/('source'+Path(source).suffix.lower())
        shutil.copyfile(source,original)
        profile=work/'profile';(profile/'user').mkdir(parents=True)
        (profile/'user/registrymodifications.xcu').write_text('''<?xml version="1.0" encoding="UTF-8"?>
<oor:items xmlns:oor="http://openoffice.org/2001/registry">
<item oor:path="/org.openoffice.Office.Common/Security/Scripting"><prop oor:name="MacroSecurityLevel" oor:op="fuse"><value>3</value></prop></item>
<item oor:path="/org.openoffice.Office.Common/Security/Scripting"><prop oor:name="DisableMacrosExecution" oor:op="fuse"><value>true</value></prop></item>
<item oor:path="/org.openoffice.Office.Common/Load"><prop oor:name="UpdateDocMode" oor:op="fuse"><value>0</value></prop></item>
</oor:items>''')
        # Runs only on the Owner Mac's already-installed approved converter.
        # The converter cannot reach a network or write outside this temporary
        # working/profile directory (apart from normal OS temporary files).
        policy='(version 1)(allow default)(deny network*)(deny file-write*)'+(
            '(allow file-write* (subpath '+json.dumps(str(work.resolve()))+') '
            '(subpath "/private/tmp") (subpath "/private/var/folders") (subpath "/dev"))')
        policy += ('(deny file-read* (require-all (subpath '+json.dumps(str(Path.home()))+') '
                   '(require-not (subpath '+json.dumps(str(work.resolve()))+')) '
                   '(require-not (subpath '+json.dumps(str(Path.home()/'.cache/codex-runtimes'))+'))))'
                   '(allow file-read-metadata)')
        result=subprocess.run(['/usr/bin/sandbox-exec','-p',policy,str(soffice),
            '-env:UserInstallation='+profile.as_uri(),'--headless','--nologo','--nodefault',
            '--nofirststartwizard','--convert-to','pdf','--outdir',str(work),str(original)],
            cwd=work,capture_output=True,timeout=90)
        generated=work/'source.pdf'
        if result.returncode or not generated.is_file():raise ValueError('OFFICE_CONVERSION_FAILED')
        prepared=prepare_pdf(generated,destination)
        if prepared['path']!=destination:shutil.copyfile(prepared['path'],destination)
    return {'path':destination,'kind':'DERIVED_PDF','sha256':file_sha256(destination),
            'pages':prepared['pages'],'active_content_removed':True}
