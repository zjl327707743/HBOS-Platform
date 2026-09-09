# M2-LIMS 启动门禁

项目名称：新乡海滨智能运营管理平台。

## 文件定位

本文件记录 M2-LIMS（实验室信息管理系统板块）启动前必须满足的门禁条件，以及 M2-LIMS 的范围边界与并行事项记录。

## 必须满足的前置条件

- M0 状态必须为 COMPLETED（已满足）。
- M1 已 closeout 为 COMPLETED，产品交付仍在 M1-FIX 中（B3 / B4 / B5 为 REVIEWING，未 closeout）——M1-FIX 作为**并行未决事项**记录，不因 M2-LIMS 启动而关闭或合并。
- 当前 Frappe / ERPNext / HRMS 环境可访问：Frappe `16.26.3` / ERPNext `16.26.2` / HRMS `16.14.0`，site=`frontend`，Desk=`http://localhost:8080/login`（`.env` 中 `HTTP_PORT=8080`；`8081` 端口被本机 SENAITE 演示容器占用，勿混淆）。
- 不允许提交 `.env`、备份文件、密钥、数据库、Docker volume 或运行时数据。
- M2 自定义 App 已获 Owner 明确授权：`hb_lims_app`（业务模块包 `hbos_lims`）。

## M2-LIMS 范围

M2-LIMS 是实验室信息管理系统板块（HB LIMS）的开发里程碑，以《海滨药业LIMS系统开发方案》为业务口径（12 模块），参考开源 SENAITE LIMS 的功能结构（仅参考业务模型，不搬代码，遵守 ADR-0004），技术承载为 HBOS 既有 Frappe 底座。

第一版为**核心闭环 MVP**（M2-R2 至 M2-R5 交付）：

- 样品管理：样品登记 / 接收 / 状态流转（草稿 → 已登记 → 检验中 → 检验完成 → 已放行 / 已拒绝 / OOS 锁定）。
- 质量标准：规格 → 检验项目 → 方法 SOP → 限度 → 单位 → 有效位数 → 版本号 → 生效日期；版本控制为复制新版本人工流程。
- 检验流程：任务分配 → 检验执行 → 数据录入 → 自动判定（合格 / 不合格 / OOS 候选）→ 复核（第二人）→ 放行；计算公式（含量 % 内置模板）；结果修改留痕（修订表，修改原因必填）。
- COA 报告：自动提取已批准结果 → Print Format 渲染 → PDF 生成 → QA 审核 → 发布归档。
- 系统管理最小落地：三角色权限（LIMS Manager / LIMS Analyst / LIMS Reviewer）+ 审计追踪查询报表。

## M2-LIMS 不做（本轮及 MVP 边界）

- 不做仪器数据集成（仅预留 `instrument_used` 字段）、稳定性考察、环境监测、试剂与标准品、微生物检验、OOS/OOT 完整调查流程（仅保留触发与锁定接口）。**留样管理（M2-R7）已按 Owner 2026-09-04 授权纳入范围**：R7 子轮按 Owner 授权推进（R7A/R7D 前端已落地，R7B/C 后端已实现并真实验证、前端已真实接入），其余扩展仍另行规划。
- 不创建 `hb_core_app`、不创建 `hb_feishu_app`。
- 不修改 Frappe / ERPNext / HRMS 核心源码。
- 不做大型 Vue / React 独立前端（Frappe Desk 原生页面；独立前端须走原型先行 + Owner 审查流程）。
- 不接真实仪器、不录入真实样品 / 人员 / 检测数据；演示数据一律 `TEST-HBOS-M2-*` 前缀。
- 不执行 `docker compose down -v`，不删除 Docker volume，不重建 `frontend` site。
- 不提交 `.env`、密钥、Excel / CSV、数据库导出或运行时产物。

## 并行事项记录

- M1-FIX-B3 / B4 / B5 为 REVIEWING，等待 Owner 和 Claude 审查；M1-FIX-C/D/E 为 PLANNED，未启动。
- M1-FIX 未决事项不阻塞 M2-LIMS 开发；M2-LIMS 工作线在独立分支 `m2-lims` 上进行，与 M1-FIX 工作线互不干扰。

## Git 工作线

- M2-LIMS MVP（R1~R5）工作在分支 `m2-lims`（自 `m1-fix-frontend-zh` 切出）上进行。
- **M2-LIMS 延伸工作线（Owner 2026-09-07 拍板分支策略 b）**：自 R6C/R6D 起，M2 后续工作（R6 系列 Vue 复刻与生产部署、R7 留样板块及其子轮 R7A~D）在 `m2-r6` 分支上进行，作为 M2-LIMS 的延伸工作线，不回并 `m2-lims`；`m2-lims` 保留为 MVP 历史线。
- 未跟踪文件（`start.sh`、`apps/hb_attendance_app/__init__.py`、`.claude/`）按 M1 既有处理原则，不误提交。
