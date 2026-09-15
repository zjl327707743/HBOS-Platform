# Current Milestone

## M1-FIX：M1 考勤一期功能补漏阶段

项目名称：新乡海滨智能运营管理平台。

M1 已 closeout 为 COMPLETED，但 Owner 亲自验收后发现大量产品功能没有真正页面可体验——「方案完成」不等于「功能完成」。M1-FIX 阶段定位为功能补漏，补齐 M1 承诺但未实际可体验的产品功能。

## 当前轮次

M1-FIX-B2：导入口径、安全与准确性修复。当前状态：COMPLETED。已通过 Claude 审查（初审 FAIL → B2-FIX 复审 PASS），Codex closeout 已完成。

M1-FIX-B3：考勤工作台入口、App 命名与 HRMS 数据一致性修复。当前状态：REVIEWING，等待 Claude 审查。

M1-FIX-B4：考勤模块架构收敛与单一入口重整。当前状态：REVIEWING / Claude PASS，但 Owner 数据链路验收发现后续问题。B4 只收敛桌面入口、Workspace、Workspace Sidebar、导入页和 HBOS / HRMS 入口口径；M1-FIX-B3 不 closeout。

M1-FIX-B5：导入数据链路核查与报表口径收敛。当前状态：REVIEWING，等待 Owner 和 Claude 审查。B5 只核查真实 Employee / Checkin / Attendance / 月度暂存链路，收敛 HBOS 报表和 HRMS 技术核查入口；M1-FIX-B3 / B4 不 closeout。

M1-FIX-B-FIX：Excel 导入与中文体验修复。历史轮次；当前后续修复由 M1-FIX-B2、M1-FIX-B3、M1-FIX-B4、M1-FIX-B5 管理。

M1-FIX 后续规划轮次（仅规划，不自动启动）：

| 轮次 | 名称 | 优先级 | 状态 |
| --- | --- | --- | --- |
| M1-FIX-A | 差距盘点与实施方案 | — | REVIEWING |
| M1-FIX-B | Excel 导入与真实本地数据闭环 | P0 | REVIEWING |
| M1-FIX-B-FIX | Excel 导入与中文体验修复 | P0 | REVIEWING |
| M1-FIX-B2 | 导入口径、安全与准确性修复 | P0 | COMPLETED |
| M1-FIX-B3 | 考勤工作台入口、App 命名与 HRMS 数据一致性修复 | P0 | REVIEWING / Owner UI 验收未通过 |
| M1-FIX-B4 | 考勤模块架构收敛与单一入口重整 | P0 | REVIEWING / Claude PASS，Owner 数据链路验收发现后续问题 |
| M1-FIX-B5 | 导入数据链路核查与报表口径收敛 | P0 | REVIEWING |
| M1-FIX-C | 异常说明三级流程 | P1 | PLANNED |
| M1-FIX-D | 考勤工作台 + 月报 + 领导 Demo | P1 | PLANNED |
| M1-FIX-E | 飞书 OAuth 最小验证 + Owner 体验脚本 + 总审查 | P2 | PLANNED |

## M3：仓储库存数字化管理

M3 由 Owner 明确授权新开，与 M1（考勤）为并列里程碑，不替代、不阻塞 M1-FIX。

| 轮次 | 名称 | 优先级 | 状态 |
| --- | --- | --- | --- |
| M3-R0 | 仓储库存只读盘点与需求确认 | — | REVIEWING |
| M3-R1 | 货位与批次主数据建模 | P0 | REVIEWING |
| M3-R2 | 入库登记与"产品—批次—货位"台账 | P0 | REVIEWING |
| M3-R3 | 出库核销、货位变更、效期预警、盘点导出 | P0 | REVIEWING |
| M3-R4 | 待检证与货位卡自动生成 | P1 | REVIEWING |
| M3-R5 | 货位二维码与手机扫码页 | P1 | REVIEWING |
| M3-R6 | 入库拍照识别服务 | P1 | IN_PROGRESS（服务端 + Frappe 侧均已交付） |
| M3-R7 | 总审查与收口 | P2 | PLANNED |

当前轮次：M3-R6（IN_PROGRESS，已开工）——入库拍照识别服务。服务骨架与约束校验层已交付并验证；准确率实测待仓库样本。

M3-R1 已完成：按方案 A1 建立货位树（`16号楼产品库 → 03区 → 五个层 → 203 个货位` + 2 个非货位区域，共 212 节点），层分布 39 / 39 / 39 / 43 / 43 校验通过，NestedSet 结构完整，脚本幂等；用 `TEST-M3R1-` 虚构数据完成粒度验证，"按批号查货位"与"货位→全部批号"双向通过。**并更正了 M3-R0 的一处关键结论**：批次不在 `Stock Ledger Entry.batch_no`（v16 中该列为空），实际在 `Serial and Batch Bundle` / `Serial and Batch Entry`。详见 `docs/milestones/M3_R1_货位主数据建模与粒度验证.md`。

