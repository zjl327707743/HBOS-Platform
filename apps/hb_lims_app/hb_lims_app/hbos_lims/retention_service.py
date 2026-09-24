# -*- coding: utf-8 -*-
"""M2-R7A 留样业务服务（Frappe 层）：登记入库 + 从检验样品创建 + 库存写路径。

约定（与 lims_service.py 一致）：
- 公开方法为 @frappe.whitelist 模块级函数，入口先校验角色。
- 显式事务管理（commit / rollback）。
- 库存 current_qty / reserved_qty 单一写路径（方案 7.4）：
  登记入库 / （R7C 交付：confirm_stock / execute_usage / execute_disposal /
  transfer_out / adjust_stock / 驳回释放）。
"""

import frappe

from hb_lims_app.hbos_lims import retention_contract as rtc
from hb_lims_app.hbos_lims import workflow_contract as wf


def _user():
	return frappe.session.user


def _now():
	return frappe.utils.now_datetime()


def _commit():
	frappe.db.commit()
	try:
		from hb_lims_app.hbos_lims.todo_service import invalidate_my_todo_summary_cache
		invalidate_my_todo_summary_cache()
	except Exception as exc:
		if hasattr(frappe, "log_error"):
			frappe.log_error(str(exc), "HBOS 我的待办摘要缓存失效失败")


def _rollback():
	frappe.db.rollback()


def _check_action(action):
	roles = frappe.get_roles(_user())
	if not any(wf.action_allowed(action, role) for role in roles):
		frappe.throw(f"当前用户（{_user()}）没有执行「{action}」的权限。")


# ---------------------------------------------------------------------------
# 登记（记录一电子化）
# ---------------------------------------------------------------------------

@frappe.whitelist()
def register_retention(retention_product=None, batch_no=None, retention_date=None,
					   retention_qty=None, package_count=None, package_spec=None,
					   source=None, expiry_type=None, expiry_date=None,
					   retention_due_date=None, storage_location=None,
					   observed_flag=0, container_no=1, source_sample=None,
					   obs_year=None, obs_selected_by=None, obs_selected_date=None,
					   obs_selected_reason=None, remarks=None, auto_calc=None):
	"""留样登记（Analyst/Manager）。

	- 液体物料硬拦截；受托产品直接以已转出落位（不经在库）。
	- 留样量：auto_calc=1 且 UOM 一致性闸通过时按 2 倍计算；否则用传入值。
	- 留样期至：未传时自动 = expiry_date + 3 年。
	- 在库登记：current_qty 初始化 + 入库流水；受托登记：0 量 + 审计事件。
	"""
	_check_action("register_retention")
	try:
		product = frappe.get_doc("HBOS Retention Product", retention_product)
		if product.is_liquid:
			frappe.throw("液体物料不留样（规程 4.1），该产品已标记为液体物料。")
		if not product.is_active:
			frappe.throw("该留样产品已停用，不再登记新留样。")

		# 留样量（2 倍自动计算 + UOM 一致性闸）
		qty = retention_qty
		if auto_calc:
			qty, err = rtc.calc_retention_qty(
				product.retention_qty_rule, product.full_test_qty,
				product.full_test_qty_uom, product.default_uom)
			if err:
				frappe.throw(err)
		if qty is None:
			frappe.throw("请填写留样量（未自动计算：产品规则非 2 倍、全检量未维护或 UOM 不一致）。")
		if float(qty) <= 0:
			frappe.throw("留样量必须大于 0。")

		is_outsource = bool(product.is_outsource)

		# 外售产品每批观察（规程 4.3.1）：自动补观察字段（DocType validate 兜底 reason）
		if product.category == "外售产品" and product.obs_rule == "每批观察（外售产品）":
			observed_flag = 1
			obs_selected_reason = obs_selected_reason or "外售产品每批"
			obs_year = obs_year or frappe.utils.getdate(retention_date).year

		doc = frappe.get_doc({
			"doctype": "HBOS Retention Sample",
			"retention_product": retention_product,
			"batch_no": batch_no,
			"container_no": container_no or 1,
			"source": source,
			"retention_date": retention_date,
			"expiry_type": expiry_type,
			"expiry_date": expiry_date,
			"retention_due_date": retention_due_date,
			"retention_qty": qty,
			"package_count": package_count,
			"package_spec": package_spec,
			"storage_location": storage_location,
			"observed_flag": observed_flag,
			"obs_year": obs_year,
			"obs_selected_by": obs_selected_by or _user(),
			"obs_selected_date": obs_selected_date or frappe.utils.today(),
			"obs_selected_reason": obs_selected_reason,
			"source_sample": source_sample,
			"retained_by": _user(),
			"remarks": remarks,
			"status": "已转出" if is_outsource else "在库",
			"current_qty": 0 if is_outsource else qty,
			"reserved_qty": 0,
		})
		# 全检量 < 1g 提示（非硬拦截）
		note = rtc.min_qty_note(product.full_test_qty, product.full_test_qty_uom)
		doc.insert(ignore_permissions=True)
		# 注意：insert 提交后 current_qty 由 on_insert 钩子在内存置值，
		# 这里统一走 _write_stock_log（append 流水 + save 落库 current_qty 与流水）。

		if not is_outsource:
			_write_stock_log(doc, "入库（登记）", qty, "HBOS Retention Sample", doc.name)
			_audit("登记入库", doc.name, new_value="qty={}".format(qty))
		else:
			# 受托转出落位（rev6）：不经在库，0 量审计事件
			_audit("受托转出", doc.name,
				   action_text="受托产品登记直接以已转出状态创建（不经在库）",
				   new_value="qty=0")
		_commit()

		message = note or None
		return {"name": doc.name, "qty": qty, "note": message,
				"status": doc.status}
	except Exception:
		_rollback()
		raise


@frappe.whitelist()
def create_retention_from_sample(sample_name, retention_qty=None, container_no=1,
								 storage_location=None, remarks=None):
	"""从检验完成批次（HBOS Sample）一键创建留样（方案第九节映射 6 规则）。"""
	_check_action("register_retention")
	try:
		sample = frappe.get_doc("HBOS Sample", sample_name)
		product_exists = bool(frappe.db.exists(
			"HBOS Retention Product", {"product_code": sample.material_code}))
		ok, err = rtc.check_sample_source_mapping(
			sample.sample_type, sample.status, sample.sample_source,
			sample.material_code, product_exists)
		if not ok:
			frappe.throw(err)

		# 产品匹配（规则 4：不自动创建）
		product = frappe.get_doc("HBOS Retention Product",
								 {"product_code": sample.material_code})
		qty = retention_qty
		if qty is None and product.retention_qty_rule == "全检量 2 倍":
			qty, err = rtc.calc_retention_qty(
				product.retention_qty_rule, product.full_test_qty,
				product.full_test_qty_uom, product.default_uom)
			if err:
				frappe.throw(err)

		return register_retention(
			retention_product=product.name,
			batch_no=sample.batch_no,
			retention_date=frappe.utils.today(),
			retention_qty=qty,
			source="检验样品 {}".format(sample_name),
			expiry_type="有效期至",
			expiry_date=None,  # 检验样品不携带效期，留样期至人工补
			storage_location=storage_location,
			container_no=container_no,
			source_sample=sample_name,
			remarks=remarks or "从检验样品 {} 创建".format(sample_name),
		)
	except Exception:
		_rollback()
		raise


