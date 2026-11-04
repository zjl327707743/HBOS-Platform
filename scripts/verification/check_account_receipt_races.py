#!/usr/bin/env python3
"""Deterministic MariaDB receipt regression harness; never attaches to a Frappe Site.

Required: DB_HOST, DB_PASSWORD. Optional DB_PORT (3306), DB_USER (root),
DB_NAME (must begin hbos_r6_receipt_), DB_ISOLATION (REPEATABLE READ or READ COMMITTED),
RECEIPT_SOURCE, SOURCE_COMMIT, RESULT_PATH.
An isolated DB is created and retained. Caller owns environment lifecycle.
The real write_receipts.py bytes run against a tiny Frappe facade backed by
independent pymysql connections. Only receipt cache.set_value is fault injected.
Existing-row retries/settlement/sealing are tested; DocType insert/auth HTTP are
outside this harness. No credentials appear in output.
"""
from __future__ import annotations
import datetime, hashlib, importlib.util, json, os, pathlib, re, sys, threading, time, types, uuid
import pymysql

SOURCE = pathlib.Path(os.environ.get('RECEIPT_SOURCE', '/Users/hb/Projects/HBOS/workspaces/product/apps/hbos_portal/hbos_portal/auth/write_receipts.py'))
SOURCE_BYTES = SOURCE.read_bytes()
SOURCE_SHA256 = hashlib.sha256(SOURCE_BYTES).hexdigest()
HOST = os.environ['DB_HOST']
PASSWORD = os.environ['DB_PASSWORD']
DB_NAME = os.environ.get('DB_NAME', 'hbos_r6_receipt_' + uuid.uuid4().hex[:12])
if not re.fullmatch(r'hbos_r6_receipt_[a-zA-Z0-9_]+', DB_NAME):
    raise SystemExit('DB_NAME must be an isolated hbos_r6_receipt_ namespace')
ISOLATION = os.environ.get('DB_ISOLATION', 'REPEATABLE READ').upper().replace('-', ' ')
if ISOLATION not in ('REPEATABLE READ', 'READ COMMITTED'):
    raise SystemExit('DB_ISOLATION must be REPEATABLE READ or READ COMMITTED')
CONN_ARGS = dict(host=HOST, port=int(os.environ.get('DB_PORT', '3306')), user=os.environ.get('DB_USER', 'root'), password=PASSWORD, charset='utf8mb4', autocommit=False)
TABLE = '`tabHBOS Account Write Receipt`'
SECRET = 'isolated-receipt-harness-key-not-a-real-site-secret'
ACTOR = 'synthetic-receipt@hbos.test'
SITE = 'isolated-receipt-harness.localhost'
CONTEXT = 'isolated-original-context-0123456789abcdef'
PAYLOAD = 'synthetic-password-intent-digest'
local = threading.local()
trace_lock = threading.Lock()
TRACE = []
RESULTS = []
CONNECTIONS = []

class QueryDeadlockError(Exception): pass
class QueryTimeoutError(Exception): pass

def error_detail(exc, depth=0):
    args = list(getattr(exc, 'args', ()))
    value = {'type':type(exc).__name__, 'args':args, 'code':args[0] if args and isinstance(args[0], int) else None, 'message':str(exc)}
    previous = exc.__cause__ or exc.__context__
    if previous is not None and previous is not exc and depth < 3:
        value['underlying'] = error_detail(previous, depth+1)
    return value

def assert_receipt_rejection(error, allowed):
    assert error and error['type'] in allowed, {'expected_receipt_rejection':sorted(allowed), 'actual':error}


def trace(event, **kw):
    with trace_lock:
        TRACE.append({'seq': len(TRACE)+1, 'thread': threading.current_thread().name, 'event': event, **kw})

