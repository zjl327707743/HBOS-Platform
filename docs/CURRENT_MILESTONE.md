# Current Milestone

## M2-LIMS：实验室信息管理系统板块（当前里程碑）

项目名称：新乡海滨智能运营管理平台。

M2-LIMS 在 HBOS 平台（Frappe/ERPNext 底座）上新增实验室信息管理系统（LIMS）板块，以《海滨药业LIMS系统开发方案》为业务口径（12 模块），参考开源 SENAITE LIMS 的功能结构（仅业务模型参考，不搬代码），自定义 Frappe App `hb_lims_app` 承载。第一版为核心闭环 MVP：样品管理 + 质量标准 + 检验流程 + COA 报告。

## 当前轮次

M2-R1（环境与骨架）：COMPLETED。`hb_lims_app` 已创建并安装到本地 `frontend` site，after_migrate 幂等同步 3 个 LIMS 角色、`海滨LIMS工作台` Workspace、Sidebar 与桌面图标，离线契约测试 8/8 全绿。主文档 `docs/milestones/M2_R1_环境与骨架.md`。

M2-R2（主数据与判定引擎）：COMPLETED。6 个主数据 DocType 已同步到 frontend site（规格命名 `format:{spec_code}-V{version}` 支持多版本）、`result_contract.py` 判定引擎、规格生效校验；离线测试 40/40 全绿；`TEST-HBOS-M2-*` 虚构主数据验证通过（含多版本/重复拒绝/限度校验/生效查询）。主文档 `docs/milestones/M2_R2_主数据与判定引擎.md`。

M2-R3（检验流程闭环）：COMPLETED。5 个事务 DocType（Sample+Item/Task/Test Result/Result Revision）、状态机、业务方法全链、待检任务看板报表已交付；离线测试 73/73 全绿；虚构数据闭环验证 29/29 通过（合格/OOS/修订/权限/报表）。主文档 `docs/milestones/M2_R3_检验流程闭环.md`。

M2-R3（检验流程闭环）：PLANNED。交付：HBOS Sample(+Item) / Sample Task / Test Result / Result Revision、`workflow_contract.py` 状态机、`lims_service.py` 业务方法全链、待检任务看板报表、虚构数据闭环。

M2-R4（COA 与报表）：COMPLETED。HBOS COA(+Item) + Print Format `HBOS COA` + create_coa / review_coa / publish_coa（PDF 附件归档 + 快照保护）、4 个报表（检验结果清单 / 样品台账 / 审计追踪查询 / COA 发布记录）已交付；离线测试 89/89 全绿；COA 发布链路验证 19/19 通过。主文档 `docs/milestones/M2_R4_COA与报表.md`。

M2-R5（验证收口）：REVIEWING，等待 Owner 和 Claude 审查。全量演练 19/19 通过、11 项验收全部通过、离线测试 105/105 全绿、Workspace 四卡片 13 链接 + 5 快捷入口已落库。审查期间增强：控制面板全面简体中文（Series→编号系列 + zh.csv DocType 名翻译）；侧边导航按业务模块下拉分组（原生 Section Break，样品管理/检验流程/报告管理/质量主数据/审计追踪 5 分组 17 子项）；定位并 workaround Frappe v16.26.3 侧边栏 DocType 项过滤核心 bug（boot_session hook 预置 user_perm_can_read 缓存，不改核心源码）；报表表格列宽拖拽修复（resize-handle 默认 opacity:0 不可见，CSS hover 表头显示手柄恢复原生拖拽与双击自适应，JS 单元格 hover 全文提示）；列表视图列宽拖拽（DocType 列表页 v16 原生不支持，monkey-patch apply_column_widths 注入表头手柄 + localStorage 持久化 + 双击复位，限定 HBOS LIMS 模块）。主文档 `docs/milestones/M2_R5_验证收口.md`。审查通过后 closeout，M2-LIMS MVP 整体收口。

## 并行未决事项（不阻塞 M2-LIMS）

M1 产品交付仍在 M1-FIX 功能补漏中，B3 / B4 / B5 为 REVIEWING，等待 Owner 和 Claude 审查，未 closeout；M1-FIX-C/D/E 为 PLANNED，未启动。M1-FIX 工作线在 `m1-fix-frontend-zh` 分支，M2-LIMS 工作线在 `m2-lims` 分支，互不干扰。

