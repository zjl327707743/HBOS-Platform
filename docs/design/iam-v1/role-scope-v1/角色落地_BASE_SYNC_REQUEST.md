## BASE_SYNC_REQUEST｜IAM 角色正式实现前产品同步（2026-10-19）

Owner 已在本轮执行任务确认采用固定设计 `90185653853d508a52cbfb9bb49b6e0cf0bc5a5d`，授权原目录推进角色正式实现与隔离验收；这不是 #52 合并/生产发布授权。根据任务第 3 节，请平台合并线确认固定产品 SHA、共享文件唯一写者和同步方式。

- 继续 `/Users/hb/Projects/HBOS-IAM-R4-B` / `feature/iam-v1` / Draft #52，工作树开工干净；同一工作区本轮仅当前执行者写入，前序 IAM 会话为 idle。不建 clone、worktree、Site、PR 或 Compose 项目。
- 当前 IAM `a38a15ce04bdfd1b8604775c63c5f3db9e458a4b`，tree `9db3a654727b19aaadd6c1df12065e8947970494`。
- 远端产品当前及拟吸收 SHA `e3f6a5a04c72f90a17948191665bc82fd7fb00bf`，tree `1352d978e022125952db20b2535fabd08c614401`（包含四业务和 #58 收口）。共同祖先 `39366822a5b5d6041b9eea94da4f77255ad26761`。旧报告 `366b3ad…` / 上轮观测 `04e0bb0…` 不再作为本次最新 tip。
- `git merge-tree --write-tree --messages --name-only` 只读工作区预演：IAM 128 个变更路径，产品 386 个，交集 6 个；返回 1，确认下面 3 个内容冲突。没有执行实际 merge，没有把冲突树供 5198 使用。

| 重叠文件 | 实测结果 | 必须保留/核对的合同 |
| --- | --- | --- |
| `frontend/hbos-portal-web/src/components/layout/GlobalHeader.vue` | 内容冲突 | IAM 主体清理、禁用期 inert、协调退出；产品 mock 通知及集团标识；产品 finally 与 IAM 退出流程逐段合并 |
| `frontend/hbos-portal-web/src/router/index.ts` | 内容冲突 | IAM 首次改密/本人/管理能力守卫与持久页面；产品仓储/生产/LIMS 新路由、LIMS 能力守卫；避免双会话初始化 |
| `frontend/hbos-portal-web/src/services/frappeClient.ts` | 内容冲突 | IAM 已验证会话事实、403/417/proof/CSRF/结果未知分类；保留产品新增调用与导出，不能回退到旧 Guest 字符串推断 |
| `frontend/hbos-portal-web/src/views/ProfileSettingsView.vue` | 文本自动合并 | 首次口令交付与原资料页均保留，需运行回归 |
| `apps/hbos_portal/hbos_portal/hooks.py` | 文本自动合并 | 保留 IAM User/Employee/请求/任务守卫与生产 provider；预演只有一份 has_permission，不沿用 #37 的重复赋值结论 |
| `apps/hb_attendance_app/hb_attendance_app/hooks.py` | 文本自动合并 | 保留 IAM 本人/原生列表/Prepared Report/File/RQ 守卫及产品 Desk bundle |

补充实读确认：产品 `composables/usePortalSession.ts` 的 runCheck 在窗口 focus/pageshow/visibilitychange 时将 sessionPending=true，LimsLayout（及相应Inventory/Production外壳）以 skeleton / RouterView v-if 链切换，会卸载业务页面。该文件与 `components/layout/AttendanceLayout.vue`（直接bootstrap）、`LimsLayout.vue`、`InventoryLayout.vue`、`ProductionLayout.vue` 一并列入平台共享接缝：保留领域权限，以单一会话协调器适配，不让产品同步回退已确认的稳定性。此为源码发现，尚未执行这些产品页面的本机运行复测。

无文本重叠不代表无语义接缝：产品 `router/portalGuard.ts` 会调用 `portal.ensureSession()`，IAM `ensurePortalSession()` 已协调会话，需统一就绪入口；产品 store/provider 是产品独有改动。考勤新增 `list_data.py` / 报表适配使用原生 get_list/User Permission，不能直接认为支持新 IAM 具名部门/公司角色。`report_scope.py` 仍为全员 SQL 报表拒绝门禁，逐路径有实测范围执行器前保留。仓储/生产/LIMS 原生领域守卫必须保留，不在本轮增加其角色。CI/公共台账仍交平台唯一写方，IAM 只提供精确 DocType allowlist/test hunk 与台账 patch。

### 请求确认的具体方案

1. 固定吸收 `e3f6a5a04c72f90a17948191665bc82fd7fb00bf`，在原 `feature/iam-v1` 普通 merge，保留历史且无需强推；不修改产品分支或 PR 目标。
2. 请平台指定以上 6 个重叠文件及 `router/portalGuard.ts`、`composables/usePortalSession.ts`、上述四个App外壳、store/provider、考勤 report/list/provider 接缝的唯一写者。建议本执行者在专属同步窗口按最小 hunk 处理 IAM 必需接缝，平台线复核；公共台账/CI 继续由平台写入。未确认前本执行者只写 IAM 专属映射与证据。
3. 确认后先完成自有 Site 原生备份/指纹，短暂停自身 5198 开发服务；同步、检查冲突、typecheck/构建及账号/Gate/三类切回/本人/四业务导航回归后恢复。仅操作既有 `hbos-iam-r4-b-20261015`；不碰其他项目、5197/5199、真实外部同步或真实库。

请以 `BASE_SYNC_CONFIRMED` 明确回复固定 SHA、唯一共享写者、同步方式（如平台另行处理共享文件，请给交付 SHA/最小 patch）。当前没有把本请求、历史 COMMENT 或其他业务审批例外当作确认。

本请求提交后继续精确模型/接口/迁移/测试映射；正式同步、角色接入及新运行验收仍等待上述确认。#52 保持 Draft，不自动合并、不发布生产。
