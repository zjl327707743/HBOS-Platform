"""飞书「调休」表 → HBOS Rest Leave Record。

与请假同步（api.sync_from_bitable）同模板：取 token → 分页拉全量 → 状态映射
→ 以 feishu_approval_id 为唯一键 upsert。另有取舍不同：
  * 日期区间按天展开后由判定侧处理，本文件只落 start/end 原始区间；
  * 失败记 Error Log 并写进返回摘要，**不在调度任务里 throw**；
  * 匹配不到员工的记录计入 unmatched，不再静默丢弃；
  * 单条记录的任何异常都被就地兜住，不会中断整批、也不会丢摘要。
加班日的解析与核实分别见 parse_pending_rest_leaves / verify_pending_rest_leaves。
"""
import time as _time

import frappe

from hb_attendance_app.hbos_attendance.ai_review import call_llm, env_config
from hb_attendance_app.hbos_attendance.api import (
    STATUS_MAP, _fetch_all_records_custom, _get_token,
)
from hb_attendance_app.hbos_attendance.rest_leave import (
    ID_PREFIX, PARSE_PENDING, REST_LEAVE_APP_TOKEN, REST_LEAVE_TABLE_ID,
    VERIFY_OK, VERIFY_PARSE_FAIL, VERIFY_PENDING,
    build_overtime_prompt, parse_overtime_dates, rest_leave_fields,
    verify_status_for,
)

DOCTYPE = "HBOS Rest Leave Record"


def _require_hr_write():
    roles = set(frappe.get_roles())
    if not roles.intersection({"HR Manager", "System Manager"}):
        frappe.throw("你无权触发调休外部同步。", frappe.PermissionError)

# 单批解析的时间预算（秒）。ai_review.AI_BATCH_SECONDS=100 是为「单次 HTTP 请求
# 须在代理 120s 内返回」而设；本函数跑在 30 分钟一次的调度任务里，没有代理超时，
# 但必须给同一调度周期内的其他任务留出余地（Frappe 调度串行执行）。取 1200s
# 即周期的 2/3，余下 10 分钟给其他任务。串行逐条调用若每条 ≤60s，最坏仍是
# limit×60s，故必须有此硬预算：超预算立即停手，剩余记录留待下次运行。
# 注意：预算是「是否再发起一次调用」的截止线，**已在途的那次调用不受它约束**，
# 所以最坏占用是 PARSE_BATCH_SECONDS + 单次调用耗时（≤ timeout，默认 60s），
# 而不是恰好 PARSE_BATCH_SECONDS。
PARSE_BATCH_SECONDS = 1200

# 年份提示缺失时的兜底年份。仅用于「8月2号」这类省略年份的写法；说明文本里
# 自带年份的写法优先，不受此值影响。取错只会让该条落到「核实不通过 → 人工」，
# 不会产生假通过（见 rest_leave.parse_overtime_dates）。
DEFAULT_HINT_YEAR = "2026"


def _match_employee(num, name):
    """工号优先匹配，其次姓名；都匹配不到返回 None。"""
    if num:
        emp = frappe.db.get_value("Employee", {"employee_number": num}, "name")
        if emp:
            return emp
    if name:
        return frappe.db.get_value("Employee", {"employee_name": name}, "name")
    return None