# ---------------------------------------------------------------------------
# 手动调整（R7A 交付；预占相关用例在 R7C）
# ---------------------------------------------------------------------------

@frappe.whitelist()
def adjust_stock(retention_name, new_current_qty, reason):
	"""手动调整结存（仅 Manager，原因必填，审计留痕）。

	R7A 边界：reserved_qty 恒为 0，校验 current_qty >= 0；
	R7C 后同方法校验 current_qty >= reserved_qty（retention_contract.check_adjust_stock 已含）。
	"""
	_check_action("adjust_stock")
	if not reason:
		frappe.throw("手动调整必须填写原因。")
	try:
		# 四步锁协议（方案 7.2）
		row = _lock_row(retention_name)
		ok, err = rtc.check_adjust_stock(row.current_qty, row.reserved_qty, new_current_qty)
		if not ok:
			frappe.throw(err)

		doc = frappe.get_doc("HBOS Retention Sample", retention_name)
		doc.flags.setdefault('allow_system_fields', True)
		delta = (new_current_qty or 0) - (row.current_qty or 0)
		doc.current_qty = new_current_qty
		doc.save(ignore_permissions=True)
		_write_stock_log(doc, "手动调整", delta, "", None)
		_audit("手动调整", retention_name, reason=reason,
			   old_value="current_qty={}".format(row.current_qty),
			   new_value="current_qty={}".format(new_current_qty))
		_commit()
		return {"name": retention_name, "current_qty": new_current_qty}
	except Exception:
		_rollback()
		raise


# ---------------------------------------------------------------------------
# R7B 观察管理（方案 5.3/5.4/6.3 + P3-3/P3-4）
# ---------------------------------------------------------------------------

OBS_REASON_ANNUAL = "年度观察批（每年 3 批）"
OBS_REASON_SALE = "外售产品每批"
OBS_REASON_OTHER = "其他"
OBS_ANNUAL_CAP = 3


def _user_has_any(roles_required):
	roles = frappe.get_roles(_user())
	return any(r in roles for r in roles_required)


@frappe.whitelist()
def select_obs_batch(retention_name, obs_year, obs_selected_reason, obs_selected_by=None):
	"""观察批选取（Reviewer/Manager）：设置留样主表观察字段；年度观察批受 N/3 上限
	（产品行 FOR UPDATE 锁内计数，rev4）；「其他」原因仅 Manager 可选（P3-3）。"""
	_check_action("select_obs_batch")
	if obs_selected_reason not in (OBS_REASON_ANNUAL, OBS_REASON_SALE, OBS_REASON_OTHER):
		frappe.throw("不支持的观察批选取原因。")
	if not obs_year:
		frappe.throw("请填写观察年度。")
	try:
		doc = frappe.get_doc("HBOS Retention Sample", retention_name)
		doc.flags.setdefault('allow_system_fields', True)
		if doc.observed_flag:
			frappe.throw("该留样已是观察样品，如需更换请先取消选取（保留选取历史后重选）。")
		product = frappe.get_doc("HBOS Retention Product", doc.retention_product)
		if product.obs_rule == "不观察":
			frappe.throw("该产品观察规则为「不观察」，不能纳入观察计划。")
		if obs_selected_reason == OBS_REASON_ANNUAL and product.obs_rule != "每年选 3 批（原料药成品）":
			frappe.throw("「年度观察批」仅适用于观察规则为「每年选 3 批」的产品。")
		if obs_selected_reason == OBS_REASON_SALE and product.obs_rule != "每批观察（外售产品）":
			frappe.throw("「外售产品每批」仅适用于每批观察的外售产品。")
		if obs_selected_reason == OBS_REASON_OTHER and not _user_has_any(
				[wf.ROLE_MANAGER, wf.ROLE_SYSTEM]):
			_audit_commit("HBOS Retention Sample", "越权拦截", retention_name,
						 action_text="尝试以「其他」原因选取观察批绕过 N/3 上限")
			frappe.throw("「其他」原因选取观察批仅 LIMS Manager 可操作（防绕过年度 3 批上限）。")

		# 年度观察批：产品行 FOR UPDATE 锁内计数（防并发第 4 批同时通过）
		if obs_selected_reason == OBS_REASON_ANNUAL:
			_locked = frappe.db.sql(
				"SELECT name FROM `tabHBOS Retention Product` WHERE name=%s FOR UPDATE",
				doc.retention_product)
			if not _locked:
				frappe.throw("留样产品不存在。")
			cnt = frappe.db.sql(
				"SELECT COUNT(*) FROM `tabHBOS Retention Sample`"
				" WHERE retention_product=%s AND obs_year=%s"
				" AND obs_selected_reason=%s AND observed_flag=1 AND name<>%s",
				(doc.retention_product, int(obs_year), OBS_REASON_ANNUAL, retention_name))[0][0]
			if int(cnt) >= OBS_ANNUAL_CAP:
				frappe.throw("{} 年该产品年度观察批已达上限 {} 批，不能再选取（如需更换先取消原批）。".format(
					obs_year, OBS_ANNUAL_CAP))

		doc.observed_flag = 1
		doc.obs_year = int(obs_year)
		doc.obs_selected_by = obs_selected_by or _user()
		doc.obs_selected_date = frappe.utils.today()
		doc.obs_selected_reason = obs_selected_reason
		# 0 月基线：next_obs 由观察回写维护；首次选取置待观察 0 月
		doc.next_obs_month = 0
		doc.next_obs_due_date = _add_months(doc.retention_date, 0)
		doc.save(ignore_permissions=True)
		_commit()
		return {"name": retention_name, "obs_year": doc.obs_year,
				"obs_selected_reason": obs_selected_reason}
	except Exception:
		_rollback()
		raise


@frappe.whitelist()
def cancel_obs_batch(retention_name):
	"""取消观察批选取（Reviewer/Manager）：清空观察字段并留审计（选取历史由审计保留）。"""
	_check_action("cancel_obs_batch")
	try:
		doc = frappe.get_doc("HBOS Retention Sample", retention_name)
		doc.flags.setdefault('allow_system_fields', True)
		if not doc.observed_flag:
			frappe.throw("该留样不在观察计划内，无需取消。")
		# 若已有该观察批观察记录则禁止取消（先删记录或已完成观察不允许回退）
		existing = frappe.db.exists("HBOS Retention Observation",
									{"retention_sample": retention_name})
		if existing:
			frappe.throw("该观察批已产生观察记录，禁止直接取消；请另选批次（历史不可抹除）。")
		_audit("修改", retention_name, action_text="取消观察批选取（清空观察字段）",
			   old_value="obs_year={}".format(doc.obs_year))
		for f in ("obs_year", "obs_selected_by", "obs_selected_date",
				  "obs_selected_reason", "next_obs_month", "next_obs_due_date"):
			doc.set(f, None)
		doc.observed_flag = 0
		doc.save(ignore_permissions=True)
		_commit()
		return {"name": retention_name, "observed_flag": 0}
	except Exception:
		_rollback()
		raise


