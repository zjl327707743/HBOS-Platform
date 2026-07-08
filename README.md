# 新乡海滨智能运营管理平台

新乡海滨智能运营管理平台面向企业级智能运营管理，长期目标是在 Frappe/ERPNext 开源底座上建设海滨自定义业务 App、外部 AI/视频/算法服务、Vue/React 驾驶舱、飞书集成与 Docker 部署体系。

准确架构叫法：Frappe/ERPNext 开源底座 + Frappe 多 App 模块化架构 + 外部独立服务扩展。

## 当前阶段

当前 M0 工程启动阶段已完成并封板，M0-REMOTE 已完成，M1 已完成 M1-R0 规划收口、M1-R1 对象模型验证收口和 M1-R2 配置试运行方案收口。M1-R3 已通过 Codex 审查，但实际结果为 PARTIAL / BLOCKED，现收口为 BLOCKED；M1-R3A 已通过 Codex 审查并收口为 COMPLETED；M1-R3B 已通过 Codex 审查并收口为 COMPLETED；M1-R3B-FIX 已通过 Codex 审查并收口为 COMPLETED；M1-R3C 已通过 Codex 审查并收口为 COMPLETED，结论为 PARTIAL / GAP_IDENTIFIED；M1-R3D 已通过 Codex 审查并收口为 COMPLETED，结论为 Gap 四类分类、均不需要立即创建 hb_attendance_app；M1-R3E 已通过 Codex 审查并收口为 COMPLETED；M1-R3F 已通过 Codex 审查并收口为 COMPLETED；M1-REQ-DESIGN-DRAFT 已完成需求确认、PRD、技术设计和 Demo 路线图四份文档交付，当前为 REVIEWING。

当前真实进度以以下文件为准：

- `docs/PROJECT_STATUS.md`
- `docs/CURRENT_MILESTONE.md`
- `docs/milestones/README.md`
- `docs/milestones/M0.md`

当前状态摘要：

- M0-R1 工程骨架与 AI 上下文治理已完成
- M0-R2 环境设计、里程碑治理与 Skill 路由规范已完成
- M0-R2E 公共入口文件收尾规则补强已完成
- M0-R3A Frappe / Docker 最小环境落地已完成，Docker 镜像已拉取，容器已启动，测试 site 已初始化，Frappe Desk 登录页已验证
- M0-R3B Frappe HR / HRMS 安装前评估已完成并通过 Codex 审查
- M0-R3C Frappe HR / HRMS 安装验证已完成，HRMS 已安装到本地 `frontend` site，基础 HR 模块可访问
- M0-R3C-FIX HRMS 前端资源与 Roster 白屏诊断修复已完成，Frappe HR 图标、基础 HR 模块和 Roster 页面已验证可访问
- M0-R3D HRMS 能力盘点与 M1 考勤一期边界设计已完成
- M0-R3E HRMS 环境可复现性收口已完成，并已通过 Codex 审查
- M0 整体已完成并封板
- M0-REMOTE GitHub Private remote 创建、`origin` 绑定和 `main` 首次 push 已完成
- M1-R0 平台入口、账号体系、角色权限、飞书 SSO 可行性、中文化 / 本地化诊断方案已完成，并已通过 Codex 独立审查
- M1-R1 HRMS 原生考勤对象模型验证记录已完成，并已通过 Codex 独立审查，状态为 COMPLETED
- M1-R2 HRMS 原生考勤配置试运行方案已完成文档交付，并已通过 Codex 独立审查，状态为 COMPLETED
- M1-R3 HRMS 原生考勤最小测试数据试运行已执行并通过 Codex 审查，最终状态为 BLOCKED；本轮未完成 14 场景闭环
- M1-R3A 运行态阻断诊断与 TEST 数据隔离 / 清理方案已通过 Codex 审查并收口为 COMPLETED
- M1-R3B 运行态最小修复方案已通过 Codex 审查并收口为 COMPLETED；本轮未执行修复、未清理 TEST 数据、未继续试运行
- M1-R3B-FIX 已通过 Codex 审查并收口为 COMPLETED；该轮只执行 `docker compose up -d redis-cache redis-queue`，Redis / worker / scheduler / bench doctor / login 已恢复或改善
- M1-R3C HRMS 原生考勤最小试运行复测已通过 Codex 审查并收口为 COMPLETED，结论为 PARTIAL / GAP_IDENTIFIED；14 个场景中 8 个通过，6 个为 GAP / PARTIAL；Attendance 可由 HRMS 原生生成，但迟到 / 早退未置位、缺卡 / 缺勤口径、请假 Leave Allocation、加班业务口径仍需 M1-R3D 诊断
- M1-R3D HRMS 原生考勤异常口径与配置 Gap 诊断已通过 Codex 审查并收口为 COMPLETED；结论为 Gap 四类分类、均不需要立即创建 `hb_attendance_app`
- M1-R3E 配置复核清单与业务口径确认表已通过 Codex 审查并收口为 COMPLETED；配置清单已覆盖 8 类配置复核项，业务口径表已确认 8/10 项阻塞 M1-R4
- M1-R3F 业务口径确认包已通过 Codex 审查并收口为 COMPLETED；9 项确认主题中 7 项必须确认，2 项可先按默认值推进
- M1-REQ-DESIGN-DRAFT 已完成需求确认、PRD、技术设计和 Demo 路线图四份文档交付，当前为 REVIEWING
- M1-R4 Demo 技术方案与实施路线拆分为 PLANNED，尚未启动