@frappe.whitelist()
def sync_rest_leave_from_bitable():
    """同步飞书调休表。任何失败都记日志并返回摘要，不抛异常。

    摘要键集合在所有返回路径上完全一致（含拉表失败的提前返回），
    调用方可以无条件读取任何一个键。键含义：
      total/created/updated 总数与新增、更新数
      skipped 脏行：飞书行缺 id，或缺人员、缺开始日期等映射不出字段
      unmatched 映射出了字段但匹配不到 Employee（不静默丢弃）
      failed 落库失败（save/commit 抛异常）
      error 拉表阶段的失败原因，非空即表示本次未处理任何记录
    """
    _require_hr_write()
    summary = {"total": 0, "created": 0, "updated": 0,
               "skipped": 0, "unmatched": 0, "failed": 0, "error": ""}
    try:
        token = _get_token()
        records = _fetch_all_records_custom(
            token, REST_LEAVE_APP_TOKEN, REST_LEAVE_TABLE_ID)
    except Exception as e:
        # 摘要先行：error 是调度器区分「跑了没做事」与「崩了」的唯一依据，
        # 必须在 return 之前就位。真正保证它不被日志异常挡住的是下面的裸防护层
        # ——log_error 自身会抛（理由见本文件首处说明），异常若在这里冒出，
        # 调用方拿到的是抛错而不是带 error 的摘要。
        summary["error"] = str(e)
        try:
            frappe.log_error(str(e), "飞书调休同步")
        except Exception:
            # 静默：日志失败不能让异常冒出，否则 error 摘要有值也回不去。
            pass
        return summary

    summary["total"] = len(records)
    for record in records:
        # 单条记录的处理整体兜底：员工匹配、exists、get_doc、update、save
        # 任一抛异常都不得冒泡出函数——否则整批中止、摘要丢失、调度链被打断。
        try:
            fields = record.get("fields", {}) or {}
            rid = record.get("id", "")
            if not rid:
                summary["skipped"] += 1
                continue
            mapped = rest_leave_fields(fields)
            if not mapped:
                summary["skipped"] += 1
                continue
            emp = _match_employee(mapped["employee_number"], mapped["employee_name"])
            if not emp:
                # 不静默丢弃：匹配不到必须可见，否则调休会无声消失
                # 计数先加、且在防护层之外无条件执行：日志写不成也不改本条归属
                # ——否则异常冒到外层 handler，同一条会再记一次 failed，
                # 一条记录同时落进 unmatched 与 failed（与核实段 skipped 同形）。
                summary["unmatched"] += 1
                try:
                    frappe.log_error(
                        "调休记录匹配不到员工: %s / %s"
                        % (mapped["employee_number"], mapped["employee_name"]),
                        "飞书调休同步")
                except Exception:
                    # 静默：本条已计入 unmatched，日志丢了不影响本条归属。
                    pass
                continue

            aid = ID_PREFIX + rid
            exists = frappe.db.exists(DOCTYPE, {"feishu_approval_id": aid})
            doc = (frappe.get_doc(DOCTYPE, {"feishu_approval_id": aid}) if exists
                   else frappe.get_doc({"doctype": DOCTYPE, "feishu_approval_id": aid}))
            # 必须在校验前暂存旧值：doc.update 会就地覆盖它们，之后再比较
            # 恒为假，「被改过 → 重新解析」将永远不触发（第一阶段踩过此坑）。
            # 同时覆盖 employee：飞书改了工号会换人，只比 remarks 会沿用
            # 原那人的加班证据（接入豁免后即「用甲的加班给乙换休」）。
            old_remarks = doc.remarks if exists else None
            old_employee = doc.employee if exists else None
            doc.update({
                "employee": emp,
                "start_date": mapped["start_date"],
                "end_date": mapped["end_date"],
                "rest_days": mapped["rest_days"],
                "remarks": mapped["remarks"],
                "approval_status": STATUS_MAP.get(fields.get("申请状态", ""), "审批中"),
                "feishu_sync_time": frappe.utils.now_datetime(),
            })
            if not exists:
                # 新记录等待 LLM 解析加班日
                doc.verify_status = PARSE_PENDING
            elif old_remarks != mapped["remarks"] or old_employee != emp:
                # 说明或员工被改过 → 加班日需重新解析
                doc.verify_status = PARSE_PENDING
            doc.save(ignore_permissions=True)
            frappe.db.commit()
            if exists:
                summary["updated"] += 1
            else:
                summary["created"] += 1
        except Exception as e:
            # 带上飞书行 id：N 条失败时才分得清是哪条。
            # 标题取中立说法——这个 try 覆盖匹配/解析/get_doc/save，
            # 写成「写入失败」会掩盖真实的失败阶段。
            # record 未必是 mapping（上游可能给畸形行），取值前先做类型守卫：
            # 在 except 里二次抛错会直接冒泡出函数，等于毁掉逐条兜底本身。
            rid = record.get("id") if isinstance(record, dict) else ""
            # 日志调用本身再裹一层：写 Error Log 也会失败，且它内部没有兜底。
            # 见 frappe/utils/error.py：log_error 是 get_doc(Error Log) +
            # insert(ignore_permissions=True)。最可能的失败场景恰恰是数据库
            # 故障——那条 INSERT 走同一条坏连接，会再抛一次。异常若从这里冒
            # 出去，上面这层逐条兜底就白写了：本批计数、摘要、调度链全丢，
            # 正是兜底注释声称要防的事。日志丢了不影响计数（已计入 failed），
            # 故静默吞掉。
            # 注意形状（勿改）：防护层刻意写成不带 as e 的裸形式。测试的定位
            # 助手 _nested_guard 从这次日志**前向**查找裸 except，并要求最近的
            # 那个 except 就是本处这一条——若本处改成带 as e 的形式，前向查找会
            # 一路跳到文件后面某个无关的裸 except 上，把别人的防护体当成本处的
            # （强化后的助手则直接判定本处没有防护）。两种情形测试都会失败。
            # 更一般地：本文件的注释与字符串里不得出现结构锚点原文，且生产代码
            # 的**形状**被 tests/ 的字符串检索式断言约束（见 test_rest_leave_parse
            # / test_rest_leave_verify 里的 _nested_guard、_except_block）；
            # 改动此处的措辞、缩进或语句顺序前，先读那些助手。
            try:
                frappe.log_error(
                    "%s: %s" % (rid, e), "飞书调休单条处理失败")
            except Exception:
                # 写 Error Log 失败（多半是 DB 故障）：不能让日志异常外泄，
                # 否则上面那层逐条兜底等于没兜。日志丢掉不影响计数——本条的
                # 计数在防护层之外无条件执行，不依赖日志是否写成。
                pass
            summary["failed"] += 1

    return summary


