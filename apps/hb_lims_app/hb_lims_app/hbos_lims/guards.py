# -*- coding: utf-8 -*-
"""通用系统字段守卫入口（板块无关）。

实现落在 M2-R8 稳定性板块的 `stability_guards`（R8A 起建立该机制）：状态、签署、
版本链等系统字段只允许业务服务（`doc.flags.allow_system_fields`）或
System Manager / Administrator 修改，表单直改与 `frappe.client.set_value` 等
低层写入一律拦截。

此处只做中性再导出，供 M2-R3/R6 检验流程等其它板块复用**同一实现**，
避免两套守卫逻辑分叉。各板块自己持有字段集：检验流程见 `workflow_contract`，
稳定性见 `stability_guards`。
"""

from hb_lims_app.hbos_lims.stability_guards import guard_system_fields

__all__ = ["guard_system_fields"]
