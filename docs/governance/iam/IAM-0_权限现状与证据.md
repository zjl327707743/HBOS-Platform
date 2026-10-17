# IAM-0 权限现状与证据

源码 Authority：`zjl327707743/HBOS-Platform@5ec35ec8510303a1c36475e80d33d57c9255d5d6`，PR #21 的 2026-10-01 查询快照。PR 描述中的运行/制品基线与 head 不完全相同，不把远端 HEAD 自动视为本地部署版本。

## 已核对的关键路径

| 编号 | 源码事实 | 工程含义 | 状态 |
| --- | --- | --- | --- |
| S01 | Portal bootstrap 逐 Provider 评估 can_enter，仅下发 can_enter | 已有应用入口授权；未下发完整动作/范围不能说无后端权限 | 保留并扩展 |
| S02 | 考勤 dashboard get_data 有 HR/User/System 角色门禁，但 Employee get_all 与 Attendance SQL 未按当前用户部门约束 | 这是 HR 全量面；不能直接充当部门主管或员工本人接口 | 范围化改造优先项 |
| S03 | 仓库 Portal summary 先用 get_list 取可见 Warehouse，再将 Bin 限制到该集合；空仓库直接返回 | 已有受限聚合实例，应复用思路；不代表全部仓库 API 都验证了 | 保留并回归 |
| S04 | LIMS action_allowed 拒绝仅凭 System Manager 执行非 get_ 动作 | 技术角色与质量业务写权限已部分分离；不能重写成万能管理员 | 保留 |
| S05 | Knowledge SubjectPolicy 由 subjects 或 default_internal 解析；检索要求能力、数据集和文档范围同时具备 | 已有文档级 allowlist；组织/岗位授权管理仍需要统一，不移除硬边界 | 迁移设计输入 |
| S06 | internal_users 主要按启用、用户类型、排除角色判定；新版另有 explicit_management_handover 分支 | 不能说完全没有管理交接；正向企业成员判定要兼容已有明确授权交接 | 定向评审 |

## 精确证据

- S01：[`services/bootstrap.py`](https://github.com/zjl327707743/HBOS-Platform/blob/5ec35ec8510303a1c36475e80d33d57c9255d5d6/apps/hbos_portal/hbos_portal/services/bootstrap.py)，`build_bootstrap`。Git blob `46ba20e144795f258df1427f2f166781ea51533c`。
- S02：[`dashboard_data.py`](https://github.com/zjl327707743/HBOS-Platform/blob/5ec35ec8510303a1c36475e80d33d57c9255d5d6/apps/hb_attendance_app/hb_attendance_app/hbos_attendance/page/hbos_attendance_dashboard/dashboard_data.py)，`get_data`，第 1–55 行。Git blob `621d043d309135c4b64b236071d4346f52b10f74`。
- S03：[`portal/summary.py`](https://github.com/zjl327707743/HBOS-Platform/blob/5ec35ec8510303a1c36475e80d33d57c9255d5d6/apps/hb_inventory_app/hb_inventory_app/hbos_inventory/portal/summary.py)，`_load_permission_aware_inventory`。Git blob `d0606a1cbe52c9d9ad0d6b836d1d32f4db64cc33`。
- S04：[`workflow_contract.py`](https://github.com/zjl327707743/HBOS-Platform/blob/5ec35ec8510303a1c36475e80d33d57c9255d5d6/apps/hb_lims_app/hb_lims_app/hbos_lims/workflow_contract.py)，`action_allowed`。Git blob `6ba2e6a066d780093cd25d6351a34885939c6953`。此函数的 scope 是 DocType 动作重名消歧，不是部门数据范围。
- S05：[`knowledge/policy.py`](https://github.com/zjl327707743/HBOS-Platform/blob/5ec35ec8510303a1c36475e80d33d57c9255d5d6/apps/hb_knowledge_app/hb_knowledge_app/hb_knowledge/policy.py)，`policy_for_subject` / `load_current_policy`。Git blob `2e30cbf94d436fd172c28028dc645164a0f42254`。
- S06：[`services/internal_users.py`](https://github.com/zjl327707743/HBOS-Platform/blob/5ec35ec8510303a1c36475e80d33d57c9255d5d6/apps/hbos_portal/hbos_portal/services/internal_users.py)，`classify_internal_user` / `load_internal_user_decision`。Git blob `a3f9405f3abe3ecd9bcfe4e2da3f76f0ce41e1c2`。

## 本轮没有证明的事情

未读取实际 Site 中 User、Has Role、Role Profile、DocPerm、Custom DocPerm、User Permission、DocShare 或组织/岗位配置；未证明任何真实人员目前越权；未运行原生列表、API、附件、报表、跨 App 的负向测试；未证明每个 ignore_permissions/get_all/SQL 调用都安全或都不安全。

本轮结论是“现有机制及范围化缺口”，不是上线安全签字。不能依据静态扫描没有发现 guard 字样就报确认漏洞，也不能依据出现 guard 字样就报 PASS。

## 下一轮必须补齐的证据

实际源版本与部署制品映射；角色定义与角色授予；User Permission 的 strict 设置及空范围语义；自定义权限覆盖；Employee/User 关联；公司/部门/仓库/检验组归属；文档分享与 Everyone 分享；用户类型与 desk_access；受限附件/导出；权限变更后的现有会话/缓存行为；知识/孪生独立配置与标准角色之间的差异。

## 框架依据（2026-10-01 核对）

[Frappe Database API](https://docs.frappe.io/framework/user/en/api/database)：get_list 应用用户权限，get_all 不执行同等过滤。
[Frappe Hooks](https://docs.frappe.io/framework/user/en/python-api/hooks)：permission_query_conditions 与 has_permission 是可用扩展点；列表条件不自动覆盖所有自定义查询。

这些是框架语义，不是目标 Site 的运行验证。