def parse_pending_rest_leaves(limit=200):
    """对 verify_status=待解析 的记录调 LLM 提取加班日并落库。

    仅在同步之后调用。判定每 10 分钟重算一次，**绝不能在判定路径调用 LLM**：
    成本与延迟不可接受，且同样输入未必同样输出，判定必须基于稳定的落库结论。

    每批有 PARSE_BATCH_SECONDS 的时间预算：超预算即停止发起新调用，剩余记录
    留在待解析（下一次运行继续），不计入 failed——「没轮到」不是失败。

    摘要键集合在所有返回路径上完全一致，调用方可以无条件读取任何一个键：
      parsed 本轮成功解析出加班日、状态转「待核实」的条数
      failed 本轮失败条数（LLM 调用失败 / 解析不出日期 / 落库失败）
      remaining 本轮结束后仍处于待解析的条数（积压可见）
      error 配置阶段的失败原因，非空即表示本轮未处理任何记录
    """
    summary = {"parsed": 0, "failed": 0, "remaining": 0, "error": ""}
    try:
        cfg = env_config()
    except Exception as e:
        # 摘要先行（理由同 sync_rest_leave_from_bitable 的拉表失败分支）：
        # error 必须在 return 之前就位；兜住「日志抛不得外泄」的是裸防护层。
        summary["error"] = str(e)
        try:
            frappe.log_error(str(e), "调休加班日解析")
        except Exception:
            # 静默：日志失败不能让异常冒出，否则 error 摘要有值也回不去。
            pass
        return summary
    if not (cfg["base_url"] and cfg["api_key"] and cfg["model"]):
        summary["error"] = "未配置 AI（HBOS_AI_BASE_URL / HBOS_AI_API_KEY / HBOS_AI_MODEL）"
        return summary

    # 取待解析列表本身也会抛（DB 故障 / 权限 / 连接断），先前只想过 get_doc 会抛，
    # 漏了这里。它与核实段 verify_pending_rest_leaves 的取待核列表同形兜住：
    # 读不到列表就没有任何可处理的对象，error 先行、日志再裹一层、原样返回摘要。
    try:
        pending = frappe.db.get_all(
            DOCTYPE,
            filters={"verify_status": PARSE_PENDING},
            fields=["name", "employee_name", "employee_number", "remarks", "start_date"],
            limit_page_length=limit,
            order_by="creation asc",
        )
    except Exception as e:
        summary["error"] = str(e)
        try:
            frappe.log_error(str(e), "调休加班日取待解析列表失败")
        except Exception:
            # 静默：日志失败不能让异常冒出，否则 error 摘要有值也回不去。
            pass
        return summary
    batch_deadline = _time.monotonic() + PARSE_BATCH_SECONDS
    for row in pending:
        # 时间预算：超预算停止发起新调用，剩余记录保持待解析，下次运行继续。
        # 不计入 failed——它们是「还没轮到」，与调用失败/解析失败不是一回事。
        if _time.monotonic() > batch_deadline:
            break

        # 逐条处理整体兜底。取年份、拼说明、读 DocType 都在这里，而读 DocType
        # 是会抛的——比如这条记录在 get_all 之后被删掉。异常一旦冒出函数，
        # 本批已落库的计数与本轮积压数全部丢失，还会打断调度链
        # （与 Task 3 是同一种失效模式，故形状保持一致）。
        try:
            year = str(row.start_date or "")[:4] or DEFAULT_HINT_YEAR
            prompt = build_overtime_prompt(
                row.employee_name or "", row.employee_number or "",
                row.remarks or "", year)
            try:
                text = call_llm(cfg, prompt)
            except Exception as e:
                # 调用失败不写 parsed_at、不改状态：下次同步/解析可重试
                # （与「解析不出日期 → 转人工、不重试」区分开）
                # 日志调用再裹一层：log_error 自身会抛（理由见本文件首处说明），
                # 异常若从这里冒出，逐条兜底失效、本批计数与调度链一起丢。
                try:
                    frappe.log_error(
                        "%s: %s" % (row.name, e), "调休加班日 LLM 调用失败")
                except Exception:
                    # 日志失败静默吞掉：调用失败的事实已计入 failed。
                    pass
                summary["failed"] += 1
                continue

            dates = parse_overtime_dates(text, year)
            doc = frappe.get_doc(DOCTYPE, row.name)
            doc.parsed_at = frappe.utils.now_datetime()
            doc.overtime_dates = ",".join(dates)
            # 解析不出日期 → 解析失败，转人工；不豁免、不重试
            doc.verify_status = VERIFY_PENDING if dates else VERIFY_PARSE_FAIL
            try:
                doc.save(ignore_permissions=True)
                frappe.db.commit()
                summary["parsed" if dates else "failed"] += 1
            except Exception as e:
                # 日志再裹一层（理由见本文件首处说明）：log_error 内部没有兜底，
                # 写 Error Log 失败会二次抛出，把逐条兜底和摘要一起带走。
                try:
                    frappe.log_error(
                        "%s: %s" % (row.name, e), "调休加班日写入失败")
                except Exception:
                    # 静默：写入失败的事实已计入 failed，日志丢了不影响计数。
                    pass
                summary["failed"] += 1
        except Exception as e:
            # 日志再裹一层（理由见本文件首处说明）：log_error 内部没有兜底，
            # 写 Error Log 失败会二次抛出，把逐条兜底和摘要一起带走。
            try:
                frappe.log_error(
                    "%s: %s" % (row.name, e), "调休加班日单条处理失败")
            except Exception:
                # 静默：本条已计入 failed，日志丢了不影响计数。
                pass
            summary["failed"] += 1
            continue

    # 积压统计同样会抛（DB 故障 / 权限 / 连接断），先前只兜了逐条处理，
    # 漏了收尾这一步。核实段 verify_pending_rest_leaves 对同名调用同形兜住：
    # 此处**不提前返回**——循环已跑完、本批计数已就绪，统计失败只影响
    # remaining 这一个键，不能连已落库的结论一起丢（与核实段收尾一致）。
    try:
        summary["remaining"] = frappe.db.count(
            DOCTYPE, {"verify_status": PARSE_PENDING})
    except Exception as e:
        summary["error"] = str(e)
        try:
            frappe.log_error(str(e), "调休加班日解析积压统计失败")
        except Exception:
            # 静默：日志失败不能让异常冒出，否则本批计数随函数一起丢。
            pass
    return summary


