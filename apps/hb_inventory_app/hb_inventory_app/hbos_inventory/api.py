"""入库拍照识别——Frappe 侧接口。

供「入库拍照识别」Desk 页面调用。三层职责清晰分开：

    ocr_client.py  只负责"跟识别服务说话"
    api.py（本文件）只负责"把业务上下文拼起来 / 落库"
    JS 页面        只负责"给人看、让人改"

边界（M3-R6 方案）：

- **识别不可用绝不伪造结果**——抛错让界面提示走人工录入（M3-R2 已具备）；
- **不自动创建 Item 主数据**——识别到未知物料只提示，不擅自建档；
- **识别结果不直接入账**——本模块只创建**草稿** `Stock Entry`，
  由操作员在标准 Desk 表单里复核后自行提交；
- **不绕过既有校验**——草稿提交时仍走 ERPNext 原生校验与 M3-R3 的放行门禁。
"""

from __future__ import annotations

import uuid

import frappe
from frappe import _
from frappe.utils import cint, flt

from hb_inventory_app.hbos_inventory import ocr_client

# 允许使用本页面的角色
ALLOWED_ROLES = {"System Manager", "Stock Manager", "Stock User"}

# 可选后端。与识别服务 `services/hbos_ocr/app/contract.py` 中的常量保持一致；
# Frappe 侧与识别服务是**两个独立部署**，不共享代码，故此处独立声明。
ALL_BACKENDS = ("stub", "c1_local_vlm", "c2_ocr")
BACKEND_STUB = "stub"

# 识别到的产品种类取值（与 M3-R2 建立的分类树一致）
SOURCE_SELF = "自产"
SOURCE_OUTSOURCED = "外购"


def _require_permission() -> None:
	if not (set(frappe.get_roles()) & ALLOWED_ROLES):
		frappe.throw(_("你无权使用入库拍照识别。"), frappe.PermissionError)


# ---------------------------------------------------------------------------
# 上下文 / 状态
# ---------------------------------------------------------------------------


@frappe.whitelist()
def get_intake_context() -> dict:
	"""页面初始化数据：货位清单、后端选项、识别服务状态。

	**识别服务不可用不是错误**——仓库本来就保留人工录入通道。
	此处如实返回 ``available=False`` 让界面提示，而不是抛错阻断整个页面。
	"""
	_require_permission()

	service = {"available": False, "reason": "", "backends": {}, "default_backend": ""}
	try:
		health = ocr_client.health()
		service = {
			"available": True,
			"reason": "",
			"backends": health.get("backends", {}),
			"default_backend": health.get("default_backend", ""),
		}
	except ocr_client.OcrUnavailable as exc:
		service["reason"] = str(exc)

	return {
		"service": service,
		"backends": list(ALL_BACKENDS),
		"source_types": [SOURCE_SELF, SOURCE_OUTSOURCED],
		"warehouses": _leaf_warehouses(),
		"company": frappe.defaults.get_defaults().get("company") or frappe.db.get_single_value(
			"Global Defaults", "default_company"
		),
	}


def _leaf_warehouses() -> list[dict]:
	"""可存货的叶子货位（``is_group = 0``），用于货位下拉。

	只列叶子——分组节点（库位 / 层）本身不能存货（M3-R0 方案 A1）。
	"""
	rows = frappe.get_all(
		"Warehouse",
		filters={"is_group": 0, "disabled": 0},
		fields=["name", "warehouse_name", "parent_warehouse"],
		order_by="name",
		limit_page_length=0,
	)
	return [
		{
			"value": r.name,
			# 短码优先展示，与货位卡 / 扫码页口径一致
			"label": (r.name or "").split(" - ")[0],
			"parent": r.parent_warehouse or "",
		}
		for r in rows
	]


# ---------------------------------------------------------------------------
# 识别
# ---------------------------------------------------------------------------


@frappe.whitelist()
def recognize_label(
	file_url: str,
	source_type: str | None = None,
	backend: str | None = None,
	request_id: str | None = None,
) -> dict:
	"""对已上传的标签照片调用识别服务，返回**经校验层处理**的结果。

	流程：先把照片用 Frappe 标准上传接口传到 `File`，再用 ``file_url`` 调本接口。
	这样避免把图片塞进 JSON，也复用了 Frappe 的附件权限体系。
	"""
	_require_permission()

	content = _read_file(file_url)

	rid = request_id or uuid.uuid4().hex
	try:
		result = ocr_client.recognize(
			file_name=(file_url or "").rsplit("/", 1)[-1],
			content=content,
			source_type=source_type,
			backend=backend,
			request_id=rid,
		)
	except ocr_client.OcrUnavailable as exc:
		# 如实告知不可用，并给出降级路径
		frappe.throw(
			_("识别服务暂不可用：{0}<br><br>"
			  "请改用人工录入，或联系管理员检查识别服务是否已启动。").format(str(exc)),
			title=_("识别服务不可用"),
		)

	result["request_id"] = result.get("request_id") or rid
	return result


def _read_file(file_url: str) -> bytes:
	"""按 file_url 读出文件内容。"""
	if not file_url:
		frappe.throw(_("缺少照片。"))

	name = frappe.db.get_value("File", {"file_url": file_url}, "name")
	if not name:
		frappe.throw(_("找不到照片文件：{0}").format(file_url))

	doc = frappe.get_doc("File", name)
	try:
		# 走 File.get_content()，自动处理 public / private 两种存储
		content = doc.get_content()
	except Exception as exc:  # noqa: BLE001
		frappe.throw(_("读取照片失败：{0}").format(type(exc).__name__))

	if isinstance(content, str):
		content = content.encode()
	if not content:
		frappe.throw(_("照片内容为空。"))
	return content