M0 阶段用于约束后续规划、执行、审查与验收。当前已完成 Frappe / ERPNext / Docker 最小环境启动验证、Frappe HR / HRMS 安装验证、HRMS 前端资源修复、M1 考勤一期边界设计、HRMS 环境可复现性收口、GitHub Private remote 首次同步、M1-R0 规划诊断收口、M1-R1 对象模型验证记录、M1-R2 配置试运行方案设计、M1-R3 局部试运行记录、M1-R3A 阻断诊断方案、M1-R3B 运行态最小修复方案、M1-R3B-FIX 运行态最小修复执行记录、M1-R3C 原生考勤最小试运行复测记录、M1-R3D 异常口径与 Gap 诊断、M1-R3E 配置复核与业务口径确认表和 M1-R3F 业务口径确认包；M1 仍未进入业务开发。

## 仓库定位

当前仓库用于承载 M0 工程启动文档、AI 协作规则、里程碑状态、阅读指南、计划文档、架构决策记录和最小 Docker 环境配置。

它不是业务代码仓库，也不是 Frappe App 仓库；当前只包含经 M0-R3A 授权创建的最小 Docker 本地验证配置。

## 主技术栈

- Frappe Framework
- ERPNext
- Frappe HR
- Python
- JavaScript
- MariaDB/MySQL 兼容体系
- Redis
- Docker
- Docker Compose
- Vue/React
- ECharts
- FastAPI

## 长期仓库规划

长期建议按职责拆分仓库，当前仅记录规划，不在未批准轮次创建这些仓库：

- `haibin-hbos-infra`：基础设施、部署、环境编排与运维脚本
- `hb_core_app`：海滨核心主数据、权限、组织与平台扩展
- `hb_attendance_app`：考勤业务扩展
- `hb_feishu_app`：飞书集成扩展
- `hb_production_app`：生产运营扩展
- `hb_quality_app`：质量管理扩展
- `hb_safety_app`：安全管理扩展
- `hb_ai_ops_app`：AI 运营、视频、算法服务对接扩展
- `hbos-dashboard-web`：Vue/React 驾驶舱与大屏前端

## 当前禁止事项

当前 M1 仍处于规划与验证阶段。继续禁止：

- 不创建自定义 Frappe App
- 不创建 `hb_core_app`、`hb_attendance_app`、`hb_feishu_app`
- 不把 HRMS 安装验证等同于考勤业务开发完成
- 不提交真实 `.env` 或真实密钥
- 不提交备份文件、数据库、Docker volume 或运行时数据
- 不开发业务
- 不接飞书真实写入
- 不做前端驾驶舱
- 不浏览或搬运大量 Obsidian 长文
- 不执行 `docker compose down -v`
- 不删除 volume
- 不重建 `frontend` site

后续路线只记录，不代表已启动：

1. M1-R3C 已通过 Codex 审查并收口，试运行完成但业务闭环未完成。
2. M1-R3D 已通过 Codex 审查并收口，Gap 已四类分类，均不需要立即创建 App。
3. M1-R3E 已通过 Codex 审查并收口，配置复核清单与业务口径确认表已交付。
4. M1-R3F 已通过 Codex 审查并收口，业务口径确认包已交付。
5. M1-REQ-DESIGN-DRAFT 已完成需求设计四份文档交付，当前等待 Codex 审查；M1-R4 新定位为 Demo 技术方案与实施路线拆分。
6. M1-R4 当前仅为 PLANNED，尚未启动。

## AI 协作方式

- ChatGPT：负责规划、拆解、上下文整理与方案边界确认
- Claude：负责按计划执行文档或代码变更
- Codex：负责工程审查、边界检查、验证与交付复核
- 用户：负责最终验收、取舍确认与里程碑放行

每轮任务开始前，AI 必须说明本轮读取了哪些文档。默认只读 `CLAUDE.md`、`AGENTS.md`、`docs/AI_CONTEXT.md`、`docs/PROJECT_STATUS.md`、`docs/CURRENT_MILESTONE.md`，禁止默认递归读取整个 `docs/`。