def _present_dates(employee, dates):
    """该员工在这些日期里，哪些天有完整上下班配对。

    判据复用系统**已经算好并落库**的配对结果，不在这里另写一套「什么算配对」：
    pairing.py 只对真正配对成功的班次写 working_hours（非豁免的 Present 必带
    真实配对间隔），所以「status='Present' 且 working_hours >= 2」就是在读它
    的结论。两处判据同源，才不会各自漂移。

    参数化：员工走 %s 占位符；日期的占位符**个数**由日期条数决定，值仍走绑定
    参数——不把日期字符串拼进 SQL（拼串既怕引号，也会让缓存失效）。空 dates
    在入口就短路，故占位符串恒非空，不会出现 `IN ()` 这种语法错。
    """
    if not dates or not employee:
        return set()
    placeholders = ",".join(["%s"] * len(dates))
    rows = frappe.db.sql(
        """
        SELECT attendance_date FROM `tabAttendance`
        WHERE employee = %s
          AND attendance_date IN ({ph})
          AND status = 'Present'
          AND working_hours >= 2
        """.format(ph=placeholders),
        tuple([employee] + list(dates)),
        as_dict=True,
    )
    return {str(r["attendance_date"]) for r in rows}


def verify_pending_rest_leaves(limit=500):
    """对 verify_status=待核实 的记录核实加班日，回写结论。

    **本阶段只写结论**：不开豁免、不重算考勤、不打断调度（不 throw）。豁免接入
    是下一阶段的事。核实判据见 _present_dates——加班日当天该员工在系统已生成的
    考勤里有完整配对，才算这一天真的发生过。

    摘要键集合在所有返回路径上完全一致，调用方可以无条件读取任何一个键：
      verified 本轮核实通过、状态转「已核实」的条数
      failed 本轮核实不通过、或处理失败的条数
      skipped 没法核的条数（缺员工 / 缺加班日），保持待核实留人工看
      remaining 本轮结束后仍处于待核实的条数（积压可见）
      error 起始阶段（读待核列表 / 统计积压）的失败原因，非空即表示本轮有异常
    """
    summary = {"verified": 0, "failed": 0, "skipped": 0,
               "remaining": 0, "error": ""}
    try:
        pending = frappe.db.get_all(
            DOCTYPE,
            filters={"verify_status": VERIFY_PENDING},
            fields=["name", "employee", "overtime_dates"],
            limit_page_length=limit,
            order_by="creation asc",
        )
    except Exception as e:
        # 顺序不变（断言切片依赖它），但先前注释里「先落摘要就不怕日志抛」的
        # 理由是错的：日志若抛，异常在 return 之前就冒出去，两种顺序下调用方
        # 都拿不到摘要。真正兜住这一点的是下面的裸防护层。
        summary["error"] = str(e)
        try:
            frappe.log_error(str(e), "调休加班核实取待核列表失败")
        except Exception:
            # 静默：日志失败不能让异常冒出，否则 error 摘要有值也回不去。
            pass
        return summary

    # 逐条处理整体兜底：切日期、查考勤、get_doc、写状态、save 全在同一个 try
    # 之内。读 DocType 是会抛的（比如这条记录在 get_all 之后被删掉），异常一旦
    # 冒出函数，本批已落库的计数与本轮积压数全部丢失，还会打断调度链
    # （与 Task 3/Task 4 是同一种失效模式，故形状保持一致）。
    for row in pending:
        try:
            dates = [
                d.strip() for d in str(row.overtime_dates or "").split(",")
                if d.strip()
            ]
            if not dates:
                # 没有加班日 = 没法核，不等于核实不通过；保持待核实留人工
                summary["skipped"] += 1
                # 计数已在上一行加过；日志再抛也不会把本条改记成 failed。
                try:
                    frappe.log_error(
                        "%s: 无加班日，无法核实" % row.name,
                        "调休加班核实缺加班日")
                except Exception:
                    # 静默：本条已计入 skipped，日志丢了不影响本条归属。
                    pass
                continue
            if not row.employee:
                # 缺员工 = 「压根没核」而不是「核了，没通过」。状态字段没有
                # 「无法核实」这一档，写「核实不通过」等于断言一个我们从未做过
                # 的判断；此路保持待核实（仍在待核队列里可见）并单独留痕，
                # 绝不产生假「已核实」。
                summary["skipped"] += 1
                # 同上：计数先加、日志后写，日志抛也不会把本条改记成 failed。
                try:
                    frappe.log_error(
                        "%s: 记录缺员工，无法核实" % row.name,
                        "调休加班核实缺员工")
                except Exception:
                    # 静默：本条已计入 skipped，日志丢了不影响本条归属。
                    pass
                continue

            paired = _present_dates(row.employee, dates)
            doc = frappe.get_doc(DOCTYPE, row.name)
            doc.verify_status = verify_status_for(dates, paired)
            doc.verify_time = frappe.utils.now_datetime()
            try:
                doc.save(ignore_permissions=True)
                frappe.db.commit()
                if doc.verify_status == VERIFY_OK:
                    summary["verified"] += 1
                else:
                    # 负面结论光有「核实不通过」不够：人工拿到的只是 claim 的
                    # 加班日，还得自己重算哪一天缺配对。写清缺的是哪几天，
                    # 人工才查得下去。
                    # 绝不写 remarks：那里存着飞书原说明，Task 4 的重新解析
                    # 靠比较它来发现说明被改过，覆写会静默毁掉重新解析。
                    missing = [d for d in dates if d not in paired]
                    summary["failed"] += 1
                    try:
                        frappe.log_error(
                            "%s: 缺配对的加班日 %s"
                            % (row.name, ",".join(missing)),
                            "调休加班核实缺少配对")
                    except Exception:
                        # 静默：结论已落库、计数已加，不能让日志异常外泄。
                        pass
            except Exception as e:
                # 日志再裹一层（理由见本文件首处说明）：log_error 内部没有兜底。
                try:
                    frappe.log_error(
                        "%s: %s" % (row.name, e), "调休加班核实写入失败")
                except Exception:
                    # 静默：本条已计入 failed，日志丢了不影响计数。
                    pass
                summary["failed"] += 1
        except Exception as e:
            # 带上记录名：N 条失败时才分得清是哪条。标题取中立说法——这个 try
            # 覆盖切日期到 save 的整条处理，写成「写入失败」会掩盖真实失败阶段。
            # 日志再裹一层（理由见本文件首处说明）：log_error 内部没有兜底，
            # 写 Error Log 失败会二次抛出，把逐条兜底和摘要一起带走。
            try:
                frappe.log_error(
                    "%s: %s" % (row.name, e), "调休加班核实单条处理失败")
            except Exception:
                # 静默：本条已计入 failed，日志丢了不影响计数。
                pass
            summary["failed"] += 1
            continue

    try:
        summary["remaining"] = frappe.db.count(
            DOCTYPE, {"verify_status": VERIFY_PENDING})
    except Exception as e:
        # 积压统计失败不影响本轮已落库的计数，故不提前返回。顺序不变（断言
        # 切片依赖它），但「先落摘要」并不构成对日志异常的保护——真正的保护
        # 是下面的裸防护层。
        summary["error"] = str(e)
        try:
            frappe.log_error(str(e), "调休加班核实积压统计失败")
        except Exception:
            # 静默：日志失败不能让异常冒出，否则本批计数随函数一起丢。
            pass
    return summary


def sync_rest_leave_pipeline():
    """调休定时任务编排入口：同步 → 解析 → 核实，顺序由业务代码显式保证。"""
    summary = {}
    sync_result = sync_rest_leave_from_bitable()
    summary["sync"] = sync_result
    # 同步阶段无法拉取源数据时，本轮不继续解析/核实，避免把旧积压误当成本轮新结果。
    if sync_result.get("error"):
        return summary

    parse_result = parse_pending_rest_leaves()
    summary["parse"] = parse_result

    verify_result = verify_pending_rest_leaves()
    summary["verify"] = verify_result
    return summary