@frappe.whitelist()
def record_observation(retention_name, obs_month, obs_date=None, appearance=None,
					   result="正常", abnormal_note=None, remarks=None):
	"""观察录入（Analyst/Reviewer/Manager）：建观察记录（sample_period_key 唯一防重复）。"""
	_check_action("record_observation")
	if obs_month is None or int(obs_month) < 0:
		frappe.throw("观察偏移月数不合法。")
	obs_month = int(obs_month)
	try:
		sample = frappe.get_doc("HBOS Retention Sample", retention_name)
		sample.flags.setdefault('allow_system_fields', True)
		if not sample.observed_flag:
			frappe.throw("该留样未入选观察批，不在观察计划内。")
		if sample.status in ("已销毁", "已转出", "已用尽"):
			frappe.throw("该留样已终结（{}），不能再做观察。".format(sample.status))
		if result not in ("正常", "异常"):
			frappe.throw("观察结果须为 正常 / 异常。")
		if result == "异常" and not (abnormal_note or "").strip():
			frappe.throw("观察结果为异常时必须填写异常描述。")

		doc = frappe.get_doc({
			"doctype": "HBOS Retention Observation",
			"retention_sample": retention_name,
			"obs_month": obs_month,
			"obs_date": obs_date or frappe.utils.today(),
			"appearance": appearance,
			"result": result,
			"abnormal_note": abnormal_note,
			"observer": _user(),
			"remarks": remarks,
		})
		try:
			doc.insert(ignore_permissions=True)
		except Exception as e:
			# 业务键（sample_period_key unique）冲突：给中文提示
			if isinstance(e, frappe.DuplicateEntryError) or "Duplicate" in str(e) \
					or "duplicate" in str(e).lower():
				frappe.throw("该留样同观察期（obs_month={}）已有观察记录，不能重复。".format(obs_month))
			raise
		if result == "异常":
			_audit("观察异常", retention_name,
				   action_text="观察结论异常", new_value="obs_month={}".format(obs_month))
		_commit()
		return {"name": doc.name, "obs_month": obs_month, "result": result}
	except Exception:
		_rollback()
		raise


@frappe.whitelist()
def review_observation(observation_name=None, retention_name=None, obs_month=None):
	"""观察审核（Reviewer/QA/Manager）：置审核签名并按全部已审核记录回写 next_obs_month
	（P3-4：next = max(已审核 obs_month) + 12，不用 +=12，超观察期至置计划完成）。

	支持直接按 留样+观察月 定位未审核记录（前端免先取记录名）。
	"""
	_check_action("review_observation")
	try:
		if not observation_name:
			if not (retention_name and obs_month is not None):
				frappe.throw("请提供观察记录或 留样 + 观察月。")
			observation_name = frappe.db.get_value(
				"HBOS Retention Observation",
				{"retention_sample": retention_name, "obs_month": int(obs_month),
				 "reviewed_by": ("is", "not set")}, "name")
			if not observation_name:
				frappe.throw("未找到该留样观察月 {} 的待审核观察记录。".format(obs_month))
		doc = frappe.get_doc("HBOS Retention Observation", observation_name)
		if doc.reviewed_by:
			frappe.throw("该观察记录已审核（{}），不能重复审核。".format(doc.reviewed_by))
		doc.reviewed_by = _user()
		doc.reviewed_date = frappe.utils.today()
		doc.save(ignore_permissions=True)

		sample = frappe.get_doc("HBOS Retention Sample", doc.retention_sample)
		sample.flags.setdefault('allow_system_fields', True)
		_recompute_next_obs(sample)
		sample.save(ignore_permissions=True)
		_audit("观察完成" if doc.result == "正常" else "观察异常",
			   doc.retention_sample,
			   action_text="观察记录 {} 审核通过".format(doc.name),
			   new_value="result={}, obs_month={}".format(doc.result, doc.obs_month))
		_commit()
		return {"name": doc.name, "reviewed_by": doc.reviewed_by,
				"next_obs_month": sample.next_obs_month}
	except Exception:
		_rollback()
		raise


@frappe.whitelist()
def get_observation_plan():
	"""观察计划看板聚合（只读）：应观察/已逾期清单 + 各产品当年已选 N/3 完整性。"""
	_check_action("get_observation_plan")
	samples = frappe.get_all("HBOS Retention Sample",
							 filters={"observed_flag": 1},
							 fields=["name", "sample_name", "batch_no",
									 "retention_product", "retention_date",
									 "retention_due_date", "obs_year",
									 "obs_selected_reason", "next_obs_month",
									 "next_obs_due_date", "status"])
	rows = []
	for s in samples:
		pid = s["retention_product"]
		prod = frappe.get_doc("HBOS Retention Product", pid)
		# 该计划月（next_obs_month）是否已有观察记录及其审核状态
		done_name = frappe.db.get_value("HBOS Retention Observation", {
			"retention_sample": s["name"], "obs_month": s["next_obs_month"],
			"reviewed_by": ("is", "set")}, "name")
		pending_name = frappe.db.get_value("HBOS Retention Observation", {
			"retention_sample": s["name"], "obs_month": s["next_obs_month"],
			"reviewed_by": ("is", "not set")}, "name")
		row = {
			"name": s["name"],
			"product": prod.product_name,
			"obs_rule": prod.obs_rule,
			"sampleName": s["sample_name"],
			"batch": s["batch_no"],
			"monthOffset": s["next_obs_month"],
			"planDate": s["next_obs_due_date"],
			"selectedReason": s["obs_selected_reason"],
			"obsYear": s["obs_year"],
			"status": s["status"],
			"due": "已完成" if done_name else ("待审核" if pending_name else _obs_due_state(s)),
			"result": frappe.db.get_value("HBOS Retention Observation", done_name, "result") if done_name else None,
			"reviewReady": bool(pending_name),
		}
		rows.append(row)

	agg = {}
	for s in samples:
		pid = s["retention_product"]
		prod = frappe.get_doc("HBOS Retention Product", pid)
		year = s["obs_year"]
		b = agg.setdefault((pid, year), {
			"product": prod.product_name, "rule": prod.obs_rule,
			"annual": 0, "observed": 0, "cap": OBS_ANNUAL_CAP if prod.obs_rule == "每年选 3 批（原料药成品）" else None,
		})
		if s["obs_selected_reason"] == OBS_REASON_ANNUAL:
			b["annual"] += 1
		b["observed"] += 1
	completeness = [{
		"product": b["product"],
		"rule": "年度观察批" if b["rule"] == "每年选 3 批（原料药成品）" else ("每批观察" if b["rule"] == "每批观察（外售产品）" else "不观察"),
		"year": k[1],
		"selected": b["annual"] if b["cap"] else b["observed"],
		"cap": b["cap"],
	} for k, b in agg.items()]
	return {
		"rows": rows,
		"completeness": completeness,
	}


def _obs_due_state(s):
	"""由 next_obs 推导应观察状态（只看待办当前月，不做多期展开）。"""
	due_date = s.get("next_obs_due_date")
	if not due_date:
		return "计划完成"
	today = frappe.utils.getdate(frappe.utils.today())
	if frappe.utils.getdate(due_date) < today:
		return "已逾期"
	return "应观察"


