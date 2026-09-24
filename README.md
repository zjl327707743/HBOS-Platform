# 新乡海滨智能运营管理平台

新乡海滨智能运营管理平台面向企业级智能运营管理，长期目标是在 Frappe/ERPNext 开源底座上建设海滨自定义业务 App、外部 AI/视频/算法服务、Vue/React 驾驶舱、飞书集成与 Docker 部署体系。

准确架构叫法：Frappe/ERPNext 开源底座 + Frappe 多 App 模块化架构 + 外部独立服务扩展。

## 当前阶段

> 状态校正（2026-09-21 本轮追加）：R8J 已上线基线之外，本轮新增稳定性取样绑定、业务检验结果同步及审查缺陷修复已按 Owner 授权同步生产；完整 pytest **341/341**、生产前端构建通过，生产路径 17 个页面/资源冒烟均返回 200，备份为 `【内部备份标识已省略】`。

> 当前状态（2026-09-23）：M2-R8K「我的待办身份绑定」仍为 REVIEWING，真实 Frappe 冒烟已通过，待 Owner 测试路径验收。生产页面已可访问该功能，但其既有发布来源未在本次核定；本次仅将侧栏「最近访问」移除补丁 `fbb1aee` 同步生产，备份 `【内部备份标识已省略】`。详见 `docs/milestones/M2_R8K_我的待办身份绑定.md`。

> 状态校正（2026-09-24）：M2-R3G「检验流程系统字段守卫」**已部署**（提交 `c8dcfcb`）。为 M2-R3/R6 检验流程的 5 个 DocType 补齐 R7/R8 已有的系统字段守卫，堵住「`frappe.client.set_value` 直写状态 / 签署字段、绕过服务层状态机与 SoD」的伪造审批缺口。验证：离线 404 passed、实机非特权用户 9 passed（正向全链多角色 + 负向 7 项 + 对照 1 项）、部署后经 nginx → gunicorn 的伪造写 HTTP **417** 被拦、HTTP 冒烟 17/18。本次为后端改动，未重建前端资产、未执行迁移。详见 `docs/milestones/M2_R3G_检验流程系统字段守卫.md`。M2-LIMS 当前子轮仍为 M2-R8K。

