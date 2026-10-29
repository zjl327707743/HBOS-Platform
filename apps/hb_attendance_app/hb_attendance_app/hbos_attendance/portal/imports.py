"""Current-authority import adapters over existing parsers, logs and writers.

Preview artifacts have immutable IAM provenance; no new identity/storage model.
All rows are resolved before any business write. No native global auto job runs.
"""
from __future__ import annotations

import base64
import hashlib
import io
import json
import tempfile
import zipfile
from contextlib import contextmanager
from datetime import timedelta
from pathlib import Path
from xml.etree import ElementTree

import frappe
from frappe.utils import getdate, now_datetime
from hbos_portal.api.iam_roles import _call
from hbos_portal.auth.onboarding import serialize
from hbos_portal.iam import audit, guards, policy, role_access
from hb_attendance_app.hbos_attendance.portal import personal, role_scope
from hb_attendance_app.hbos_attendance.import_contract import MAX_IMPORT_FILE_SIZE, MONTHLY_SUMMARY

NATIVE = 'hb_attendance_app.hbos_attendance.doctype.hbos_attendance_import_log.hbos_attendance_import_log'
LOG = 'HBOS Attendance Import Log'
PREVIEW = 'attendance.import.preview'
SCHEDULE_PREVIEW = 'attendance.schedule.import.preview'
LOG_FIELDS = ('name','import_type','import_status','run_by','source_file','source_file_name',
    'source_file_hash','period_start','period_end','matched_rows','success_rows','failed_rows',
    'created_checkins','created_attendance','existing_attendance','skipped_duplicates',
    'monthly_summary_staging','notes','modified')


def _native():
    return frappe.get_module(NATIVE)


def _bound(operation):
    value = role_scope.context(operation)
    if value is None or len(value.get('companies', [])) != 1:
        frappe.throw('导入需要当前角色明确的一家公司范围。', frappe.PermissionError)
    return value


def validate_workbook(raw, filename):
    if not isinstance(filename,str) or Path(filename).name != filename or any(char in filename for char in ('?','#','\\')) or not filename.lower().endswith('.xlsx') or len(filename)>140:
        frappe.throw('请选择文件名明确的 .xlsx 文件。', frappe.ValidationError)
    if not raw or len(raw)>MAX_IMPORT_FILE_SIZE:
        frappe.throw('文件须为1字节至10MB。', frappe.ValidationError)
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            entries = archive.infolist()
            if len(entries)>200 or sum(item.file_size for item in entries)>50*1024*1024:
                raise ValueError('展开后的工作簿过大')
            cells=0
            for entry in entries:
                if entry.filename.endswith('vbaProject.bin') or '/externalLinks/' in entry.filename:
                    raise ValueError('不接受宏或外部链接')
                if entry.filename.startswith('xl/worksheets/') and entry.filename.endswith('.xml'):
                    root=ElementTree.fromstring(archive.read(entry))
                    for cell in root.iter('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}c'):
                        cells+=1
                        ref=cell.get('r','')
                        letters=''.join(char for char in ref if char.isalpha())
                        number=''.join(char for char in ref if char.isdigit())
                        col=0
                        for char in letters:col=col*26+ord(char.upper())-64
                        if col>256 or not number or int(number)>20000 or cells>100000:
                            raise ValueError('表格行列超过单批上限')
    except (ValueError,zipfile.BadZipFile,KeyError,ElementTree.ParseError) as exc:
        frappe.throw('无法接受此工作簿：'+str(exc),frappe.ValidationError)


@contextmanager
def _parsed(raw, filename, kind):
    validate_workbook(raw,filename)
    with tempfile.TemporaryDirectory(prefix='hbos-import-') as directory:
        path=Path(directory)/'source.xlsx'
        path.write_bytes(raw)
        if kind=='schedule':
            from hb_attendance_app.hbos_attendance.schedule_import import parse_xlsx_matrix,parse_xlsx_vertical
            records,_=parse_xlsx_matrix(path)
            if not records:records,_=parse_xlsx_vertical(path)
            parsed=frappe._dict(records=records)
        elif kind=='attendance':
            parsed=_native()._parse_xlsx(path)
        else:
            frappe.throw('未登记的导入类型。',frappe.PermissionError)
        if not parsed.records or len(parsed.records)>5000:
            frappe.throw('单批须包含1至5000条可识别记录。',frappe.ValidationError)
        yield parsed