def connect(use_db=True):
    c = pymysql.connect(**CONN_ARGS, **({'database': DB_NAME} if use_db else {}))
    with c.cursor() as cur:
        cur.execute('SET SESSION TRANSACTION ISOLATION LEVEL '+ISOLATION)
        cur.execute('SET SESSION innodb_lock_wait_timeout=8')
        cur.execute('SELECT CONNECTION_ID()')
        cid = cur.fetchone()[0]
        cur.execute('SELECT @@session.tx_isolation')
        actual_isolation = cur.fetchone()[0]
    c.commit()
    with trace_lock: CONNECTIONS.append({'connection_id':cid, 'actual_tx_isolation':actual_isolation})
    trace('connection_open', connection_id=cid, actual_tx_isolation=actual_isolation)
    return DB(c, cid)

class DB:
    def __init__(self, conn, cid): self.conn, self.cid, self.read_hook = conn, cid, None
    def sql(self, query, args=None, as_dict=False):
        with self.conn.cursor(pymysql.cursors.DictCursor if as_dict else pymysql.cursors.Cursor) as cur:
            try:
                cur.execute(query, args)
            except pymysql.err.OperationalError as exc:
                code = exc.args[0] if exc.args else None
                # Pinned Frappe database.py 277-281 / mariadb/database.py 27-33:
                # is_deadlocked = ER.LOCK_DEADLOCK(1213) or ER.CHECKREAD(1020);
                # is_timedout = ER.LOCK_WAIT_TIMEOUT(1205). No other translation.
                mapped = {1205:QueryTimeoutError, 1213:QueryDeadlockError, 1020:QueryDeadlockError}.get(code)
                trace('sql_error', connection_id=self.cid, error=error_detail(exc), normalized_to=mapped.__name__ if mapped else None)
                if mapped: raise mapped(*exc.args) from exc
                raise
            result = list(cur.fetchall()) if cur.description else []
            if 'FOR UPDATE' in query.upper(): trace('locking_read', connection_id=self.cid, rows=result)
            elif query.lstrip().upper().startswith('UPDATE '): trace('update', connection_id=self.cid, affected=cur.rowcount)
            return result
    def get_value(self, doctype, filters, fields, as_dict=False, **kwargs):
        assert doctype == 'HBOS Account Write Receipt'
        names = fields if isinstance(fields, (list, tuple)) else [fields]
        where = ' AND '.join('`'+k+'`=%s' for k in filters)
        result = self.sql('SELECT '+','.join('`'+k+'`' for k in names)+' FROM '+TABLE+' WHERE '+where, tuple(filters.values()), as_dict=as_dict)
        row = result[0] if result else None
        trace('snapshot_read', connection_id=self.cid, state=(row or {}).get('state') if as_dict else None, attempt=(row or {}).get('attempt_count') if as_dict else None)
        hook, self.read_hook = self.read_hook, None
        if hook: hook(row)
        return row
    def set_value(self, doctype, name, values, **kwargs):
        assert doctype == 'HBOS Account Write Receipt'
        q = 'UPDATE '+TABLE+' SET '+','.join('`'+k+'`=%s' for k in values)+' WHERE name=%s'
        self.sql(q, (*values.values(), name))
    def commit(self): self.conn.commit(); trace('commit', connection_id=self.cid)
    def rollback(self): self.conn.rollback(); trace('rollback', connection_id=self.cid)
    def close(self): self.conn.rollback(); self.conn.close()

class DBProxy:
    def __getattr__(self, key): return getattr(local.db, key)

class FlagsProxy:
    def __getattr__(self, key): return getattr(local, key)
    def __setattr__(self, key, value): setattr(local, key, value)
    def __delattr__(self, key): delattr(local, key)

class Cache:
    def __init__(self): self.fail_writes = False; self.write_failures = 0
    def set_value(self, key, value, **kwargs):
        if self.fail_writes:
            self.write_failures += 1
            raise ConnectionError('controlled receipt accelerator write failure')
    def get_value(self, key): return None

