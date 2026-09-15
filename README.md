# 新乡海滨智能运营管理平台

新乡海滨智能运营管理平台面向企业级智能运营管理，长期目标是在 Frappe/ERPNext 开源底座上建设海滨自定义业务 App、外部 AI/视频/算法服务、Vue/React 驾驶舱、飞书集成与 Docker 部署体系。

准确架构叫法：Frappe/ERPNext 开源底座 + Frappe 多 App 模块化架构 + 外部独立服务扩展。

## 当前阶段

当前 M0 已完成并封板。M1 产品交付仍在 M1-FIX 功能补漏中，尚未完成；当前轮次为 M1-FIX-B5（REVIEWING）：正在核查导入数据链路并收敛 HBOS 报表、月度汇总暂存和 HRMS 原生技术核查口径。M1-FIX-B2 为 COMPLETED；M1-FIX-B3 为 REVIEWING / Owner UI 验收未通过；M1-FIX-B4 为 REVIEWING / Claude PASS，但 Owner 数据链路验收发现后续问题；M1-FIX-C/D/E 和 M2 未启动。

M3 仓储库存数字化管理已由 Owner 授权新开，与 M1-FIX 并列。当前轮次为 M3-R6（IN_PROGRESS，已开工）：入库拍照识别服务——**照片不出内网，走本地部署**，暂部署在这台 Mac；服务端骨架、约束校验层、Frappe 侧入口与人工校对界面均已交付，**真实跨进程端到端已验证通过**；M3-R5 已执行完毕（REVIEWING）：货位二维码标签与手机扫码页（展示全部字段、不脱敏）；M3-R4 已实现待检证与自产/外购货位卡自动生成；M3-R3 已交付出库放行门禁、货位变更、`效期预警` 与 `库级盘点三对账` 报表、`仓储库存工作台` 入口；M3-R2 已落地 `hb_inventory_app`、主数据与台账报表并把货位树改挂到 `3904`；M3-R0、M3-R1 亦为 REVIEWING。

当前真实进度以以下文件为准：