def _recompute_next_obs(sample):
	"""next_obs_month = max(已审核 obs_month) + 12；超过留样期至置计划完成（P3-4）。"""
	reviewed = frappe.get_all("HBOS Retention Observation",
							  filters={"retention_sample": sample.name,
									   "reviewed_by": ("is", "set")},
							  fields=["obs_month"])
	months = [int(r["obs_month"]) for r in reviewed]
	if not months:
		return
	next_month = max(months) + 12
	next_due = _add_months(sample.retention_date, next_month)
	if sample.retention_due_date and frappe.utils.getdate(next_due) > frappe.utils.getdate(sample.retention_due_date):
		sample.next_obs_month = None
		sample.next_obs_due_date = None
		return
	sample.next_obs_month = next_month
	sample.next_obs_due_date = next_due


def _add_months(date_str, months):
	"""dateutil.relativedelta 安全加月（P3-6：月末溢出）。"""
	from dateutil.relativedelta import relativedelta
	base = frappe.utils.getdate(date_str)
	return (base + relativedelta(months=int(months))).strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# R7C 使用申请审批链（方案 6.1 FLOW_USAGE_APPLY / 7.x / 6.4 SoD）
# ---------------------------------------------------------------------------

USE_REASON_OPTIONS = ["用户投诉", "检验结果分析", "生产异常", "上市前研发", "其他"]

# status -> (动作, 签名字段, 下一状态, 上一签名比较字段)
_USAGE_APPROVE_MAP = {
	"待QC批准": ("usage_qc", "qc_approval", "待QA批准", "stock_confirm_by"),
	"待QA批准": ("usage_qa", "qa_approval", "待QM批准", "qc_approval"),
	"待QM批准": ("usage_qm", "qm_approval", "已批准", "qa_approval"),
}


def _audit_on(doctype, log_type, doc_name, action_text="", old_value="", new_value="", reason=""):
	from hb_lims_app.hbos_lims.lims_service import audit_log
	audit_log(log_type, doctype, doc_name, action_text=action_text,
			  old_value=old_value, new_value=new_value, reason=reason, commit=False)


def _audit_commit(doctype, log_type, doc_name, action_text="", old_value="", new_value="", reason=""):
	"""违规尝试（SoD/越权）审计：抛错前事务内记录，不提交当前业务事务；拒绝操作的持久化证据由独立日志/Outbox承担。"""
	from hb_lims_app.hbos_lims.lims_service import audit_log
	audit_log(log_type, doctype, doc_name, action_text=action_text,
			  old_value=old_value, new_value=new_value, reason=reason, commit=False)


def _release_reservation(sample, apply_qty, from_state):
	"""释放预占（rev6 P1）：本单已持有预占才释放（锁已由调用方持有）。"""
	if not rtc.release_requires(from_state):
		return False
	ok, err = rtc.check_release_reservation(sample.reserved_qty, apply_qty, from_state)
	if not ok:
		frappe.throw(err)
	sample.reserved_qty = (sample.reserved_qty or 0) - apply_qty
	return True


@frappe.whitelist()
def create_usage_apply(retention_name, apply_qty, reason_type, reason_detail="", apply_dept=None):
	"""发起使用申请（Analyst/Manager 申请人）：建草稿。"""
	_check_action("create_usage_apply")
	if not apply_qty or float(apply_qty) <= 0:
		frappe.throw("申请量必须大于 0。")
	if reason_type not in USE_REASON_OPTIONS:
		frappe.throw("不支持的触发场景。")
	try:
		sample = frappe.get_doc("HBOS Retention Sample", retention_name)
		sample.flags.setdefault('allow_system_fields', True)
		if sample.status not in ("在库", "部分使用"):
			frappe.throw("留样状态为「{}」，不可申请使用。".format(sample.status))
		if (sample.current_qty or 0) <= 0:
			frappe.throw("该留样结存为 0，无可申请量。")
		doc = frappe.get_doc({
			"doctype": "HBOS Retention Usage Apply",
			"retention_sample": retention_name,
			"apply_qty": float(apply_qty),
			"reason_type": reason_type,
			"reason_detail": reason_detail,
			"apply_dept": apply_dept,
			"applicant": _user(),
			"apply_date": frappe.utils.today(),
			"status": "草稿",
		})
		doc.insert(ignore_permissions=True)
		_commit()
		return {"name": doc.name}
	except Exception:
		_rollback()
		raise


@frappe.whitelist()
def submit_usage_apply(usage_name):
	"""申请人提交草稿 → 待库存确认。"""
	_check_action("create_usage_apply")
	try:
		doc = frappe.get_doc("HBOS Retention Usage Apply", usage_name)
		if doc.status != "草稿":
			frappe.throw("仅草稿状态可提交。")
		doc.status = "待库存确认"
		doc.save(ignore_permissions=True)
		_commit()
		return {"name": doc.name, "status": doc.status}
	except Exception:
		_rollback()
		raise


@frappe.whitelist()
def confirm_stock(usage_name):
	"""库存确认 + 预占（QC/Manager；四步锁协议，锁内复核可用量）。"""
	_check_action("usage_confirm")
	try:
		doc = frappe.get_doc("HBOS Retention Usage Apply", usage_name)
		if doc.status != "待库存确认":
			frappe.throw("当前状态为「{}」，不可库存确认。".format(doc.status))
		row = _lock_row(doc.retention_sample)
		ok, err = rtc.check_confirm_stock(row.current_qty, row.reserved_qty, doc.apply_qty)
		if not ok:
			frappe.throw(err)
		sample = frappe.get_doc("HBOS Retention Sample", doc.retention_sample)
		sample.flags.setdefault('allow_system_fields', True)
		before = (sample.current_qty or 0) - (sample.reserved_qty or 0)
		sample.reserved_qty = (sample.reserved_qty or 0) + doc.apply_qty
		sample.save(ignore_permissions=True)
		doc.stock_qty = before
		doc.stock_confirm_by = _user()
		doc.stock_confirm_date = frappe.utils.today()
		doc.status = "待QC批准"
		doc.save(ignore_permissions=True)
		_audit_on("HBOS Retention Usage Apply", "预占", doc.name,
				  action_text="库存确认即预占", new_value="reserved += {}".format(doc.apply_qty))
		_commit()
		return {"name": doc.name, "status": doc.status, "stock_qty": before}
	except Exception:
		_rollback()
		raise


@frappe.whitelist()
def approve_usage(usage_name):
	"""使用申请逐级批准（QC/QA/QM，按当前状态定位）；含 SoD 硬校验。"""
	try:
		doc = frappe.get_doc("HBOS Retention Usage Apply", usage_name)
		info = _USAGE_APPROVE_MAP.get(doc.status)
		if not info:
			frappe.throw("当前状态「{}」无批准动作。".format(doc.status))
		action, field, nxt, prev_field = info
		_check_action(action)
		prev_signer = doc.get(prev_field) or None
		ok, err = rtc.check_sod_sign(doc.applicant, prev_signer, _user())
		if not ok:
			_audit_commit("HBOS Retention Usage Apply", "SoD 拦截", doc.name,
						 action_text="审批签署 SoD", reason=err)
			frappe.throw(err)
		doc.set(field, _user())
		if nxt == "已批准":
			doc.status = "已批准"
		else:
			doc.status = nxt
		doc.save(ignore_permissions=True)
		_audit_on("HBOS Retention Usage Apply", "审批签署", doc.name,
				  action_text="{}（{}）".format(field, _user()), new_value="status={}".format(doc.status))
		_commit()
		return {"name": doc.name, "status": doc.status}
	except Exception:
		_rollback()
		raise


