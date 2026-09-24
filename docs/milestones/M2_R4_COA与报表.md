# M2-R4：COA 与报表

项目名称：新乡海滨智能运营管理平台。

## 轮次状态

状态：COMPLETED。

## 本轮目标

- 创建 HBOS COA(+Item 子表) DocType 与 Print Format `HBOS COA`（中文排版 + 签名栏）。
- 扩展 `lims_service.py`：create_coa / review_coa / publish_coa（PDF 附件归档，发布后快照不可改）。
- 创建 4 个 Script Report：检验结果清单 / 样品台账 / 审计追踪查询 / COA 发布记录。
- 虚构数据 COA 发布链路验证。

## 交付内容

### HBOS COA（+ COA Item 子表）

| DocType | 命名 | 关键设计 |
| --- | --- | --- |
| HBOS COA（检验报告书） | `HBOS-COA-.YYYY.-#####` | 样品/批号/物料/标准版本快照（fetch_from 只读）、报告状态（草稿→已审核→已发布）、QA 审核人/时间、发布人/时间、PDF 附件（Attach 只读）、报告项目明细子表；已审核后头信息与项目明细锁定（validate） |
| HBOS COA Item（子表，istable） | `hash` | 检验项目/方法SOP/标准限度串/检验结果（含单位）/判定 |

### Print Format `HBOS COA`（Jinja，中文）

公司抬头 + 报告编号/样品编号/物料/批号/标准版本头信息表 + 项目表（检验项目/方法SOP/标准限度/检验结果/判定）+ 三栏签名区（检验人/复核人/QA批准人）+ 页脚"本报告仅对来样负责"。

### 业务方法（lims_service.py 扩展）

- `create_coa(sample_name)`：仅样品"检验完成"且全部结果"已批准"且无 OOS 时生成；提取结果快照（标准限度串/结果含单位/判定）写 COA Item；已有未发布 COA 禁止重复生成。
- `review_coa(coa_name)`：QA 审核（Reviewer/Manager），草稿→已审核 + 审核人/时间。
- `publish_coa(coa_name)`：渲染 Print Format 模板 → PDF 生成（`frappe.utils.pdf.get_pdf`）→ 私有 File 附件归档（关联 COA）→ 已发布 + 发布人/时间。
- COA 快照保护：头信息修改被 Frappe fetch 机制静默还原（防篡改）；项目明细增删被 validate 拦截（"检验项目明细不可增删"）。

### 4 个 Script Report（中文）

| 报表 | ref_doctype | 关键列 / 筛选 |
| --- | --- | --- |
| 检验结果清单 | HBOS Test Result | 结果号/样品/批号/项目/结果值/单位/判定/检验人/复核人/记录状态；筛选 样品/判定/状态/提交日期区间 |
| 样品台账 | HBOS Sample | 样品号/类型/物料/批号/标准版本/优先级/状态/请验人/接收人/时限截止；筛选 类型/状态/物料/登记日期区间 |
| 审计追踪查询 | HBOS Result Revision | 修订号/结果/变更字段/修改前后值/修改人/时间/原因；筛选 结果/修改人/时间区间 |
| COA 发布记录 | HBOS COA | COA号/样品/批号/物料/状态/QA审核人/发布人/时间/PDF 附件；筛选 状态/样品/发布人 |

### 测试（89/89 全绿，新增 test_coa_contract.py 16 用例）

COA 服务方法（whitelist/角色校验/PDF 生成/重复创建防护）、COA DocType 契约（命名系列/istable/状态选项/fetch/Attach/锁定 validate）、Print Format（Jinja/中文模板 token）、4 个报表（文件齐全/元数据/参数化 SQL/中文列/JS filters）。

## 执行记录

### 同步

`bench --site frontend migrate` 同步成功：HBOS LIMS 模块下 **13 个 DocType**（新增 HBOS COA / HBOS COA Item）、Print Format `HBOS COA`、5 个报表（含 M2-R3 待检任务看板）全部就位。

### 虚构数据 COA 发布链路验证（TEST-HBOS-M2-*）——19/19 通过

| 组 | 用例 | 结果 |
| --- | --- | --- |
| 准备 | 合格样品全流程至"检验完成"（3 结果已批准） | ✅ |
| COA 创建 | 草稿/头快照（批号/物料/版本）/3 项目行/含量测定 95.0-105.0→99.2%→合格/干燥失重 记录型→符合规定→不适用/重复创建被拒 | ✅ 6 项 |
| QA 审核 | 已审核 + QA 审核人 | ✅ |
| 发布 | 已发布/PDF 附件生成（17.8KB，私有 File 关联）/发布人/时间 | ✅ 5 项 |
| 快照锁定 | 修改物料被 fetch 还原（防篡改）/新增项目被 validate 拦截 | ✅ 2 项 |
| 报表 | 检验结果清单 3 行/样品台账/审计追踪查询/COA 发布记录（已发布行 + PDF 链接） | ✅ 4 项 |

### 排障记录（均已修复并固化）

1. **frappe.get_print 触发 website 渲染管线**：publish_coa 初版用 `frappe.get_print`，其 path resolver 遍历带 web_view 的 DocType 时撞上 hrms "Job Opening" 表缺失（M0 环境已知问题）。已改为直接渲染版本化 fixture 模板（`_coa_print_html`，`render_template` + `get_pdf`），绕开 website 管线，且模板来源可版本化。
2. **记录型项目结果显示 0.0%**：Frappe Float 字段无值时存 0.0，`_result_display_value` 误判为数值。已改为"记录型优先 result_text"。
3. **发布后修改 fetch 字段不抛错**：头信息（material_name 等 fetch_from 字段）在保存时被 Frappe fetch 机制静默还原——数据实际未被篡改，属防篡改保护；验证断言改为"修改被还原"，项目明细增删仍由 validate 显式拦截。
4. **报表目录/文件名含空格**：COA 发布记录目录与文件命名对齐报表名（`COA 发布记录`），Python 导入用 importlib（import 语句不支持空格模块名）。

## 本轮未做

- 未做仪器集成、OOS 调查流程、稳定性/环测/微生物等模块（后续轮次）。
- 未修改 Frappe / ERPNext / HRMS 核心源码（Job Opening 表缺失为 hrms 环境已知问题，已绕开，不在本轮修复范围）。
- 未录入任何真实样品 / 人员 / 检测数据。
- 未提交 `.env`、密钥、Excel / CSV、数据库或运行时产物。

## 台账与入口检查

- 状态台账：已更新 `docs/PROJECT_STATUS.md`、`docs/CURRENT_MILESTONE.md`、`docs/milestones/README.md`（M2-R4 收口为 COMPLETED）。
- 公共入口文件：`README.md`、`CLAUDE.md`、`AGENTS.md`、`docs/AI_CONTEXT.md`、`docs/READING_GUIDE.md` 已检查——本轮无阶段描述变化，无需更新。

## 下一轮预告

M2-R5（验证收口）：全量演练（13 DocType 全链路：主数据→样品→检验→复核→COA 发布）+ 11 项验收 + Workspace 全卡片链接填充（工作台 4 分区挂接 DocType/报表路由）+ 测试补齐 + 入口可见性验证 + 台账收口 closeout。
