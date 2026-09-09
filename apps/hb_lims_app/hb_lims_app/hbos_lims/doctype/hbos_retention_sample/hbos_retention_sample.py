# -*- coding: utf-8 -*-
# Copyright (c) 2026, HBOS and contributors
# For license information, please see license.txt

from frappe.model.document import Document

# 受托产品登记落位（方案 6.1 rev6）：不经在库，直接以已转出状态创建
OUTSOURCE_STATUS = "已转出"


class HBOSRetentionSample(Document):
	def validate(self):
		self._validate_product_flags()
		self._generate_business_key()
		self._auto_due_date()
		self._validate_obs_fields()
		self._guard_system_fields()
		self._guard_stock_invariants()

	def _guard_system_fields(self):
		"""字段级系统写入守卫：库存/状态字段仅系统服务（带 allow_system_fields 标记）
		或 System Manager/Administrator 可改；普通角色直写（frappe.client.set_value/
		DocType 表单）一律拦截（read_only 不构成服务端保护，此处为双保险）。"""
		import frappe
		before = self.get_doc_before_save()
		if not before:
			return
		roles = frappe.get_roles()
		if frappe.session.user == "Administrator" or "System Manager" in roles:
			return
		if self.flags.get("allow_system_fields"):
			return
		for f in ("current_qty", "reserved_qty", "status"):
			if str(before.get(f) or "") != str(self.get(f) or ""):
				frappe_throw("库存/状态字段「{}」仅能通过业务操作（服务方法）修改，禁止直接编辑。".format(f))

	def _guard_stock_invariants(self):
		"""库存不变量（防御层，任何写入路径都生效）：结存/预占不为负、预占不超结存。"""
		cur = self.current_qty
		res = self.reserved_qty
		if cur is not None and float(cur) < 0:
			frappe_throw("当前结存不得为负。")
		if res is not None and float(res) < 0:
			frappe_throw("预占量不得为负。")
		if cur is not None and res is not None and float(res) > float(cur):
			frappe_throw("预占量不得大于当前结存（当前结存 {} / 预占 {}）。".format(cur, res))

	def before_insert(self):
		"""登记即入库（初始状态=在库）；受托产品直接以已转出落位（rev6）。"""
		if self._is_outsource():
			self.status = OUTSOURCE_STATUS
			self.current_qty = 0
			self.reserved_qty = 0

	def on_insert(self):
		if self._is_outsource():
			# 受托转出落位：不写入库流水，写 0 量审计事件（登记逻辑层触发，
			# 由 lims_service.register_retention 统一埋点，避免双重事件）
			return
		# 在库登记：current_qty 初始化 = retention_qty，写入库流水
		# （库存写路径唯一入口在 lims_service.register_retention，这里不重复写，
		#   仅保证字段初值一致，见方案 7.4 单一写路径）
		self.current_qty = self.retention_qty or 0
		self.reserved_qty = 0

	# ------------------------------------------------------------------

	def _product(self):
		return frappe_get_doc("HBOS Retention Product", self.retention_product)

	def _is_outsource(self):
		product = self._product()
		return bool(product.get("is_outsource"))

	def _validate_product_flags(self):
		product = self._product()
		if product.get("is_liquid"):
			frappe_throw("液体物料不留样（规程 4.1），该产品已标记为液体物料，禁止登记。")
		if not product.get("is_active"):
			frappe_throw("该留样产品已停用，不再登记新留样。")
		if product.get("is_outsource") and self.status != OUTSOURCE_STATUS:
			# 受托产品：允许登记但直接落位已转出（before_insert 已置）；
			# 若用户手工把状态改回在库则拦截
			if self.status not in (None, "", OUTSOURCE_STATUS, "在库"):
				frappe_throw("受托生产样品由受托方留样，登记直接以「已转出」状态创建。")

	def _generate_business_key(self):
		"""业务键（产品#批号#容器）单字段 unique，validate 时生成。"""
		product_code = self.material_code or ""
		self.product_batch_container_key = "{}#{}#{:02d}".format(
			product_code, self.batch_no or "", self.container_no or 1
		)

	def _auto_due_date(self):
		"""留样期至 = 有效期/复验期 + 3 年（人工修正允许，由审计层留痕）。"""
		if not self.retention_due_date and self.expiry_date:
			self.retention_due_date = add_years(self.expiry_date, 3)

	def _validate_obs_fields(self):
		"""观察字段成组校验：观察样品须有选取人/日期；外售产品每批自动进观察。"""
		product = self._product()
		if product.get("category") == "外售产品" and product.get("obs_rule") == "每批观察（外售产品）":
			if not self.observed_flag:
				self.observed_flag = 1
				self.obs_selected_reason = "外售产品每批"
		if self.observed_flag:
			if not (self.obs_year and self.obs_selected_by and self.obs_selected_date and self.obs_selected_reason):
				frappe_throw(
					"观察样品必须完整填写观察年度、选中人、选中日期、选取原因。"
				)
			if not self.next_obs_month:
				self.next_obs_month = 0
			self.next_obs_due_date = add_months_safe(self.retention_date, self.next_obs_month)


def frappe_get_doc(doctype, name):
	import frappe
	return frappe.get_doc(doctype, name)


def frappe_throw(msg):
	import frappe
	frappe.throw(msg)


def add_years(date_str, years):
	import frappe
	return frappe.utils.add_years(date_str, years)


def add_months_safe(date_str, months):
	"""月末溢出安全加月（P3-6：用 relativedelta，1/31+12 个月=次年 1/31）。"""
	if not date_str:
		return None
	from dateutil.relativedelta import relativedelta
	import datetime
	base = frappe_utils_getdate(date_str)
	return (base + relativedelta(months=months)).strftime("%Y-%m-%d")


def frappe_utils_getdate(date_str):
	import frappe
	return frappe.utils.getdate(date_str)