@frappe.whitelist()
def execute_usage(usage_name):
	"""取样执行 + 原子扣减（Analyst/Manager；四步锁协议）。"""
	_check_action("usage_execute")
	try:
		doc = frappe.get_doc("HBOS Retention Usage Apply", usage_name)
		if doc.status != "已批准":
			frappe.throw("仅「已批准」的使用申请可取样执行。")
		row = _lock_row(doc.retention_sample)
		ok, err = rtc.check_execute_usage(row.current_qty, row.reserved_qty, doc.apply_qty)
		if not ok:
			frappe.throw(err)
		sample = frappe.get_doc("HBOS Retention Sample", doc.retention_sample)
		sample.flags.setdefault('allow_system_fields', True)
		sample.current_qty = (sample.current_qty or 0) - doc.apply_qty
		sample.reserved_qty = (sample.reserved_qty or 0) - doc.apply_qty
		_apply_usage_status(sample)
		sample.save(ignore_permissions=True)
		_write_stock_log(sample, "使用出库", -doc.apply_qty,
						 "HBOS Retention Usage Apply", doc.name)
		doc.status = "已执行"
		doc.executed_by = _user()
		doc.executed_date = frappe.utils.today()
		doc.save(ignore_permissions=True)
		_audit_on("HBOS Retention Usage Apply", "使用出库", doc.name,
				  action_text="取样执行扣减", new_value="-{} {}".format(doc.apply_qty, doc.qty_uom))
		_commit()
		return {"name": doc.name, "status": doc.status, "current_qty": sample.current_qty}
	except Exception:
		_rollback()
		raise


def _apply_usage_status(sample):
	"""出库后留样生命周期状态推导：0→已用尽；<retention_qty→部分使用；否则在库。"""
	cur = sample.current_qty or 0
	if cur <= 0:
		sample.status = rtc.RET_EXHAUSTED
	elif (sample.retention_qty or 0) > 0 and cur < sample.retention_qty:
		sample.status = rtc.RET_PARTIAL_USED
	else:
		sample.status = rtc.RET_IN_STOCK


@frappe.whitelist()
def reject_usage(usage_name, reason):
	"""驳回使用申请（当前审批级角色可驳）：驳回为终态；已持有预占则释放。"""
	try:
		doc = frappe.get_doc("HBOS Retention Usage Apply", usage_name)
		stage_action = _usage_stage_action(doc.status)
		if not stage_action:
			frappe.throw("当前状态不可驳回。")
		_check_action(stage_action)
		if not reason:
			frappe.throw("驳回必须填写原因。")
		sample = frappe.get_doc("HBOS Retention Sample", doc.retention_sample)
		sample.flags.setdefault('allow_system_fields', True)
		row = _lock_row(doc.retention_sample)
		if _release_reservation(sample, doc.apply_qty, doc.status):
			_audit_on("HBOS Retention Usage Apply", "释放预占", doc.name,
					  action_text="驳回释放预占", new_value="-{}".format(doc.apply_qty))
		sample.save(ignore_permissions=True)
		doc.status = "已驳回"
		doc.save(ignore_permissions=True)
		_audit_on("HBOS Retention Usage Apply", "驳回", doc.name, reason=reason)
		_commit()
		return {"name": doc.name, "status": doc.status}
	except Exception:
		_rollback()
		raise


@frappe.whitelist()
def cancel_usage_apply(usage_name, reason):
	"""取消使用申请逃生口（仅 Manager）：草稿直接取消；已批准取消并释放预占。"""
	_check_action("usage_cancel")
	try:
		doc = frappe.get_doc("HBOS Retention Usage Apply", usage_name)
		if doc.status not in ("草稿", "已批准"):
			frappe.throw("仅「草稿 / 已批准」状态可由 Manager 取消（当前：{}）。".format(doc.status))
		if not reason:
			frappe.throw("取消必须填写原因。")
		sample = frappe.get_doc("HBOS Retention Sample", doc.retention_sample)
		sample.flags.setdefault('allow_system_fields', True)
		if doc.status == "已批准":
			_lock_row(doc.retention_sample)
			if _release_reservation(sample, doc.apply_qty, "已批准"):
				sample.save(ignore_permissions=True)
				_audit_on("HBOS Retention Usage Apply", "释放预占", doc.name,
						  action_text="Manager 取消释放预占", new_value="-{}".format(doc.apply_qty))
		doc.status = "已取消"
		doc.save(ignore_permissions=True)
		_audit_on("HBOS Retention Usage Apply", "审批签署", doc.name,
				  action_text="取消（逃生口）", reason=reason)
		_commit()
		return {"name": doc.name, "status": doc.status}
	except Exception:
		_rollback()
		raise


def _usage_stage_action(status):
	"""驳回按当前审批级角色校验。"""
	if status == "待库存确认":
		return "usage_confirm"
	m = _USAGE_APPROVE_MAP.get(status)
	return m[0] if m else None


# ---------------------------------------------------------------------------
# R7C 处理申请（方案 6.1 FLOW_DISPOSAL_APPLY / 6.5 4/5 级 / 7.x）
# ---------------------------------------------------------------------------

DSP_TYPE_DESTROY = "留样期满销毁"
DSP_TYPE_CONTINUE = "留样期满继续留样"
DSP_TYPE_OTHER = "其他"
DSP_TYPES = [DSP_TYPE_DESTROY, DSP_TYPE_CONTINUE, DSP_TYPE_OTHER]

# status -> (动作, 签名字段, 上一签名比较字段, 是否 QA 线)
_DSP_APPROVE_MAP = {
	"待QC主管审核": ("disposal_qc", "qc_supervisor_sign", None),
	"待QC负责人审核": ("disposal_qc", "qc_manager_sign", "qc_supervisor_sign"),
	"待QA审核": ("disposal_qa", "qa_review_sign", "qc_manager_sign"),
	"待QA负责人审核": ("disposal_qa", "qa_manager_sign", "qa_review_sign"),
	"待QM批准": ("disposal_qm", "qm_sign", "qa_review_sign"),
}