历史阶段摘要：M0 已完成并封板，M1 产品交付仍在 M1-FIX 功能补漏中，M2-R1 至 M2-R4 已 COMPLETED；本项目当前工作状态以本节新增的 M2-R8K 条目及 `docs/PROJECT_STATUS.md`、`docs/CURRENT_MILESTONE.md` 为准。
M2-R6A（样品登记动态表单设计）已交付下拉决策条 + 9 类样品类型完整表单切换方案，进入 REVIEWING，等待 Owner 审查。
M2-R6B（检验结果台账双模式设计）已交付明细台账 + 样品表（每样品种类一表）双模式方案，Owner 已确认原型与交互，进入 REVIEWING，设计文档待审查。
M2-R6C（检验结果台账 Vue 复刻与生产部署）已将双模式复刻进 Vue 并上线生产，Owner 已确认测试路径。
M2-R6D（合规审计日志）已交付：后端 HBOS Audit Log DocType（write-once 防篡改）+ 全量捕获 + 查询 API + 业务埋点，前端合规组新增合规审计日志入口与页面；已上线生产，Owner 已确认测试路径；并修复生产部署新旧 hash 错配致个别页面 404。
M2-R6C（检验结果台账 Vue 复刻与生产部署）双模式已复刻进 Vue 并上线生产，Owner 已确认测试路径效果，DEPLOYED。
M2-R7D（留样板块前端 Vue 复刻与生产部署）DEPLOYED：留样方案 rev6 口径定稿（Owner 已确认角色方案 B+SoD、分支策略 b）；R7A（主数据与留样登记 3 DocType + retention_service + 前端两页）已在 m2-r6 交付并测试路径验证；6 视图 Vue 板块已同步生产 `/hbos-lims`（工作台/观察/使用/处理 4 视图已切换真实后端接入，登记台账/产品沿用 R7A API），Owner 2026-09-08 已确认测试路径；R7B（观察管理）/R7C（使用与处理审批）后端已实现并真实验证，审计连通性已核验。
M2-R8J（稳定性板块前后端审查与缺陷修复）**DEPLOYED / 待 Owner 测试路径验收**：2026-09-21 后续回滚模拟复现的 8 项 P1 与 2 项 P2 业务缺陷已完成修复；离线契约 **321/321**、前端类型检查与构建通过，测试路径浏览器冒烟覆盖变更条件、结果录入与趋势、取样计划及延期派生区域。**已提交 `e447f97` 并同步生产 `/hbos-lims`（备份 `【内部备份标识已省略】`）。上线后 Owner 验收发现的稳定性工作台「待 R8B~R8D」占位文案（KPI 卡 + 整块面板）已修复——后端补样品/时间点/结果真实计数与时间点执行结构，前端 KPI 6→8 张；侧边栏「取样与检测计划 / 结果录入与趋势」角标改接真实数据（原为原型遗留硬编码 4/3 且恒显红色，提交 `6e06155`）（提交 `b61f83d`，已同步生产）。趋势摘要产品/检验项目下拉控件宽度补丁已同步生产，生产发布脚本 pytest **342/342**、`build:prod` 和 17 条 HTTP 冒烟通过，并完成生产浏览器复测（备份 `【内部备份标识已省略】`）。**主文档 `docs/milestones/M2_R8J_稳定性板块审查与修复.md`。
M2-R8I（稳定性剩余三视图前端接入 + 5 张 Script Report 物化）DONE / 待 Owner 审查：交付 稳定性台账 / 检测进度跟踪 / 年度覆盖清单 / 温湿度记录查询 / 设备与校准到期清单 5 张 Script Report（方案 6 张报表全部就位，有效截止日由服务层派生）；`api/stability.ts` +64 接口函数与 6.3.5~6.3.8 全量动作角色；重写「结果录入与趋势」「报告与有效期」「变更·稳定性室·设备」三视图（读 + 写全接、按会话角色显隐），横幅改 live、演示数据层 `stabilityDemo.ts` 356→21 行退役。验证：离线 311/311、5 张报表非 Administrator 实机渲染、浏览器真实会话写链与角色显隐、`vue-tsc` 0 错误、build 成功、375px 三页无溢出。**稳定性板块 7 视图至此全部接入真实后端**；未部署生产。主文档 `docs/milestones/M2_R8I_稳定性剩余三视图前端接入.md`。
M2-R8H（稳定性前端接入：样品入箱与台账 + 取样与检测计划）DONE / 待 Owner 审查：把 R8B 的后端接到 R8F 的两个视图（读 + 写全接、按会话角色显隐）。后端补 3 处（`get_stability_schedule` 增三层日期与延期状态、新增跨时间点延期列表 `get_stability_delays` 并注册角色、`_policy_latest_test` 入参由对象改值）；前端新增 22 个接口函数，重写两个视图（样品台账 + 详情 + 动作弹窗；月度看板改为整月日期列 + 时间点日期链 + 计划台账三层日期 + 延期审批含批准/驳回），新增登记入箱与申请延期两个抽屉，vite 补 `/printview` 代理（标签打印走 Frappe 打印视图），`stabilityDemo.ts` 删除这两节孤儿导出。验证：离线 246/246、`vue-tsc` 0 错误、build 成功、浏览器真实会话走通读 + 写全链与角色门控、375px 三页无溢出。至此稳定性 7 视图中 4 个已接真实后端。未部署生产。主文档 `docs/milestones/M2_R8H_稳定性样品与计划前端接入.md`。
M2-R8B（稳定性后端：样品、时间点与取样检测计划）DONE / 待 Owner 审查：交付 5 个 DocType（HBOS Stability Sample + Sample Log；HBOS Stability Timepoint + Timepoint Item + Timepoint Delay）+ 3 条状态机（FLOW_STB_SAMPLE / FLOW_STB_TIMEPOINT / 延期子表机）+ 21 个动作方法 + 4 个只读接口 + scheduler_scan + 标签 Print Format「HBOS 稳定性样品标签」+ Script Report「取样与检测计划看板」。核心口径：`current_qty` 单一写路径与四步锁（锁顺序固定 Sample → Timepoint）、时间点生成幂等可重跑、延期三段流程与四段日期链全链校验、逾期纯派生不改状态；Result（R8C）依赖处做前向兼容守卫。验证：离线 244/244、实机 40/40、补充 10/10。本轮只做后端 + 标签 + 报表，前端接入另起一轮；未部署生产。主文档 `docs/milestones/M2_R8B_稳定性样品与时间点后端.md`。
M2-R8G（稳定性前端接入真实 API：工作台 + 考察申请与方案）DONE / 待 Owner 审查：把 R8F 的演示数据前端接到 R8A 后端。后端补 5 个只读接口（产品 / 主数据白名单 / 方案台账 / 方案详情 / 稳定性审计摘要）；前端新增 `src/api/stability.ts`（7 只读 + 14 写 + 角色动作矩阵），重写「稳定性工作台」与「考察申请与方案」两视图（读 + 写全接：建档 / 提交 / QC 确认 / 批准 / 驳回 / 取消 / 关闭 + 方案起草 / 提交 / 审核 / 批准 / 驳回 / 作废），按钮按会话角色显隐（后端仍为硬校验）；其余 5 视图保留演示数据并标注「演示数据 · 待 R8B~R8D」。修复 2 项 R8A 遗留缺陷：`HBOS Stability Protocol` 漏建 `snapshot_frozen` 致方案冻结快照守卫恒失效；命名系列 `-####` 在本版 Frappe 下非法、生成 `HBOS-STB-NOT-2026-####00009` 畸形单号（已改为不含 `#` 的既有约定写法）。验证：离线 203/203、实机 28/28、只读接口 7/7、浏览器真实会话走通读 + 写全链与角色门控、`vue-tsc` 0 错误、build 成功、375px 无溢出。**未部署生产**（先给测试端链接，Owner 确认后再同步）。主文档 `docs/milestones/M2_R8G_稳定性前端接入真实API.md`。
M2-R8A（稳定性主数据与通知单/方案后端实现与实机验证）DONE / 待 Owner 审查：11.3 启动门禁 7/7 已闭环（Owner 2026-09-16），在 `hb_lims_app` 落地 10 个 DocType（4 主数据 + Notice + Protocol + 4 子表）、`FLOW_STB_NOTICE`/`FLOW_STB_PROTOCOL` 两条状态机、新增 `LIMS QA Manager`/`LIMS QP` 两角色、批准后冻结快照与版本链；DocType 层 6 个 LIMS 角色一律只读（方案 8.6），写路径唯一为 `stability_service`。实机 migrate 已执行，端到端 + 负向用例 **28/28 通过**、离线契约 **199/199 全绿**；验证中修复 4 项缺陷（非法 fieldtype、`extra_condition_reason` 缺失致 >2 条件不可提交、审计 `log_type` 未入受控枚举、越权/SoD/非法转移/删除未留痕）。本轮未接前端真实 API、未启动 R8B。主文档 `docs/milestones/M2_R8A_后端实现与实机验证.md`。
M2-R8F（稳定性板块前端 Vue 复刻与生产部署）DEPLOYED：Owner 2026-09-16 已确认测试路径并授权同步生产。在 `frontend/hbos-lims-web` 复刻稳定性 7 视图（工作台 / 考察申请与方案 / 样品入箱与台账 / 取样与检测计划 / 结果录入与趋势 / 报告与有效期 / 变更·稳定性室·设备）+ 7 条 `/stability*` 路由 + 侧栏「稳定性管理」分组 7 入口 + 演示数据层（`TEST-HBOS-M2-STB-*`）；生产构建后同步 `/hbos-lims`（备份 `【内部备份标识已省略】`，84 个文件与本地逐字节一致、全路由与 7 个 chunk 均 200），`deploy_lims_fix.sh` 冒烟清单已补 `/stability*`。本轮不创建稳定性 DocType、不改 `hb_lims_app`、不接真实 API、不启动 R8A（该轮口径；R8A 其后已由本轮完成）。
M2-R8E（稳定性板块前端设计方案与 HTML 原型）REVIEWING / Owner 已确认原型：已交付 7 个原型视图、工作台 PNG 设计图和设计方案文档。

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
- M1-REQ-DESIGN-DRAFT 已通过 Codex 审查并收口为 COMPLETED；四份设计文档交付完成
- M1-R4 Demo 技术方案与实施路线拆分已通过 Codex 审查并收口为 COMPLETED
- M1-R5 HRMS 配置基线、考勤工作台与月度汇总 Demo 已通过 Codex 审查并收口为 COMPLETED；本轮未创建 App / DocType，未写入站点数据库，未启动 R6/R7
- M1-R6A Excel 导入与异常流程落地方案 / Gate 判定已通过 Codex 审查并收口为 COMPLETED
- M1-R6B 脱敏打卡流水导入最小实现已通过 Codex 审查并收口为 COMPLETED；本轮未提交 Excel / CSV，未创建 App / DocType，未启动 R6C/R7
- M1-R6C 异常识别与异常说明流程最小实现当前为 COMPLETED；已通过 Codex 审查并 closeout
- M1-FIX-B 已按 Owner 授权创建轻量 `hb_attendance_app`、导入日志和 `海滨考勤工作台`，并使用 Owner 本地真实 Excel 完成导入闭环验证；M1-FIX-B-FIX 已补齐 `导入考勤机导出表` 浏览器入口、中文 `打卡流水` / `考勤结果` 报表、重复导入可读日志和默认白班/行政班 08:30-17:30；M1-FIX-B4 已收敛桌面入口、Workspace Sidebar、导入页归属和 HBOS / HRMS 入口口径；M1-FIX-B5 已核查真实 Employee / Checkin / Attendance / 月度暂存链路，并收敛 HBOS 报表和 HRMS 技术核查入口；真实 Excel、真实员工清单和导入产物不提交 Git
- M2-R1 已按 Owner 授权创建 `hb_lims_app`（实验室信息管理系统板块骨架），已安装到本地 `frontend` site，after_migrate 幂等同步 3 个 LIMS 角色、`海滨LIMS工作台` Workspace、Sidebar 与桌面图标，离线契约测试 8/8 全绿；本轮未创建 DocType / 业务方法（主数据与检验流程为 M2-R2 至 M2-R5）
- M2-R2 主数据与判定引擎、M2-R3 检验流程闭环、M2-R4 COA 与报表已 COMPLETED；M2-R5 验证收口为 REVIEWING（全量演练 19/19、11 项验收、离线测试 109/109）
- M2-R6 Vue 前端原型与开发流程已交付（`docs/frontend/M2_LIMS_Vue前端原型.html` + `docs/frontend/M2_LIMS_Vue前端开发流程.md`），REVIEWING 等待 Owner 审查；未创建 Vue 工程、未接真实 API