权威文件：

- `docs/milestones/M3.md`
- `docs/milestones/M3_START_GATE.md`
- `docs/milestones/M3_R0_仓储库存只读盘点与需求确认.md`
- `docs/milestones/M3_R1_货位主数据建模与粒度验证.md`
- `docs/milestones/M3_R2_入库登记与批次货位台账方案与执行记录.md`
- `docs/milestones/M3_R3_出库核销效期预警与盘点导出.md`
- `docs/milestones/M3_R4_待检证与货位卡自动生成.md`
- `docs/milestones/M3_R5_货位二维码与手机扫码页.md`
- `docs/milestones/M3_R6_入库拍照识别服务方案.md`

## M1 历史轮次（已完成）

M1 规划收口已完成；产品交付仍在 M1-FIX 中，尚未完成。全部 19 个历史轮次状态见里程碑索引。

M0 已完成并封板。M0-REMOTE 已完成。

权威状态文件：

- `docs/PROJECT_STATUS.md`
- `docs/CURRENT_MILESTONE.md`
- `docs/milestones/M0.md`

权威方案文件：

- `docs/milestones/M1_FIX_功能补漏实施方案.md`

## 本轮范围

M1-FIX-B / M1-FIX-B-FIX 只做 Excel 导入与真实本地数据闭环修复：

- 创建轻量 `hb_attendance_app`
- 创建导入日志
- 支持 Owner 在 Frappe Desk 页面上传考勤机月度导出表、识别预览、确认导入、查看导入日志与中文结果
- 创建 / 匹配 Employee
- 生成打卡流水
- 尝试 HRMS 原生自动考勤，并在必要时记录本地兜底生成
- 生成考勤结果并展示导入统计、重复跳过说明和失败摘要
- 默认白班/行政班为 08:30-17:30
- 不提交真实 Excel、真实员工清单或导入产物

## 本轮禁止事项

-- 不创建 `hb_core_app`
-- 不创建 `hb_feishu_app`
-- 不创建月度汇总 DocType
-- 不创建异常三级流程 DocType
- 不创建/删除/清理 TEST 数据
- 不接真实考勤机
- 不配置真实飞书密钥
- 不要求 Owner 在聊天中粘贴 App Secret
- 不提交 `.env`、密钥、token、数据库、日志、缓存、运行产物
- 不修改 Frappe/ERPNext/HRMS 核心源码
- 不启动大型 Vue/React 前端
- 不启动 M2
- 不把「计划可行」写成「功能已实现」

## M1-FIX 全阶段禁止事项

- 不创建 `hb_core_app`
- 不修改 Frappe/ERPNext/HRMS 核心源码
- 不提交 `.env`、App Secret、密钥、token
- 不提交真实员工姓名、真实工号、真实数据
- 不提交 Excel/CSV 数据文件
- 不接真实考勤机
- 不部署公司内网/云服务器
- 不启动大型 Vue/React 前端
- 不启动 M2
- 不伪造飞书登录成功
- 不执行 `docker compose down -v`
- 不删除 Docker volume
- 不重建 `frontend` site

## 当前状态口径

```
M1     = IN_PROGRESS（产品交付，M1-FIX 中）
M1-FIX = IN_PROGRESS
M1-FIX-A = REVIEWING
M1-FIX-B = REVIEWING
M1-FIX-B-FIX = REVIEWING
M1-FIX-B2 = COMPLETED
M1-FIX-B3 = REVIEWING / Owner UI 验收未通过
M1-FIX-B4 = REVIEWING / Claude PASS，Owner 数据链路验收发现后续问题
M1-FIX-B5 = REVIEWING
M3     = IN_PROGRESS
M3-R0  = REVIEWING
M3-R1  = REVIEWING
M3-R2  = REVIEWING（已执行）
M3-R3  = REVIEWING（已执行）
M3-R4  = REVIEWING（已执行）
M3-R5  = REVIEWING（已执行）
M3-R6  = IN_PROGRESS
M3-R7  = PLANNED
M2     = NOT STARTED / WAITING OWNER AUTHORIZATION
```

## 下一轮预告

M1-FIX-B5 已进入 REVIEWING，等待 Owner 和 Claude 审查。M1-FIX-B3 / B4 不 closeout。M1-FIX-C（异常说明三级流程）为 PLANNED / 待 Owner 授权。M1-FIX-D/E 与 M2 均未启动。