# ---------------------------------------------------------------------------
# 落库（草稿）
# ---------------------------------------------------------------------------


@frappe.whitelist()
def create_intake_draft(
	item_code: str,
	batch_no: str,
	qty,
	warehouse: str,
	file_url: str,
	source_type: str | None = None,
	manufacturing_date: str | None = None,
	expiry_date: str | None = None,
) -> dict:
	"""把校对后的识别结果落成**草稿入库单**，照片作为附件。

	**刻意只创建草稿（``docstatus = 0``）**：
	- 识别结果不直接入账，操作员须在标准 Desk 表单里复核后再提交；
	- 提交时仍走 ERPNext 原生校验（本模块不绕过任何既有规则）。
	"""
	_require_permission()

	item_code = (item_code or "").strip()
	batch_no = (batch_no or "").strip()
	warehouse = (warehouse or "").strip()
	qty = flt(qty)

	if not item_code:
		frappe.throw(_("物料代码不能为空。"))
	if not batch_no:
		frappe.throw(_("批号不能为空。"))
	if not warehouse:
		frappe.throw(_("货位不能为空。"))
	if qty <= 0:
		frappe.throw(_("数量必须大于 0。"))

	# 不自动创建物料主数据——未知物料只提示（M3-R6 方案）
	if not frappe.db.exists("Item", item_code):
		frappe.throw(
			_("物料代码 {0} 尚未建档。请先在物料主数据中创建，或核对识别结果是否取错字段。").format(
				item_code
			),
			title=_("物料未建档"),
		)

	warehouse_doc = frappe.db.get_value("Warehouse", warehouse, ["is_group", "company"], as_dict=True)
	if not warehouse_doc:
		frappe.throw(_("找不到货位：{0}").format(warehouse))
	if cint(warehouse_doc.is_group):
		frappe.throw(
			_("「{0}」是库位 / 层等分组节点，不能直接存货。请选择具体货位。").format(warehouse)
		)

	company = warehouse_doc.company or frappe.defaults.get_defaults().get("company")
	if not company:
		frappe.throw(_("无法确定公司，请先设置默认公司。"))

	_batch = _ensure_batch(
		batch_no=batch_no,
		item_code=item_code,
		source_type=source_type,
		manufacturing_date=manufacturing_date,
		expiry_date=expiry_date,
	)

	entry = frappe.new_doc("Stock Entry")
	entry.update(
		{
			"stock_entry_type": "Material Receipt",
			"purpose": "Material Receipt",
			"company": company,
			"to_warehouse": warehouse,
			"remarks": _("由「入库拍照识别」创建草稿，请复核后提交。"),
		}
	)
	entry.append(
		"items",
		{
			"item_code": item_code,
			"qty": qty,
			"t_warehouse": warehouse,
			"use_serial_batch_fields": 1,
			"batch_no": batch_no,
		},
	)
	entry.flags.ignore_permissions = True
	entry.insert()

	_attach_photo(file_url, "Stock Entry", entry.name)

	return {
		"name": entry.name,
		"docstatus": entry.docstatus,
		"batch": batch_no,
		"route": f"/app/stock-entry/{entry.name}",
	}


def _ensure_batch(
	*,
	batch_no: str,
	item_code: str,
	source_type: str | None,
	manufacturing_date: str | None,
	expiry_date: str | None,
) -> str:
	"""确保批次存在，并把识别到的属性写上去。

	若已存在则**只补空缺字段**，不覆盖人工已填的值——避免把人工修正过的
	效期 / 来源又改回识别值。
	"""
	if frappe.db.exists("Batch", batch_no):
		patch = {}
		existing = frappe.db.get_value(
			"Batch",
			batch_no,
			["hbos_source_type", "manufacturing_date", "expiry_date"],
			as_dict=True,
		)
		if source_type and not (existing.hbos_source_type or "").strip():
			patch["hbos_source_type"] = source_type
		if manufacturing_date and not existing.manufacturing_date:
			patch["manufacturing_date"] = manufacturing_date
		if expiry_date and not existing.expiry_date:
			patch["expiry_date"] = expiry_date
		if patch:
			frappe.db.set_value("Batch", batch_no, patch, update_modified=False)
		return batch_no

	batch = frappe.new_doc("Batch")
	batch.update(
		{
			"batch_id": batch_no,
			"item": item_code,
			"manufacturing_date": manufacturing_date or None,
			"expiry_date": expiry_date or None,
			"hbos_source_type": source_type or SOURCE_SELF,
		}
	)
	batch.flags.ignore_permissions = True
	batch.insert()
	return batch.name


def _attach_photo(file_url: str, doctype: str, docname: str) -> None:
	"""把标签照片挂到单据上（原始凭证留存）。

	照片最终归档在 **Frappe 的 `File`**（本司内网），随单据走；
	识别服务侧不长期留存（M3-R6 方案第六节）。
	"""
	if not file_url:
		return
	try:
		source = frappe.get_doc("File", {"file_url": file_url})
	except frappe.DoesNotExistError:
		return

	# 已经是挂在该单据上的就不重复挂
	if source.attached_to_doctype == doctype and source.attached_to_name == docname:
		return

	source.attached_to_doctype = doctype
	source.attached_to_name = docname
	source.flags.ignore_permissions = True
	source.save()