cache = Cache()
frappe = types.ModuleType('frappe')
frappe.db = DBProxy()
frappe.local = types.SimpleNamespace(site=SITE, conf={'hbos_account_write_receipt_key': SECRET})
frappe.flags = FlagsProxy()
frappe.cache = cache
frappe.QueryDeadlockError = QueryDeadlockError
frappe.QueryTimeoutError = QueryTimeoutError
frappe.utils = types.SimpleNamespace(now_datetime=lambda: datetime.datetime.now(), get_datetime=lambda x: x if isinstance(x, datetime.datetime) else datetime.datetime.fromisoformat(str(x)))
sys.modules['frappe'] = frappe
r = types.ModuleType('receipt_subject')
r.__file__ = str(SOURCE)
exec(compile(SOURCE_BYTES, str(SOURCE), 'exec'), r.__dict__)

root = connect(False)
root.sql('CREATE DATABASE `'+DB_NAME+'` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci')
root.commit(); root.close()
control = connect()
local.db = control
control.sql('CREATE TABLE '+TABLE+' (name varchar(140) PRIMARY KEY,request_key varchar(64) NOT NULL UNIQUE,channel varchar(32),request_id varchar(36),site_name varchar(140),actor varchar(140),subject varchar(140),action varchar(32),state varchar(32),intent_digest varchar(64),claimed_at datetime(6),committed_at datetime(6),failed_at datetime(6),sealed_at datetime(6),sealed_by varchar(140),failure_code varchar(140),attempt_count int NOT NULL DEFAULT 0,outcome_json text) ENGINE=InnoDB')
for table in ('effects', 'audit'):
    control.sql('CREATE TABLE `'+table+'` (id bigint AUTO_INCREMENT PRIMARY KEY, request_key varchar(64), attempt int, worker varchar(64)) ENGINE=InnoDB')
control.commit()

def seed(channel='session', state='ABORTED', attempt=1, stale=False):
    request_id = str(uuid.uuid4())
    action = 'recovery' if channel == 'guest_recovery' else 'password'
    key = (r.guest_request_key(SECRET, site=SITE, request_id=request_id, context=CONTEXT) if channel == 'guest_recovery' else r.session_request_key(SECRET, site=SITE, actor=ACTOR, request_id=request_id))
    row = dict(name=uuid.uuid4().hex, request_key=key, channel=channel, request_id=request_id, site_name=SITE, actor=ACTOR, subject=ACTOR, action=action, state=state, intent_digest=r.intent_digest(SECRET, site=SITE, actor=ACTOR, subject=ACTOR, action=action, payload_digest=PAYLOAD), attempt_count=attempt, claimed_at=datetime.datetime.now()-datetime.timedelta(seconds=300 if stale else 1), committed_at=datetime.datetime.now() if state == 'COMMITTED' else None)
    control.sql('INSERT INTO '+TABLE+' ('+','.join('`'+k+'`' for k in row)+') VALUES ('+','.join(['%s']*len(row))+')', tuple(row.values()))
    control.commit()
    return row

def claim(row):
    if row['channel'] == 'guest_recovery':
        return r.claim_guest_recovery(actor=ACTOR, action='recovery', request_id=row['request_id'], context=CONTEXT, payload_digest=PAYLOAD, secret=SECRET)
    return r.claim(actor=ACTOR, subject=ACTOR, action='password', request_id=row['request_id'], payload_digest=PAYLOAD, secret=SECRET)

def token(row): return dict(status='claimed', request_key=row['request_key'], row=row.copy(), attempt=row['attempt_count'])
def getrow(row):
    control.rollback()
    return control.sql('SELECT state,attempt_count,claimed_at FROM '+TABLE+' WHERE name=%s', (row['name'],), as_dict=True)[0]
def counts(row):
    control.rollback()
    return {t:control.sql('SELECT COUNT(*) FROM `'+t+'` WHERE request_key=%s', (row['request_key'],))[0][0] for t in ('effects','audit')}
def settle(tok):
    if hasattr(r, 'assert_active'): r.assert_active(tok)
    for t in ('effects', 'audit'):
        local.db.sql('INSERT INTO `'+t+'` (request_key,attempt,worker) VALUES (%s,%s,%s)', (tok['request_key'],tok['attempt'],threading.current_thread().name))
    r.mark_committed(tok, {'synthetic': True})
    local.db.commit()