- `docs/PROJECT_STATUS.md`
- `docs/CURRENT_MILESTONE.md`
- `docs/milestones/README.md`
- `docs/milestones/M0.md`
- `docs/milestones/M3.md`

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
- M3-R6 入库拍照识别服务**已开工**（IN_PROGRESS）：服务骨架 `services/hbos_ocr/` 与约束校验层已交付并验证（约束层单测 26/26、端到端冒烟 18/18，**进程内跑、未启动常驻服务**）；后端可插拔（`stub`/`c1_local_vlm`/`c2_ocr`）且缺依赖不崩；门禁已确认：**照片不出内网 → 走本地部署**，暂部署在这台 Mac（`host.docker.internal` 实测可达，服务原生跑在 Mac 上，不塞进 Frappe 容器）；方案 C 内比较 C1（本地量化 VLM）/ C2（PaddleOCR + 规则 + 主数据约束），**推荐两条都实现后用同一测试集选定**；识别范围收敛为 5 个字段；人工校对强制、低置信度高亮、结果不直接入账；准确率标准已制定（批号/代码 ≥95%，**高置信度错误 ≤1%**）；仍待确认测试样本来源
- M3-R5 货位二维码与手机扫码页已执行完毕并进入 REVIEWING：二维码内容为**货位查询链接**（不含静态物料信息，扫码实时查库）；新增打印格式 `HBOS 货位二维码`（60×40mm 标签，内联 SVG）；扫码页 `/hbos_bin` 为 Frappe 原生 www 页面，传货位短码显示该货位明细、传库位/层显示下级汇总；Owner 确认**展示全部字段、不脱敏**；实测 6 个场景（匿名跳转/货位/库位汇总/层/不存在/无参数）均正确
- M3-R4 待检证与货位卡自动生成已执行完毕并进入 REVIEWING：新增三个 Print Format（`HBOS 待检证` 75×110mm 小标签、`HBOS 自产货位卡`、`HBOS 外购货位卡`，后两者 A4），挂在 `Batch` 上按批次数据自动生成，渲染与 PDF 生成均验证通过；新增打印辅助方法与 `Batch.hbos_source_type` 字段；定案「多货位在货位号单元格内逐行列出」；件数按容器类型汇总；流水表按单据净减少判断（库内移库不计入发出）
- M3-R3 出库核销、货位变更、效期预警与盘点导出已执行完毕并进入 REVIEWING：新增出库放行门禁（`before_submit`，限 `Delivery Note` 与 `Stock Entry` Material Issue；待检批次出库被拦截、已放行批次通过、入库与移库不受影响）；货位变更复用原生 Material Transfer 并复验通过；新增 `效期预警`（紧急度分级）与 `库级盘点三对账`（ERP数量 + 留空的货位卡/实物列）两个报表；补建 `仓储库存工作台` 入口（补 M3-R2 遗漏）
- M3-R2 入库登记与批次货位台账已执行完毕并进入 REVIEWING：新建并安装 `hb_inventory_app`，落地 10 个 UOM、六车间 8 个库位、5 个产品分类树节点、Item 5 + Batch 7 自定义字段、包装构成子表 `HBOS Packaging Detail`、报表 `按批号查货位` / `货位明细表`；货位树由 `16号楼产品库` 改名改挂为 `3904 六车间中间库`（203 货位保留、层分布 39/39/39/43/43 不变）；全链路验证通过；并修复 `hb_attendance_app` 一处导致 `bench migrate` 全站失败的既有缺陷
- M3-R0 仓储库存只读盘点与需求确认已完成并进入 REVIEWING；已确认 ERPNext 原生 `Stock` 模块可覆盖除拍照识别与扫码页之外的绝大部分需求，当前 site 无库存业务数据可直接从零建模；已确认 Owner 决策（新开 M3 里程碑、拍照识别用外部 FastAPI + 视觉模型、扫码页用 Frappe 原生 Web 页、固定货位 + 随机存放、货位建模走方案 A、层管理走方案 A1、"工作台""退回产品区"建成叶子 `Warehouse`、试点只做 16 号楼产品库）；已由 Owner 授权安装 `lark-cli` 并只读拉取两篇飞书参考文档与附件，提取到货位编码格式、待检证字段与关键业务规则；Owner 补充提供两份《自产物料/产品货位卡》实例与批号编制规则（三类型结构），已解析并据此暴露关键约束：出库须有 QA 放行手续与合格证、一个批号只对应一张货位卡、批号不存在撞号（`batch_id` 可直接用）、有效期口径按产品种类区分、货位卡"件数"属包装构成（件=5kg桶含尾桶，听/瓶为取样小样）、**所有产品种类（含混粉）走同一套登记流程**；业务口径 20 项中 12 项已明确、3 项决策已确认，已无高优先级待确认项
- M3-R1 货位主数据建模与粒度验证已完成并进入 REVIEWING；已建立 `16号楼产品库 → 03区 → 五个层 → 203 个货位` 的 `Warehouse` 树（共 212 节点，层分布 39/39/39/43/43 校验通过，NestedSet 结构完整，脚本幂等），并用 `TEST-M3R1-` 虚构数据验证"按批号查货位"与"货位→全部批号"双向通过；**更正 M3-R0 结论**：v16 中批次数据在 `Serial and Batch Entry`（关联 `Serial and Batch Bundle`），`SLE.batch_no` 为空列不可用；另发现批次功能开关默认关闭（已开启）、出库批次选取原生即为 FIFO、`UOM` 中无「件」

M0 阶段用于约束后续规划、执行、审查与验收。当前已完成 Frappe / ERPNext / Docker 最小环境启动验证、Frappe HR / HRMS 安装验证、HRMS 前端资源修复、M1 考勤一期边界设计、HRMS 环境可复现性收口、GitHub Private remote 首次同步、M1-R0 规划诊断收口、M1-R1 对象模型验证记录、M1-R2 配置试运行方案设计、M1-R3 局部试运行记录、M1-R3A 阻断诊断方案、M1-R3B 运行态最小修复方案、M1-R3B-FIX 运行态最小修复执行记录、M1-R3C 原生考勤最小试运行复测记录、M1-R3D 异常口径与 Gap 诊断、M1-R3E 配置复核与业务口径确认表、M1-R3F 业务口径确认包、M1 需求设计四份文档、M1-R4 Demo 技术方案与实施路线拆分、M1-R5 HRMS 配置基线、考勤工作台与月度汇总 Demo、M1-R6A Gate 判定和 M1-R6B 脱敏打卡流水导入最小验证；M1 仍未进入完整考勤业务开发。

