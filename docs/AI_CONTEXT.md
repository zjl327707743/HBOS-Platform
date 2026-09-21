# AI Context

项目名称：新乡海滨智能运营管理平台。

## 架构定案

准确叫法：Frappe/ERPNext 开源底座 + Frappe 多 App 模块化架构 + 外部独立服务扩展。

长期架构包括：

- Frappe/ERPNext 开源底座
- 海滨自定义 Frappe App
- 外部 AI/视频/算法服务
- Vue/React 驾驶舱
- 飞书集成
- Docker 部署

主技术栈：Frappe Framework、ERPNext、Frappe HR、Python、JavaScript、MariaDB/MySQL 兼容体系、Redis、Docker、Docker Compose、Vue/React、ECharts、FastAPI。

## 当前上下文

当前阶段：M0 工程启动与上下文治理已完成并封板；M1 产品交付仍在 M1-FIX 功能补漏中，尚未完成。M1-FIX-B2 已 COMPLETED；M1-FIX-B3 为 REVIEWING / Owner UI 验收未通过；M1-FIX-B4 为 REVIEWING / Claude PASS，但 Owner 数据链路验收发现后续问题；当前 M1-FIX-B5 已进入 REVIEWING，用于核查导入数据链路并收敛 HBOS 报表、月度汇总暂存和 HRMS 原生技术核查口径。

当前目标：M1-FIX-B5 为 REVIEWING，等待 Owner 和 Claude 审查。M1-FIX-B3 / B4 不 closeout。M1 产品交付仍未完成，M1-FIX-C/D/E 未启动。M2 未启动 / 待 Owner 授权。

当前已在用户授权范围内安装 HRMS，并完成 Frappe HR 图标、基础 HR 模块和 Roster 页面的前端资源修复验证。M0-R3E HRMS 环境可复现性收口已完成并通过 Codex 审查，M0 整体状态为 COMPLETED。