def run_case(name, fn):
    start = len(TRACE)
    try:
        detail = fn()
        raw_sql_errors=[e for e in TRACE[start:] if e['event']=='sql_error' and not e.get('normalized_to')]
        assert not raw_sql_errors, {'unrecognized_sql_errors':raw_sql_errors}
        RESULTS.append({'name':name,'status':'PASS','detail':detail,'trace_range':[start+1,len(TRACE)]})
    except Exception as e:
        control.rollback()
        RESULTS.append({'name':name,'status':'FAIL','error':error_detail(e),'sql_errors':[x for x in TRACE[start:] if x['event']=='sql_error'],'trace_range':[start+1,len(TRACE)]})

def controlled_retry(channel, winner):
    row = seed(channel)
    barrier = threading.Barrier(2)
    release_b = threading.Event()
    outcomes, errors, cids = {}, {}, {}
    def worker(label):
        d=connect(); local.db=d; cids[label]=d.cid
        def pause(snapshot):
            assert snapshot['state']=='ABORTED' and snapshot['attempt_count']==1
            trace('barrier_after_snapshot', label=label, state=snapshot['state'], attempt=snapshot['attempt_count'])
            barrier.wait(10)
            if label=='B':
                if not release_b.wait(15): raise TimeoutError('A did not finish')
                trace('B_released_after_A_commit')
        d.read_hook=pause
        try:
            tok=claim(row)
            outcomes[label]={'status':tok['status'],'attempt':tok.get('attempt')}
            if tok['status']=='claimed':
                if label=='A' and winner=='pending': pass
                elif label=='A' and winner=='sealed':
                    d.sql('UPDATE '+TABLE+' SET state=%s,claimed_at=%s WHERE name=%s',('PENDING',datetime.datetime.now()-datetime.timedelta(seconds=300),row['name']))
                    d.commit()
                    if channel!='session': raise AssertionError('seal test only session')
                    r.seal(ACTOR,row['request_id'],action='password',secret=SECRET)
                    d.commit()
                else: settle(tok)
        except Exception as e:
            d.rollback(); errors[label]=error_detail(e)
        finally:
            if label=='A': release_b.set()
            d.close()
    a=threading.Thread(target=worker,args=('A',),name='A-'+winner)
    b=threading.Thread(target=worker,args=('B',),name='B-'+winner)
    a.start(); b.start(); a.join(25); b.join(25)
    assert not a.is_alive() and not b.is_alive(), 'controlled worker timeout'
    final=getrow(row); n=counts(row)
    detail={'connection_ids':cids,'outcomes':outcomes,'errors':errors,'final':final,'counts':n,'initial_state':'ABORTED','initial_attempt':1,'winner':winner}
    trace('case_observation',**detail)
    assert len(set(cids.values()))==2, detail
    assert 'A' not in errors, detail
    # A successful-looking final row must never mask raw database exceptions.
    # B must explicitly replay the winner or receive a receipt-domain refusal.
    if 'B' in errors:
        assert_receipt_rejection(errors['B'], {'ReceiptProcessing','ReceiptSealed'})
    elif winner=='committed':
        assert outcomes.get('B',{}).get('status')=='replayed', detail
    else:
        raise AssertionError({'missing_explicit_loser_refusal':detail})
    assert sum(o['status']=='claimed' for o in outcomes.values())==1, detail
    if winner=='committed': assert final['state']=='COMMITTED' and n=={'effects':1,'audit':1}, detail
    elif winner=='pending': assert final['state']=='PENDING' and final['attempt_count']==2 and n=={'effects':0,'audit':0}, detail
    else: assert final['state']=='SEALED' and n=={'effects':0,'audit':0}, detail
    return detail

