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
| M3-R6 | 入库拍照识别服务 | P1 | IN_PROGRESS（**准确率/耗时达标 + 入库后自动生成货位卡/待检证**） |
| M3-R7 | 总审查与收口 | P2 | PLANNED |

当前轮次：M3-R6（IN_PROGRESS，已开工）——入库拍照识别服务。服务骨架、约束校验层、Frappe 侧入口与校对界面均已交付并验证；**真实样本准确率实测已完成**（`small` 档，250 个字段命中 236 = 94.4%，**但该数字主要衡量数字、不是汉字**）。**Owner 已决策（2026-09-16）**：效期只印到月时**按月末推定**、**不加粒度字段**（打印件会比标签更细，已知取舍）；**外购暂缓**（外购到货时已有现成待检证与货位卡），本轮按自产收口。**耗时问题已解决**：改用 PaddleOCR `small` 档（免装依赖，只是换模型名）→ 单张约 **7 s**，已进 10 s 标准线，accuracy 仍达标（全字段 82%）。**分档实测已完成（2026-09-21）**：大字（5 结构化字段）`small` 全字段 82%、`medium` 86%；小字（16 个模板恒定串 × 50 张）`small` 整串命中 **83.5%**、`medium` **85.2%**，长串/小字最弱（运输注意事项整句仅 25/50）；**手写档给不出准确率**——无真值，人工转写同样在可获分辨率下辨认不出，仅可记录「操作人/日期 标签后为空 34/50、姓名 50 张无一读出」。换 `medium` 每提 1 个点要付 4 倍耗时，**维持 `small`**。**品名抽取规则已修（2026-09-21）**：Owner 报「汉字准确率太低」后逐张核对，查出抽取层三个真缺陷——① 值里含 ASCII 就整条丢掉（把读对的 `美罗培南（B）` 扔了）② 标签与值被 OCR 切成两行时取不到 ③ 频次法无长度下限、从残渣里编答案（`避免硫碰。`/`存新件`/`合证`）。修后 `small` 品名 90% → **92%**，**错答 4 → 0**（3 处转为诚实的「空」，由物料主数据补上）。注意：**原始识别读错字（`美罗培南→美罗第南`）是模型上限、改规则救不了**，靠标签上重复印刷 + 主数据兜底。**第五批**已交付「入库提交后自动生成货位卡 / 待检证」；**第六批**修完 M3-R4/R5 的打印纸型缺陷与货位二维码小标签（**全量 224 个标签验证**）、并加固物料建档守卫。**仍待定：置信度类标准**（C2 无逐字段置信度，测不了）。

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

M3-R3 已执行完毕（REVIEWING）：新增出库放行门禁（`before_submit`，限 `Delivery Note` 与 `Stock Entry` Material Issue；待检批次出库被拦截、已放行批次通过、入库与移库不受影响）；货位变更复用原生 Material Transfer 并复验通过；新增 `效期预警` 与 `库级盘点三对账` 两个报表；补建 `仓储库存工作台` 入口（补 M3-R2 遗漏；**该入口两个缺陷已于 2026-09-23 修复**——顶层图标曾误用与 ERPNext 原生 `Stock` 相同的 `stock` 致点错进原生模块且回不来，以及**桌面图标因 label 与侧边栏名不一致被 Frappe 静默丢弃**（父图标被丢弃还会连带子图标），现已三者同名，详见其主文档 6.2 节）。前置口径：出库批次选取原生即 FIFO；负库存采用 ERPNext 默认「不允许」。

M3-R4 已执行完毕（REVIEWING）：新增三个 Print Format（`HBOS 待检证` 75×110mm 小标签、`HBOS 自产货位卡`、`HBOS 外购货位卡`，后两者 A4），挂在 `Batch` 上按批次数据自动生成；新增打印辅助方法与 `Batch.hbos_source_type` 字段；定案「多货位在货位号单元格内逐行列出」；件数按容器类型汇总；流水表按单据净减少判断（库内移库不计入发出）。三个模板渲染与 PDF 生成均验证通过。**注意**：当时**只验了「能不能出 PDF」，没验纸型与页数**——后续实测发现三者「手动点打印」全都按 A4 出、且待检证会溢出成 2 页，已于 M3-R6 第五批一并修复（详见该批记录）。

M3-R5 已执行完毕（REVIEWING）：货位二维码内容为**货位查询链接**（不含静态物料信息，扫码实时查库）；新增打印格式 `HBOS 货位二维码`（60×40mm 标签，内联 SVG）；扫码页 `/hbos_bin` 为 Frappe 原生 www 页面，传货位短码显示该货位明细、传库位/层显示下级汇总。Owner 确认**展示全部字段、不脱敏**。实测 6 个场景（匿名跳转/货位/库位汇总/层/不存在/无参数）均正确。修复 www 路由含连字符导致 500、以及 hooks.py 中 `jinja` 重复定义两处问题。