M3-R0 与 M3-R1 均已进入 REVIEWING，等待 Owner 和 Claude 审查。M3-R1 已交付货位主数据树（212 节点）与粒度验证。

M3-R2 已执行完毕（REVIEWING）。Owner 授权后：新建 `hb_inventory_app` 并安装；Owner 授权修改 `docker-compose.yml`（8 个服务）并重建容器（volume 全保留）；落地 10 个 UOM、六车间 7 个新库位、5 个分类树节点、Item 5 + Batch 7 自定义字段、子表 `HBOS Packaging Detail`、2 个报表；货位树改名改挂到 `3904`（203 货位保留、层分布不变）；全链路验证通过。

**修复既有缺陷**：`hb_attendance_app` 的 `hbos_monthly_upload.json` 缺 `doctype` 等必需字段，导致 `bench migrate` 全站失败（`KeyError: 'doctype'`）；已按同目录标准结构补齐，migrate 恢复正常。此前任何依赖 migrate 的操作（含 `after_migrate` 钩子）均不生效。

M3-R3 已执行完毕（REVIEWING）：新增出库放行门禁（`before_submit`，限 `Delivery Note` 与 `Stock Entry` Material Issue；待检批次出库被拦截、已放行批次通过、入库与移库不受影响）；货位变更复用原生 Material Transfer 并复验通过；新增 `效期预警` 与 `库级盘点三对账` 两个报表；补建 `仓储库存工作台` 入口（补 M3-R2 遗漏）。前置口径：出库批次选取原生即 FIFO；负库存采用 ERPNext 默认「不允许」。

M3-R4 已执行完毕（REVIEWING）：新增三个 Print Format（`HBOS 待检证` 75×110mm 小标签、`HBOS 自产货位卡`、`HBOS 外购货位卡`，后两者 A4），挂在 `Batch` 上按批次数据自动生成；新增打印辅助方法与 `Batch.hbos_source_type` 字段；定案「多货位在货位号单元格内逐行列出」；件数按容器类型汇总；流水表按单据净减少判断（库内移库不计入发出）。三个模板渲染与 PDF 生成均验证通过。

M3-R5 已执行完毕（REVIEWING）：货位二维码内容为**货位查询链接**（不含静态物料信息，扫码实时查库）；新增打印格式 `HBOS 货位二维码`（60×40mm 标签，内联 SVG）；扫码页 `/hbos_bin` 为 Frappe 原生 www 页面，传货位短码显示该货位明细、传库位/层显示下级汇总。Owner 确认**展示全部字段、不脱敏**。实测 6 个场景（匿名跳转/货位/库位汇总/层/不存在/无参数）均正确。修复 www 路由含连字符导致 500、以及 hooks.py 中 `jinja` 重复定义两处问题。

M3-R6 已开工（IN_PROGRESS）：**服务骨架 `services/hbos_ocr/`、约束校验层、Frappe 侧入口与校对界面均已交付并验证**（约束层单测 26/26、服务端冒烟 18/18、Frappe 侧 API 与边界用例全通过；均未启动常驻服务）。后端可插拔（`stub`/`c1_local_vlm`/`c2_ocr`），缺依赖不崩。门禁已确认：**照片不能出内网** → 排除云端方案，走**本地部署**；暂部署在这台 Mac（Mac mini M4 / 16GB）；使用范围**全部产品**；准确率标准由本轮制定。方案已据此修订：重点从「A vs C」转为**方案 C 内部 C1（本地量化 VLM）/ C2（PaddleOCR + 规则 + 主数据约束）两条路线对比**，推荐**两条都实现后用同一测试集选定**。`host.docker.internal` 实测可达，服务原生跑在 Mac 上。**第 4 项已答复**：**样本只能去仓库实地获取**；方案已补 7.8 实地取样清单。除「准确率测量」外其余工作**均不被样本阻塞**。

## 飞书登录提前实现记录（M2-R0）

由 Owner 直接授权，在 M2 整体未启动前，提前落地 M2 飞书集成的两项：

1. **飞书 OAuth 登录**：已完成代码实现并在本地 Docker 环境用真实飞书应用完成端到端验证（授权跳转 → 回调 → 自动建号绑定 → 进入 Desk）。
2. **HRMS 汉化与「Frappe HR」→「海滨HR」改名**：切系统语言为中文、编译 HRMS 自带中文翻译、Custom Translation 改名与补漏，已本地验证通过。

详见 `docs/milestones/M2_R0_飞书登录实现记录.md`，状态 REVIEWING。

本轮不改动 M2 整体状态（M2 仍 NOT STARTED）；M1-FIX 各轮次状态不变。遗留：飞书身份 → Employee 匹配未实现、临时默认角色为 `Desk User`、访问地址为临时 cpolar 隧道。
