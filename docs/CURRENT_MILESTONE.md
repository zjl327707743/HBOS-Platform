> **2026-10-29 R6 部门应用权限解释与原型保真 / REVIEWING**：按《HBOS R6 部门应用权限解释与原型保真》单 Agent 任务书，在 #63 定向整改“部门按应用设置默认权限”和“员工按应用单独设置”的页面语义，并对个人中心、员工管理、部门页面、角色与权限、变更记录逐页核对 R6-A2.2 / v1.3 原型。部门页新增固定应用标题与紧凑应用选择、把 LEGACY 兼容状态从第三个灰色单选改为独立状态说明、无修改时不显示取消修改并统一禁用主按钮样式、影响摘要区分服务端可见成员/跟随者/个人安排/实际变化；员工抽屉新增按应用权限总览，考勤兼岗显示“本人考勤”与“明确负责（不含下级）”两个独立范围，未接入应用不绘制为可生效开关。前端 50 文件/466 测试、TypeScript、构建与改动文件 ESLint 通过；未改后端权限合同、未新增授予、不把知识库/LIMS/仓储/生产写成已接入。合成 18191 固定候选、多视口同尺寸对照与 Owner 两条理解回执仍待完成；未合并、未转 Ready、无标签、main 与团队发布。详见统一入口 `R6_DEPARTMENT_SEMANTICS_AND_FIDELITY_20261029.md`。以下按日期保留历史。

> **2026-10-27 · 原型整改代码候选**：员工/部门/个人中心/草稿发布完整流程已重做并完成离线复核：44文件409测试、TypeScript及18个改动文件lint通过。浏览器工具在Owner启用后仍返回禁用，同状态原型复核与新构建真实UAT未通过。TEAM_PULL_READY=BLOCKED，不提交整体验收、不发布。详见本轮主记录末节。

> **2026-10-27 · G3/G4 原型完整性重新实施**：Owner否决753候选的员工应用角色、部门安排、个人中心和角色发布理解体验。按固定R6-A2.2/v1.3补齐完整正式流程，旧接口/权限分项结果不代表整体验收。原生200%仅Owner确认753版本；新候选待测。本地DeepSeek按文件执行A/B/C，总实施Codex统一复核、Git及运行验收。浏览器工具当前禁用，新视觉证据待补；TEAM_PULL_READY=BLOCKED_G3_G4_FIDELITY，未生产上线。

> **G4 分页边界修复（2026-10-27）**：真实浏览器在初次读取前点击分页曾发出page=0并进入400；人员/审计分页现仅接受已加载范围内的正整数页，加载及空态禁用。40文件326测试、typecheck及改动lint通过，须新组合复测。Owner已批准的两项独立后端修复在#65/#66实施，当前测试7a的HR开户/首次改密/关联14项及副作用核验PASS，未合并。TEAM_PULL_READY=PENDING。下列按日期保留历史。

> **G4 抽屉键盘修复待新构建（2026-10-27）**：332的界面建档、20次往返、动效、暂停/deny/停用已有真实证据；Shift+Tab曾跳到背景，局部焦点循环已修并通过325项离线测试，须真实复测。并发鉴权与HR开户两个独立安全修复仍待Owner授权，未应用。

> **G4 继续验收（2026-10-27）**：af0434e 的20项读取/拒绝、38项角色联调及39个CSS视口通过；323前端测试通过。T08草稿切换和T04表单修复待新构建复测；并发鉴权500独立补丁待Owner授权。`TEAM_PULL_READY=PENDING`。

> **G4 隔离联调修复中（2026-10-27）**：旧测试组合 97e0272 实际发现岗位为空、个人中心卡片 top 偏移重叠；前后端各自修复后须新 SHA 构建复测。旧组合不计 G4 PASS，产品仍为 22b47dc，未发布。

# Current Milestone

