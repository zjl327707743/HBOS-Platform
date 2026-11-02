"""One-shot local profiling of a real authenticated request; no payload capture.

An Owner-controlled file in the existing private configuration mount arms an
exact request ID for at most ten minutes. There is no public arming endpoint.
Only function names, counts, CPU/wall totals and caller edges are persisted.
"""
from __future__ import annotations
import cProfile
import json
import os
from pathlib import Path
import pstats
import re
import time
import contextlib

ARM = Path('/run/hbos-reference/rc1-profile-arm.json')
OUT = Path('/run/hbos-uat4-audit/rc1-profiles')

def begin():
    import frappe
    if not ARM.is_file():return
    try:
        request=frappe.request
        if not request or request.path not in {
            '/api/method/hb_knowledge_app.hb_knowledge.api.search',
            '/api/method/hb_knowledge_app.hb_knowledge.frappe_factory.authority_call',
            '/api/method/hb_knowledge_app.hb_knowledge.frappe_factory.authority_search',
        }:return
        rid=request.headers.get('X-HBOS-Request-ID','')
        if not re.fullmatch(r'rc1-profile-[A-Za-z0-9_-]{1,80}',rid):return
        arm=json.loads(ARM.read_text())
        if arm.get('request_id')!=rid or not time.time()<float(arm['expires_at'])<=time.time()+600:return
        # Portal authentication has already run before before_request. Signed
        # callbacks authenticate in their handler, and their business result is
        # independently checked by the orchestrating Portal request.
        if request.path.endswith('.api.search') and frappe.session.user in {'Guest','Administrator'}:return
        OUT.mkdir(mode=0o700,parents=True,exist_ok=True)
        endpoint=request.path.rsplit('.',1)[-1]
        for number in range(1,4):
            profile_id=rid+'--'+endpoint+'-'+str(number)
            claim=OUT/(profile_id+'.claimed')
            try:fd=os.open(claim,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
            except FileExistsError:continue
            os.close(fd);break
        else:return
        profiler=cProfile.Profile()
        frappe.local.hbos_request_profile=(profile_id,profiler,time.perf_counter(),time.thread_time())
        profiler.enable()
    except (OSError,ValueError,KeyError,TypeError):return

def finish(response=None):
    import frappe
    state=getattr(frappe.local,'hbos_request_profile',None)
    if state is None:return
    rid,profiler,wall,cpu=state
    profiler.disable()
    del frappe.local.hbos_request_profile
    _persist(rid,profiler,time.perf_counter()-wall,time.thread_time()-cpu,getattr(response,'status_code',None))

def _persist(rid,profiler,elapsed,cpu_elapsed,status_code):
    stats=pstats.Stats(profiler)
    def key(f):
        filename,line,name=f
        # No request arguments, source lines, locals, environment or headers.
        return {'file':str(filename),'line':line,'function':name}
    rows=[]
    for f,(primitive,total,self_time,cumulative,callers) in stats.stats.items():
        rows.append({**key(f),'primitive_calls':primitive,'total_calls':total,
                     'self_wall_s':self_time,'cumulative_wall_s':cumulative,
                     'callers':[{'caller':key(parent),'counts_and_times':list(counts) if isinstance(counts,tuple) else [counts]} for parent,counts in callers.items()]})
    payload={'request_id':rid,'handler_wall_s':elapsed,'handler_thread_cpu_s':cpu_elapsed,
             'status_code':status_code,'functions':rows,
             'accounting':'Cumulative times are nested and must not be summed. Wall and thread CPU totals are independent; socket/SQL/queue functions retain caller edges.'}
    target=OUT/(rid+'.json');temporary=target.with_suffix('.tmp')
    try:
        with temporary.open('w') as handle:
            os.chmod(temporary,0o600);json.dump(payload,handle,separators=(',',':'))
        os.replace(temporary,target)
    except OSError:pass

@contextlib.contextmanager
def function_profile(request_id):
    """The same finite profile on the synchronous service search function."""
    profiler=None
    try:
        arm=json.loads(ARM.read_text())
        if (request_id==arm.get('request_id') and isinstance(request_id,str)
                and re.fullmatch(r'rc1-profile-[A-Za-z0-9_-]{1,80}',request_id)
                and time.time()<float(arm['expires_at'])<=time.time()+600):
            OUT.mkdir(mode=0o700,parents=True,exist_ok=True)
            claim=OUT/(request_id+'--service-search.claimed')
            fd=os.open(claim,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600);os.close(fd)
            profiler=cProfile.Profile();wall=time.perf_counter();cpu=time.thread_time();profiler.enable()
    except (OSError,ValueError,TypeError,KeyError):pass
    try:yield
    finally:
        if profiler:
            profiler.disable();_persist(request_id+'--service-search',profiler,time.perf_counter()-wall,time.thread_time()-cpu,None)
