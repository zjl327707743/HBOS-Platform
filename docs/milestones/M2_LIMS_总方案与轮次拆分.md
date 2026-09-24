# M2-LIMS：实验室信息管理系统板块总方案与轮次拆分

项目名称：新乡海滨智能运营管理平台。

## 定位

M2-LIMS 在 HBOS 平台（Frappe 底座）上新增实验室信息管理系统（LIMS）板块，以《海滨药业LIMS系统开发方案》（12 模块、ALCOA+、GMP 合规）为业务口径，参考开源 SENAITE LIMS 的功能结构（仅业务模型参考，不搬代码），自定义 Frappe App `hb_lims_app` 承载。

## 已确认决策（Owner 批准）

| 决策点 | 结论 |
| --- | --- |
| 第一版范围 | **核心闭环 MVP**：样品管理 + 质量标准 + 检验流程 + COA 报告 |
| 里程碑归属 | 新建 M2-LIMS 里程碑；M1-FIX 为并行未决事项 |
| App 命名 | `hb_lims_app`（业务模块包 `hbos_lims`，对齐模块名 "HBOS LIMS" 的 Frappe 包名约定） |
| 验证方式 | 安装到本地 `frontend` site，虚构 `TEST-HBOS-M2-*` 数据走通闭环 |

## 技术路线

- Frappe 16 / ERPNext 16 / MariaDB / Redis / Docker（HBOS 既有底座），Desk `http://localhost:8080`。
- 业务承载全部使用 Frappe 原生扩展机制：DocType、状态字段 + whitelist 方法 + validate 钩子、Role、Workspace / Sidebar / Desktop Icon、Script Report、Print Format。
- 不修改 Frappe / ERPNext / HRMS 核心源码。

## 数据模型（13 个 DocType = 10 主 + 3 子表）

主数据层（5 主 + 1 子表）：HBOS Sample Type / HBOS Lab Department / HBOS Test Item / HBOS Calculation / HBOS Specification(+Item)。

事务层（5 主 + 2 子表）：HBOS Sample(+Item) → HBOS Sample Task → HBOS Test Result → HBOS Result Revision → HBOS COA(+Item)。

命名系列：Sample=`HBOS-SMP-.YYYY.-#####`、Task=`HBOS-TSK-`、Result=`HBOS-TR-`、Revision=`HBOS-REV-`、COA=`HBOS-COA-`；主数据 `field:xx_code`。

## 关键技术决策

| 决策点 | 方案 | 理由 |
| --- | --- | --- |
| 状态机 | 状态字段 + whitelist 方法 + validate 钩子 + Role 权限（不用 Frappe Workflow） | 复核人不可改原始数据需字段级锁定；电子签名（检验人 / 复核人 / 批准人）需字段化 |
| 审计追踪 | HBOS Result Revision 修订表（不改原始行，修改原因必填） | 满足 ALCOA Original + Accurate |
| 电子签名 | 字段签名（用户 + 时间戳 + 含义串） | MVP 流程语义；国密 SM2 / CA 验签留远期 |
| COA 生成 | Print Format（HTML）+ PDF 导出 + whitelist 发布 | Frappe 原生中文 PDF、附件归档 |
| 业务分层 | result_contract.py / workflow_contract.py 零 frappe 依赖 + lims_service.py whitelist 层 | 离线单测、显式事务 |

## 轮次拆分

| 轮次 | 名称 | 交付物 | 状态 |
| --- | --- | --- | --- |
| M2-R1 | 环境与骨架 | M2_START_GATE / 总方案、docker-compose 挂载、hb_lims_app 骨架、after_migrate 幂等同步（3 Role + Workspace + Sidebar + Desktop Icon）、安装验证、测试脚手架 | COMPLETED |
| M2-R2 | 主数据与判定引擎 | 6 个主数据 DocType JSON、result_contract.py + 测试全绿、spec 生效校验 | COMPLETED |
| M2-R3 | 检验流程闭环 | Sample / Task / Result / Revision、workflow_contract、lims_service 全链、待检任务看板、虚构数据闭环 | COMPLETED |
| M2-R4 | COA 与报表 | COA(+Item) + Print Format + 发布链路、4 个报表 | COMPLETED |
| M2-R5 | 验证收口 | 全量演练 + 验收、入口可见、台账更新、closeout | REVIEWING |
| M2-R6 | Vue 前端原型与开发流程 | 交互式 HTML 原型（7 视图）+ 开发流程文档 + Vue 3 技术栈与 API 契约映射；原型 REVIEWING 待 Owner 审查 | REVIEWING |
| M2-R6A | 样品登记动态表单设计 | 固定样品类型 / 检验优先级决策条 + 9 类样品类型模板驱动表单；方案文档与原型交互 REVIEWING 待 Owner 审查 | REVIEWING |
| M2-R7 | 留样管理板块开发方案 | 以《留样管理规程》v09 为业务依据的完整开发方案（5 主 + 1 子 DocType、三状态机、审计复用 R6D、R7A~D 四子轮拆分）；Owner 已授权，方案 REVIEWING rev6（终审修订完成）；角色方案 B 与分支策略 b 已 Owner 2026-09-07 确认，余 6 项按节拍推进 | REVIEWING |

## 后续轮次（MVP 之外，仅规划）

仪器集成、稳定性、环境监测、试剂与标准品、微生物、OOS/OOT 完整调查流程、审计追踪通用引擎、国密电子签名——均在 M2-LIMS MVP 收口后另行规划，不自动启动。**留样管理（M2-R7）已按 Owner 2026-09-04 授权启动**：方案见 `docs/milestones/M2_R7_留样管理板块开发方案.md`（REVIEWING rev6，终审修订完成；角色方案 B 与分支策略 b 已 Owner 确认），R7A~D 子轮须方案审查通过后逐轮启动，R7A 启动待 Owner 指令。

## 验证与验收（M2-R5 全量）

1. 13 个 DocType 可访问、中文 label 正常。
2. 闭环：登记 → 任务生成 → 分配 → 开始 → 提交（自动判定）→ 复核 → 批准 → COA 创建 / 审核 / 发布（PDF）。
3. 判定引擎边界用例（含上下限临界值）通过。
4. 复核人修改已提交结果被系统拒绝。
5. 修订产生 Revision 且原记录不可变（superseded 链）。
6. COA PDF 可下载、含中文与签名栏。
7. 5 个报表筛选与中文列正确。
8. 工作台 / 桌面图标 / Sidebar 在浏览器可见。
9. 离线单测全绿。
10. 无真实数据入库，`TEST-HBOS-M2-*` 前缀可识别。
11. Git 无 `.env` / 密钥 / Excel / CSV / 数据库产物提交。

## 每轮收尾强制

更新 `docs/PROJECT_STATUS.md`、`docs/CURRENT_MILESTONE.md`、`docs/milestones/README.md`、本轮主文档；检查公共入口文件（README / CLAUDE / AGENTS / AI_CONTEXT / READING_GUIDE）是否存在过期描述；禁止把"计划可行"写成"功能已实现"。