> **2026-10-27 R6-B / G4_UAT_IN_PROGRESS**：#62 与 #61 已分别按 Owner 精确授权正常 Squash，实际产品基线为 `22b47dcdcc17e8dfd0f0640d2b9a04ec14303b0b`。实际提交四个 CI 作业通过。R6 从该 SHA 的 `feat/hbos-r6b-experience-v1` 实施，固定设计依据 R6-A2.2 / v1.3；G4 真实权限与浏览器验收、G5 独立审查及固定 SHA 合并、G6 统一构建/标签/团队发布尚未完成。`TEAM_PULL_READY=PENDING`，未生产上线。详见 [本轮主记录](milestones/Portal_R6B_正式管理体验与稳定集成.md)。以下按日期保留的旧状态为历史。


> **2026-10-27 #62 旧站点登录兼容修复 / REVIEWING**：Owner 已授权修复旧站点在非试点且关闭自动开户时可能重新开放飞书登录的问题。修复保留该旧关闭语义，并仅在显式试点名单有效时允许关闭自动开户的受控登录；原身份、权限和 proof 合同不变。新增入口及旧回调拒绝负例，Python 3.11/3.12 各 248 项本地测试通过。当前候选尚未部署，最终 GitHub HEAD 的 CI、非作者身份安全审查和固定 HEAD/base 的独立合并授权仍须核对；#61/#62 均未合并，未批准标签或生产发布。历史首通证据见下文。

> **2026-10-26 R5-B 真实首通已核验 / REVIEWING**：产品基线 `1a0d44de1399afca513855f3688eb06c1978429e`。Owner 已本人完成 Administrator 绑定并确认飞书登录；官方回调、企业和在职成员校验成功，真实飞书签发会话的同 User、工作台/IAM/库存/LIMS 读取、原生退出与旧会话重放拒绝已核验，密码登录仍有效，未复制 User/Employee 或新增角色。仅本人 Administrator 试点，自动开户关闭。视觉 Draft #61、认证 Draft #62 均暂缓合并；最终页面/管理员使用验收和专门审查门禁分别记录，不代表生产发布。见 [本轮记录](milestones/Portal_R5B_受控飞书登录候选.md)。以下各日期内容保留历史含义。


## 历史集成状态 — 2026-10-19

**四个完整业务 PR 已实际合并：#42 考勤、#46 生产、#39 仓储、#43 LIMS。** 唯一目标为 `feature/hbos-portal-product`；业务合并基线为 `04e0bb033cb2e7156e407cf49a7b6966b0d2a022`，状态文档在其后维护。[#43](https://github.com/zjl327707743/HBOS-Platform/pull/43) 于 2026-10-19 03:28:29 UTC 正常 Squash Merge；来源、父提交与树见[项目状态](PROJECT_STATUS.md)。

