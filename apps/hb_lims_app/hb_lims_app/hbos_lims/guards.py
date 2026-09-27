# -*- coding: utf-8 -*-
"""通用写入守卫入口（板块无关）。

实现落在 M2-R8 稳定性板块的 `stability_guards`（R8A 起建立该机制）：

- `guard_system_fields`：状态、签署、版本链等系统字段只允许业务服务
  （`doc.flags.allow_system_fields`）或 System Manager / Administrator 修改，
  表单直改与 `frappe.client.set_value` 等低层写入一律拦截。
- `guard_content_frozen`：状态进入受控取值（如质量标准已生效/已废止）后，内容
  字段与子表整体只读，且**不设特权旁路** —— 受控文件生效后的任何改动都须走升版
  （L10-P0-04）。

此处只做中性再导出，供 M2-R3/R6 检验流程等其它板块复用**同一实现**，
避免两套守卫逻辑分叉。各板块自己持有字段集与受控状态：检验流程见
`workflow_contract` 与各 DocType 控制器，稳定性见 `stability_guards`。
"""

import frappe

from hb_lims_app.hbos_lims import stability_guards
from hb_lims_app.hbos_lims import workflow_contract as wf
from hb_lims_app.hbos_lims.stability_guards import guard_content_frozen
from hb_lims_app.hbos_lims.stability_guards import guard_system_fields

__all__ = ["guard_system_fields", "guard_content_frozen", "system_fields_for",
		   "SYSTEM_FIELD_SETS"]

# DocType -> 受守卫的系统字段集（状态 / 签署 / 版本链）。
# 应急处置（break-glass）据此限定可改字段：**未登记即拒绝**，避免逃生口变成绕过
# 内容冻结（L10-P0-04 / P0-05）的后门。登记表必须与各控制器 validate() 里实际守卫
# 的字段集一致，由 tests/test_lims_guards_contract.py::TestSystemFieldRegistry 防漂移。
SYSTEM_FIELD_SETS = {
	"HBOS Sample": wf.HBOS_SAMPLE_SYSTEM_FIELDS,
	"HBOS Sample Task": wf.HBOS_SAMPLE_TASK_SYSTEM_FIELDS,
	"HBOS Test Result": wf.HBOS_TEST_RESULT_SYSTEM_FIELDS,
	"HBOS COA": wf.HBOS_COA_SYSTEM_FIELDS,
	"HBOS Specification": wf.HBOS_SPECIFICATION_SYSTEM_FIELDS,
	"HBOS Stability Notice": stability_guards.NOTICE_SYSTEM_FIELDS,
	"HBOS Stability Protocol": stability_guards.PROTOCOL_SYSTEM_FIELDS,
	"HBOS Stability Sample": stability_guards.SAMPLE_SYSTEM_FIELDS,
	"HBOS Stability Timepoint": stability_guards.TIMEPOINT_SYSTEM_FIELDS,
	"HBOS Stability Result": stability_guards.RESULT_SYSTEM_FIELDS,
	"HBOS Stability Report": stability_guards.REPORT_SYSTEM_FIELDS,
	"HBOS Stability Change": stability_guards.CHANGE_SYSTEM_FIELDS,
	"HBOS Stability Room Log": stability_guards.ROOM_LOG_SYSTEM_FIELDS,
	"HBOS Stability Fault Ticket": stability_guards.FAULT_SYSTEM_FIELDS,
	"HBOS Stability Equipment": stability_guards.EQUIPMENT_SYSTEM_FIELDS,
}


def system_fields_for(doctype):
	"""返回该 DocType 已登记的系统字段集；未登记即拒绝应急处置修改。

	未登记（如 `HBOS Retention Sample`：库存 / 状态另有 `adjust_stock`、使用与处理
	审批链等受审计业务路径）时抛错，属**安全默认** —— 逃生口不应自动覆盖所有 DocType。
	"""
	fields = SYSTEM_FIELD_SETS.get(doctype)
	if fields is None:
		frappe.throw("DocType「{}」未登记系统字段，应急处置不得修改；请走对应的业务操作。"
					 .format(doctype))
	return fields