M3-R6 已开工（IN_PROGRESS）：**服务骨架 `services/hbos_ocr/`、约束校验层、Frappe 侧入口与校对界面均已交付；真实跨进程端到端已验证通过**（约束层单测、服务端冒烟、Frappe 侧边界用例全通过；实测容器→宿主机连通、Frappe→HTTP→FastAPI 识别、幂等命中、停止后降级均正确）。后端可插拔（`stub`/`c1_local_vlm`/`c2_ocr`），缺依赖不崩。门禁已确认：**照片不能出内网** → 排除云端方案，走**本地部署**；暂部署在这台 Mac（Mac mini M4 / 16GB）；使用范围**全部产品**；准确率标准由本轮制定。`host.docker.internal` 实测可达，服务原生跑在 Mac 上。**样本只能去仓库实地获取**；方案已补 7.8 实地取样清单。

**第四批：真实样本准确率实测已完成**（主文档第九之五节；样本与结果均在仓库外，未提交）。Owner 提供 50 张仓库实地样本后执行：

- **选型**：先上 **C2**（PaddleOCR 3.7.0 + PaddlePaddle 3.3.1，CPU）；C1（`mlx-vlm`）**未装**。
- **实测（50 张，250 个字段，`small` 档）**：批号 **100%**、物料代码 **98%**、生产日期 **94%**、有效期至 **90%**、品名 **90%**；**整体 94.4%**，全字段正确 80%。日期按**真值印刷粒度**比对。
  - ⚠ **2026-09-21 更正口径**：**这组数字不能读成「汉字识别准确率」**——5 个字段里 4 个是数字，只有品名是汉字，所以它**主要衡量数字**。标签上的汉字（公司名/车间/储存条件/操作人/注意事项）**从未进入该指标**，恰恰错得最多；数字的高分还被多处重复印刷撑高。**换 medium 档小字一样错**，瓶颈是**小字成像**。详见 R6 主文档第九之五节 ⚠ 小节。
- **修复三个真实缺陷**：① **只到月的日期被整条丢弃**（实测 39/50 张标签效期只印到月；原校验层返回 None → 三分之二效期会丢）→ 改为补**当月最后一天**并提示（**Owner 已确认按月末；不加粒度字段**）；② **签核日期顶掉生产日期**（操作人/复核人日期混入"取最早"判断）→ 排除签核行；③ **C2 后端按 PaddleOCR 2.x 写的，在 3.x 上完全失效** → 按 3.x 重写。
- **剩余 10 处未命中已逐张核对识别原文**：**8 处是 OCR 读错/漏读**（能力上限），2 处规则误配已修。
- **性能**：原图**约 35 s/张**；**不可降分辨率提速**（有效期是小字，降到 2000 px 会读错）。
- **识别范围**：**只做自产**——外购到货时已有现成的待检证与货位卡，**不经过本识别流程**，故外购无需测试。样本另一局限：**「拍法」列全空**（测不出理想 vs 现实的落差）。
- **单测**：约束层 33 + C2 抽取规则 37 = **70 条全通过**。

**第五批：入库后自动生成货位卡与待检证已交付并验证**（主文档第九之六节）。新建 `hbos_inventory/doc_gen.py` 挂 `Stock Entry.on_submit`——**入库单提交后**按批次自动生成「待检证(75×110mm) + 货位卡(A4)」**合并 PDF** 挂到 `Batch` 附件；`Batch` 表单加「重新生成」按钮。挂 `on_submit` 因为货位卡依赖真实库存流水（草稿阶段还不存在）。**失败吞异常不阻断入库**。实测：2 批次 1.55s、拆行去重、不堆附件、非入库单不触发、**渲染失败提交仍成功**、自产/外购分流正确。

**顺带修复 M3-R4/R5 的纸型缺陷**：三个格式与二维码**手动点打印时全都按 A4 出**（`@page size` 被 wkhtmltopdf 忽略）+ Frappe 框架注入 `min-height: 11.69in` 导致小标签溢出成多页；已修，待检证恢复 1 页 75×110mm。**货位二维码的 SVG 尺寸问题同批已修**（尺寸写进 SVG 属性 + 去掉冗余 URL 行）。**该批中断于二维码验证之前**，收尾见下一批。

**第六批：收尾修复与物料建档守卫已交付并验证**（主文档第九之七节）。