**合并前精确组合：PASS。** [R10 39184807396](https://github.com/zjl327707743/HBOS-Platform/actions/runs/39184807396) 全部 10 jobs SUCCESS，五个原生域与离线／契约／构建在本次 #43 来源和产品基线的真实组合上通过；该组合树与实际 Squash 树相同。

**实际产品合并后回归：PASS。** [R11 39195037712](https://github.com/zjl327707743/HBOS-Platform/actions/runs/39195037712) 全部 10 jobs SUCCESS；五个原生域均直接运行业务合并基线 `04e0bb033cb2e7156e407cf49a7b6966b0d2a022`，无额外 merge，实际单父与树一致，双 migrate 与清理均成功。LIMS 原有 32 项、新增审计 9 项、独立 Todo 1 项合计 42 项原生测试全部通过；Todo 只有 1 项，归属 LIMS。

当前轮次为四项完整业务 PR 的合并后验证与状态收口：#42 → #46 → #39 → #43 均已实际合入唯一产品分支，R11 五个原生域及 LIMS 独立 Todo 1 项补证均通过。当前收口包括状态文档与两处 Python 3.10 测试夹具兼容修复；本收尾 PR 必须在固定候选 SHA 的 Python 3.10／3.12 检查通过后方可合并，实际结果以本 PR 最新 Owner 裁定及最终报告所列 SHA／Job 为准，详见项目状态的独立 CI 事件记录。IAM #52、#37、OCR、真实样本、实体打印及生产 UAT／部署不由本次代码合并 closeout；质量放行撤回未在本轮实现。

业务合并基线与文档保存后的 HEAD 分开记录。Run1–9 的历史失败、未合并及 `NOT_PRODUCT_COMPOSITION` 均按各自日期、来源和作业保留，详见 [PR #56](https://github.com/zjl327707743/HBOS-Platform/pull/56)；最新业务与回归状态以本节和项目状态为准。

### 历史回归 — 2026-10-18 Run8（#39 合并后）

**合并后回归：PASS。** [Run8 39107944012](https://github.com/zjl327707743/HBOS-Platform/actions/runs/39107944012) 全部 8 jobs SUCCESS；四个业务域直接检出实际产品 `a1cc65dde73cfad656faf290264f75fb1a25c32b`，记录 `post_merge_baseline`，源码树为 `43b59653ebbe61db530f523ea980163c88f1899e`、唯一父提交为 `4ddf9bebe5bd9f0d73cdb84bd4ddfa9b8615ad30`。仓储事务 8/8、报表22项HTTP与8项跨仓CSV、卡证权限74/74、考勤原生范围及生产28项检查均通过；所有原生Site双migrate与清理通过。完整来源与后续文档提交见 [PR #56](https://github.com/zjl327707743/HBOS-Platform/pull/56)，不以文档提交后的新HEAD冒充上述已运行提交。

## 验证历史 — 2026-10-18 Run6

[报表、扫码及附件验证](https://github.com/zjl327707743/HBOS-Platform/actions/runs/39103298497/job/117603810152) **74 PASS / 0 FAIL**；[事务验证](https://github.com/zjl327707743/HBOS-Platform/actions/runs/39103298497/job/117603810103) **6 PASS / 2 FAIL**。余两项失败为按单一 URL 误选 Batch File 的测试定位错误，LIMS 放行后两种外发 submit/cancel 仍 **NOT_REACHED**，完整仓储门禁未通过。

## 验证历史 — 2026-10-18 Run5

以下保留 Run5 当时的观察与判断，其中“当前”“尚未通过”“原因待定位”均指该次验证；后续状态以页首“当前集成状态”和实际 PR 记录为准。

当前继续完成 Owner 授权的业务 PR 合并。完整 #42 考勤与 #46 生产已合并，已核对产品为 `4ddf9bebe5bd9f0d73cdb84bd4ddfa9b8615ad30`。[#39 仓储](https://github.com/zjl327707743/HBOS-Platform/pull/39) **尚未合并／技术门禁 FAIL**：Run 5 的扫码与附件权限域 73/74 通过、真实事务域 3/8 场景通过；PDF 正文、注册外协目标放行旁路及完整 LIMS 放行链仍需收口。具体失败、`NOT_REACHED` 和固定 SHA 见 [项目状态](PROJECT_STATUS.md) 与 [#56](https://github.com/zjl327707743/HBOS-Platform/pull/56)，不能用来源分支提交替代产品合并。

下一步在最新仓储来源修复并重跑其真实组合，满足门禁后才 Squash、重读产品 HEAD 并做合并后回归。#43 后置；其独立 39/39 契约与 4 项 mutation 检查通过只记为 `NOT_PRODUCT_COMPOSITION`。本轮不据此完成 M3-R6 的 OCR／实体打印验收，不推进 IAM #52、#37 或生产部署。

## 历史阶段记录

下方较早合并、账号、M1 与 Portal 阶段的“当前”“本轮”和允许范围保留原日期含义，不覆盖页首 R3 授权与验证记录；实际最新来源、验证及合并以 PR #39、PR #56 和远端产品 ref 为准。

> 2026-10-18 生产已完成集成：完整 #42 考勤、#46 生产均已实际合并。最新核对产品为 `4ddf9bebe5bd9f0d73cdb84bd4ddfa9b8615ad30`，来源、审批与原生验证见 [项目状态](PROJECT_STATUS.md)。继续推进 #39 仓储，#43 后置；以下较早产品 SHA 为各阶段历史记录，不替代远端最新 ref。

> 2026-10-18 最新代码集成：**首个完整业务 #42 考勤已实际合并**。产品基线 `374e2bd8633d4127fabcc4659c2314e4a7ca7cd8`，实际父提交 `45658fe4b84d8fb7dd4433c459aa30572e0d13d3`。来源与审批、CI、归档证据见 [PR #42](https://github.com/zjl327707743/HBOS-Platform/pull/42) 和 [项目状态](PROJECT_STATUS.md)。下一顺序为 #46 生产、#39 仓储，#43 LIMS 后置；每项仍以当前 SHA 的权限、运行与审查门禁为准。Owner 承担本批次最终审批，具体方式见 [正式裁定](governance/HBOS_Owner_业务集成批次裁定_20261018.md)。本轮不代表真实环境部署或 IAM #52 完成。

> 历史记录：2026-10-18 物料只读集成窗口：仓储物料只读浏览由 [PR #55](https://github.com/zjl327707743/HBOS-Platform/pull/55) 独立承接；当前代码来源以远端 `feature/hbos-portal-product` 与该 PR 实际合并 SHA 为准。下方 PR #21 的 SHA/账号验收是历史记录，不代表最新产品 HEAD。完整业务 #42/#43/#46/#39 和 IAM #52 各自保留独立门禁；本轮不安装或部署真实环境。

## Portal 产品分支合并后 Gate — 2026-10-01

当前：**PR21_FINAL_REVIEW_PASS / PRODUCT_BRANCH_ACTIVE**。PR #21 已 squash 合入 `feature/hbos-portal-product@e4b16ee80aaaf21aac2304246a4de1f9fe8995ea`；Owner 最新无破坏验收与 Browser final-submit 3/3 已通过，新 squash 四项 CI SUCCESS。旧 #22 已关闭且未合并，IAM-0 由 clean Draft PR #23 单独承接；#15 仍 Open Draft，main 未变化。

下一阶段不再重复 PR #21 的 Owner OAuth、设密/改密/恢复验收。Portal 进入 main 仍需单独 Gate；IAM-0/后续 IAM 实施不因 #21 合并自动完成。

## 账号小范围收尾 — 2026-10-01

本轮接续交付基线 `eee1c5e22c57be3436244e77c65e189bd7eee242` 与 PR #21，仅做资料登录渠道、唯一个人导航、折叠偏好说明、飞书头像同步及 C03/C07/C09/F03 缺项补测；不重新全量审计、重画页面或新增账号功能。真实 Administrator 已成功飞书登录为 USER_CONFIRMED_SUCCESS，绑定、密码、MFA、Secret、企业与回调保留。本机沿用既有 P1 Site/Compose/入口，发布分支不合并、不强推、不推 main/base。 补测确认并修复参与页期限遗漏与 GET 回调未提交记录，原矩阵历史保持；最终浏览器新凭据步骤由工具要求人工接手，团队脚本与未执行状态单列。


## Portal 本轮独立授权

本轮（2026-10-01）接续 PR #21，执行登录账号模块 UI 规范回归与全功能审修。Owner 已亲自确认 Administrator 能通过本人飞书验证并登录，记为 OWNER_CONFIRMED_SUCCESS；历史成员权限待审批或登录失败记录不再代表当前事实。保留真实绑定、密码、MFA、Secret、企业与回调；不要求重复配置。认证页沿用已有 Ant Design Vue / ConfigProvider / typography / tokens，修复表单、证明期限、错误状态、同路由目标与提交结果处理。破坏性、并发与交接只在独立合成 Site 验证。新版本真人 OAuth、本人收到验证码、第二位真人交接与移动软键盘结果单独记录，未执行不写 PASS。复用现有 P1 / Compose / 卷与常用入口，最终本机 SHA/build ID、远端提交、CI 和制品须一致。公司服务器为 NOT_DEPLOYED。主记录：`docs/milestones/M1_RP3_统一账号飞书绑定与正式发布.md`。PR #21 head `codex/portal-unified-account-release`、base `feature/hbos-portal-product`；不强推、不自动合并、不推 main/base。

下述考勤历史轮次的范围不约束已明确授权的 Portal v3；Portal 不替其他业务轮次 closeout。

团队代码已通过 [PR #21](https://github.com/zjl327707743/HBOS-Platform/pull/21) squash 合入 `feature/hbos-portal-product@e4b16ee80aaaf21aac2304246a4de1f9fe8995ea`。P1 继续作为固定本地运行环境；PR #15/main 仍按后续独立 Gate 管理。

## M1-FIX：M1 考勤一期功能补漏阶段

项目名称：新乡海滨智能运营管理平台。

M1 已 closeout 为 COMPLETED，但 Owner 亲自验收后发现大量产品功能没有真正页面可体验——「方案完成」不等于「功能完成」。M1-FIX 阶段定位为功能补漏，补齐 M1 承诺但未实际可体验的产品功能。

## 考勤既有轮次记录

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
M2     = NOT STARTED / WAITING OWNER AUTHORIZATION
```

## 下一轮预告

M1-FIX-B5 已进入 REVIEWING，等待 Owner 和 Claude 审查。M1-FIX-B3 / B4 不 closeout。M1-FIX-C（异常说明三级流程）为 PLANNED / 待 Owner 授权。M1-FIX-D/E 与 M2 均未启动。


## 并行产品工作流：HBOS Portal

Owner 已于 2026-09-24 明确授权 HBOS Portal 独立并行启动。

该授权不改变本文件顶部的 M1-FIX 主里程碑。

Portal 当前状态：

```text
EA-1 ~ EA-4 = BASELINE
EA-5 Owner Visual Gate = APPROVED
EA-5.3 = BASELINE
EA-5.4 = DESIGN ENGINEERING BASELINE
EA-5.5 = NEXT
```

正式工作分支：`feature/hbos-portal-product`。

允许范围：
- Portal Experience Architecture 文档；
- 已批准原型复刻；
- Vue 3 + Ant Design Vue Portal Skeleton；
- EA-5.5 响应式 / 可访问性 / 交互 QA。

在后续 Gate 前暂不创建 `apps/hbos_portal`，不接真实业务 Provider。


### Portal Phase B 更新

```text
Phase B — Vue Portal Skeleton
= SOURCE INITIALIZED / BUILD VERIFICATION PENDING
```

已在 `frontend/hbos-portal-web/` 初始化经 Owner 批准视觉母版的 Vue 3 + Ant Design Vue 工程骨架。

本轮仍属于“前端复刻”，没有进入“真实功能接入”。

下一 Gate 保持：

```text
EA-5.5 Interaction QA + Responsive + Accessibility
```

在 build Gate 和 EA-5.5 通过前，不创建 `apps/hbos_portal`。


### EA-5.5 已启动

Portal 并行工作流当前更新为：

```text
EA-5.4 = DESIGN ENGINEERING BASELINE
Vue Portal Skeleton = BUILD PASS
EA-5.5 = IN_PROGRESS
```

EA-5.5 当前只做交互、响应式、可访问性和 LIMS V1 Operational Page 验证，不进入真实 API 功能接入。


### Portal EA-5.5 Gate

```text
EA-5.5 Implementation = PASS
HBOS Quality Gate = PASS
Portal Frontend Build Gate = PASS
Owner Product Review = PENDING
```

在 Owner Review 前，EA-5.5 不标记 COMPLETE，不进入真实 Provider / backend implementation。


### Portal Gate Update — 2026-09-25

EA-5.5 已通过 Owner 验收并收口。

下一允许范围：

- P1 `hbos_portal` Platform App Architecture；
- App Registry / Bootstrap / Session / Access / Provider Discovery 设计；
- 不改变 Attendance / Inventory / LIMS 领域 Authority；
- P1 架构收口前不引入业务事实副本。


### Portal P1 Architecture Gate — 2026-09-25

`docs/experience/P1_HBOS_Portal平台App架构.md` 已形成架构基线。

下一允许范围：P2 `apps/hbos_portal` skeleton；不接三业务 APP Provider，不创建业务事实 DocType。


### Portal P2 Gate Update — 2026-09-25

- `apps/hbos_portal` skeleton 已创建；
- Portal Backend Gate = PASS；
- Vue Frappe Bootstrap Adapter = PASS；
- 下一 Gate = P2.2 Runtime Smoke Test；
- 尚未接三业务 APP Provider。


### Portal P2.2 Runtime Gate — 2026-09-25

```text
P2.2 Runtime Smoke Test = PASS
P3 Business App Registration = NEXT
```

Runtime 使用独立 Portal worktree + 临时 Compose override，正式 `main` Attendance 工作区未 switch / stash / reset / clean。

验证完成后：

- `hbos_portal` 已安全卸载；
- site app list 恢复 baseline；
- 28 个 Docker volume 名称保持一致；
- Attendance bind mount 恢复正式工作区；
- 业务数据未改变。

Attendance hook import warning 为非阻断观察项，留在 Attendance Authority 下后续处理。


### Portal P3-LIMS-1 Gate — 2026-09-25

```text
P3 Business App Registration = IN_PROGRESS
P3-LIMS-1 First Real Provider = COMPLETE
P3-LIMS-2 Stable Deep-link Adapter = NEXT
```

Runtime clean-site 已真实验证 Frappe Hook → Portal Registry → LIMS Access → Bootstrap，且没有开启业务数据 capability。

同轮 Attendance G1 与 LIMS → Inventory release integration 继续 PASS。


### Portal P3-LIMS-2 / P3-LIMS-3 Closeout — 2026-09-25

Portal 分支已先同步最新 `main`（含已合并 PR #20 的 LIMS production-entry 修复），同步后保持：

- LIMS `/hbos-lims/*` 正式入口与持久静态资源能力；
- `hbos_portal_provider` 动态 Provider discovery；
- `hbos_portal` Runtime mount / Registry；
- 三业务 App 原有联合门禁。

P3 当前状态：

```text
P3 Business App Registration = IN_PROGRESS
P3-LIMS-1 Manifest / Access / Registration = COMPLETE
P3-LIMS-2 Stable Deep-link Adapter = COMPLETE / RUNTIME PASS
P3-LIMS-3 My Work Projection = COMPLETE / RUNTIME PASS
P3-LIMS-4 Summary Projection = NEXT
P3-LIMS-5 Search Provider = PLANNED
```

LIMS manifest 当前只开放：

```json
["tasks"]
```

Summary / Search 仍未开放。

P3-LIMS-2 已建立 LIMS internal route → stable `/hbos/lims/...` → current `/hbos-lims/...` 的双向适配，并保持 `hbos_portal` 不静态 import LIMS。

P3-LIMS-3 已复用现有 `todo_service.get_my_todos()` 输出 Unified Task DTO，Portal 不创建第二套 Todo，不持有业务状态，不执行 LIMS 业务动作。

最终 Runtime：

```text
Portal Backend Gate = PASS
Portal Frontend Gate = PASS
HBOS Quality Gate = PASS
Platform Integration Gate run 36042393976 = SUCCESS
HBOS PLATFORM clean-site integration = PASS
```

clean-site 已验证 `lims_manifest_capabilities=["tasks"]`、Stable Route、LIMS task provider 调用、LIMS + Inventory release chain 与 LIMS production entry 共存。


### Portal P3-LIMS-4 / P3-LIMS-5 Closeout — 2026-09-25

LIMS 首个完整 Application Provider experience contract 已完成：

```text
P3-LIMS-1 Manifest / Access / Registration = COMPLETE
P3-LIMS-2 Stable Deep-link Adapter = COMPLETE / RUNTIME PASS
P3-LIMS-3 My Work Projection = COMPLETE / RUNTIME PASS
P3-LIMS-4 Summary Projection = COMPLETE / RUNTIME PASS
P3-LIMS-5 Search Provider = COMPLETE / RUNTIME PASS
```

最终 LIMS manifest：

```json
["summary", "tasks", "search"]
```

最新 clean-site authority：

```text
Head = 7cc1804e4d484feef221ba8b513ec07f036af281
Platform Integration Gate run 36045590049 = SUCCESS
HBOS PLATFORM clean-site integration = PASS
```

Portal 当前下一 Gate：

```text
P3-ATT-1 — Attendance Manifest / Access / Stable Entry
```


### Portal P3 — Three-App Registry Baseline — 2026-09-25

三大业务 APP 已同时进入 Portal Registry：

```text
LIMS
  Manifest / Access / Stable Route = COMPLETE
  Tasks = COMPLETE
  Summary = COMPLETE
  Search = COMPLETE

Attendance
  Manifest / Access / Stable Route = COMPLETE
  HR Summary = COMPLETE
  Tasks / Search = GATED
  Ordinary Employee Portal Access = GATED

Inventory
  Manifest / Access / Stable Route = COMPLETE
  Permission-aware Summary = COMPLETE / RUNTIME PASS
  Tasks / Search = GATED
```

三 APP clean-site Registry authority：

```text
registry_entries = ["attendance", "inventory", "lims"]
registry_failures = 0
bootstrap_apps = ["attendance", "inventory", "lims"]
```

Inventory registration Gate：

```text
run 36048253825 = SUCCESS
```

最新真实数据硬化 HEAD：

```text
f6267baf44813c5b89f83adfe744d8f0192d03bb
```

该版本：
- Frappe mode 不再展示原型期 12/12、7 apps、SAMPLE-001、Digital Twin LIVE 等演示数据；
- 没有 Provider 的模块直接隐藏；
- 多 APP Summary 采用 round-robin 选择，避免一个 APP 独占 Hero 四个指标。

最新 Platform Integration Gate `36048726221` = SUCCESS。

P3 下一阶段从“注册 APP”转为“逐 App 数据能力深化”。


### Portal P3-INV-2 — Inventory Permission-aware Summary — 2026-09-25

状态：**COMPLETE / RUNTIME PASS**。

```text
Inventory manifest = ["summary"]
Inventory Summary metrics = 4
Stable Route = /hbos/inventory -> /app/hbos-photo-intake
Raw-SQL report reuse = NONE
Cross-UOM quantity aggregation = NONE
```

权限链：

```text
Frappe Session
  -> permission-aware visible Warehouse
  -> Bin explicitly scoped to visible Warehouse
  -> Inventory semantic projection
  -> Portal dispatcher
```

Runtime authority：

```text
Inventory real-site first pass:
  Head 3c6f1d5f54a5795d4a7b1ed486c8ce32c64ea7e4
  Platform run 36082817979 = SUCCESS

Portal dispatcher / strict three-app code authority:
  Head ea15676af42e14c2eb47bd65fa402481693b0cac
  Platform run 36083304003
  Three-app clean-site integration step = SUCCESS
```

本地运行工具已加入：

```text
scripts/portal/start_local_workspace.sh
scripts/portal/p3_workspace_runtime_smoke.sh
```

下一 Gate：

```text
Owner local P3 workspace smoke
    ->
P4-F0 real runtime screenshot / journey baseline
    ->
three-app frontend strengthening audit / prototype
```


### Portal P3 Local Isolated Preview Closeout — 2026-09-25

状态：**PASS / P3 RUNTIME CLOSEOUT / P4-F0 READY**。

Owner 本机隔离预览最终通过：

```text
Runtime authority = a6411fadaeccf644a47ffbf93595d00ce9e5b04b
Docker project    = hbos-portal-preview
Preview Site      = portal-preview.localhost
Portal            = http://127.0.0.1:5179
Frappe            = http://127.0.0.1:18091
```

验证完成：

```text
Portal Home                       PASS
App Center                        PASS
My Work                           PASS
Attendance Portal Navigation      PASS
Inventory Portal Navigation       PASS
LIMS Portal Navigation            PASS
Portal native /hbos routes        PASS
Frappe Session across navigation  PASS
Inventory Summary                 PASS
Three-App Registry                PASS
New anonymous volumes             0
Formal workspace                  PRESERVED
Formal Docker runtime             PRESERVED
Formal volumes                    PRESERVED
Formal frontend Site              PRESERVED
```

最终实际落地点：

```text
Attendance -> http://127.0.0.1:18091/desk/hbos-attendance-dashboard
Inventory  -> http://127.0.0.1:18091/desk/hbos-photo-intake
LIMS       -> http://127.0.0.1:18091/hbos-lims/dashboard
```

因此：

```text
P3 Three-App Workspace Integration = COMPLETE / LOCAL + REMOTE RUNTIME PASS
P4-F0 Runtime Screenshot / Journey Baseline = READY
```

P4 开始后仍执行前端 Gate：真实页面审计 → 原型 / 视觉方案 → Owner 审查 → 单 App 实施，不允许三个 App 同时直接大规模改代码。