M0-REMOTE 已完成 GitHub Private remote 创建、`origin` 绑定和 `main` 首次 push。M1-R0 已完成方案和诊断并通过 Codex 独立审查；M1-R1 已完成只读对象模型验证记录，并已通过 Codex 独立审查，状态为 COMPLETED。M1-R2 已完成配置试运行方案设计，并已通过 Codex 独立审查，状态为 COMPLETED。M1-R3 已创建部分 `TEST-HBOS-M1R3-` 虚构测试数据；Codex 审查 PASS 后，M1-R3 最终状态收口为 BLOCKED。M1-R3A 已通过 Codex 审查并收口为 COMPLETED。M1-R3B 已通过 Codex 审查并收口为 COMPLETED。M1-R3B-FIX 已通过 Codex 审查并收口为 COMPLETED。M1-R3C 已新增 `TEST-HBOS-M1R3C-*` 虚构 TEST 数据；M1-R3C 已通过 Codex 审查并收口为 COMPLETED，结论为 PARTIAL / GAP_IDENTIFIED。M1-R3D 已通过 Codex 审查并收口为 COMPLETED。M1-R3E 已通过 Codex 审查并收口为 COMPLETED。M1-R3F 已通过 Codex 审查并收口为 COMPLETED。M1-REQ-DESIGN-DRAFT 为 COMPLETED。M1-R4 为 COMPLETED，已通过 Codex 审查并收口。M1-R5 为 COMPLETED，已通过 Codex 审查并收口。M1-R6A 已通过 Codex 审查并收口为 COMPLETED。M1-R6B 为 COMPLETED。M1-R6C 为 COMPLETED（已通过 Codex 审查并 closeout）。M1-R7 为 COMPLETED（已通过 Codex 审查并 closeout）。M1 历史 closeout 已完成，但 Owner UI 验收发现产品功能缺口，因此当前 M1 产品交付仍处于 M1-FIX IN_PROGRESS。M1-FIX-B 已创建轻量 `hb_attendance_app`、导入日志和 `海滨考勤工作台`，并使用 Owner 本地真实 Excel 完成导入闭环验证；M1-FIX-B-FIX 已补齐页面导入与中文体验；M1-FIX-B4 已收敛运行态入口主线；M1-FIX-B5 已核查真实 Employee / Employee Checkin / Attendance / 月度暂存数据链路，新增月度汇总暂存报表并增强 HBOS 报表过滤；真实 Excel、真实员工清单和导入产物不提交 Git。M2 未启动。M3 仓储库存数字化管理已由 Owner 授权新开，与 M1-FIX 并列，不替代、不阻塞 M1-FIX；M3-R0 至 M3-R5 均已交付并进入 REVIEWING（M3-R2 至 M3-R5 已执行完毕），M3-R6 已开工（IN_PROGRESS）、M3-R7 为 PLANNED / 待 Owner 逐轮授权。M3-R4 已实现按批次自动生成待检证与自产/外购两种货位卡（三个 Print Format）；M3-R5 已实现货位二维码与手机扫码页（展示全部字段、不脱敏，需登录）；M3-R6 拍照识别服务的服务端骨架、约束校验层、Frappe 侧入口与人工校对界面均已交付，**真实跨进程端到端已验证通过**；**真实样本准确率与耗时均已实测达标**（50 张 / 250 字段；选用 PaddleOCR `small` 档：全字段 80%、单张均 8.1 s（7~9 s）；accuracy 与 ≤10 s 均达标；换档免装依赖。**分档实测（2026-09-21）**：大字/5 个结构化字段全字段 `small` 80% / `medium` 84%，小字（16 个模板恒定串 × 50 张）整串命中 `small` **83.5%** / `medium` 85.2%（串越长字越小命中越低，运输注意事项整句仅 25/50），**手写档无真值、给不出准确率**——姓名 50 张无一读出；换 `medium` 每提 1 个点付 4 倍耗时，维持 `small`。置信度两项因 C2 无逐字段置信度仍**无法测量**；**外购标签零覆盖**）。**再次启动常驻服务须单独授权。**M3-R6 第五批把「入库提交 → 自动生成待检证 + 货位卡」接上（`hbos_inventory/doc_gen.py` 挂 `Stock Entry.on_submit`，失败不阻断入库），并顺带发现并修复 M3-R4/R5 的打印纸型缺陷（`@page size` 被 wkhtmltopdf 忽略 → 三个格式手动打印全按 A4 出 + 小标签溢出多页）。**第六批**收尾：手动打印路径**全量 224 个货位标签验证**（全部 1 页 60×40mm）、四个格式纸型确认无回归；并把 `create_intake_draft` 的物料检查从「存不存在」加固为「能不能用」（**未停用 / `is_stock_item` / `has_batch_no`**，缺什么说什么）——物料存在但没勾批次管理时，原先会炸在 ERPNext 的英文报错上。**物料建档清单见 R6 主文档第九之七节。****第七批按 Owner 提供的样本批量建档**：扫描三个样本目录 312 个文件，抽出并建成 **128 个物料**；顺带修掉 M3-R2 的分类树缺陷（5 个节点当初误建为分组节点，物料放不进去）；**37 个文件上的 19 个物料无代码**（代码栏印 `/`），须由 SAP 分配。**第八批**让拍照识别页可**手工补录 OCR 读不到的字段**（储存条件 / 生产车间 / 效期类型 / 供货单位 / 生产单位 / 原厂批号 / 包装构成），全部流进待检证与货位卡；物料级三项**写回主数据但仅补空**。新增 `Batch.hbos_supplier_name`（标准 `Batch.supplier` 是只读 Supplier 链接，不能塞自由文本）。M3-R2 已新建并安装 `hb_inventory_app`，落地 10 个 UOM、六车间 8 个库位、5 个产品分类树节点、Item 5 + Batch 7 自定义字段、包装构成子表 `HBOS Packaging Detail`、2 个报表，并把货位树改挂到 `3904`。**Owner 已授权创建 `hb_inventory_app`，该 App 已于 M3-R2 创建并安装**；Owner 亦已授权修改 `docker-compose.yml` 为它补挂载（8 个服务）。`hb_core_app`、`hb_feishu_app` 仍未授权创建。M3-R1 已建立 203 个货位的 `Warehouse` 树（212 节点，层分布 39/39/39/43/43 校验通过），并通过"按批号查货位"双向粒度验证；同时更正了 M3-R0 的结论——**v16 中批次数据在 `Serial and Batch Entry`，`SLE.batch_no` 为空列不可用**。货位建模为**方案 A（`Warehouse` = 货位）** + **方案 A1（层作为 `Warehouse` 树一级）**，存放模式为**固定货位 + 随机存放**，试点范围**只做 16 号楼产品库**；已由 Owner 授权安装 `lark-cli` 并只读拉取两篇飞书参考文档与附件。当前不接飞书真实写入，不实现 SSO，不做前端驾驶舱，除非用户明确授权对应轮次。

## AI 默认读取规则

默认只读以下文件：

- `CLAUDE.md`
- `AGENTS.md`
- `docs/AI_CONTEXT.md`
- `docs/PROJECT_STATUS.md`
- `docs/CURRENT_MILESTONE.md`