@frappe.whitelist()
def create_disposal_apply(retention_name, disposal_type, qty, reason="",
						  disposal_method="", disposal_location="", qa_manager_required=1,
						  new_retention_due_date=None):
	"""新建处理申请（Analyst/Manager 申请人）。"""
	_check_action("create_disposal_apply")
	if disposal_type not in DSP_TYPES:
		frappe.throw("不支持的处理类型。")
	if not qty or float(qty) <= 0:
		frappe.throw("处理数量必须大于 0。")
	if disposal_type == DSP_TYPE_CONTINUE and not new_retention_due_date:
		frappe.throw("续留类型必须填写新留样期至。")
	try:
		# 先取行锁：并发下 唯一在途/状态/数量/预占 复核都在该锁内（防两并发单都读到“无在途”）
		row = _lock_row(retention_name)
		if row.get("status") not in ("在库", "部分使用"):
			frappe.throw("留样状态为「{}」，不可发起处理申请。".format(row.get("status")))
		# 同留样唯一在途处理申请（在行锁内复核，防并发同建多单）
		inflight = frappe.db.get_all(
			"HBOS Retention Disposal Apply",
			filters={"retention_sample": retention_name,
					 "status": ("in", ["草稿", "待QC主管审核", "待QC负责人审核", "待QA审核",
										"待QA负责人审核", "待QM批准", "已批准", "待执行"])},
			fields=["name"], limit=1)
		if inflight:
			frappe.throw("该留样已有在途处理申请（{}），请处理完成或取消后再新建。".format(inflight[0]["name"]))
		if disposal_type != DSP_TYPE_CONTINUE:
			if (row.get("reserved_qty") or 0) != 0:
				frappe.throw("该留样存在在途预占，不可发起销毁/其他类处理申请。")
			if float(qty) != float(row.get("current_qty") or 0):
				frappe.throw("销毁/其他类处理数量必须等于当前结存（当前结存 {}，申请 {}）。".format(row.get("current_qty"), qty))
		doc = frappe.get_doc({
			"doctype": "HBOS Retention Disposal Apply",
			"retention_sample": retention_name,
			"disposal_type": disposal_type,
			"qty": float(qty),
			"qa_manager_required": 1 if qa_manager_required else 0,
			"reason": reason,
			"disposal_method": disposal_method,
			"disposal_location": disposal_location,
			"new_retention_due_date": new_retention_due_date,
			"applicant": _user(),
			"apply_date": frappe.utils.today(),
			"status": "草稿",
		})
		doc.insert(ignore_permissions=True)
		_commit()
		return {"name": doc.name}
	except Exception:
		_rollback()
		raise


@frappe.whitelist()
def submit_disposal_apply(dsp_name):
	"""提交处理草稿 → 待QC主管审核。"""
	_check_action("create_disposal_apply")
	try:
		doc = frappe.get_doc("HBOS Retention Disposal Apply", dsp_name)
		if doc.status != "草稿":
			frappe.throw("仅草稿状态可提交。")
		doc.status = "待QC主管审核"
		doc.save(ignore_permissions=True)
		_commit()
		return {"name": doc.name, "status": doc.status}
	except Exception:
		_rollback()
		raise


@frappe.whitelist()
def approve_disposal(dsp_name):
	"""处理申请逐级批准（QC 线 Reviewer / QA 线 QA / QM Manager；支持 4/5 级跳过）。"""
	try:
		doc = frappe.get_doc("HBOS Retention Disposal Apply", dsp_name)
		info = _DSP_APPROVE_MAP.get(doc.status)
		if not info:
			frappe.throw("当前状态「{}」无批准动作。".format(doc.status))
		action, field, prev_field = info
		_check_action(action)
		if field == "qm_sign":
			# QM 上一签按链型取最近签署位：5 级=QA 负责人；4 级（跳过 QA 负责人）=QA 审核
			prev_field = "qa_manager_sign" if doc.qa_manager_required else "qa_review_sign"
		prev_signer = doc.get(prev_field) if prev_field else None
		ok, err = rtc.check_sod_sign(doc.applicant, prev_signer, _user())
		if not ok:
			_audit_commit("HBOS Retention Disposal Apply", "SoD 拦截", doc.name,
						 action_text="处理审批 SoD", reason=err)
			frappe.throw(err)
		doc.set(field, _user())
		nxt = _dsp_next(doc.status, doc.qa_manager_required)
		doc.status = nxt
		if nxt == "已批准":
			doc.qm_approved_at = _now()
		if doc.status == "待QM批准" and not doc.qa_manager_required:
			_audit_on("HBOS Retention Disposal Apply", "审批层跳过", doc.name,
					  action_text="4 级链跳过 QA 负责人层（qa_manager_required=0）")
		# QM 批准后分流：销毁/其他 → 待执行（deadline + 留样进待处理快照）；续留 → 已批准待续留执行
		if nxt == "已批准" and doc.disposal_type != DSP_TYPE_CONTINUE:
			doc.status = "待执行"
			doc.deadline = _add_months_dt(doc.qm_approved_at, 3)
			doc.save(ignore_permissions=True)
			_enter_pending(doc)
		else:
			doc.save(ignore_permissions=True)
		_audit_on("HBOS Retention Disposal Apply", "审批签署", doc.name,
				  action_text="{}（{}）".format(field, _user()), new_value="status={}".format(doc.status))
		_commit()
		return {"name": doc.name, "status": doc.status}
	except Exception:
		_rollback()
		raise


def _dsp_next(status, qa_manager_required):
	if status == "待QA审核":
		return "待QM批准" if not qa_manager_required else "待QA负责人审核"
	if status == "待QM批准":
		return "已批准"
	if status == "待QA负责人审核":
		return "待QM批准"
	# 顺序推进
	return {
		"草稿": "待QC主管审核",
		"待QC主管审核": "待QC负责人审核",
		"待QC负责人审核": "待QA审核",
	}[status]


def _add_months_dt(dt, months):
	from dateutil.relativedelta import relativedelta
	base = frappe.utils.get_datetime(dt)
	return (base + relativedelta(months=int(months))).strftime("%Y-%m-%d")


def _enter_pending(doc):
	"""QM 批准销毁类处理 → 留样进入待处理并记录进入前状态快照。"""
	sample = frappe.get_doc("HBOS Retention Sample", doc.retention_sample)
	sample.flags.setdefault('allow_system_fields', True)
	if sample.status == "待处理":
		return
	if sample.status not in (rtc.RET_IN_STOCK, rtc.RET_PARTIAL_USED):
		frappe.throw("留样状态「{}」不可进入待处理。".format(sample.status))
	doc.sample_prev_status = sample.status
	row = _lock_row(doc.retention_sample)
	if (row.reserved_qty or 0) != 0:
		frappe.throw("该留样存在在途预占，进入待处理被拒绝。")
	sample.status = rtc.RET_PENDING
	sample.save(ignore_permissions=True)
	doc.save(ignore_permissions=True)


@frappe.whitelist()
def dispose_handle(dsp_name):
	"""销毁处理人签名（Analyst/Manager）：双签之一。"""
	_check_action("disposal_handler")
	return _dsp_sign(dsp_name, "disposal_by", "disposal_date")


@frappe.whitelist()
def dispose_monitor(dsp_name):
	"""销毁监督人（QA/Manager）签名：双签之二。"""
	_check_action("disposal_monitor")
	return _dsp_sign(dsp_name, "monitor_by", "monitor_date")


def _dsp_sign(dsp_name, who_field, date_field):
	try:
		doc = frappe.get_doc("HBOS Retention Disposal Apply", dsp_name)
		if doc.status != "待执行":
			frappe.throw("仅「待执行」状态可执行处理。")
		if doc.get(who_field):
			frappe.throw("该签署位已签名，不能重复。")
		who = _user()
		if who_field == "disposal_by" and doc.monitor_by and doc.monitor_by == who:
			_audit_commit("HBOS Retention Disposal Apply", "SoD 拦截", dsp_name,
						 action_text="处理人与监督人同人", reason="SoD")
			frappe.throw("处理人与监督人不得为同一用户（SoD）。")
		if who_field == "monitor_by" and doc.disposal_by and doc.disposal_by == who:
			_audit_commit("HBOS Retention Disposal Apply", "SoD 拦截", dsp_name,
						 action_text="处理人与监督人同人", reason="SoD")
			frappe.throw("处理人与监督人不得为同一用户（SoD）。")
		doc.set(who_field, who)
		doc.set(date_field, frappe.utils.today())
		doc.save(ignore_permissions=True)
		_complete_if_signed(doc)
		_commit()
		return {"name": doc.name, "status": doc.status}
	except Exception:
		_rollback()
		raise