def _plan(parsed,kind):
    operation='attendance.schedule.import' if kind=='schedule' else PREVIEW
    bound=_bound(operation)
    monthly=kind=='attendance' and isinstance(parsed,_native().MonthlyWorkbook)
    if kind=='schedule':
        dates=[getdate(row['date']) for row in parsed.records]
    else:
        summary=parsed.preview_summary()
        dates=[getdate(summary['period_start']),getdate(summary['period_end'])]
    start,end=min(dates),max(dates)
    personal.bounded_request(str(start),str(end))
    if (end-start).days>30:
        frappe.throw('一次导入最多31天。',frappe.ValidationError)
    pad=timedelta(days=2) if kind=='attendance' and not monthly else timedelta(0)
    people=role_scope.historical_employees(bound,start-pad,end+pad)
    by_number,by_name={},{}
    for person in people:
        if person.status!='Active':continue
        device=frappe.db.get_value('Employee',person.name,'attendance_device_id',for_update=True)
        for number in {person.employee_number,device}-{None,''}:
            by_number.setdefault(number,set()).add(person.name)
        by_name.setdefault(person.employee_name,set()).add(person.name)
    by_id={person.name:person for person in people}
    mapping,resolved={},[]
    for index,row in enumerate(parsed.records):
        number,name=row.get('employee_number'),row.get('employee_name')
        matches=by_number.get(number,set()) if number else by_name.get(name,set())
        if len(matches)!=1:
            frappe.throw(f'第{row.get("row",index+1)}行员工未唯一匹配到本公司可证期间；请先核对员工建档与归属。',frappe.PermissionError)
        employee=next(iter(matches)); person=by_id[employee]
        if name and name!=person.employee_name:
            frappe.throw('员工工号与姓名不一致，整批未导入。',frappe.ValidationError)
        department=row.get('department')
        if department and department not in {person.department,frappe.db.get_value('Department',person.department,'department_name',for_update=True) if person.department else ''}:
            frappe.throw('源表部门与可证期间归属不一致，整批未导入。',frappe.PermissionError)
        mapping[row.get('row',index)]=employee
        resolved.append((employee,row))
    names=sorted(set(mapping.values()))
    if len(names)>200:frappe.throw('单批最多200名员工。',frappe.ValidationError)
    params=dict(names=tuple(names),start=start-pad,end=end+pad)
    specs={
        'Employee':('name,modified,employee_name,employee_number,attendance_device_id,company,department,status,default_shift,holiday_list,date_of_joining,relieving_date','name in %(names)s'),
        'HBOS Employee Schedule':('*','employee in %(names)s and schedule_date between %(start)s and %(end)s'),
    }
    if kind=='attendance' and not monthly:
        specs.update({
            'Employee Checkin':('name,modified,employee,time,log_type,shift,shift_start,shift_end,shift_actual_start,shift_actual_end,attendance,skip_auto_attendance,offshift','employee in %(names)s and date(time) between %(start)s and %(end)s'),
            'Attendance':('name,modified,employee,company,attendance_date,docstatus,status,attendance_request,leave_application','employee in %(names)s and attendance_date between %(start)s and %(end)s'),
            'Shift Assignment':('name,modified,employee,company,shift_type,start_date,end_date,docstatus,status','employee in %(names)s and start_date<=%(end)s and (end_date is null or end_date>=%(start)s)'),
            'Leave Application':('name,modified,employee,company,department,from_date,to_date,docstatus,status','employee in %(names)s and from_date<=%(end)s and to_date>=%(start)s and docstatus<2'),
        })
    sources={doctype:frappe.db.sql(f'select {fields} from `tab{doctype}` where {predicate} order by name for update',params,as_dict=True) for doctype,(fields,predicate) in specs.items()}
    company=bound['companies'][0]
    for doctype in ('Attendance','Shift Assignment','Leave Application'):
        for row in sources.get(doctype,[]):
            if row.company and row.company!=company:
                frappe.throw('既有原生记录公司不一致，须先核对。',frappe.PermissionError)
            if doctype=='Leave Application':
                person=by_id[row.employee]
                if getdate(row.from_date)<start-pad or getdate(row.to_date)>end+pad:
                    full=role_scope.historical_employees(bound,getdate(row.from_date),getdate(row.to_date))
                    if row.employee not in {item.name for item in full}:
                        frappe.throw('原生请假的完整期间归属缺少依据。',frappe.PermissionError)
                if row.department and row.department!=person.department:
                    frappe.throw('原生请假部门不一致。',frappe.PermissionError)
    if kind=='schedule':
        keys=[(employee,str(row['date'])) for employee,row in resolved]
        if len(keys)!=len(set(keys)):frappe.throw('源表含同员工同日重复排班。',frappe.ValidationError)
    else:
        shift_names={row.shift_type for row in sources.get('Shift Assignment',[]) if row.shift_type}
        shift_names|={row.default_shift for row in sources['Employee'] if row.default_shift}
        shift_names|={row.shift for row in sources.get('Employee Checkin',[]) if row.shift}
        sources['Shift Type']=frappe.db.sql('select * from `tabShift Type` where name in %s order by name for update',(tuple(sorted(shift_names)) or ('',),),as_dict=True)
    manifest=dict(kind=kind,company=company,scope=bound['scope_label'],employee_names=names,
        date_from=str(start),date_to=str(end),mode='monthly' if monthly else kind,
        expected_inputs=role_access.digest(dict(mapping=mapping,sources=sources,start=start,end=end)))
    summary=dict(total_rows=len(parsed.records),matched_rows=len(names),period_start=str(start),period_end=str(end),
        import_type='员工排班表' if kind=='schedule' else parsed.preview_summary()['import_type'],
        notes='月度汇总仅暂存，不写入打卡或考勤结果。' if monthly else '整批核验通过后按原生规则处理；不自动创建员工。')
    return manifest,mapping,resolved,summary