## 仓库定位

当前仓库用于承载 M0 工程启动文档、AI 协作规则、里程碑状态、阅读指南、计划文档、架构决策记录、最小 Docker 环境配置和经 Owner 授权创建的 M1-FIX 轻量自定义 App。

当前已包含 `apps/hb_attendance_app`。该 App 仅用于考勤导入入口、导入日志和 M1-FIX 必需扩展，不代表启动大而全 HR App。

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
- `hb_inventory_app`：仓储库存扩展（已由 Owner 授权并在 M3-R2 创建安装，承载仓储自定义字段、UOM、报表、打印格式与扫码页）
- `hb_feishu_app`：飞书集成扩展
- `hb_production_app`：生产运营扩展
- `hb_quality_app`：质量管理扩展
- `hb_safety_app`：安全管理扩展
- `hb_ai_ops_app`：AI 运营、视频、算法服务对接扩展
- `hbos-dashboard-web`：Vue/React 驾驶舱与大屏前端

## 当前禁止事项

当前 M1-FIX 仍处于功能补漏阶段，M3 已授权新开，M3-R0 至 M3-R5 已执行、M3-R6 已开工。继续禁止：

- 未经 Owner 明确授权，不创建新的自定义 Frappe App
- 不创建 `hb_core_app`、`hb_feishu_app`
- 不把 `hb_attendance_app` 扩大为大而全 HR App
- 不把 HRMS 安装验证等同于考勤业务开发完成
- 不提交真实 `.env` 或真实密钥
- 不提交备份文件、数据库、Docker volume 或运行时数据
- 未经 Owner 逐轮授权，不启动 M3-R6 及之后轮次，不创建 M3 相关 DocType，不写 M3 业务代码，不创建库存业务数据
- 不接飞书真实写入
- 不做前端驾驶舱
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
15. M3-R5 已执行完毕（`docs/milestones/M3_R5_货位二维码与手机扫码页.md`）：货位二维码标签（内容为货位查询链接，扫码实时查库）+ 扫码页 `/hbos_bin`（Frappe 原生 Web 页，展示全部字段、不脱敏）。当前 REVIEWING。
14. M3-R4 已执行完毕（`docs/milestones/M3_R4_待检证与货位卡自动生成.md`）：三个 Print Format（待检证 + 自产/外购货位卡）按批次自动生成，渲染与 PDF 均通过；定案多货位逐行呈现、件数按容器类型汇总、流水按单据净减少。当前 REVIEWING。
13. M3-R3 已执行完毕（`docs/milestones/M3_R3_出库核销效期预警与盘点导出.md`）：出库放行门禁、货位变更、效期预警与库级盘点三对账报表、仓储库存工作台入口。前置口径：出库批次选取原生即 FIFO；负库存采用默认「不允许」。当前 REVIEWING。
12. M3-R2 已交付并执行完毕（`docs/milestones/M3_R2_入库登记与批次货位台账方案与执行记录.md`）：新建并安装 `hb_inventory_app`；Owner 授权修改 `docker-compose.yml` 并重建容器（volume 全保留）；落地 10 个 UOM、六车间 7 个新库位、5 个分类树节点、Item 5 + Batch 7 自定义字段、子表 `HBOS Packaging Detail`、2 个报表；货位树改名改挂到 `3904`（203 货位保留）；全链路验证通过。另修复 `hb_attendance_app` 一处导致 `bench migrate` 全站失败的既有缺陷。当前 REVIEWING。

## AI 协作方式

- ChatGPT：负责规划、拆解、上下文整理与方案边界确认
- Claude：负责按计划执行文档或代码变更
- Codex：负责工程审查、边界检查、验证与交付复核
- 用户：负责最终验收、取舍确认与里程碑放行

每轮任务开始前，AI 必须说明本轮读取了哪些文档。默认只读 `CLAUDE.md`、`AGENTS.md`、`docs/AI_CONTEXT.md`、`docs/PROJECT_STATUS.md`、`docs/CURRENT_MILESTONE.md`，禁止默认递归读取整个 `docs/`。