M0 阶段用于约束后续规划、执行、审查与验收。当前已完成 Frappe / ERPNext / Docker 最小环境启动验证、Frappe HR / HRMS 安装验证、HRMS 前端资源修复、M1 考勤一期边界设计、HRMS 环境可复现性收口、GitHub Private remote 首次同步、M1-R0 规划诊断收口、M1-R1 对象模型验证记录、M1-R2 配置试运行方案设计、M1-R3 局部试运行记录、M1-R3A 阻断诊断方案、M1-R3B 运行态最小修复方案、M1-R3B-FIX 运行态最小修复执行记录、M1-R3C 原生考勤最小试运行复测记录、M1-R3D 异常口径与 Gap 诊断、M1-R3E 配置复核与业务口径确认表、M1-R3F 业务口径确认包、M1 需求设计四份文档、M1-R4 Demo 技术方案与实施路线拆分、M1-R5 HRMS 配置基线、考勤工作台与月度汇总 Demo、M1-R6A Gate 判定和 M1-R6B 脱敏打卡流水导入最小验证；M1 仍未进入完整考勤业务开发。

## 仓库定位

当前仓库用于承载 M0 工程启动文档、AI 协作规则、里程碑状态、阅读指南、计划文档、架构决策记录、最小 Docker 环境配置和经 Owner 授权创建的自定义 Frappe App。

