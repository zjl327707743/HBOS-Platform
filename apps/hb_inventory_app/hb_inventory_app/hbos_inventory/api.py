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

# **允许由入库页补录**的物料级字段（白名单）。
# 白名单不只是为了安全——字段名要拼进 SQL，只有限定在自有常量里才无注入风险。
# 这三个字段都印在待检证 / 货位卡上，且同一物料每批都一样，故写回主数据。
ITEM_GAP_FIELDS = ("hbos_storage_condition", "hbos_workshop", "hbos_shelf_life_type")


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

	# 识别服务**不碰数据库**（它是独立进程，无 site 上下文），所以「拿主数据校正
	# 识别结果」这一步只能在这边做——这里是唯一能查到 Item 的地方。
	_enrich_from_master(result)
	return result


def _enrich_from_master(result: dict) -> None:
	"""用**物料主数据**校正识别结果（就地改 ``result``）。

	两件事，都建立在「物料代码是所有印刷信息里最可靠的一项」之上
	（实测 50 张样本代码准确率 98%，且代码是唯一能唯一定位物料的键）：

	## 1. 品名以主数据为准

	打印的品名本来就取 `Item.item_name`（见 `print_utils` 与两个货位卡模板），
	OCR 读到的品名**只是用来交叉核对的**。所以代码一对上主数据，品名就该直接用
	主数据里的。

	这一层同时兜住**识别没读到品名**的情况（OCR 返回 None）——那种场合
	主数据照样把名字补上，界面上不会出现空白，也不会出现一个错的。

	OCR 原本读到的值**保留在 ``raw_fields.product_name``**，界面据此并列展示
	「AI 读作 X / 主数据 Y」，读错了正好暴露出来。

	## 2. 物料代码在主数据里找不到时，尝试形近纠错

	OCR 会把代码读少一位或读错一位（实测出现过 `13000901` 读成 `1300090`）。
	在**已建档的代码**里找编辑距离 ≤1 的候选：

	- **唯一命中** → 判定为读错，改过去并提示；
	- **多个命中** → **不猜**，只列出候选让人自己选。少一个数字时往往同时匹配
	  好几个代码（`1300090` 能补出 `13000900`~`13000909`），硬猜就是造数据。

	这两步都只影响**提示与默认值**，最终仍由操作员在界面上确认。
	"""
	fields = result.get("fields") or {}
	raw_fields = result.get("raw_fields") or {}
	hints = result.setdefault("hints", {})

	code = (fields.get("item_code") or "").strip()

	# ---- 2. 代码纠错（放在品名之前：品名要用纠正后的代码去查）----
	if code and not frappe.db.exists("Item", code):
		cand = _nearby_item_codes(code)
		if len(cand) == 1:
			fixed = cand[0]
			hints.setdefault("item_code", []).append(
				_("主数据中没有「{0}」，但有且仅有「{1}」与之相差一位，已按主数据纠正。").format(
					code, fixed
				)
			)
			fields["item_code"] = fixed
			code = fixed
		elif cand:
			hints.setdefault("item_code", []).append(
				_("主数据中没有「{0}」。与之相近的代码有 {1}，请照标签核对是哪一个。").format(
					code, "、".join(cand[:5])
				)
			)

	# ---- 1. 品名以主数据为准 ----
	if not code:
		return
	item_name = frappe.db.get_value("Item", code, "item_name")
	if not item_name:
		return

	ocr_name = (fields.get("product_name") or "").strip()
	if ocr_name and ocr_name != item_name:
		hints.setdefault("product_name", []).append(
			_("识别读到的品名为「{0}」，与主数据不符；打印以主数据「{1}」为准，请核对是否取错了字。").format(
				ocr_name, item_name
			)
		)
	fields["product_name"] = item_name
	# 供界面展示「主数据里是什么」，免得再去查一次
	result["master_item_name"] = item_name


def _nearby_item_codes(code: str, max_results: int = 6) -> list[str]:
	"""在主数据里找与 ``code`` 相差一位（增/删/改）的代码。

	为什么用「编辑距离 ≤1」而不是模糊匹配打分：物料代码是 8 位定长数字串，
	OCR 的典型错误就是**少一位或多一位**或**某一位形近读错**，这两种都正好落在
	距离 1 内。打分排序反而会把无关的代码排前面。

	代码库是内存里过一遍（当前 129 条，量级很小），不做缓存也不建索引。
	"""
	if not code:
		return []
	cands = []
	for name in frappe.get_all("Item", pluck="name", limit_page_length=0):
		if _within_one_edit(code, name):
			cands.append(name)
			if len(cands) >= max_results:
				break
	return cands


