> **G4 隔离联调修复中（2026-10-27）**：旧测试组合 97e0272 实际发现岗位为空、个人中心卡片 top 偏移重叠；前后端各自修复后须新 SHA 构建复测。旧组合不计 G4 PASS，产品仍为 22b47dc，未发布。

# 项目状态

> **2026-10-27 R6-B / G3_IMPLEMENTING**：#62 与 #61 已分别按 Owner 精确授权正常 Squash，实际产品基线为 `22b47dcdcc17e8dfd0f0640d2b9a04ec14303b0b`。实际提交四个 CI 作业通过。R6 从该 SHA 的 `feat/hbos-r6b-experience-v1` 实施，固定设计依据 R6-A2.2 / v1.3；G4 真实权限与浏览器验收、G5 独立审查及固定 SHA 合并、G6 统一构建/标签/团队发布尚未完成。`TEAM_PULL_READY=PENDING`，未生产上线。详见 [本轮主记录](milestones/Portal_R6B_正式管理体验与稳定集成.md)。以下按日期保留的旧状态为历史。


> **2026-10-27 #62 旧站点登录兼容修复 / REVIEWING**：Owner 已授权修复旧站点在非试点且关闭自动开户时可能重新开放飞书登录的问题。修复保留该旧关闭语义，并仅在显式试点名单有效时允许关闭自动开户的受控登录；原身份、权限和 proof 合同不变。新增入口及旧回调拒绝负例，Python 3.11/3.12 各 248 项本地测试通过。当前候选尚未部署，最终 GitHub HEAD 的 CI、非作者身份安全审查和固定 HEAD/base 的独立合并授权仍须核对；#61/#62 均未合并，未批准标签或生产发布。历史首通证据见下文。

> **2026-10-26 R5-B 真实首通已核验 / REVIEWING**：产品基线 `1a0d44de1399afca513855f3688eb06c1978429e`。Owner 已本人完成 Administrator 绑定并确认飞书登录；官方回调、企业和在职成员校验成功，真实飞书签发会话的同 User、工作台/IAM/库存/LIMS 读取、原生退出与旧会话重放拒绝已核验，密码登录仍有效，未复制 User/Employee 或新增角色。仅本人 Administrator 试点，自动开户关闭。视觉 Draft #61、认证 Draft #62 均暂缓合并；最终页面/管理员使用验收和专门审查门禁分别记录，不代表生产发布。见 [本轮记录](milestones/Portal_R5B_受控飞书登录候选.md)。以下各日期内容保留历史含义。


## 历史集成状态 — 2026-10-19

**四个完整业务 PR 已实际合并：#42 考勤、#46 生产、#39 仓储、#43 LIMS。** 唯一目标为 `feature/hbos-portal-product`。业务合并基线为 `04e0bb033cb2e7156e407cf49a7b6966b0d2a022`，状态文档在其后维护；不把后续文档提交的 HEAD 当作已经运行过的业务提交。#43 于 2026-10-19 03:28:29 UTC 正常 Squash Merge，REST 已核对实际单父 `366b3ad5ceba7fbc417bb3cd8ba93b12e57a7857` 与树 `aeb1c8d3db671cb6b3e60cb5f7175f5fd620e620`。