def _log_hash(name):
    # Hash inside SQL; a department reader never loads another department's
    # batch statistics or staging JSON just to verify immutable provenance.
    fields=','.join("coalesce(cast(`"+field+"` as char),'')" for field in LOG_FIELDS)
    rows=frappe.db.sql(f'select sha2(concat_ws(char(31),{fields}),256) as value from `tab{LOG}` where name=%s for update',(name,),as_dict=True)
    return rows[0].value if rows else None


def _source(manifest):
    file=frappe.get_doc('File',manifest['file_id'],for_update=True)
    target=(LOG,manifest['log_name']) if manifest.get('log_name') else ('Page','hbos-shift-management')
    if not file.is_private or file.owner!=manifest['actor'] or (file.attached_to_doctype,file.attached_to_name)!=target:
        frappe.throw('导入来源附件不一致。',frappe.PermissionError)
    from hb_attendance_app.hbos_attendance.portal.artifacts import private_content
    raw=private_content(file,max_size=MAX_IMPORT_FILE_SIZE)
    if hashlib.sha256(raw).hexdigest()!=manifest['file_hash']:
        frappe.throw('导入来源文件已变化。',frappe.PermissionError)
    return file,raw


def _preview(event_name):
    row=frappe.db.get_value(audit.EVENT,event_name,['actor','operation','after_json'],as_dict=True,for_update=True)
    if not row or row.actor!=policy.get_current_user() or row.operation not in {PREVIEW,SCHEDULE_PREVIEW}:
        frappe.throw('此预览不属于当前账号。',frappe.PermissionError)
    manifest=json.loads(row.after_json)
    if manifest.get('actor')!=row.actor:frappe.throw('预览来源不一致。',frappe.PermissionError)
    _bound('attendance.schedule.import' if manifest['kind']=='schedule' else PREVIEW)
    return manifest