def _within_one_edit(a: str, b: str) -> bool:
	"""``a`` 与 ``b`` 是否相差一次「增、删、改」。"""
	if a == b:
		return False
	if abs(len(a) - len(b)) > 1:
		return False
	if len(a) == len(b):
		return sum(x != y for x, y in zip(a, b)) == 1
	short, long = (a, b) if len(a) < len(b) else (b, a)
	# 长串删掉某个字符能否得到短串
	for i in range(len(long)):
		if long[:i] + long[i + 1:] == short:
			return True
	return False


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
	file_name: str | None = None,
	source_type: str | None = None,
	manufacturing_date: str | None = None,
	expiry_date: str | None = None,
	storage_condition: str | None = None,
	workshop: str | None = None,
	shelf_life_type: str | None = None,
	supplier_name: str | None = None,
	manufacturer: str | None = None,
	supplier_batch_no: str | None = None,
	packaging: str | None = None,
	label_text: str | None = None,
) -> dict:
	"""把校对后的识别结果落成**草稿入库单**，照片作为附件。

	**刻意只创建草稿（``docstatus = 0``）**：
	- 识别结果不直接入账，操作员须在标准 Desk 表单里复核后再提交；
	- 提交时仍走 ERPNext 原生校验（本模块不绕过任何既有规则）。

	后 7 个参数是**识别读不到、由操作员手工补的信息**（M3-R6 第七批）。
	它们分别落到两个层级：

	===================  ==============================  ==========
	参数                  落到                            语义
	===================  ==============================  ==========
	``storage_condition``  ``Item.hbos_storage_condition``  **仅补空**
	``workshop``           ``Item.hbos_workshop``           **仅补空**
	``shelf_life_type``    ``Item.hbos_shelf_life_type``    **仅补空**
	``supplier_name``      ``Batch.hbos_supplier_name``     本批
	``manufacturer``       ``Batch.hbos_manufacturer``      本批
	``supplier_batch_no``  ``Batch.hbos_supplier_batch_no`` 本批
	``packaging``          ``Batch.hbos_packaging`` 子表     本批（替换式）
	``label_text``         ``Batch.hbos_label_text``        本批
	===================  ==============================  ==========

	前三项是**物料级**的（同一物料每批都一样），故写回主数据、且**只在原值为空时写**；
	后四项是**批次级**的（逐批不同），写进本批次。

	**全部参数都不传时，行为与加这些参数之前完全一致。**
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

	_require_item_ready(item_code)

	# 先解析包装构成——格式不对就在建任何东西之前报错
	packaging_rows = _parse_packaging(packaging)

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

	# 物料级：写回主数据，仅补空
	filled = _fill_item_master_gaps(
		item_code,
		{
			"hbos_storage_condition": storage_condition,
			"hbos_workshop": workshop,
			"hbos_shelf_life_type": shelf_life_type,
		},
	)

	# 批次级：写进本批次
	_batch = _ensure_batch(
		batch_no=batch_no,
		item_code=item_code,
		source_type=source_type,
		manufacturing_date=manufacturing_date,
		expiry_date=expiry_date,
		supplier_name=supplier_name,
		manufacturer=manufacturer,
		supplier_batch_no=supplier_batch_no,
		packaging=packaging_rows,
		label_text=label_text,
	)

	entry = frappe.new_doc("Stock Entry")
	entry.update(
		{
			"stock_entry_type": "Material Receipt",
			"purpose": "Material Receipt",
			"company": company,
			"to_warehouse": warehouse,
			"remarks": _("由「入库拍照识别」创建草稿，请复核后提交。"),
			# 来源标记。提交后前端据此提示「去批次取货位卡/待检证」，
			# 而不是靠 remarks 的中文文案（改一句话就失效）。
			"hbos_intake_batch": batch_no,
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

	_attach_photo(file_url, "Stock Entry", entry.name, file_name=file_name)

	return {
		"name": entry.name,
		"docstatus": entry.docstatus,
		"batch": batch_no,
		# 本次真正补进物料主数据的字段，供界面如实回显
		"filled": filled,
	}


def _require_item_ready(item_code: str) -> None:
	"""校验物料是不是「能在这个流程里用」——不只是「存不存在」。

	**不自动创建物料主数据**——未知物料只提示，不擅自建档（M3-R6 方案）。

	只查 `frappe.db.exists` 是不够的（实测教训）：`Item` 存在但**没勾批次管理**时，
	本流程会一路走到 `_ensure_batch` 才炸在 ERPNext 的 `Batch.validate()` 上，
	报的是英文的「The selected item cannot have Batch」，操作员完全看不懂该去改哪里。
	所以在这里把本流程真正依赖的两个开关一次查清，缺什么说什么。

	本流程依赖（且**必须先于**货位校验报出来，否则操作员会先去改一个没问题的字段）：

	- `is_stock_item`：入库单是库存事务，非库存物料过不了；
	- `has_batch_no`：本页批号必填，`_ensure_batch` 必然建批次。
	"""
	item = frappe.db.get_value(
		"Item", item_code, ["is_stock_item", "has_batch_no", "disabled"], as_dict=True
	)
	if not item:
		frappe.throw(
			_("物料代码 {0} 尚未建档。请先在物料主数据中创建，或核对识别结果是否取错字段。").format(
				item_code
			),
			title=_("物料未建档"),
		)

	missing = []
	if item.disabled:
		missing.append(_("已停用"))
	if not cint(item.is_stock_item):
		missing.append(_("未勾选「维护库存」"))
	if not cint(item.has_batch_no):
		missing.append(_("未勾选「有批号」"))

	if missing:
		frappe.throw(
			_("物料代码 {0} 已建档，但不满足入库要求：{1}。<br><br>"
			  "请到物料主数据中补上后再试（本页批号必填，故物料必须启用批次管理）。").format(
				item_code, "、".join(missing)
			),
			title=_("物料建档不完整"),
		)


def _fill_item_master_gaps(item_code: str, values: dict) -> list[dict]:
	"""把手工补录的物料级字段写回 `Item` 主数据，**只在原值为空时写**。

	## 为什么是「仅补空」

	这三个字段（储存条件 / 生产车间 / 复检期还是有效期）描述的是**物料本身**，
	不是某一批次——同类料每批都一样。所以由操作员在入库时填一次、写回主数据，
	以后每批都自动带上，不用重填。但**绝不覆盖已有值**：已在主数据里的值可能是
	质量或技术部门维护的口径，不该被仓库操作员的一次入库改写掉。

	## 为什么用条件 UPDATE 而不是「先读再写」

	先读再写有 TOCTOU 竞态：两个操作员同时给同一物料入库、都读到空，就会**后提交的
	覆盖先提交的**，与「仅补空」的承诺相矛盾。改成把「为空」写进 WHERE 条件、
	让数据库自己判定，再用 `ROW_COUNT()` 确认是否真的写了。

	## 权限

	写库时 `ignore_permissions=True`，与 `api.py` 其余写库处一致。这是**有意绕过**
	ERPNext 默认矩阵：实测 `Item` 只有 `Item Manager` 有写权限，页面允许的三个角色
	（System Manager / Stock Manager / Stock User）**都没有**——若改用
	`frappe.has_permission("Item", "write")`，功能对任何操作员都不可用。
	风险由「仅补空」+「Comment 留痕」两道保险承担，见 M3-R6 方案第九之九节。

	返回本次**真正写进去**的字段列表（`[{field, label, value}]`），供界面如实回显。
	本来就有值、因而没写的字段**不出现**在返回里——避免界面谎称「已补录」。
	"""
	filled: list[dict] = []
	if not item_code or not values:
		return filled

	meta = frappe.get_meta("Item")
	for fieldname in ITEM_GAP_FIELDS:  # 白名单，字段名不来自调用方
		value = (values.get(fieldname) or "").strip()
		if not value:
			continue

		field = meta.get_field(fieldname)
		if not field:
			continue

		# Select 字段先校验取值，别把非法值写进主数据（set_value / 裸 SQL 都不走校验）
		if field.fieldtype == "Select" and field.options:
			allowed = [o for o in field.options.split("\n") if o]
			if value not in allowed:
				frappe.throw(
					_("{0} 的取值「{1}」不合法，只能是：{2}。").format(
						_(field.label), value, " / ".join(allowed)
					)
				)

		frappe.db.sql(
			f"""update `tabItem`
			    set `{fieldname}` = %s, modified = now(), modified_by = %s
			    where name = %s and ifnull(`{fieldname}`, '') = ''""",
			(value, frappe.session.user, item_code),
		)
		if not frappe.db.sql("select row_count()")[0][0]:
			continue  # 原值不为空，按「仅补空」不写

		filled.append({"field": fieldname, "label": _(field.label), "value": value})

		# 裸 SQL 不走 Frappe 的文档缓存失效，显式清一次，免得别处读到旧值
		frappe.clear_document_cache("Item", item_code)

		# 留痕：纯 SQL / set_value 都不产生 Version 记录，主数据会改得无声无息
		frappe.get_doc(
			{
				"doctype": "Comment",
				"comment_type": "Info",
				"reference_doctype": "Item",
				"reference_name": item_code,
				"content": _("由「入库拍照识别」补录 {0}：{1}（原为空值）").format(
					_(field.label), value
				),
			}
		).insert(ignore_permissions=True)

	return filled


def _parse_packaging(raw) -> list[dict] | None:
	"""解析前端传来的包装构成。

	返回 `None` 表示**本次不动**包装构成（区别于返回 `[]` 的清空）。
	格式不对就抛错——静默当空会让操作员以为填了、实际没存。
	"""
	if raw is None:
		return None
	if isinstance(raw, list):
		rows = raw
	else:
		text = str(raw).strip()
		if not text:
			return None
		try:
			rows = frappe.parse_json(text)
		except Exception:
			frappe.throw(_("包装构成格式不正确（应为数组），请检查后重试。"))
		if not isinstance(rows, list):
			frappe.throw(_("包装构成格式不正确（应为数组），请检查后重试。"))

	meta = frappe.get_meta("HBOS Packaging Detail")
	container_field = meta.get_field("container_type")
	allowed_types = [o for o in (container_field.options or "").split("\n") if o]

	out: list[dict] = []
	for row in rows:
		if not isinstance(row, dict):
			continue
		container = (row.get("container_type") or "").strip()
		weight = row.get("unit_weight")
		count = cint(row.get("count"))
		# 整行空着（界面上的空白行）直接跳过
		if not container and not weight and not count:
			continue
		if not container:
			frappe.throw(_("包装构成：容器类型不能为空。"))
		if container not in allowed_types:
			frappe.throw(
				_("包装构成：容器类型「{0}」不合法，只能是：{1}。").format(
					container, " / ".join(allowed_types)
				)
			)
		if count <= 0:
			frappe.throw(_("包装构成：{0} 的件数必须大于 0。").format(container))
		out.append(
			{
				"container_type": container,
				"unit_weight": flt(weight) or 0,
				"count": count,
				"is_tail": cint(row.get("is_tail")),
				"remark": (row.get("remark") or "").strip(),
			}
		)
	return out


def _ensure_batch(
	*,
	batch_no: str,
	item_code: str,
	source_type: str | None,
	manufacturing_date: str | None,
	expiry_date: str | None,
	supplier_name: str | None = None,
	manufacturer: str | None = None,
	supplier_batch_no: str | None = None,
	packaging: list[dict] | None = None,
	label_text: str | None = None,
) -> str:
	"""确保批次存在，并把属性写上去。

	**已存在时只补空缺字段**，不覆盖人工已填的值——避免把人工修正过的
	效期 / 来源又改回识别值。

	两个例外，都在下面的注释里说明：
	- `supplier_name` / `manufacturer` / `supplier_batch_no` 同样只补空缺；
	- `packaging` 是**替换式**——见 `_replace_packaging` 的注释。
	"""
	if frappe.db.exists("Batch", batch_no):
		patch = {}
		existing = frappe.db.get_value(
			"Batch",
			batch_no,
			[
				"hbos_source_type",
				"manufacturing_date",
				"expiry_date",
				"hbos_supplier_name",
				"hbos_manufacturer",
				"hbos_supplier_batch_no",
				"hbos_label_text",
			],
			as_dict=True,
		)
		if source_type and not (existing.hbos_source_type or "").strip():
			patch["hbos_source_type"] = source_type
		if manufacturing_date and not existing.manufacturing_date:
			patch["manufacturing_date"] = manufacturing_date
		if expiry_date and not existing.expiry_date:
			patch["expiry_date"] = expiry_date
		if supplier_name and not (existing.hbos_supplier_name or "").strip():
			patch["hbos_supplier_name"] = supplier_name
		if manufacturer and not (existing.hbos_manufacturer or "").strip():
			patch["hbos_manufacturer"] = manufacturer
		if supplier_batch_no and not (existing.hbos_supplier_batch_no or "").strip():
			patch["hbos_supplier_batch_no"] = supplier_batch_no
		if (label_text or "").strip() and not (existing.hbos_label_text or "").strip():
			# 只留非空行——界面按行渲染，空行是格式噪声，存了没用
			patch["hbos_label_text"] = _clean_label_text(label_text)

		if not patch and packaging is None:
			return batch_no

		# 子表**不能用 `frappe.db.set_value` 写**——那会对 Table 字段发出
		# `UPDATE tabBatch SET hbos_packaging=...`，MariaDB 报「未知列」。
		# 必须走文档对象。顺带 `save()` 也会走一遍 Batch 自己的校验，这是好事。
		batch = frappe.get_doc("Batch", batch_no)
		for key, value in patch.items():
			batch.set(key, value)
		if packaging is not None:
			_replace_packaging(batch, packaging)
		batch.flags.ignore_permissions = True
		batch.save()
		return batch_no

	batch = frappe.new_doc("Batch")
	batch.update(
		{
			"batch_id": batch_no,
			"item": item_code,
			"manufacturing_date": manufacturing_date or None,
			"expiry_date": expiry_date or None,
			"hbos_source_type": source_type or SOURCE_SELF,
			"hbos_supplier_name": supplier_name or None,
			"hbos_manufacturer": manufacturer or None,
			"hbos_supplier_batch_no": supplier_batch_no or None,
			"hbos_label_text": _clean_label_text(label_text) or None,
		}
	)
	if packaging:
		for row in packaging:
			batch.append("hbos_packaging", row)
	batch.flags.ignore_permissions = True
	batch.insert()
	return batch.name


def _clean_label_text(raw: str | None) -> str:
	"""标签原文逐行校对后的文本：去掉空行、去掉行首尾空白。

	界面是按行渲染的，空行只是格式噪声（OCR 输出里很常见），存下来没有检索价值。
	"""
	if not raw:
		return ""
	return "\n".join(line.strip() for line in str(raw).split("\n") if line.strip())


def _replace_packaging(batch, rows: list[dict]) -> None:
	"""**替换式**写入包装构成，而非追加。

	为什么不能追加：`hbos_packaging_count` / `hbos_packaging_spec`（print_utils.py）
	都是把子表**汇总求和**的。同一批次重复入库（或操作员返工重来）若只是 append，
	件数会翻倍、包装规格会重复打印。所以先清空再写。
	"""
	batch.set("hbos_packaging", [])
	for row in rows:
		batch.append("hbos_packaging", row)


def _attach_photo(
	file_url: str, doctype: str, docname: str, file_name: str | None = None
) -> None:
	"""把标签照片挂到单据上（原始凭证留存）。

	照片最终归档在 **Frappe 的 `File`**（本司内网），随单据走；
	识别服务侧不长期留存（M3-R6 方案第六节）。

	定位方式：**优先用 `File` 的 docname**。原因：两份内容相同的上传可能产生
	**两条 `File` 记录共用同一个 `file_url`**，此时按 `file_url` 取会拿到不确定的
	那一条，可能把别人已挂的附件改挂走。前端上传后拿到 `message.name`，
	一并传下来即可精确定位。
	"""
	if not (file_name or file_url):
		return

	source = None
	if file_name and frappe.db.exists("File", file_name):
		source = frappe.get_doc("File", file_name)
	else:
		# 兜底：按 file_url 取（取最早一条，行为确定）
		rows = frappe.get_all(
			"File", filters={"file_url": file_url}, fields=["name"], order_by="creation asc", limit=1
		)
		if rows:
			source = frappe.get_doc("File", rows[0].name)
	if source is None:
		return

	# 已经是挂在该单据上的就不重复挂
	if source.attached_to_doctype == doctype and source.attached_to_name == docname:
		return

	source.attached_to_doctype = doctype
	source.attached_to_name = docname
	source.flags.ignore_permissions = True
	source.save()