- **二维码标签收尾 + 全量验证**：确认改动已随 `bench migrate` 落库；**手动打印路径全量回归 224 个货位 / 库位**——全部 **1 页 60×40mm**（SVG 带 `width="20mm"`）；另三个格式同期回归 **待检证 1 页 75×110mm、自产/外购货位卡各 1 页 A4**，无回归。验的是「手动点打印」那条路（不注入覆盖 CSS），读的是 PDF 每页**实际物理尺寸**。
- **物料建档守卫**：`create_intake_draft` 原来只查「物料存不存在」——**不够**：物料存在但没勾批次管理时，会一路炸在 ERPNext 的 `Batch.validate()`（英文 `The selected item cannot have Batch`），操作员看不出该改哪个字段。已改为 `_require_item_ready()`，一次查清 **未停用 / `is_stock_item` / `has_batch_no`**，缺什么说什么；**仍不自动创建物料主数据**。
- **建档需要什么**：原生必填仅「代码 / 名称 / 物料组 / 计量单位」，走通本流程还需 `is_stock_item`、**`has_batch_no`**、海滨分类、效期类型与期限、**`hbos_storage_condition`**（缺了待检证储存条件印成空白）、`hbos_workshop`。清单见 R6 主文档第九之七节。
- **未做**：未替 Owner 修改任何真实物料主数据（须授权）。

**第七批：按 Owner 提供的样本批量建档**（主文档第九之八节）。扫描三个样本目录 312 个文件，抽出 **128 个不重复物料并全部建档**。字段来源：代码/品名取单元格原文，分类按**代码前四位**（M3-R2 6.1 口径），单位取「数量/件数」单元格（**不是**包装规格——`30%过氧化氢` 规格 500ml/瓶 但按**瓶**存），生产车间 31 个、储存条件 28 个来自样本。**顺带修掉 M3-R2 一处缺陷**：海滨分类树 5 个节点当初全建成**分组节点**（`is_group = 1`），**物料根本放不进去**、树形同虚设；已按 Owner 选定改为叶子节点并给 `sync_item_groups` 补纠偏逻辑。**37 个文件上的 19 个物料**（多为培养基）代码栏印的是 `/`，**须先由 SAP 分配代码**。`hbos_shelf_life_type` / `hbos_shelf_life_months` 仍空——样本上勾选框全是 `□`，须质量/仓库给口径。抽取产物只落 `/tmp`，已确认全仓库无真实代码品名泄漏。

**第八批：补充信息手工录入**（主文档第九之九节）。Owner 要求「没获取到的信息可以手工加入」。**校对区改为「全部字段列在一处」**——识别到的预填、没读到的留空就地补；**OCR 识别原文按行拆成可编辑行**逐字校对，校对后文本存进 `Batch.hbos_label_text`（照片不可搜，这段可搜；不参与打印）。可录 **储存条件 / 生产车间 / 复检期还是有效期 / 供货单位 / 生产单位 / 原厂批号 / 包装构成（逐条，件数自动汇总）**，全部流进待检证与货位卡。**物料级三项写回 `Item` 主数据但仅补空**（已有值绝不覆盖，并发下保先到者）；批次级写进本批次。新增 `Batch.hbos_supplier_name` 自由文本字段（标准 `Batch.supplier` 是只读 Supplier 链接，塞自由文本会把批次卡死）。**权限有意绕开默认矩阵**——实测 `Item` 连 `System Manager` 都只有读权限，用标准权限门会把三个角色全挡死。验证全通过（含回归与 Stock User 身份）。**顺带修掉一个误导性控件**：页面上可编辑的「产品名称」从未传给后端、改了不生效，已改为只读对照。**未在真实浏览器验证界面**，建议 Owner 亲自走一遍。

## 飞书登录提前实现记录（M2-R0）

由 Owner 直接授权，在 M2 整体未启动前，提前落地 M2 飞书集成的两项：

1. **飞书 OAuth 登录**：已完成代码实现并在本地 Docker 环境用真实飞书应用完成端到端验证（授权跳转 → 回调 → 自动建号绑定 → 进入 Desk）。
2. **HRMS 汉化与「Frappe HR」→「海滨HR」改名**：切系统语言为中文、编译 HRMS 自带中文翻译、Custom Translation 改名与补漏，已本地验证通过。

详见 `docs/milestones/M2_R0_飞书登录实现记录.md`，状态 REVIEWING。

本轮不改动 M2 整体状态（M2 仍 NOT STARTED）；M1-FIX 各轮次状态不变。遗留：飞书身份 → Employee 匹配未实现、临时默认角色为 `Desk User`、访问地址为临时 cpolar 隧道。
