# PR #37 CI 定向修复与来源同步

2026-10-15；本轮只处理候选源码与 CI。来源分支 `pr-m2-r11`，修复前 Head `a91708d858c9c4c7a06ea999426c29dc2efd4386`，指定产品 Base `39366822a5b5d6041b9eea94da4f77255ad26761`。实际交付 Head 以 Git 日志及本轮外部交付报告为准。

状态：**CI_FIX_READY_FOR_REVIEW / RUNTIME_SECURITY_NOT_RUN / PR37_NOT_MERGE_READY**。

## 授权与实现范围

Owner 仅允许八个既有组织/IAM 模型暂留 `hbos_portal` 物理 App，作为受控平台 IAM 子域候选。范围检查、离线安全契约和来源分支同步不代表最终产品设计、业务权限矩阵、正式启用、数据库迁移、部署或 PR 整包合并获批。V2 架构候选继续为 PROPOSED；S02、管理 GET/POST、Grant 及真人验收的旧门禁保持。

已将指定 Base 单向 merge 进来源分支。唯一实际冲突为 `docs/PROJECT_STATUS.md`：保留产品侧多 APP 治理记录和来源侧阶段交付/恢复历史，增加本轮状态及历史解释，不整文件选择任一侧。产品与 main 分支不写入。

## 精确模型范围

全部路径使用前缀 `apps/hbos_portal/hbos_portal/hbos_portal/doctype/`，后缀为 `<slug>/<slug>.json`。下表逐一按现有 JSON 读取确认；全部 `doctype=DocType`、`module=HBOS Portal`。

| slug | JSON name | 范围 |
| --- | --- | --- |
| hbos_external_identity | HBOS External Identity | 原有账号安全模型 |
| hbos_account_operation | HBOS Account Operation | 原有账号安全模型 |
| hbos_account_change_event | HBOS Account Change Event | 原有账号安全模型 |
| hbos_account_security | HBOS Account Security | 原有账号安全模型 |
| hbos_position | HBOS Position | 本轮候选登记 |
| hbos_position_revision | HBOS Position Revision | 本轮候选登记 |
| hbos_personnel_assignment | HBOS Personnel Assignment | 本轮候选登记 |
| hbos_personnel_assignment_revision | HBOS Personnel Assignment Revision | 本轮候选登记 |
| hbos_organization_command_receipt | HBOS Organization Command Receipt | 本轮候选登记 |
| hbos_organization_write_lock | HBOS Organization Write Lock | 本轮候选登记 |
| hbos_organization_management_policy | HBOS Organization Management Policy | 本轮候选登记 |
| hbos_organization_management_policy_revision | HBOS Organization Management Policy Revision | 本轮候选登记 |

完整路径、JSON name/module/doctype 必须匹配；未知模型、相同文件名放错路径、身份篡改、重复身份必须失败并列出文件与原因。原四项权限内容保持原样，八项新增模型逐项保持空原生权限、禁止 import/rename。测试验证实际 controller 继承、读写 hook、未经授权拒绝和合法受控路径，不通过“一律拒绝”获得成功。

本轮不修改运行时业务逻辑、八个模型 JSON、飞书开户/绑定、姓名拼音与重名、密码生命周期或管理员预建账号要求；既有 `/private/tmp` 两行修复不重复修改。

## 本轮验证

本地 Linux Python 3.12.13、网络隔离/只读源码临时容器：Portal 546、LIMS Provider 25、Attendance Provider 12、Inventory Provider 12、Knowledge 18、Twin 32 项均通过；另外 Gateway 10、本地脚本 5 项通过。合计 660 项后端离线回归，按套件与实际覆盖判断，非按数量阈值放行。

新增 24 项范围契约：12 项独立映射、原 4 项原生权限保持、未知模型/异路径/三类身份字段篡改/重复身份/缺失登记/坏 JSON/过深嵌套诊断/重复键/符号链接/嵌套模型与 CLI 诊断；全部负向夹具位于临时目录。新增 7 项安全测试逐一覆盖 8 个实际 controller 和 hook，保留精确 capability 插入/可变 head 更新与合法服务入口等正向行为；两份既有 metadata 测试增加逐模型身份/引擎检查。

Node 22.22.3：Portal lint、Node 35、Vitest 246、LIMS 契约/Mock 门禁/Shell 检查、Portal 正式模式构建通过；LIMS Node 10 和生产构建通过。最终候选提交上的正式 production bundle、复跑以及远端新 SHA 证据在外部交付报告逐项记录，本文不预判远端成功。旧提交成功记录不充当本轮验证。

真实 Site 未运行，普通 `test_*.py` 离线契约不替代真实安全验收。状态台账、当前里程碑、M2 Gate 与公共入口仅追加本轮候选说明，未将既有业务/恢复阶段关闭；AGENTS/CLAUDE 变更来自指定产品基线同步，非本轮扩权。

## 下一轮独立隔离验收清单（本轮不执行）

- Portal、Desk、REST、RPC、列表/报表、导出/附件逐入口的未授权拒绝、合法受控读取、撤权/停用和会话撤销；覆盖普通用户、System Manager、Administrator 的不同执行路径及跨部门/跨域访问。
- 核验所有全局请求 hook 对 LIMS、考勤、仓库、知识、孪生的影响，保留原生合法服务路径，未知入口默认关闭；附件和导出不得旁路对象范围。
- 组织关系及管理政策 schema 的幂等迁移、根锁初始化、事务/并发、备份指纹、回退和恢复分别验收；不得因当前 CI 通过自动运行。
- `apps/hbos_portal/tests/integration_native_read_boundary.py` 不由普通 unittest 自动发现。显式入口为：在另行批准的 Preview bench/sites 工作目录，使用该 bench Python 执行 `<本轮仓库>/apps/hbos_portal/tests/integration_native_read_boundary.py --phase preflight --expected-database-sha256 <批准的数据库摘要>`；preflight 成功且获得测试写入授权后，才可改为 `--phase test`。脚本含固定 `SITE` 和数据库摘要守卫，必须先核对与批准目标精确一致；本轮连 preflight 也未执行。test 会使用合成记录、会话及 Report/DocShare，不能标为只读。
- `integration_organization_storage.py --phase prepare` 涉及 reload_doc/真实 DDL/commit，**本轮未执行**；下一轮也必须独立批准。不能以脚本存在或历史 Preview 记录作为迁移/回退已通过的证据。

## 待评审差异与停止位置

未使用或修改 `HBOS-IAM-V1`、`design/iam-v1-prototype-20261014` 或 PR #50；无法据本轮范围断言现候选与 IAM V1 原型完全一致。八个存储模型、角色/范围/委派与 UI 产品矩阵继续待独立评审。本 PR 既有 LIMS、共享认证/客户端和恢复工具增量不由本轮 CI 修复获得整包放行。

本地检查通过后仅普通 push 原来源分支，收集新 Head、实际 Base 和 Actions checkout merge SHA。保留 **RUNTIME_SECURITY_NOT_RUN / PR37_NOT_MERGE_READY**，停止等待独立评审和隔离验收；不自动 Merge，不修改真实 Site 或 Docker 卷。