def late_attempt(op, channel='session'):
    row=seed(channel,state='PENDING'); old=token(row)
    control.sql('UPDATE '+TABLE+' SET state=%s WHERE name=%s',('ABORTED',row['name'])); control.commit()
    new=claim(row); control.commit()
    d=connect(); local.db=d; rejected=False
    try:
        if op=='abort': r.abort(old,'late-old-attempt')
        else:
            try: settle(old)
            except r.ReceiptError: d.rollback(); rejected=True
    finally: d.close(); local.db=control
    final=getrow(row); n=counts(row)
    detail={'old_attempt':old['attempt'],'new_attempt':new['attempt'],'final':final,'counts':n,'rejected':rejected}
    assert final['state']=='PENDING' and final['attempt_count']==2 and n=={'effects':0,'audit':0},detail
    if op=='commit': assert rejected,detail
    settle(new)
    assert counts(row)=={'effects':1,'audit':1},detail
    detail['new_attempt_settled']=getrow(row)
    return detail

def delayed_seal():
    row=seed(state='PENDING',stale=True)
    read=threading.Event(); release=threading.Event(); result={}
    def worker():
        d=connect();local.db=d
        def pause(snapshot):
            assert snapshot['state']=='PENDING' and snapshot['attempt_count']==1
            read.set()
            if not release.wait(15):raise TimeoutError('seal release')
        d.read_hook=pause
        try:result['response']=r.seal(ACTOR,row['request_id'],action='password',secret=SECRET);d.commit()
        except Exception as e:result['error']=error_detail(e);d.rollback()
        finally:d.close()
    t=threading.Thread(target=worker,name='late-seal');t.start()
    assert read.wait(10)
    control.sql('UPDATE '+TABLE+' SET state=%s WHERE name=%s',('ABORTED',row['name']));control.commit()
    new=claim(row);control.commit();release.set();t.join(20)
    assert not t.is_alive()
    final=getrow(row)
    detail={'seal_result':result,'final':final,'old_attempt':1,'new_attempt':new['attempt']}
    assert_receipt_rejection(result.get('error'), {'ReceiptProcessing'})
    assert final['state']=='PENDING' and final['attempt_count']==2,detail
    settle(new)
    return detail

def terminal_protection(state):
    row=seed(state=state)
    d=connect();local.db=d
    try:
        tok=token(row)
        r.abort(tok,'late')
        try:r.mark_committed(tok,{});d.commit();accepted=True
        except r.ReceiptError:d.rollback();accepted=False
        try:out=claim(row);d.rollback()
        except r.ReceiptError as e:d.rollback();out={'error':error_detail(e)}
    finally:d.close();local.db=control
    final=getrow(row)
    assert final['state']==state and not accepted,{'final':final,'accepted':accepted,'claim':out}
    return {'final':final,'claim':out,'stale_settle_rejected':not accepted}

def cache_failure():
    row=seed();tok=claim(row);settle(tok)
    cache.fail_writes=True
    try:r.publish_cache(tok)
    finally:cache.fail_writes=False
    state=r.read_receipt(ACTOR,row['request_id'],action='password',secret=SECRET)
    again=claim(row);control.rollback()
    n=counts(row)
    assert state['completed'] and again['status']=='replayed' and n=={'effects':1,'audit':1} and cache.write_failures>=1
    return {'state':state,'replay':again['status'],'counts':n,'injected_write_failures':cache.write_failures,'injection_scope':'receipt cache.set_value only; SQL is real; not an actual Redis outage'}

def guest_binding():
    row=seed(channel='guest_recovery');tok=claim(row);settle(tok)
    own=r.read_guest_recovery(request_id=row['request_id'],context=CONTEXT,payload_digest=PAYLOAD,secret=SECRET)
    blank=r.read_guest_recovery(request_id=row['request_id'],context='',payload_digest=PAYLOAD,secret=SECRET)
    wrong=r.read_guest_recovery(request_id=row['request_id'],context='different-context-0123456789abcdef',payload_digest=PAYLOAD,secret=SECRET)
    mismatch=False
    try:r.read_guest_recovery(request_id=row['request_id'],context=CONTEXT,payload_digest='changed-intent',secret=SECRET)
    except r.ReceiptError:mismatch=True
    control.rollback()
    assert own['completed'] and blank is None and wrong is None and mismatch
    return {'correct_context_completed':True,'bare_uuid_result':blank,'wrong_context_result':wrong,'changed_intent_rejected':mismatch,'expiry_http':'NOT_RUN_BY_THIS_HARNESS'}

