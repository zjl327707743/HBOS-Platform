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

from hb_lims_app.hbos_lims.stability_guards import guard_content_frozen
from hb_lims_app.hbos_lims.stability_guards import guard_system_fields

__all__ = ["guard_system_fields", "guard_content_frozen"]
