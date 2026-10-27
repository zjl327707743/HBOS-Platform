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

MAX_PAGES = 2000
MAX_OBJECTS = 200000
MAX_OFFICE_EXPANDED = 64 * 1024 * 1024
ACTIVE_ACTIONS = frozenset({'/JavaScript','/Launch','/GoToR','/GoToE','/URI',
                            '/SubmitForm','/ImportData','/Rendition','/Sound',
                            '/Movie','/RichMediaExecute'})


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
            if kind=='/Catalog':blocked.update({'/AA','/OpenAction','/AcroForm','/Names','/Collection','/AF'})
            if kind=='/Page':blocked.update({'/AA','/Annots','/AF'})
            if kind=='/Annot':blocked.update({'/A','/AA','/RichMediaContent','/RichMediaSettings'})
            if kind=='/Filespec':blocked.update({'/EF','/AF'})
            if str(resolve(obj.get('/S',''))) in ACTIVE_ACTIONS:
                blocked.update({'/S','/JS','/JavaScript','/URI','/F','/Next','/EF'})
            for key in list(obj):
                child=obj.raw_get(key)
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
    if reader.is_encrypted or not 1<=len(reader.pages)<=MAX_PAGES:
        raise ValueError('PDF_ENCRYPTED_OR_PAGE_LIMIT')
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
            or [tuple(float(x) for x in p.mediabox) for p in verified.pages]!=dimensions):
        temporary.unlink(missing_ok=True)
        raise ValueError('PDF_PREVIEW_VALIDATION_FAILED')
    temporary.replace(destination)
    return {'path':destination,'kind':'DERIVED_PDF','sha256':file_sha256(destination),
            'pages':len(dimensions),'active_content_removed':True}


def office_admitted(source):
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
                root=ElementTree.fromstring(archive.read(item))
                if any(node.attrib.get('TargetMode','').lower()=='external' for node in root):
                    raise ValueError('OFFICE_EXTERNAL_LINK')
            if name.endswith('.xml'):
                if item.file_size>8*1024*1024:raise ValueError('OFFICE_XML_LIMIT')
                text=archive.read(item).decode('utf-8','strict')
                if re.search(r'\b(?:DDEAUTO|DDE|INCLUDETEXT|INCLUDEPICTURE|WEBSERVICE|DATABASE)\b',text,re.I):
                    raise ValueError('OFFICE_ACTIVE_FIELD')


def prepare_office(source, destination, *, soffice):
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
