# LIMS P4-F6-5 COA / 质量标准只读实现记录

状态：**已实现 / 真实 Frappe 集成待环境恢复**
日期：2026-09-30
范围：`frontend/hbos-portal-web` 与 LIMS Portal Provider 只读投影

## 1. 交付内容

- 新增稳定路由：
  - `/hbos/lims/coa`：检验报告（COA）清单与明细抽屉；
  - `/hbos/lims/specifications`：质量标准版本清单与检验项目明细抽屉。
- 新增 Portal API：
  - `hbos_portal.api.coa.get_coas`；
  - `hbos_portal.api.specifications.get_specifications`。
- 新增 LIMS Provider projection：
  - COA 报告状态、样品、批号、物料、标准版本、QA 审核 / 发布签署链、报告项目快照；
  - 质量标准编号、物料、版本、依据、生效日期、储存条件、留样量、状态和项目限度。
- 新增 `coa` / `specifications` capability，并接入桌面侧栏、移动抽屉与路由守卫。
- 视图只开放查看、筛选、刷新和分页；不在 Portal 暴露创建、审核、发布、修订、生效、废止或删除按钮。

## 2. 权限与数据边界

- 清单读取使用 Frappe `get_list` 的当前会话权限过滤；详情先确认当前账号可见，再投影文档和子表。
- Portal 不直接访问数据库，不复制 COA / 质量标准业务规则，不重新计算检验判定或限度。
- COA 发布、质量标准维护和状态迁移继续由现有 LIMS 领域服务 / 管理端负责。
- `lims.audit.read` 仍只用于合规审计入口；COA 和质量标准属于普通 `lims.read` 只读能力，不扩大写权限。

## 3. 中文与实验室使用习惯

- 页面按钮和筛选器采用中文；`COA`、`SOP`、`PDF` 等保留为必要专业名词。
- COA 清单按报告号 / 样品、物料 / 批号、标准版本、QA 审核状态组织；明细先显示样品上下文，再显示报告项目快照。
- 质量标准清单按标准编号、物料、版本、生效日期与状态组织；明细直接展示检验项目、方法 / SOP、限度模式、限度和单位。
- 桌面表格与移动端抽屉均支持加载、空态、错误态和筛选后的安全反馈。

## 4. 验证

- `PYTHONPATH=.. python3 -m pytest -q ...`：**158 passed, 1 skipped**；
- `npm run build`：通过；Vite 仅保留已有大包体积提示；
- `bash scripts/portal/lims_shell_contract.sh`：`LIMS SHELL CONTRACT PASS`；
- `git diff --check`：应在收尾时通过；
- Docker / Frappe 运行环境当前不可用，尚未执行真实会话、真实角色、真实分页和深链回归。

## 5. 后续

下一项进入留样工作台的领域契约核验；COA 与质量标准的真实 Frappe 会话验证应在运行环境恢复后补做，不能用 Mock 结果替代。