| 轮次 | 名称 | 优先级 | 状态 |
| --- | --- | --- | --- |
| M1-FIX-B3 | 考勤工作台入口、App 命名与 HRMS 数据一致性修复 | P0 | REVIEWING / Owner UI 验收未通过 |
| M1-FIX-B4 | 考勤模块架构收敛与单一入口重整 | P0 | REVIEWING / Claude PASS，Owner 数据链路验收发现后续问题 |
| M1-FIX-B5 | 导入数据链路核查与报表口径收敛 | P0 | REVIEWING |
| M1-FIX-C | 异常说明三级流程 | P1 | PLANNED |
| M1-FIX-D | 考勤工作台 + 月报 + 领导 Demo | P1 | PLANNED |
| M1-FIX-E | 飞书 OAuth 最小验证 + Owner 体验脚本 + 总审查 | P2 | PLANNED |

## 本轮范围（M2-R1，已收口）

- 建立 M2-LIMS 启动门禁与总方案文档。
- 将 `hb_lims_app` 挂载进 Docker Compose 环境（8 处 service + 6 处 PYTHONPATH）。
- 创建 `hb_lims_app` 完整骨架（双层结构 + hooks + config + public logo + after_migrate 幂等同步）。
- 安装到 `frontend` site 并验证入口对象与静态资源可达。
- 搭建离线测试脚手架并跑通。

M2-R1 禁止事项：不创建 DocType；不创建业务方法；不修改 Frappe/ERPNext/HRMS 核心源码；不录入样品 / 人员 / 检测数据；不提交 `.env`、密钥、Excel/CSV、数据库或运行时产物；不执行 `docker compose down -v`；不删除 volume；不重建 `frontend` site。

## M2-LIMS 全阶段禁止事项

- 不创建 `hb_core_app`、`hb_feishu_app` 或其他未授权 App
- 不修改 Frappe/ERPNext/HRMS 核心源码
- 不把 `hb_lims_app` 扩大为 12 模块全量 LIMS（仪器集成、稳定性、环测、微生物、试剂、留样、OOS 调查等另行规划）
- 不做大型 Vue/React 独立前端（须原型先行 + Owner 审查）
- 不接真实仪器、不录入真实样品 / 人员 / 检测数据；演示数据一律 `TEST-HBOS-M2-*` 前缀
- 不提交 `.env`、App Secret、密钥、token、真实数据、Excel/CSV
- 不执行 `docker compose down -v`，不删除 Docker volume，不重建 `frontend` site
- 不把「计划可行」写成「功能已实现」

## 当前状态口径

```
M2-LIMS   = IN_PROGRESS（MVP 交付完成，R5 待审查）
M2-R1     = COMPLETED
M2-R2     = COMPLETED
M2-R3     = COMPLETED
M2-R4     = COMPLETED
M2-R5     = REVIEWING（待 closeout）
M2-R4     = PLANNED
M2-R5     = PLANNED
M1-FIX    = IN_PROGRESS（并行未决，B3/B4/B5 REVIEWING）
M1-FIX-C/D/E = PLANNED / 待 Owner 授权
```

## 下一轮预告

M2-R5 审查 closeout：等待 Owner 浏览器 UI 验收（海滨LIMS 桌面图标 → 工作台 → 样品登记 → 检验全流程 → COA 发布）与 Claude 审查；通过后 M2-LIMS MVP 整体收口为 COMPLETED。M2-LIMS 扩展模块（仪器集成、稳定性、环测、微生物、试剂、留样、OOS 调查、审计追踪通用引擎、国密电子签名）另行规划，不自动启动。

权威状态文件：

- `docs/PROJECT_STATUS.md`
- `docs/CURRENT_MILESTONE.md`
- `docs/milestones/M2_START_GATE.md`
- `docs/milestones/M2_LIMS_总方案与轮次拆分.md`
- `docs/milestones/README.md`

权威方案文件：

- `docs/milestones/M2_LIMS_总方案与轮次拆分.md`
- `/Users/hbzl/Desktop/海滨药业LIMS系统开发方案.md`（私有，不入库，业务口径来源）