当前已包含 `apps/hb_attendance_app`（考勤导入入口、导入日志和 M1-FIX 必需扩展，不代表启动大而全 HR App）与 `apps/hb_lims_app`（M2-LIMS 实验室信息管理系统板块，MVP 覆盖样品管理、质量标准、检验流程与 COA 报告，演示数据一律 `TEST-HBOS-M2-*` 前缀）。

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

当前 M1-FIX 仍处于功能补漏阶段，M2-LIMS 已按 Owner 授权启动。继续禁止：

- 未经 Owner 明确授权，不创建新的自定义 Frappe App（已授权：`hb_attendance_app`、`hb_lims_app`）
- 不创建 `hb_core_app`、`hb_feishu_app`
- 不把 `hb_attendance_app` 扩大为大而全 HR App
- 不把 `hb_lims_app` 扩大为 M2-LIMS MVP 之外的模块（仪器集成、环测、微生物、试剂、OOS 调查等另行规划）。**例外（已授权）**：留样板块 M2-R7 已按 Owner 2026-09-04 授权纳入范围，R7 子轮按 Owner 授权推进（R7A 与 R7D 前端已落地，R7B/C 后端已实现并真实验证、前端已真实接入）；稳定性板块 M2-R8 已按 Owner 2026-09-15 授权纳入范围，R8A~R8J 已按当前里程碑推进；本轮 R8J 测试路径修复已按 Owner 2026-09-21 授权同步生产
- 不把 HRMS 安装验证等同于考勤业务开发完成
- 不提交真实 `.env` 或真实密钥
- 不提交备份文件、数据库、Docker volume 或运行时数据
- 不开发业务
- 不接飞书真实写入
- 不在原型审查通过前实现前端驾驶舱
- 不浏览或搬运大量 Obsidian 长文
- 不执行 `docker compose down -v`
- 不删除 volume
- 不重建 `frontend` site