def _complete_if_signed(doc):
	"""销毁类双签齐备 → 出库完成；续留类无需监督人，由续留方法收口。"""
	sample = frappe.get_doc("HBOS Retention Sample", doc.retention_sample)
	sample.flags.setdefault('allow_system_fields', True)
	if doc.disposal_type in (DSP_TYPE_DESTROY, DSP_TYPE_OTHER):
		if not (doc.disposal_by and doc.monitor_by):
			return
		row = _lock_row(doc.retention_sample)
		ok, err = rtc.check_execute_disposal(doc.qty, row.current_qty, row.reserved_qty)
		if not ok:
			frappe.throw(err)
		qty_now = sample.current_qty or 0
		sample.current_qty = 0
		sample.status = rtc.RET_DESTROYED
		sample.save(ignore_permissions=True)
		_write_stock_log(sample, "销毁出库", -qty_now,
						 "HBOS Retention Disposal Apply", doc.name)
		doc.status = "已完成"
		doc.save(ignore_permissions=True)
		_audit_on("HBOS Retention Disposal Apply", "销毁出库", doc.name,
				  action_text="双签完成销毁", new_value="-{} {}".format(qty_now, doc.qty_uom))


@frappe.whitelist()
def continue_retention(dsp_name):
	"""续留执行：回写留样 retention_due_date（审计 old/new）并完成（无需监督双签）。"""
	_check_action("disposal_handler")
	try:
		doc = frappe.get_doc("HBOS Retention Disposal Apply", dsp_name)
		if doc.disposal_type != DSP_TYPE_CONTINUE:
			frappe.throw("仅「留样期满继续留样」类型可走续留执行。")
		if doc.status not in ("已批准", "待执行"):
			frappe.throw("当前状态不可续留执行。")
		if not doc.new_retention_due_date:
			frappe.throw("缺少续留新留样期至。")
		row = _lock_row(doc.retention_sample)
		sample = frappe.get_doc("HBOS Retention Sample", doc.retention_sample)
		sample.flags.setdefault('allow_system_fields', True)
		old = sample.retention_due_date
		sample.retention_due_date = doc.new_retention_due_date
		if doc.sample_prev_status and row.get("status") == rtc.RET_PENDING:
			sample.status = doc.sample_prev_status
		sample.save(ignore_permissions=True)
		doc.status = "已完成"
		doc.disposal_by = doc.disposal_by or _user()
		doc.disposal_date = frappe.utils.today()
		doc.save(ignore_permissions=True)
		_audit_on("HBOS Retention Disposal Apply", "续留改期", doc.name,
				  action_text="续留回写留样期至", old_value="due={}".format(old),
				  new_value="due={}".format(doc.new_retention_due_date))
		_commit()
		return {"name": doc.name, "status": doc.status}
	except Exception:
		_rollback()
		raise


@frappe.whitelist()
def reject_disposal(dsp_name, reason):
	"""驳回处理申请（当前审批级角色）：驳回为终态。"""
	try:
		doc = frappe.get_doc("HBOS Retention Disposal Apply", dsp_name)
		info = _DSP_APPROVE_MAP.get(doc.status)
		stage_action = info[0] if info else None
		if not stage_action or doc.status == "草稿":
			frappe.throw("当前状态不可驳回。")
		_check_action(stage_action)
		if not reason:
			frappe.throw("驳回必须填写原因。")
		doc.status = "已驳回"
		doc.save(ignore_permissions=True)
		_audit_on("HBOS Retention Disposal Apply", "驳回", doc.name, reason=reason)
		_commit()
		return {"name": doc.name, "status": doc.status}
	except Exception:
		_rollback()
		raise


@frappe.whitelist()
def cancel_disposal_apply(dsp_name, reason):
	"""取消处理申请逃生口（仅 Manager）：草稿/审批中直接取消；待执行取消需恢复留样快照。"""
	_check_action("disposal_cancel")
	try:
		doc = frappe.get_doc("HBOS Retention Disposal Apply", dsp_name)
		if doc.status in ("已完成", "已驳回", "已取消", "已销毁"):
			frappe.throw("终态单据不可取消。")
		if not reason:
			frappe.throw("取消必须填写原因。")
		if doc.status == "待执行" and doc.sample_prev_status:
			row = _lock_row(doc.retention_sample)
			if row.get("status") == rtc.RET_PENDING:
				sample = frappe.get_doc("HBOS Retention Sample", doc.retention_sample)
				sample.flags.setdefault('allow_system_fields', True)
				sample.status = doc.sample_prev_status
				sample.save(ignore_permissions=True)
		doc.status = "已取消"
		doc.save(ignore_permissions=True)
		_audit_on("HBOS Retention Disposal Apply", "驳回", doc.name,
				  action_text="Manager 取消（逃生口）", reason=reason)
		_commit()
		return {"name": doc.name, "status": doc.status}
	except Exception:
		_rollback()
		raise


# ---------------------------------------------------------------------------
# 内部：库存写路径唯一入口（方案 7.4）
# ---------------------------------------------------------------------------

def _lock_row(retention_name):
	"""四步锁协议第 2 步：FOR UPDATE 行级锁并返回锁内值。"""
	row = frappe.db.sql(
		"SELECT status, current_qty, reserved_qty FROM `tabHBOS Retention Sample`"
		" WHERE name=%s FOR UPDATE",
		retention_name, as_dict=True)
	if not row:
		frappe.throw("留样 {} 不存在。".format(retention_name))
	return row[0]


def _write_stock_log(doc, transaction_type, qty_delta, source_doctype, source_name):
	"""写库存操作流水子表（入库/使用/销毁/转出/调整全来源通用）。"""
	today = frappe.utils.today()
	doc.append("stock_logs", {
		"transaction_date": today,
		"transaction_type": transaction_type,
		"source_doctype": source_doctype or "",
		"source_name": source_name or "",
		"qty_delta": qty_delta or 0,
		"qty_uom": doc.qty_uom,
		"remaining_qty": doc.current_qty or 0,
		"operator": _user(),
	})
	doc.flags.setdefault("allow_system_fields", True)
	doc.save(ignore_permissions=True)


def _audit(log_type, doc_name, action_text="", old_value="", new_value="", reason=""):
	"""审计埋点（复用 R6D audit_log，事件枚举受控——方案 8.1）。"""
	from hb_lims_app.hbos_lims.lims_service import audit_log
	audit_log(log_type, "HBOS Retention Sample", doc_name,
			  action_text=action_text, old_value=old_value, new_value=new_value,
			  reason=reason, commit=False)


# ---------------------------------------------------------------------------
# scheduler cron 入口（R7C；方案 8.3：纯派生不改状态）
# ---------------------------------------------------------------------------