禁止默认递归读取整个 `docs/`。

默认不读取：

- `docs/archive`
- `docs/research`
- `docs/legacy`

每轮任务开始前，必须说明本轮读取了哪些文档。

只有任务明确涉及当前里程碑时，才读取：

- `docs/plans/m0_engineering_bootstrap.md`

只有架构决策变更时，才读取：

- `docs/adr/`

## Skill 路由

本项目通过 `docs/AI技能路由规范.md` 管理不同任务类型对应的 AI skill 使用规则。

当前已确认拥有 / 可用的 skill：

- `superpowers`
- `frontend-design`
- `lark-cli`（飞书官方 CLI 工具，不是统一总 skill）
- `lark-shared`（飞书官方共享基础 skill）
- `lark-*` 官方领域 skills（详见 `docs/AI技能路由规范.md`）

未安装 skill 只能进入候选池，不得直接调用。任何 Agent 在执行开发、审查、前端设计、集成、文档维护前，必须先根据该文件判断本轮应使用的 skill。

## 提交与文档命名

本项目后续 Git 提交描述优先使用中文。可以保留 `docs`、`fix`、`feat`、`chore` 等 conventional commit 前缀，但冒号后的描述应使用中文。

新增文档名称优先使用中文或中英混合命名。技术专有名词可以保留英文，例如 Frappe、Docker、ERPNext、FastAPI、API、Skill。

Skill 路由规范文件为：

- `docs/AI技能路由规范.md`

## 后续路线

后续路线只记录，不代表已启动：

1. M1-R5 已通过 Codex 审查并收口为 COMPLETED，已交付 HRMS 配置基线、考勤工作台入口、月度汇总 Demo 和 Excel 月报导出路径。
2. M1 历史 closeout 已完成，但产品交付仍在 M1-FIX 中，尚未完成。M1-FIX-B3 为 REVIEWING / Owner UI 验收未通过；M1-FIX-B4 为 REVIEWING / Claude PASS，但 Owner 数据链路验收发现后续问题；M1-FIX-B5 为 REVIEWING。M2 未启动 / 待 Owner 授权。
3. M3 仓储库存数字化管理已由 Owner 授权新开，与 M1-FIX 并列。M3-R0 至 M3-R5 均为 REVIEWING（M3-R2 至 M3-R5 已执行完毕）；M3-R6 为 IN_PROGRESS（真实端到端已验证；**准确率与耗时均已实测达标**）；M3-R7 为 PLANNED / 待 Owner 逐轮授权。M3 优先复用 ERPNext 原生 `Stock` 模块，不重写已有功能。Owner 已授权创建 `hb_inventory_app`，并已提供产品主数据口径：物料代码 8 位、SAP 按前四位分大类（1000 原料药 / 1100 包材 / 120x 辅助用品 / 1300 中间体 / 1400 成品）；六车间 8 个库位需一并建入 `Warehouse`；计量单位按实际建 11 种；盘点按库级三对账（ERP数量 / 货位卡数量 / 实物数量）。

## 前端实施流程规范

独立前端（Vue/React 驾驶舱、AI 工作台、复杂交互页面）开发必须遵循"原型先行 + Owner 审查 + 复刻实现 + 功能接入"流程。详见：

- `docs/frontend/FRONTEND_IMPLEMENTATION_GUIDE.md`

核心规则：凡涉及漂亮页面、驾驶舱、AI 工作台、复杂交互页面，必须先使用 `frontend-design` skill 产出原型/视觉方案，Owner 人工审查通过后再进入前端复刻和功能接入。Frappe Desk 后台页面不要强行重做成独立前端。

## 边界提醒

不直接修改 Frappe / ERPNext / HRMS 核心源码。优先使用原生配置、角色权限、DocType、报表、导入、API 和低代码定制。自定义 App 只用于海滨特有规则，不用于重写 HRMS 已有功能。`hb_attendance_app` 已在 M1-FIX-B 经 Owner 授权创建，后续不得擅自扩大为大而全 HR App。任何飞书真实写入必须由用户明确授权。

任何海滨自定义 App 生成、业务模型实现、真实业务数据配置、飞书真实写入、前端驾驶舱、AI 视频服务实现，以及 Docker volume 删除、site 重建或环境重构，都属于后续轮次或后续明确授权范围。M3 仓储库存同样按此规则执行：不得默认启动 M3-R1 及之后轮次，不得默认创建自定义 App 或 DocType，不得默认启动外部 FastAPI 服务或独立前端，须逐轮由 Owner 明确授权。