**独立前端开发规则**：凡涉及独立前端、驾驶舱、AI 工作台、复杂交互页面，必须先完成原型设计/视觉方案，经 Owner 人工审查通过后再进行前端复刻开发，最后接入真实页面功能和数据。详见 `docs/frontend/FRONTEND_IMPLEMENTATION_GUIDE.md`。

后续路线只记录，不代表已启动：

1. M1-R3C 已通过 Codex 审查并收口，试运行完成但业务闭环未完成。
2. M1-R3D 已通过 Codex 审查并收口，Gap 已四类分类，均不需要立即创建 App。
3. M1-R3E 已通过 Codex 审查并收口，配置复核清单与业务口径确认表已交付。
4. M1-R3F 已通过 Codex 审查并收口，业务口径确认包已交付。
5. M1-REQ-DESIGN-DRAFT 已通过 Codex 审查并收口，需求设计四份文档全部完成。
6. M1-R4 已通过 Codex 审查并收口为 COMPLETED；M1-R4 定位为 Demo 技术方案与实施路线拆分，后续 R5/R6/R7 按递进拆分。
7. M1-R5 已通过 Codex 审查并收口为 COMPLETED；本轮定位为 HRMS 配置基线、考勤工作台与月度汇总 Demo，未启动 R6/R7。
8. M1-R6A 已通过 Codex 审查并收口为 COMPLETED；本轮定位为 Excel 导入与异常流程落地方案 / Gate 判定，已 closeout。
9. M1-R6B 已通过 Codex 审查并收口为 COMPLETED；M1-R6C 为 COMPLETED。M1-R7 已通过 Codex 审查并 closeout 为 COMPLETED。
10. M1-FIX-B 已完成 Excel 导入与真实本地数据闭环实现，M1-FIX-B-FIX 已补齐浏览器导入与中文体验修复，M1-FIX-B2 为 COMPLETED，M1-FIX-B3 为 REVIEWING / Owner UI 验收未通过，M1-FIX-B4 为 REVIEWING / Claude PASS 但数据链路验收发现后续问题，M1-FIX-B5 为 REVIEWING。
11. M2-LIMS 已启动：M2-R1 至 M2-R4（环境与骨架、主数据与判定引擎、检验流程闭环、COA 与报表）COMPLETED；M2-R5 验证收口 REVIEWING；M2-R6 Vue 前端原型与开发流程 REVIEWING（待 Owner 审查，审查通过后才进入 Vue 工程初始化与页面复刻）。
M2-R6A 样品登记动态表单设计 REVIEWING（随 M2-R6 并行审查）。
M2-R6B 检验结果台账双模式设计 REVIEWING（Owner 已确认原型与交互，设计文档待审查）。
M2-R6C 检验结果台账 Vue 复刻与生产部署 DEPLOYED（双模式已上线生产）。
M2-R7D 留样板块前端 Vue 复刻与生产部署 DEPLOYED：留样方案 rev6 口径定稿（Owner 2026-09-07 已确认角色方案 B+SoD、分支策略 b，m2-r6 为 M2 延伸工作线）；R7A（主数据与留样登记 3 DocType + retention_service + 前端两页）已在 m2-r6 交付并测试路径验证；按设计稿在 `m2-r6` Vue 工程落地 6 视图留样板块（工作台/登记台账/产品/观察/使用/处理），工作台/观察/使用/处理 4 视图已切换真实后端接入，登记台账/产品沿用 R7A API；`vue-tsc` 0 错误、生产构建成功并同步 `/hbos-lims`（备份 【内部备份标识已省略】），Owner 2026-09-08 已确认测试路径。R7B（观察管理）/R7C（使用与处理审批）后端已实现并真实验证。
M2-R8 稳定性管理板块开发方案 REVIEWING **rev15**：Owner 2026-09-15 提供《稳定性管理》规程全套 5 份文件（新版 v9.0 `SOP-LC-1-00-019` 为主，旧版 05 版为差异基线）并授权方案设计；评审两份桌面方案后技术路线 Frappe 原生化。**rev1 审核 FAIL（4 P0 + 6 P1）→ rev2**（Timepoint 提升为独立主 DocType、补 Result/Report 状态机、批准后冻结快照与版本链、电子签名能力边界更正（操作签名 ≠ GMP 合规电子签名）、数据模型全量显式定义、时间单位统一并补计划检测日期/取整/月末/工作日历、显著变化判定配置化、「控制图」改称「趋势图」、新增 Stability Room / Stability Test Item 主数据、角色身份先定后授权限、逾期纯派生 + 延期审批独立动作）；**复审"有条件通过"（5 必修 + 3 补强）→ rev3**（结果版本键 `result_version_key` + `is_current` 生效指针、双延期模型 `HBOS Stability Timepoint Delay`、补全 `HBOS Stability Test Item Form` + 5.8 节 DocType 清单总表、按 DocType 逐一定义的删除拦截 + 子表仅追加、0 月来源 `baseline_doctype`/`baseline_name`、检测日期物理约束与锚定口径、`approve_change_general` 收紧为 QA 线专属、有效期字段拆分，新增 11.3 节 R8A 启动前置门禁）。**三轮复审 → rev4**（0 月免取样口径、时间点生成触发与中间条件、`append_conditions` 闭环、变更实施落点 7.9 节、`ROUND_HALF_UP`）；**四轮复审 FAIL → rev5**（结果生效指针仅在新版批准后同事务切换、统一 `effective_due_date`、新增 `LIMS QA Manager`、6.3 动作矩阵改全转移覆盖表、Timepoint Item 防重复、年度类 Notice 快照链、`append_conditions` 原子化、统一并发锁协议）；**五轮复审"有条件通过" → rev6**（补 `mark_for_disposal`/`cancel_disposal` 使「待处理」可达、入箱超期改强制评估四件套、`append_conditions` 入矩阵、门禁 3 时序校正）；**六轮复审 FAIL → rev7**（结果状态与生效指针冲突修正、期限三层模型与政策硬上限、`record_result` 收紧为 `Timepoint=检测中`、`pre_disposal_status` 快照、`approve_report` 三条硬前置、Report 补 `client`/`seq`/`source_ref`、补全驳回/作废/人日字段、延期历史单一口径，新增 8.6 禁止绕过业务服务与 8.7 违规审计独立持久化）；**七轮复审 FAIL → rev8**（补 `apply_delay`/`reject_delay` 并统一字段名、补 `已批准→已作废` 出口与时间点重开、流水补「受托转出」、Notice 补驳回/取消字段、Report 改 Dynamic Link、8.3 按 DocType 列终止动作、期限审批口径入启动门禁）；**八轮复审 FAIL → rev9**（Timepoint 状态机矛盾消除 + 系统动作 `reopen_timepoint` 登记、重开判定改按必检项目粒度、启动门禁口径统一为 11.3 的 5 项、Report 映射表移位、8.6 措辞更正、台账 R7 版本恢复）；**九轮复审 FAIL → rev10**（`void_result` 行改按必检项目粒度重开、`report_period_key` 纳入 `source_doctype` 消歧并补 `seq` 并发锁、里程碑摘要版本校正）；**十轮复审 FAIL → rev11**（`reopen_timepoint` 补"仅已完成才调用"守卫、延期日期全链校验、8.6 权限隔离更正、`seq` 锁指定产品行、`report_period_key` 改用 `client_code`、`mark_superseded` 语义界定、页脚版本号校正）；**十一轮复审 FAIL（1 P0 结论确认 + 3 P1 + 2 P2 补强）→ rev12**（11.3 门禁维持"5 项未闭环、不得启动 R8A"；`apply_delay`/`approve_delay` 矩阵行补日期链、`reopen_timepoint` 矩阵行补状态守卫、映射规则与唯一性总表 `client` 统一为 `client_code`；`client_code` 定案五条规则、8.6 新增运行期一致性扫描同步 8.1/8.4/门禁 16）；**十二轮复审 FAIL（1 P0 结论确认 + 2 P1 + 1 P2）→ rev13**（11.3 门禁维持"5 项未闭环、不得启动 R8A"；`client_code` 重定案——删名称回退、新增 `customer` Link 且 `client_code` 唯一来源为 `Customer` 文档名；台账修复 AI_CONTEXT/PROJECT_STATUS 旧口径；业务依据统一 v9.0 拟执行依据待生效确认、v8.0 仅作历史差异基线）；**十三轮复审 FAIL（1 P0 结论确认 + 3 P1 + 1 P2）→ rev14 修订（11.3 门禁维持 5 项未闭环；`client_code` 收紧为**始终只读派生** + 硬校验 `client_code == customer.name`、删「带出后可改」；格式约束落 ERPNext `Customer` 主数据命名规范并**删运行时隐式规范化**；`README` 旧待确认口径更正为 11.3-1/2/4/5/7、四份台账补 v9.0 拟执行标注；`report_period_key` 入键成分禁 `#`、非专项报告 `customer`/`client_code`/`seq` 必须为空）；**十四轮复审 FAIL（1 P0 结论确认 + 2 P1 + 2 P2）→ rev15 修订（11.3 门禁维持 5 项未闭环；Customer 编码格式补两层可执行保障——validate 钩子强制校验 + R8A 前存量扫描；「规范化 client_code」旧措辞统一改为 Customer 文档名原值；`client` 展示字段定稿只读派生 `customer.customer_name`；清理文档头重复修订史）**。定案 14 主 + 8 子 DocType（= 22）、8 条状态机、8 项强校验点、ICH Q1E 外推助手，拆 R8A~R8E，并新增跨轮验收门禁 6 类；Owner 已确认两项范围边界（全量 12 模块、稳定性室手工记录纳入本板块）；含 6 项规程疑点与 13 项待确认；**R8A 启动判定以 11.3 节 7 项为准，7 项已于 Owner 2026-09-16 全部闭环**（v9.0 **已正式生效**、角色身份映射采纳 §6.2 + 新增 `LIMS QA Manager`/`LIMS QP`、取样延期 10% 采甲、DocType 采纳 5.8、期限口径 ①需审批 ②委外窗口可留空）。**Owner 2026-09-15 决策两项**：电子签名走路线 ①（操作签名 + 审计追踪，GMP 合规电子签名由平台后续统一专项、各板块统一接入）；R8 工作分支为新建 **`m2-r8`**。**R8A 已启动并完成**（11.3 启动门禁 7/7 已闭环，见上方 M2-R8A 条目）；R8B~R8E 待逐轮启动。主文档 `docs/milestones/M2_R8_稳定性管理板块开发方案.md`。

## AI 协作方式

- ChatGPT：负责规划、拆解、上下文整理与方案边界确认
- Claude：负责按计划执行文档或代码变更
- Codex：负责工程审查、边界检查、验证与交付复核
- 用户：负责最终验收、取舍确认与里程碑放行

每轮任务开始前，AI 必须说明本轮读取了哪些文档。默认只读 `CLAUDE.md`、`AGENTS.md`、`docs/AI_CONTEXT.md`、`docs/PROJECT_STATUS.md`、`docs/CURRENT_MILESTONE.md`，禁止默认递归读取整个 `docs/`。