def scheduler_scan():
	"""每日扫描：销毁超期 / 到期 30 天临期留样数量，仅派生统计（不改单据状态）。

	结果写 site cache `hbos_retention_scheduler_summary` 供报表/工作台派生展示，
	不做推送、不改状态（销毁超期在报表层标红）。
	"""
	import datetime
	today = frappe.utils.getdate(frappe.utils.today())
	due30 = today + datetime.timedelta(days=30)
	# 销毁超期：deadline < 今日 且未完成/未取消的销毁类处理单
	overdue = frappe.get_all("HBOS Retention Disposal Apply",
							 filters={"disposal_type": DSP_TYPE_DESTROY,
									  "deadline": ("<", today.strftime("%Y-%m-%d")),
									  "status": ("in", ["已批准", "待执行"])},
							 fields=["name", "deadline", "status"])
	# 临期留样：到期 ≤30 天 且未终结
	near = frappe.get_all("HBOS Retention Sample",
						  filters={"retention_due_date": ("between", [today.strftime("%Y-%m-%d"), due30.strftime("%Y-%m-%d")]),
								   "status": ("not in", [rtc.RET_DESTROYED, rtc.RET_TRANSFERRED, rtc.RET_EXHAUSTED])},
						  fields=["name", "retention_due_date"])
	summary = {"date": today.strftime("%Y-%m-%d"), "disposal_overdue": len(overdue),
			   "near_due_30d": len(near)}
	frappe.cache.set_value("hbos_retention_scheduler_summary", summary)
	return summary


# ---------------------------------------------------------------------------
# 只读聚合投影（供 Vue 前端单次读取，避免多路 get_list join；含派生字段）
# ---------------------------------------------------------------------------

def _sample_brief(name):
	"""留样投影：产品名/批号/单位/结存/预占/可用量。"""
	s = frappe.get_doc("HBOS Retention Sample", name)
	s.flags.setdefault('allow_system_fields', True)
	pname = frappe.db.get_value("HBOS Retention Product", s.retention_product, "product_name")
	return {
		"retention_name": name,
		"product": pname,
		"sample_name": s.sample_name,
		"batch": s.batch_no,
		"uom": s.qty_uom,
		"current_qty": s.current_qty or 0,
		"reserved_qty": s.reserved_qty or 0,
		"available_qty": (s.current_qty or 0) - (s.reserved_qty or 0),
	}


@frappe.whitelist()
def list_usage_applies(status=None):
	"""使用申请列表（只读聚合投影，供前端列表/详情一次性读取）。"""
	_check_action("get_retention_ledger")
	filters = {"status": status} if status else {}
	docs = frappe.get_all("HBOS Retention Usage Apply", filters=filters,
						  order_by="modified desc", limit_page_length=200)
	out = []
	for d in docs:
		doc = frappe.get_doc("HBOS Retention Usage Apply", d["name"])
		brief = _sample_brief(doc.retention_sample)
		out.append({
			"name": doc.name,
			"retention_name": doc.retention_sample,
			"product": brief["product"],
			"sample_name": brief["sample_name"],
			"batch": brief["batch"],
			"qty": doc.apply_qty,
			"uom": brief["uom"],
			"scenario": doc.reason_type,
			"reason": doc.reason_detail,
			"dept": doc.apply_dept,
			"applicant": doc.applicant,
			"applicant_date": str(doc.apply_date or ""),
			"status": doc.status,
			"stock_confirm_by": doc.stock_confirm_by,
			"stock_qty": doc.stock_qty,
			"qc_approval": doc.qc_approval,
			"qa_approval": doc.qa_approval,
			"qm_approval": doc.qm_approval,
			"current_qty": brief["current_qty"],
			"reserved_qty": brief["reserved_qty"],
			"available_qty": brief["available_qty"],
		})
	return {"rows": out, "total": len(out)}


@frappe.whitelist()
def list_disposal_applies(status=None):
	"""处理申请列表（只读聚合投影）。"""
	_check_action("get_retention_ledger")
	filters = {"status": status} if status else {}
	docs = frappe.get_all("HBOS Retention Disposal Apply", filters=filters,
						  order_by="modified desc", limit_page_length=200)
	out = []
	for d in docs:
		doc = frappe.get_doc("HBOS Retention Disposal Apply", d["name"])
		brief = _sample_brief(doc.retention_sample)
		cat = ""
		rp = frappe.db.get_value("HBOS Retention Sample", doc.retention_sample, "retention_product")
		if rp:
			cat = frappe.db.get_value("HBOS Retention Product", rp, "category") or ""
		out.append({
			"name": doc.name,
			"retention_name": doc.retention_sample,
			"product": brief["product"],
			"sample_name": brief["sample_name"],
			"batch": brief["batch"],
			"category": cat,
			"qty": doc.qty,
			"uom": brief["uom"],
			"type": doc.disposal_type,
			"reason": doc.reason,
			"method": doc.disposal_method,
			"location": doc.disposal_location,
			"qa_manager_required": doc.qa_manager_required,
			"applicant": doc.applicant,
			"applicant_date": str(doc.apply_date or ""),
			"status": doc.status,
			"current_qty": brief["current_qty"],
			"reserved_qty": brief["reserved_qty"],
			"deadline": str(doc.deadline or ""),
			"new_retention_due_date": str(doc.new_retention_due_date or ""),
			"sample_prev_status": doc.sample_prev_status,
			"disposal_by": doc.disposal_by,
			"monitor_by": doc.monitor_by,
			"qm_approved_at": str(doc.qm_approved_at or ""),
			"qc_supervisor_sign": doc.qc_supervisor_sign,
			"qc_manager_sign": doc.qc_manager_sign,
			"qa_review_sign": doc.qa_review_sign,
			"qa_manager_sign": doc.qa_manager_sign,
			"qm_sign": doc.qm_sign,
		})
	return {"rows": out, "total": len(out)}


@frappe.whitelist()
def transfer_out(retention_name, reason="受托转出"):
	"""受托转出（Manager；四步锁协议）：前置 reserved_qty==0，结存整量转出（已转出终态）。"""
	_check_action("transfer_out")
	try:
		row = _lock_row(retention_name)
		ok, err = rtc.check_transfer_out(row.reserved_qty)
		if not ok:
			frappe.throw(err)
		if not rtc.can_retention_transition(row.get("status"), rtc.RET_TRANSFERRED):
			frappe.throw("留样状态「{}」不可执行受托转出（终态/待处理禁止）。".format(row.get("status")))
		doc = frappe.get_doc("HBOS Retention Sample", retention_name)
		product = frappe.get_doc("HBOS Retention Product", doc.retention_product)
		if not product.is_outsource:
			frappe.throw("仅受托（is_outsource）留样产品可执行受托转出；常规留样转出请走处置流程。")
		doc.flags.setdefault('allow_system_fields', True)
		qty = doc.current_qty or 0
		doc.current_qty = 0
		doc.status = rtc.RET_TRANSFERRED
		doc.save(ignore_permissions=True)
		_write_stock_log(doc, "受托转出", -qty, "", None)
		_audit("受托转出", doc.name, action_text="受托转出整量", reason=reason,
			   old_value="current_qty={}".format(qty), new_value="current_qty=0")
		_commit()
		return {"name": doc.name, "status": doc.status, "qty": qty}
	except Exception:
		_rollback()
		raise
