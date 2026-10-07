# 新乡海滨智能运营管理平台

## 知识候选连续执行 R1 — 2026-10-08

状态：IN_PROGRESS，专用分支 `codex/knowledge-autonomous-r1`，Draft PR #30，固定产品基线 `72e5b1728981b7ef102a2c9ee033ce0452c400e7`。已核验 K1C2 归档与独立评审，并恢复已审候选到独立源码副本；补齐 Binding 列/JSON/关联身份校验及写入守卫，修复搜索标签网格布局与知识页局部字号，并实现授权知识空间列表、范围选择与文档数量。核心/进程内 HTTP 与新增领域回归 241 项、候选/原 P1 契约 56 项、前端 83 项通过，Vue typecheck/frappe 数据模式构建通过。

全新登记 Site 的元数据/跨连接版本/空间接口已通过 14 项真实数据库 HTTP 测试；Chrome 桌面/移动/键盘及撤权验证首轮通过 10 项，最终代码、镜像和浏览器证据同步复跑中。原生 HTTP 首轮 19 项中 18 项通过，1 项测试辅助读取遇 Redis TTL 竞态；修复辅助读取后该项单独通过，完整重跑中。

主任务书 `HBOS_KNOWLEDGE_AUTONOMOUS_MASTER_TASK_R1.md` 未随已提供三附件出现，本机按名称检索未找到；时间/资源/完整依赖与分仓目标待补齐。其他可确定且安全的修复、空间功能和原生验证已持续完成。RAGFlow、模型、正式员工 MCP、旧库恢复与发布均未计为通过。现行 P1、个人 MCP、旧知识数据及真实权限未由本批次修改；不合并 main/product，不切换部署。知识执行事实见 `docs/milestones/M1_KB_AUTO_R1_知识候选连续执行.md`；以下旧轮次条目保留为历史与其他业务范围。

## 并行权限治理 IAM-0 — 2026-10-01

Owner 已批准进入统一身份与权限治理。当前仅交付设计、角色—动作—范围矩阵、只读源码盘点工具与本机任务书；实际 Site 盘点和隔离验收仍为 NOT_RUN，不修改账号、角色或业务数据，不替代原账号收尾。入口：[IAM-0 治理资料](docs/governance/iam/README.md)。

最新产品基线：PR #21 已在 FINAL_REVIEW_PASS 后 squash 合入 `feature/hbos-portal-product`，产品 HEAD `e4b16ee80aaaf21aac2304246a4de1f9fe8995ea`。Owner 最新无破坏验收 PASS、浏览器设密/改密/恢复 final-submit 3/3 PASS，新 squash 四项 CI SUCCESS。IAM-0 已由 clean Draft PR #23 承接，旧 #22 已关闭且未合并；PR #15 仍为 Draft，main 未变化。[当前 Gate](docs/milestones/M1_RP3_统一账号飞书绑定与正式发布.md) 记录本轮收口事实。

Frappe/ERPNext 开源底座 + Frappe 多 App 模块化架构 + 外部独立服务扩展。

## 当前交付

本轮（2026-10-01）接续 PR #21，执行登录账号模块 UI 规范回归与全功能审修。Owner 已亲自确认 Administrator 能通过本人飞书验证并登录，记为 OWNER_CONFIRMED_SUCCESS；历史成员权限待审批或登录失败记录不再代表当前事实。保留真实绑定、密码、MFA、Secret、企业与回调；不要求重复配置。认证页沿用已有 Ant Design Vue / ConfigProvider / typography / tokens，修复表单、证明期限、错误状态、同路由目标与提交结果处理。破坏性、并发与交接只在独立合成 Site 验证。新版本真人 OAuth、本人收到验证码、第二位真人交接与移动软键盘结果单独记录，未执行不写 PASS。复用现有 P1 / Compose / 卷与常用入口，最终本机 SHA/build ID、远端提交、CI 和制品须一致。公司服务器为 NOT_DEPLOYED。主记录：`docs/milestones/M1_RP3_统一账号飞书绑定与正式发布.md`。PR #21 已 squash 合入 `feature/hbos-portal-product@e4b16ee80aaaf21aac2304246a4de1f9fe8995ea`；团队后续 Portal 代码以产品分支为准。PR #15 仍 Draft，不推 main；IAM 由 Draft PR #23 单独承接。

平台已包含考勤、仓储库存、LIMS、Portal、知识助理与设备/数字孪生自定义 App。密码和飞书使用同一 Frappe User；原有业务权限仍由原 App 约束。业务通知、生成式知识回答、现场遥测、工艺动画及偏好同步尚未实现，具体状态见前端完整性矩阵。安全变更通知单独记录真实发送状态，不能等同业务通知能力完成。

- [项目状态](docs/PROJECT_STATUS.md)
- [当前里程碑](docs/CURRENT_MILESTONE.md)
- [Mac 常用启动与团队同步](docs/deployment/Mac本地运行与团队同步.md)
- [团队部署、备份与回退](docs/deployment/统一账号与Portal正式部署说明.md)
- [前端完整性矩阵](docs/frontend/统一账号发布与前端完整性矩阵.md)

## 团队构建

在已审查的 clean checkout 使用 Node 22 执行 `bash scripts/release/build_bundle.sh`，生成同源 Portal 和 LIMS 编译资产及六 App 部署包。通用 Gateway 位于 `services/hbos_gateway`，依赖、基线与 HRMS commit 见 `scripts/release/依赖版本锁.json`。既有目标版本不得为了匹配基线而降级。

升级必须保留已确认原 Site/数据库，先备份并验证恢复，再迁移及核对原账号/角色/权限/业务关联。制品或 PR 不包含账号数据库、Secret、私有知识索引/原文或真实模型；这些经批准私下部署。

## 协作与边界

`AGENTS.md`、`CLAUDE.md` 为规则入口；进度以状态台账与对应里程碑为准。Portal 本轮不改变其他考勤/库存里程碑的 Owner 验收状态。禁止创建未知替代库、覆盖未知数据库、重置原密码/角色、发布凭据或私有资料。

团队后续 Portal 代码来源：`feature/hbos-portal-product@e4b16ee80aaaf21aac2304246a4de1f9fe8995ea`。PR #21 保留为已合并的审查与发布证据；Mac 本地运行与本人验收分开记录，公司生产尚未部署。