@frappe.whitelist(methods=['POST'])
def preview_import(kind, filename, file_content, request_id, **kwargs):
    def run():
        guards.require_post();role_scope.check_fields({'kind','filename','file_content','request_id'})
        _bound('attendance.schedule.import' if kind=='schedule' else PREVIEW)
        if not isinstance(file_content,str) or len(file_content)>MAX_IMPORT_FILE_SIZE*4//3+8:
            frappe.throw('源文件超过单批限制。',frappe.ValidationError)
        try:raw=base64.b64decode(file_content,validate=True)
        except (ValueError,TypeError):frappe.throw('文件编码无效。',frappe.ValidationError)
        with serialize('attendance-import','company'),_parsed(raw,filename,kind) as parsed:
            manifest,_,_,summary=_plan(parsed,kind)
            operation=SCHEDULE_PREVIEW if kind=='schedule' else PREVIEW
            subject=manifest['employee_names'][0]
            payload=dict(kind=kind,file_hash=hashlib.sha256(raw).hexdigest(),filename=filename)
            replay=audit.replay(request_id,operation,'Employee',subject,payload)
            if replay is not None:
                _source(replay)
                return dict(replay,summary=summary,event_name=frappe.db.get_value(audit.EVENT,{'request_id':request_id},'name',for_update=True),replayed=True)
            log=None
            if kind=='attendance':
                log=frappe.get_doc(dict(doctype=LOG,import_type=summary['import_type'],import_status='Previewed',run_by=policy.get_current_user()))
                log.insert(ignore_permissions=True)
            target=(LOG,log.name) if log else ('Page','hbos-shift-management')
            from hb_attendance_app.hbos_attendance.portal.import_scope import new_file
            # File owns filesystem creation and its native rollback callback.
            # file_manager.save_file writes bytes before creating that document
            # and does not register equivalent cleanup on this native version.
            with new_file(policy.get_current_user(),target):
                file=frappe.get_doc(dict(doctype='File',file_name=filename,content=raw,is_private=1,
                    attached_to_doctype=target[0],attached_to_name=target[1])).insert(ignore_permissions=True)
            manifest.update(actor=policy.get_current_user(),file_id=file.name,file_hash=payload['file_hash'],source_operation=operation)
            if log:
                log.source_file=file.file_url;log.source_file_name=filename;log.source_file_hash=payload['file_hash']
                _native()._apply_summary(log,{**parsed.preview_summary(),**summary},'Previewed')
                log.save(ignore_permissions=True)
                manifest.update(log_name=log.name,log_hash=_log_hash(log.name))
            manifest['summary']=summary
            event=audit.append_event(request_id,operation,'Employee',subject,payload,after=manifest)
            return dict(manifest,event_name=event.name)
    return _call(run)


@frappe.whitelist(methods=['POST'])
def execute_import(event_name, expected_inputs, request_id, **kwargs):
    def run():
        guards.require_post();role_scope.check_fields({'event_name','expected_inputs','request_id'})
        with serialize('attendance-import','company'):
            manifest=_preview(event_name)
            operation={'schedule':'attendance.schedule.import','monthly':'attendance.import.monthly','attendance':'attendance.import.execute'}[manifest['mode']]
            _bound(operation)
            file,raw=_source(manifest)
            with _parsed(raw,file.file_name,manifest['kind']) as parsed:
                current,mapping,resolved,summary=_plan(parsed,manifest['kind'])
                subject=current['employee_names'][0]
                payload=dict(event_name=event_name,expected_inputs=expected_inputs)
                replay=audit.replay(request_id,operation,'Employee',subject,payload)
                if replay is not None:return dict(replay,replayed=True)
                if current['company']!=manifest['company'] or current['employee_names']!=manifest['employee_names'] or current['expected_inputs']!=expected_inputs or manifest['expected_inputs']!=expected_inputs:
                    frappe.local.response['http_status_code']=409
                    frappe.throw('员工、排班或导入源数据已变化，请重新预览。',frappe.ValidationError)
                if manifest['kind']=='schedule':
                    from hb_attendance_app.hbos_attendance.page.hbos_shift_management.shift_management_data import _apply_resolved_schedules
                    result=_apply_resolved_schedules(resolved,file.name,len(resolved),commit=False)
                else:
                    if _log_hash(manifest['log_name'])!=manifest['log_hash']:
                        frappe.local.response['http_status_code']=409
                        frappe.throw('导入批次已处理或发生变化，请重新预览。',frappe.ValidationError)
                    log=frappe.get_doc(LOG,manifest['log_name'],for_update=True)
                    log.started_at=now_datetime()
                    if manifest['mode']=='monthly':
                        for record in parsed.records:record['employee']=mapping[record['row']]
                        result=_native()._stage_monthly_summary(parsed,log)
                    else:result=_native()._execute_raw_checkins(parsed,False,0,log,employee_map=mapping)
                    _native()._apply_summary(log,result,'Success')
                    log.finished_at=now_datetime();log.save(ignore_permissions=True)
                after={**manifest,'source_operation':operation,'changed':True,'summary':result}
                if manifest.get('log_name'):after['log_hash']=_log_hash(manifest['log_name'])
                audit.append_event(request_id,operation,'Employee',subject,payload,after=after)
                return after
    return _call(run)