def before_non_sql_effects(channel):
    row=seed(channel,state='PENDING'); old=token(row)
    control.sql('UPDATE '+TABLE+' SET state=%s WHERE name=%s',('ABORTED',row['name']));control.commit()
    new=claim(row);control.commit()
    non_sql={'old_attempt_effects':0,'new_attempt_effects':0}
    rejection=None
    d=connect();local.db=d
    try:
        try:
            # Match accounts.py: fence before proof consumption, session/epoch
            # invalidation, password mutation or other irreversible operations.
            if hasattr(r,'assert_active'):r.assert_active(old)
            non_sql['old_attempt_effects']+=1
        except r.ReceiptError as exc:
            rejection=error_detail(exc);d.rollback()
        assert_receipt_rejection(rejection, {'ReceiptSealed'})
        assert non_sql['old_attempt_effects']==0,non_sql
        if hasattr(r,'assert_active'):r.assert_active(new)
        non_sql['new_attempt_effects']+=1
        settle(new)
    finally:d.close();local.db=control
    final=getrow(row);n=counts(row)
    assert final['state']=='COMMITTED' and final['attempt_count']==2 and n=={'effects':1,'audit':1} and non_sql=={'old_attempt_effects':0,'new_attempt_effects':1}
    return {'old_attempt_rejection':rejection,'non_sql_counters':non_sql,'final':final,'counts':n}

for ch in ('session','guest_recovery'):
    run_case(ch+'__attempt_fence_before_non_sql_effects',lambda ch=ch:before_non_sql_effects(ch))

for ch in ('session','guest_recovery'):
    for winner in ('committed','pending'):
        run_case(ch+'__two_aborted_retries__'+winner,lambda ch=ch,winner=winner:controlled_retry(ch,winner))
run_case('session__stale_aborted_cannot_regress_sealed',lambda:controlled_retry('session','sealed'))
for ch in ('session','guest_recovery'):
    for op in ('commit','abort'):
        run_case(ch+'__late_old_attempt_'+op,lambda op=op,ch=ch:late_attempt(op,ch))
run_case('session__late_old_attempt_seal',delayed_seal)
for s in ('COMMITTED','SEALED'):
    run_case('terminal_'+s,lambda s=s:terminal_protection(s))
run_case('receipt_cache_write_failure',cache_failure)
run_case('guest_context_and_intent_binding',guest_binding)
control.close()
output={'at':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),'source':str(SOURCE.resolve()),'source_sha256':SOURCE_SHA256,'source_commit':os.environ.get('SOURCE_COMMIT','WORKING_FILE'),'database':DB_NAME,'database_retained':True,'requested_isolation':ISOLATION,'connections':CONNECTIONS,'sql_error_normalization':{'1205':'QueryTimeoutError','1213':'QueryDeadlockError','1020':'QueryDeadlockError (pinned Frappe CHECKREAD); raw/normalized SQL exceptions never accepted as receipt-domain rejection'},'scope':'isolated empty MariaDB database; production module bytes; tiny Frappe SQL/cache facade; no Site/user/real business data','passed':sum(x['status']=='PASS' for x in RESULTS),'failed':sum(x['status']=='FAIL' for x in RESULTS),'cases':RESULTS,'trace':TRACE}
body=json.dumps(output,ensure_ascii=False,indent=2,default=str)
if os.environ.get('RESULT_PATH'):pathlib.Path(os.environ['RESULT_PATH']).write_text(body)
print(body)
sys.exit(1 if output['failed'] else 0)