**合并前 R10：PASS；实际产品 R11：PASS。** [R10 39184807396](https://github.com/zjl327707743/HBOS-Platform/actions/runs/39184807396) 与 [R11 39195037712](https://github.com/zjl327707743/HBOS-Platform/actions/runs/39195037712) 均为全部 10 jobs SUCCESS；R11 五个原生域直接运行实际产品 `04e0bb033cb2e7156e407cf49a7b6966b0d2a022`，已核单父、树、双 migrate 与清理。LIMS 原有 32 项、新增审计 9 项、独立 Todo 1 项，共 42 项原生测试全部通过；Todo 只有 1 项，归属 LIMS。

### 四项实际合并与来源

| 完整业务 PR | 合并前正式来源 HEAD | 实际 Squash | 实际父提交 | 实际产品树 |
| --- | --- | --- | --- | --- |
| [#42 考勤](https://github.com/zjl327707743/HBOS-Platform/pull/42) | `5780924fb000c869ddf7e23afa76e2f95fe15ea8` | `374e2bd8633d4127fabcc4659c2314e4a7ca7cd8` | `45658fe4b84d8fb7dd4433c459aa30572e0d13d3` | `31097c5f9e6f245ecbaca779643c421a4458bee8` |
| [#46 生产](https://github.com/zjl327707743/HBOS-Platform/pull/46) | `3f0e8847f2769025d764214ae56950fe97693808` | `4ddf9bebe5bd9f0d73cdb84bd4ddfa9b8615ad30` | `374e2bd8633d4127fabcc4659c2314e4a7ca7cd8` | `dabf7846817f096434949bc38a48c7cc4ec958bd` |
| [#39 仓储](https://github.com/zjl327707743/HBOS-Platform/pull/39) | `463284fea3a3094f689611d63704c19931f5d437` | `a1cc65dde73cfad656faf290264f75fb1a25c32b` | `4ddf9bebe5bd9f0d73cdb84bd4ddfa9b8615ad30` | `43b59653ebbe61db530f523ea980163c88f1899e` |
| [#43 LIMS](https://github.com/zjl327707743/HBOS-Platform/pull/43) | `06e4639fe8efeda9d1874b0eb5d5d33706be98d2` | `04e0bb033cb2e7156e407cf49a7b6966b0d2a022` | `366b3ad5ceba7fbc417bb3cd8ba93b12e57a7857` | `aeb1c8d3db671cb6b3e60cb5f7175f5fd620e620` |

#39 于 2026-10-18 07:28:34 UTC 正常 Squash Merge。前三项来源分别保存在 `archive/owner-r3-pr42-5780924-20261018`、`archive/owner-r3-pr46-3f0e884-20261018`、`archive/owner-r3-pr39-463284f-20261018`。#39 来源分支在合并后自动删除，固定来源仍由上述 archive 引用保存。#55 Item 只读增量此前已合并，当前保留唯一入口；本次 #39 才是完整仓储合并。#49 既有已合并事实保持。#43 最终来源已保存并回读为 `archive/owner-r3-pr43-06e4639-20261019`，指向 `06e4639fe8efeda9d1874b0eb5d5d33706be98d2`。#57 文档收口此前已形成 `366b3ad5ceba7fbc417bb3cd8ba93b12e57a7857`，是本次 #43 的真实产品父提交；它不计作第五个业务 PR。

#42 的 [Owner Approve](https://github.com/zjl327707743/HBOS-Platform/pull/42#pullrequestreview-5561462238) 与 #46 的 [Owner Approve](https://github.com/zjl327707743/HBOS-Platform/pull/46#pullrequestreview-5561524421) 对应上表来源。#39 由 [Owner 最终审查评论 6247133194](https://github.com/zjl327707743/HBOS-Platform/pull/39#issuecomment-6247133194) 按本批次授权承接审查责任，逐项关闭 B1 四报表跨仓读取、B2 Send to Subcontractor 和普通 Material Transfer 到已登记外协仓的放行旁路；[旧 Review 5486039245](https://github.com/zjl327707743/HBOS-Platform/pull/39#pullrequestreview-5486039245) 已为 **DISMISSED**。#39 作者为 Owner，未伪造自我 Approve；历史 Review、失败与原始来源均保留。#43 的 [Owner Approve 5566593947](https://github.com/zjl327707743/HBOS-Platform/pull/43#pullrequestreview-5566593947) 对应本表最终来源与 R10 精确组合；原审查及失败记录继续保留。

### R10 合并前精确组合 — 2026-10-19

产品 base `366b3ad5ceba7fbc417bb3cd8ba93b12e57a7857` 与 #43 正式 source `06e4639fe8efeda9d1874b0eb5d5d33706be98d2` 的实际组合树为 `aeb1c8d3db671cb6b3e60cb5f7175f5fd620e620`，与实际 Squash 树相同。R10 全部 10 jobs SUCCESS；它是合并前组合证据，不替代 R11 对真实单父产品提交的回归。

R10／R11 各自的十个 jobs 中，冻结 `1a8f49251dc818859336ee70fbf81dcef87c0bfd` 的旧契约作业仍仅证明旧来源；当前 LIMS 完整契约已分别在 R10 实际组合的 [offline Job 117844865393](https://github.com/zjl327707743/HBOS-Platform/actions/runs/39184807396/job/117844865393) 与 R11 实际产品的 [offline Job 117875877290](https://github.com/zjl327707743/HBOS-Platform/actions/runs/39195037712/job/117875877290) 中独立运行，未用旧来源结果替代当前契约证据。

| R10 验证范围 | 实际结果与证据 |
| --- | --- |
| 离线、契约与双构建 | [Job 117844865393](https://github.com/zjl327707743/HBOS-Platform/actions/runs/39184807396/job/117844865393) SUCCESS；593 PASS、42 项 skip、5976 个 subtests 分列记录，skip 不计为原生通过；Portal 前端 190 项、LIMS 前端 10 项、双构建及契约检查通过 |
| LIMS 原生 | [Job 117844865453](https://github.com/zjl327707743/HBOS-Platform/actions/runs/39184807396/job/117844865453) SUCCESS；原有 32 项原生验证与新增 9 项审计验证均 0 failure / 0 error / 0 skip，R3 runner 的 47 组检查 PASS（含 12 项质量父／子表负向）；两种计数口径分列，不相互替代 |
| 考勤原生 | R10 对同一实际组合的范围、权限负向及会话回归 SUCCESS |
| 生产服务原生 | R10 同组合 28 PASS / 0 FAIL / 0 SKIP；保持真实 Frappe → HTTP → FastAPI → 合成上游与权限、失败恢复、关闭 AI 的门禁 |
| 仓储报表与附件原生 | R10 同组合 22 项 HTTP、8 项跨仓 CSV、74 项卡证／权限检查通过 |
| 仓储事务原生 | R10 同组合 8/8 PASS；真实库存账与 GL、LIMS 放行后出库、两种外协提交／取消及自动制证权限闭环通过 |

### R11 实际业务产品合并后回归 — PASS

[R11 39195037712](https://github.com/zjl327707743/HBOS-Platform/actions/runs/39195037712) 使用 runner `f870a68b5c10ae244fd8df888b499ce84bd0908c`、runner tree `8caab22aba170c16d348092e4dc0707db93316b0`，全部 10 jobs SUCCESS。五个原生域的 base、source 与实际运行 commit 均为 `04e0bb033cb2e7156e407cf49a7b6966b0d2a022`，直接检出产品，无额外 merge；实际单父均为 `366b3ad5ceba7fbc417bb3cd8ba93b12e57a7857`，树均为 `aeb1c8d3db671cb6b3e60cb5f7175f5fd620e620`。各原生 Site 的两次 migrate 与清理均成功，退出码为 0。

| R11 实际产品验证 | 实际结果与直接证据 |
| --- | --- |
| LIMS 原生 | [Job 117875877169](https://github.com/zjl327707743/HBOS-Platform/actions/runs/39195037712/job/117875877169) SUCCESS；R3 runner 47 组检查全 PASS，无 FAIL 或 NOT_RUN；原有 32 项、新增审计 9 项、独立 Todo 1 项合计 42 项原生测试通过，均无 failure／error／skip |
| 考勤原生 | [Job 117875877444](https://github.com/zjl327707743/HBOS-Platform/actions/runs/39195037712/job/117875877444) SUCCESS；实际产品的范围、权限负向及会话回归通过 |
| 生产服务原生 | [Job 117875877412](https://github.com/zjl327707743/HBOS-Platform/actions/runs/39195037712/job/117875877412) 28 PASS / 0 FAIL / 0 SKIP；真实服务链、权限拒绝及失败恢复通过 |
| 仓储报表与附件原生 | [Job 117875877374](https://github.com/zjl327707743/HBOS-Platform/actions/runs/39195037712/job/117875877374) 22 项 HTTP、8 项跨仓 CSV、74 项卡证／权限检查通过 |
| 仓储事务原生 | [Job 117875877351](https://github.com/zjl327707743/HBOS-Platform/actions/runs/39195037712/job/117875877351) 8/8 PASS；真实库存账、GL、放行后出库、两种外协提交／取消与自动制证权限回归通过 |
| 离线、契约与双构建 | [Job 117875877290](https://github.com/zjl327707743/HBOS-Platform/actions/runs/39195037712/job/117875877290) SUCCESS；593 passed、42 skipped、5976 个 subtests 分列，离线 skip 不折算为 PASS；Portal 前端 190 项／20 文件、LIMS 前端 10 项与双构建通过，原生验证见上述独立作业 |

独立 Todo 是 LIMS 的 1 项既有原生测试，在同一合成 Site 使用真实 LIMS Manager（无 System Manager 身份），结果为 1 passed / 0 failure / 0 error / 0 skip。原测试文件 SHA-256 为 `ae34b6b5a2a2e685cf86b5eeff01de57a5287172f5583f0bcac6fe30ec6324b4`；finally 的 rollback 与恢复 Administrator 均为 true。计数为原有 32 + 审计 9 + Todo 1 = 42，不与 runner 的 47 组检查或离线 subtests 累加。

### 独立 CI 事件与测试夹具收口

实际产品 push 的 [Backend 39194854851](https://github.com/zjl327707743/HBOS-Platform/actions/runs/39194854851) 与 [Frontend 39194854885](https://github.com/zjl327707743/HBOS-Platform/actions/runs/39194854885) 已 SUCCESS。

既有 Draft [#15](https://github.com/zjl327707743/HBOS-Platform/pull/15) 从产品分支指向 main，其自动 `pull_request` 事件的 [Quality Gate 39194859711 / Job 117875314410](https://github.com/zjl327707743/HBOS-Platform/actions/runs/39194859711/job/117875314410) 因 Python 3.10 测试夹具失败而为 FAIL。该原始失败作为历史保留。本次 docs/test 收尾只修正两个测试夹具的特殊属性处理，业务源码与测试断言保持不变；本收尾 PR 必须在固定候选 SHA 的 Python 3.10／3.12 检查通过后方可合并，实际结果以本 PR 最新 Owner 裁定及最终报告所列 SHA／Job 为准。此处不提前声明修复后 PASS，不涉及 main 合并或仓库保护规则变更，也不把 R10／R11 的指定事件成功概括成仓库所有 CI 均成功。

### 保留的历史验证边界

[Run9 39146339006](https://github.com/zjl327707743/HBOS-Platform/actions/runs/39146339006) 的失败、当次来源与夹具前提按原始作业和 [PR #56](https://github.com/zjl327707743/HBOS-Platform/pull/56) 保留，后续修复和 R10 通过不回写其历史结论。Run8 对应 #39 后的 `a1cc65dde73cfad656faf290264f75fb1a25c32b`，当时 #43 的独立契约不构成产品组合证据；该限制属于当次记录。

### Run8 实际产品合并后回归 — 2026-10-18

**合并后回归：PASS。** [Run8 39107944012](https://github.com/zjl327707743/HBOS-Platform/actions/runs/39107944012) 全部 8 jobs SUCCESS；四个业务域直接检出实际产品 `a1cc65dde73cfad656faf290264f75fb1a25c32b`，记录 `post_merge_baseline`，源码树为 `43b59653ebbe61db530f523ea980163c88f1899e`、唯一父提交为 `4ddf9bebe5bd9f0d73cdb84bd4ddfa9b8615ad30`。仓储事务 8/8、报表22项HTTP与8项跨仓CSV、卡证权限74/74、考勤原生范围及生产28项检查均通过；所有原生Site双migrate与清理通过。完整来源与后续文档提交见 [PR #56](https://github.com/zjl327707743/HBOS-Platform/pull/56)，不以文档提交后的新HEAD冒充上述已运行提交。

固定 runner `af5d3f3edcba5f7c80a096618216396256e89f3f`，runner tree `f18f8a83d9d0f2247b240270587d58939206f1a0`；四个业务域的 base、source和运行commit均为实际产品 `a1cc65dde73cfad656faf290264f75fb1a25c32b`，没有构造新的业务组合。GitHub Run整体SUCCESS，源树与实际单父再次核对。

| 实际产品回归 | 结果与直接证据 |
| --- | --- |
| 考勤原生 | [117617740704](https://github.com/zjl327707743/HBOS-Platform/actions/runs/39107944012/job/117617740704) SUCCESS；真实来源范围、同会话grant/revoke、离职/孤立/零员工、CSV403、Prepared拒绝及私有文件撤权、夹具恢复通过 |
| 生产服务原生 | [117617740697](https://github.com/zjl327707743/HBOS-Platform/actions/runs/39107944012/job/117617740697) 28 PASS/0 FAIL/0 SKIP；真实Frappe→FastAPI→合成上游、权限负向、60秒超时与恢复、AI模型/上游写入0、凭据扫描和默认拒绝通过 |
| 仓储报表与附件 | [117617740555](https://github.com/zjl327707743/HBOS-Platform/actions/runs/39107944012/job/117617740555) 22HTTP＋8跨仓CSV＋74/74权限检查通过；真实两页PDF正文/哈希、owner/DocShare、变形写入、同cookie撤权通过 |
| 仓储真实事务 | [117617740681](https://github.com/zjl327707743/HBOS-Platform/actions/runs/39107944012/job/117617740681) 8/8 PASS，无NOT_REACHED；真实放行后Material Issue与两种外协提交/取消、原生库存账/GL、三种自动PDF权限和同进程恢复通过 |
| 完整离线与双构建 | [117617740690](https://github.com/zjl327707743/HBOS-Platform/actions/runs/39107944012/job/117617740690) SUCCESS；考勤540/0skip，LIMS402/10原生环境skip，库存173/1上游源码环境skip，Portal84/0skip，生产41/AI26；Portal前端171/19文件、LIMS前端10项与双构建通过 |

另外两项考勤/生产offline作业及#43固定独立来源契约作业同样SUCCESS，总计8个jobs。#43那项仍只验证 `1a8f49251dc818859336ee70fbf81dcef87c0bfd` 的39/39契约和4mutation，不是本轮实际产品包含#43的证明。普通生产角色保持默认拒绝，IAM V1未实施；仓储报表夹具没有过账，账务证据来自独立事务Site。全部原生Site的双migrate、权限/撤权和清理结果已读日志确认。

### Run7 合并前最终门禁 — 2026-10-18

[Run7 39107142955](https://github.com/zjl327707743/HBOS-Platform/actions/runs/39107142955) 固定 runner `9a3a6a6b99452accdc69583dfb663ba441934146`，**全部 8 jobs SUCCESS**。库存两个原生域基于产品 `4ddf9bebe5bd9f0d73cdb84bd4ddfa9b8615ad30` 与来源 `463284fea3a3094f689611d63704c19931f5d437` 普通合成，实际组合树 `43b59653ebbe61db530f523ea980163c88f1899e` 与最终 Squash 树一致。仓储当前来源的六项正式 GitHub CI 均 SUCCESS，逐项链接及共享文件审查见上述 Owner 评论。

| 验证范围 | 当前来源实际结果 | 证据及准确边界 |
| --- | --- | --- |
| 四报表及跨仓 CSV | **22 项 HTTP 符合预期、8/8 CSV 拒绝** | [报表 Job 117615367652](https://github.com/zjl327707743/HBOS-Platform/actions/runs/39107142955/job/117615367652)：12 次授权读取200、10次跨仓／角色拒绝403；CSV在原生export已授权下全部403、无跨仓数据泄漏。该站点仅报表夹具，`stock_posting=NOT_RUN` |
| 扫码／打印／卡证／私有附件 | **74/74 PASS** | 同一报表 Job：原生Warehouse范围、owner／DocShare、私有URL／fid／download／ZIP、文件改写／别名及同cookie撤权均通过；普通私有Batch附件授权行为保留 |
| 真实库存与账务 | **8/8 场景 PASS，无 NOT_REACHED** | [事务 Job 117615367143](https://github.com/zjl327707743/HBOS-Platform/actions/runs/39107142955/job/117615367143)：收货／取消、盘点100→123→100、内部隔离与跨公司拒绝；纯Stock User不能擅自盘点提交／取消 |
| 产品既有 LIMS 放行与 Material Issue | **完整正反例 PASS** | 真实检验、复核、COA发布、Batch六字段投影；待检拒绝，放行后100→93，GL两条平衡；取消恢复100、GL四条逐账户反转。PDF失败注入后的回滚也通过 |
| 两种已登记外协出库 | **待检拒绝、放行后提交及取消均 PASS** | 真实SCO下 Send to Subcontractor 与普通 Material Transfer：待检417且库存未动；放行后A99／外协1，取消恢复100／0。相同库存账户的两次移库GL前后均0行，未伪造账务 |
| 三种原生收货自动制证 | **3/3 PASS** | 纯Stock User、A仓受限用户及同进程恢复：真实SBB/SBE/SLE/GL、PDF正文与私有归属；受限receiving-owner下载／ZIP403，伪造flags、私有RPC、手动再生拒绝与context／打印flag恢复均通过 |
| 精确组合离线回归与构建 | **SUCCESS** | [Job 117615367160](https://github.com/zjl327707743/HBOS-Platform/actions/runs/39107142955/job/117615367160)：各领域后端、Portal前端171项、LIMS前端10项及双构建通过；原生环境相关skip单列于Owner评论，不折算为原生PASS |
| 考勤／生产产品基线复核 | **SUCCESS** | [考勤 native](https://github.com/zjl327707743/HBOS-Platform/actions/runs/39107142955/job/117615367156)、[生产 native](https://github.com/zjl327707743/HBOS-Platform/actions/runs/39107142955/job/117615367259) 与各自offline作业成功，验证对象为已合入两项业务的 `4ddf9bebe5bd9f0d73cdb84bd4ddfa9b8615ad30`；合并后整棵新产品回归见上方 Run8 |
| #43 独立来源契约 | **39/39 契约＋4项mutation PASS；NOT_PRODUCT_COMPOSITION** | [Job 117615366938](https://github.com/zjl327707743/HBOS-Platform/actions/runs/39107142955/job/117615366938) 仅验证独立来源 `1a8f49251dc818859336ee70fbf81dcef87c0bfd`，#43仍未合入产品 |

实际报表PDF为两页、67,338字节，正文含A/B仓库及数量；授权下载与ZIP内原件哈希一致，SHA256为 `4c72a2c08856efa8aa8a6a23aea1b58f65589946cbe5044f180426177a2913b2`。Frappe16.26.3／ERPNext16.26.2、固定HRMS、独立合成Site、双migrate与资源清理已通过；未单独验证PDF金额字段或实体打印。

当前权限口径：二维码保留原生Warehouse可见范围内全部字段；全批次卡读取要求全仓范围；受控原生收货只生成本次提交批次的私有附件，不授予后续读取／下载权限，手动再生仍需Batch.write与全仓范围。外协目标识别依据原生已提交SCO／外协PO登记；历史上名称和URL都已丢失卡证识别信息的附件仍为 `NOT_COVERED`；Stock Balance客户端CSV与四报表原生export证据分列。

以上 Run7／Run8 为各自历史业务基线的验证记录，#43 的实际合并与新产品回归见页首。IAM #52、OCR、真实样本、实体打印、生产 UAT／部署继续独立；本轮未合 main、未整包合 #37，未操作 Owner Mac 既有项目或真实业务库。库存单据取消与 GL 反转不构成 LIMS 质量放行撤回流程的证明，现有已放行样品仍为终态。

Run1–6的真实失败完整保留在 [PR #56](https://github.com/zjl327707743/HBOS-Platform/pull/56)；以下Run6、Run5及更早阶段均为有日期的历史快照，其中的“当前”“未通过”“未合并”只指该次记录，实际状态以页首和最新PR为准。

## 验证历史 — 2026-10-18 Run6

已执行快照：产品 base `4ddf9bebe5bd9f0d73cdb84bd4ddfa9b8615ad30`，库存来源 `2119e26e9eb8bd5a17b56e1ddf70d1483e9c5416`，来源树 `c2a4cfeab7de4b879174b3acdf7058b2f0adc214`。该来源 SHA 只标识 Run6，不是本文件保存后的来源 HEAD。

| 验证 | 正式结果 | 准确边界 |
| --- | --- | --- |
| [报表、扫码与附件原生 Job 117603810152](https://github.com/zjl327707743/HBOS-Platform/actions/runs/39103298497/job/117603810152) | **74 PASS / 0 FAIL** | 实际 2 页 PDF 的 A/B 仓正文、哈希与产物复核通过；跨仓、下载、owner/DocShare、zip、改写及撤权检查通过，不代表真实环境或实体打印验收 |
| [事务原生 Job 117603810103](https://github.com/zjl327707743/HBOS-Platform/actions/runs/39103298497/job/117603810103) | **6 PASS / 2 FAIL** | 既有三项账务和三项自动收货制证通过；整个事务 Job 仍为 FAIL |
| 自动制证 | 三项均 PASS | 纯 Stock User、A 受限用户及同进程收货均有真实 SBB/SBE/SLE/GL；PDF 仓库 A/B 与数量正确。受限 receiving-owner 的私有 URL/download/zip 为 403；伪造 flags、私有 RPC、手动再生拒绝及 context/打印 flag 恢复通过。未单独验 PDF 金额字段 |
| 外协与 LIMS 完整链 | 待检拒绝已观察，完整链未完成 | Send to Subcontractor 待检提交 417；普通 Material Transfer 到已登记外协仓也被拒绝且库存未动。实际 publish/release 及六个投影字段正确，但测试按单一 URL 误选 Batch File，导致两项案例失败；放行后的两种外发 submit/cancel 均为 **NOT_REACHED** |

Run5 的 CMap/PDF 内容失败和已登记外协待检旁路已有上述复验证据；仍不能由部分通过推定未到达的出库、取消链通过。Run6 失败保留为真实历史结果，等待新来源的 Run7，不通过删除断言、删除合法附件或降低权限要求转绿。

## 验证历史 — 2026-10-18 Run5

以下保留 Run5 当时的观察与判断，其中“当前”“尚未通过”“原因待定位”均指该次验证；后续状态以页首“当前集成状态”和实际 PR 记录为准。

**当前结论：两个完整业务 PR 已合并，#39 仓储技术门禁未通过，尚未合并。** 唯一目标为 `feature/hbos-portal-product`；#42 考勤实际 Squash 为 `374e2bd8633d4127fabcc4659c2314e4a7ca7cd8`，#46 生产实际 Squash／本记录已核对产品为 `4ddf9bebe5bd9f0d73cdb84bd4ddfa9b8615ad30`。来源、审批和合并后证据见下方对应记录。

本次 Run 5 验证快照：产品 base `4ddf9bebe5bd9f0d73cdb84bd4ddfa9b8615ad30`，仓储来源 `bb74cb3c5143b5319219ef352188dda462e80ff4`，运行器 `9790397d7bf8478972de68ac73439fd468ed4b8e`。后续最新来源、门禁和实际 Squash 以 [PR #39](https://github.com/zjl327707743/HBOS-Platform/pull/39)、[PR #56 验证记录](https://github.com/zjl327707743/HBOS-Platform/pull/56) 及远端产品 ref 为准；这些 SHA 是已经发生的验证快照，不是文档提交后的新产品 HEAD。

| 验证范围 | Run 5 已观察结果 | 仍未满足的门禁 |
| --- | --- | --- |
| 库存报表、扫码及附件权限 | [原生 Job 117600061266](https://github.com/zjl327707743/HBOS-Platform/actions/runs/39102020894/job/117600061266)：74 项中 73 PASS、1 FAIL；扫码、跨仓拒绝、下载、File owner／DocShare、zip、改写与撤权检查通过 | 真实 PDF 返回 200、2 页，但提取正文缺 A/B 仓标识，内容断言 FAIL，原因待定位 |
| 真实库存和账务 | [事务 Job 117600061186](https://github.com/zjl327707743/HBOS-Platform/actions/runs/39102020894/job/117600061186)：8 个场景中 3 PASS、5 FAIL；Run 4 已通过的收货／取消、对账 `100→123→100`、内部移库与跨公司拒绝在本次继续 PASS | 完整事务门禁仍 FAIL，不能以前三项通过代表整个仓储可合并 |
| 既有产品 LIMS 完整放行链 | 真实 COA 渲染和注入 PDF 失败后的回滚检查 PASS | 后续链遇到 `AssertionError`，待定位；不能记为完整放行出库通过 |
| 注册外协目标移库 | 已建立真实 `SC-ORD-2026-00001`；普通 Material Transfer `MAT-STE-2026-00010` 使待检批次进入外协仓 1 单位（HTTP 200），随后原生 cancel 恢复库存 | 已确认放行旁路，必须修复并重验；同公司目标不能自动视为普通内部货位 |
| 纯 Stock User 自动制证 | 三场景均产生真实私有 Batch PDF，owner 和本单 SBB/SBE/SLE/GL 来源核验通过；同进程 ContextVar／打印 flag 恢复及后续直接再生拒绝的前置断言已通过 | 三场景均在 PDF 仓库正文断言处 FAIL；后续 HTTP 下载与伪造参数负例为 `NOT_REACHED`，不得记 PASS |

Run 5 后的新候选已完成 PDF CMap 处理与已登记外协目的仓识别的最小修复，原生复验待运行；上表保留 Run 5 的真实失败记录，不提前将新候选记为 PASS。

#43 LIMS 独立增量仍后置。独立候选 `1a8f49251dc818859336ee70fbf81dcef87c0bfd` 的 [契约 Job 117600061138](https://github.com/zjl327707743/HBOS-Platform/actions/runs/39102020894/job/117600061138) 已通过 39/39 契约和 4 项 mutation 检查，但证据级别为 **NOT_PRODUCT_COMPOSITION**，不替代它与最新产品、仓储的组合验证。

#39 候选的当前权限口径：扫码保留获授权 Warehouse 范围内的全部字段；全批次卡证读取要求全仓读取范围；受控原生收货可生成其私有衍生附件，但不授予收货人后续读取、下载或手动再生权限。手动再生仍要求 Batch.write 与全仓范围。历史附件若在修复前已同时改掉文件名和 URL 的库存卡标识，仍为 `NOT_COVERED`。

本轮只使用远端源码与云端合成 Site，未操作 Mac 既有项目、真实业务库或生产。#37 不在任务范围，IAM #52 保持独立。M3-R6 的 OCR、置信度与实体打印验收不因本次代码集成自动完成。以下按发生阶段保留历史证据，其中“当前”“本轮”只适用于对应记录。

# 历史记录：2026-10-18 考勤和生产已实际合并

最新已核对产品基线为 `4ddf9bebe5bd9f0d73cdb84bd4ddfa9b8615ad30`，实际父提交为考勤基线 `374e2bd8633d4127fabcc4659c2314e4a7ca7cd8`，代码树为 `dabf7846817f096434949bc38a48c7cc4ec958bd`。

完整 [#46 生产 PR](https://github.com/zjl327707743/HBOS-Platform/pull/46) 已普通 Squash Merge，来源 `3f0e8847f2769025d764214ae56950fe97693808` 保存于 `archive/owner-r3-pr46-3f0e884-20261018`；[Owner 正式审批](https://github.com/zjl327707743/HBOS-Platform/pull/46#pullrequestreview-5561524421) 与当前树的五项 CI、[28项真实服务链验证](https://github.com/zjl327707743/HBOS-Platform/actions/runs/39098816237/job/117590685169) 均已核对。服务/AI 41+26项、Portal前端146项通过，AI模型调用与上游写入均为0。普通生产角色仍默认拒绝，Administrator 例外明确；代码集成不代表启用真实服务或完成车间范围授权。

#39 仓储正在新基线上继续真实库存、账务、外协放行、二维码与打印附件权限门禁；#43 LIMS 独立增量后置。当前远端产品 ref 与各 PR 的实际合并记录是后续更新的权威；下面保留每阶段的历史证据。

# 2026-10-18 Owner 业务集成：首个完整业务已合并

**#42 考勤已实际 Squash Merge** 到唯一产品分支 `feature/hbos-portal-product`。新产品提交为 `374e2bd8633d4127fabcc4659c2314e4a7ca7cd8`，父提交为 `45658fe4b84d8fb7dd4433c459aa30572e0d13d3`，树为 `31097c5f9e6f245ecbaca779643c421a4458bee8`；与已审批、已测试的真实组合相符。来源 `5780924fb000c869ddf7e23afa76e2f95fe15ea8` 保存在 `archive/owner-r3-pr42-5780924-20261018`。

证据：[实际 PR #42](https://github.com/zjl327707743/HBOS-Platform/pull/42)、[当前来源 Owner 审批](https://github.com/zjl327707743/HBOS-Platform/pull/42#pullrequestreview-5561462238)、[原生权限与导出补充验证](https://github.com/zjl327707743/HBOS-Platform/actions/runs/39097688048/job/117587422856)。批次最终审批由 Owner 承担，依据 [本批次正式裁定](governance/HBOS_Owner_业务集成批次裁定_20261018.md) 执行，不伪造另一位人工审批，也不减免技术门禁。

后续以每次合并后的真实产品 HEAD 顺序验证 #46 生产、#39 仓储，#43 LIMS 独立增量后置。#55 物料只读子范围此前已合并；完整仓储不能据此算作完成。生产原生服务链、仓储库存账务和质检放行各以当前来源 SHA 的实际运行结果为准。历史环境验收不等于本轮部署；本轮仅使用远端源码与新建的云端合成 Site。

## 历史记录：2026-10-18 仓储物料只读候选

本轮从 #39 固定 HEAD `136e90dc102cc40d294650b8f463ac2e709c92cb` 单独提取物料浏览，使用已有 Portal Shell、原批准主从页面和 Frappe Item 原生 ACL。候选新增列表/搜索/详情与深链，保留库存原 Desk 默认入口；不携带 SQL 报表、二维码、附件导出、库存写入、调账、放行、角色或 Schema 修改。

本增量仅供非生产产品开发分支使用；实际合并与 CI 以 [PR #55](https://github.com/zjl327707743/HBOS-Platform/pull/55) 固定 HEAD 及最终 squash 为准。完整 #42/#43/#46/#39 均仍受各自高风险人工审查及运行门禁约束，不因本子范围进入代码基线而完成。真实 Site、IAM #52、main、Owner 本机项目均未操作。物料可见范围是既有 Item ACL，不等于仓库范围；无可见记录与服务失败明确区分。

# 项目状态

## 2026-10-10 HBOS 多 APP 集成治理（产品分支）

制定 `docs/governance/HBOS_CONCURRENT_APP_INTEGRATION_V1.md` 作为并行开发、PR 粒度与分批合并协作规范：Portal 任务以当前产品分支为基线，领域增量与共享入口分离，拉代码不自动 migrate。此项仅为治理文档，不代表 #33/#34/#37 的高风险代码或 #30 知识库已合并、不代表原本本机运行版本已更新。正式合并/验收按各 PR 最新 SHA 独立记录。


## 并行权限治理 IAM-0 — 2026-10-01

Owner 已批准进入统一身份与权限治理。当前仅交付设计、角色—动作—范围矩阵、只读源码盘点工具与本机任务书；实际 Site 盘点和隔离验收仍为 NOT_RUN，不修改账号、角色或业务数据，不替代原账号收尾。入口：[IAM-0 治理资料](governance/iam/README.md)。

## PR #21 合并后收口 — 2026-10-01

状态：**FINAL_REVIEW_PASS / MERGED_TO_PORTAL_PRODUCT**。PR #21 已使用 expected-head squash 合入 `feature/hbos-portal-product`，产品 HEAD `e4b16ee80aaaf21aac2304246a4de1f9fe8995ea`；Owner 最新无破坏验收 PASS，团队合成浏览器 final-submit 3/3 PASS，新 squash 四项 CI SUCCESS。旧 #22 已关闭未合并，IAM-0 由 clean Draft PR #23 仅承接原 11 文件增量；PR #15 仍 Open Draft，main 未变化。

合并前发现并修复的原生 MFA Administrator proof P1 已完成回归；本次收口未修改 Owner 密码、MFA、飞书绑定、Secret、业务数据或 P1 卷。合并前 BLOCKED/WAITING 状态继续作为历史证据保留，但不再作为当前项目状态。

团队后续 Portal Authority：`feature/hbos-portal-product@e4b16ee80aaaf21aac2304246a4de1f9fe8995ea`。

## 账号小范围收尾 — 2026-10-01

本轮接续交付基线 `eee1c5e22c57be3436244e77c65e189bd7eee242` 与 PR #21，仅做资料登录渠道、唯一个人导航、折叠偏好说明、飞书头像同步及 C03/C07/C09/F03 缺项补测；不重新全量审计、重画页面或新增账号功能。真实 Administrator 已成功飞书登录为 USER_CONFIRMED_SUCCESS，绑定、密码、MFA、Secret、企业与回调保留。本机沿用既有 P1 Site/Compose/入口，发布分支不合并、不强推、不推 main/base。 补测确认并修复参与页期限遗漏与 GET 回调未提交记录，原矩阵历史保持；最终浏览器新凭据步骤由工具要求人工接手，团队脚本与未执行状态单列。


项目：新乡海滨智能运营管理平台。架构：Frappe/ERPNext 开源底座 + Frappe 多 App 模块化架构 + 外部独立服务扩展。

## 当前 Portal 轮次 — 2026-10-01

本轮（2026-10-01）接续 PR #21，执行登录账号模块 UI 规范回归与全功能审修。Owner 已亲自确认 Administrator 能通过本人飞书验证并登录，记为 OWNER_CONFIRMED_SUCCESS；历史成员权限待审批或登录失败记录不再代表当前事实。保留真实绑定、密码、MFA、Secret、企业与回调；不要求重复配置。认证页沿用已有 Ant Design Vue / ConfigProvider / typography / tokens，修复表单、证明期限、错误状态、同路由目标与提交结果处理。破坏性、并发与交接只在独立合成 Site 验证。新版本真人 OAuth、本人收到验证码、第二位真人交接与移动软键盘结果单独记录，未执行不写 PASS。复用现有 P1 / Compose / 卷与常用入口，最终本机 SHA/build ID、远端提交、CI 和制品须一致。公司服务器为 NOT_DEPLOYED。主记录：`docs/milestones/M1_RP3_统一账号飞书绑定与正式发布.md`。PR #21 head `codex/portal-unified-account-release`、base `feature/hbos-portal-product`；不强推、不自动合并、不推 main/base。

| 项目 | 实际状态 |
| --- | --- |
| 唯一 User 与密码/飞书账号流程 | 统一账号与受控变更已实现并分层测试；密码记录保留；Owner 已确认本人飞书成功登录，新版本正常回归单列 |
| 五应用与已批准前端 | Administrator 五入口实际打开；普通用户按原角色仅开放知识/设备；未实现项明确标注 |
| 备份恢复/保留校验/production 制品 | 当前 P1 原卷已备份并迁移，账号/密码/角色/权限/业务/身份指纹保留；Portal 与 LIMS 编译资产已部署 |
| 通用 Gateway/团队依赖 | 版本化通用代码、Dockerfile、完整 lock 已提供；私有资料不进 Git |
| 真实 PR/CI | [PR #21](https://github.com/zjl327707743/HBOS-Platform/pull/21) 已合并到 Portal 产品分支；当前 CI/制品以产品 HEAD `e4b16ee80aaaf21aac2304246a4de1f9fe8995ea` 为准 |
| 固定 Mac 入口 | P1 的 loopback 同源入口 5188 已运行；本机隐藏设密工具已提供，未自动修改密码 |
| Owner 本人验收 | Owner 已确认 Administrator 本人飞书成功登录；第二位员工开户、本人验证码与交接另行记录，合成测试不替代真人 |
| 公司服务器 | 未部署，固定 IP / 正式 HTTPS 后续；不影响已交付 Mac 状态 |

## 其他既有里程碑

M0 已完成并封板。考勤 M1 产品验收仍由 M1-FIX 主记录维护，不因本轮 Portal 代码测试而 closeout；M1-FIX-F 原状态为 REVIEWING。库存 M2-STOCK-R1 原状态为 IN_PROGRESS，其余独立轮次不由本任务推进。历史记录见 `docs/milestones/` 对应主文档，本公开状态摘要不携带人员、私有路径或内部运行报告。

本轮未回退或重建既有 Portal 开发分支，未重做 P0，未覆盖候选数据库，未重置原密码/角色。Owner 已选择 P1 作为固定本地使用环境；保留原 Site 和数据，未删除数据库、用户、文件或卷。公司生产首次部署另行授权。
