> **2026-10-27 R6 独立安全修复 / G4_IMPLEMENTING**：既有受控开户/关联中仅为Website User准备精确Employee和Company原生限制，保留原生钩子和角色/类型/启用状态核验，并拒绝范围增长或原限制丢失。基线实际产品22b47dcdcc17e8dfd0f0640d2b9a04ec14303b0b；Owner本轮明确授权独立兼容修复与18191合成验证，提案补丁e2fe046269f5f5cd983b908191b84e27ea315da21d5a566178bc91c63708d115。本分支未合并、真实UAT未部署、标签及团队发布未获授权，TEAM_PULL_READY=PENDING。详见 `docs/milestones/Portal_R6_具名HR原生关联兼容修复.md`。下列带日期的状态保留历史含义。

# 项目状态

> **2026-10-27 #62 旧站点登录兼容修复 / REVIEWING**：Owner 已授权修复旧站点在非试点且关闭自动开户时可能重新开放飞书登录的问题。修复保留该旧关闭语义，并仅在显式试点名单有效时允许关闭自动开户的受控登录；原身份、权限和 proof 合同不变。新增入口及旧回调拒绝负例，Python 3.11/3.12 各 248 项本地测试通过。当前候选尚未部署，最终 GitHub HEAD 的 CI、非作者身份安全审查和固定 HEAD/base 的独立合并授权仍须核对；#61/#62 均未合并，未批准标签或生产发布。历史首通证据见下文。

> **2026-10-26 R5-B 真实首通已核验 / REVIEWING**：产品基线 `1a0d44de1399afca513855f3688eb06c1978429e`。Owner 已本人完成 Administrator 绑定并确认飞书登录；官方回调、企业和在职成员校验成功，真实飞书签发会话的同 User、工作台/IAM/库存/LIMS 读取、原生退出与旧会话重放拒绝已核验，密码登录仍有效，未复制 User/Employee 或新增角色。仅本人 Administrator 试点，自动开户关闭。视觉 Draft #61、认证 Draft #62 均暂缓合并；最终页面/管理员使用验收和专门审查门禁分别记录，不代表生产发布。见 [本轮记录](milestones/Portal_R5B_受控飞书登录候选.md)。以下各日期内容保留历史含义。

## 当前集成状态 — 2026-10-19

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

> 知识专项（PR #30，分支 `codex/knowledge-autonomous-r1`）：以下为知识轮次自己的状态记录，保留其原日期含义；是否合入、验收与部署以 [PR #30](https://github.com/zjl327707743/HBOS-Platform/pull/30) 的实际记录为准。

## 2026-10-27 Knowledge RC14 V2

当前为隔离员工体验候选的 REVIEWING / LOCAL_UAT / OWNER_NOT_RUN。采用 Codex Main + 三个真实外部应用执行入口，D 安全后端由 Main 负责；外部完成、失败、超时和 Main 修正如实分列。当前轮次见 [RC14 员工体验候选](milestones/M1_KB_RC14_员工体验候选.md)。真实分数、资料净增、运行版本、费用未知项与 CI 仅认 Owner 私有 RC14 交付，不继承旧 PASS。

受控下载独立授权，默认拒绝；只有精确候选测试范围可开启。PDF 原版式与 Office 派生预览均经原件哈希、当前版本、撤回和当前账号复核。仅本机候选，PR #30 保持 Draft，不合并、不切 P1、不开放正式员工。产品生成仍为批准 DeepSeek，千问 1024 维与 rerank 关闭保持。

## 2026-10-26 RC1.1 执行

承接 RC1。围绕已命中资料的正文证据补足、有限同源章节检索、原目录缓存复用与质量发布、目录返回保留以及隔离恢复副本验证继续收敛。原20题及目标身份保持，首次结果保留；最终实际问答完成率、140项优先资料处理和净新增、时延、CI及回退回执仅认Owner本机 `OWNER_RC1_1_RESULT.md` 与联合锁。新版本仍为待验候选，不据代码测试宣称业务通过。

自动生成仅 deepseek-flash，原千问/1024维与零rerank保持；不合并PR #30、不切P1、不开放员工、正式目录只读。RC1既有两次切换收据保留；RC1.1保留一次计划切换及目录滚动、实际chunk DTO契约两次有据修复，只有Main Agent操作。

## 2026-10-26 Knowledge UAT6 RC1 当前候选

Owner 已授权在现有隔离 UAT6 上收敛 RC1。保留模型配置、原千问 1024 维、零 rerank、融合后排序修复、MCP 负向和页面软复核；本轮补充真实 ID/版本评测、普通资料实际处理、原目录浏览及不可变制品/可执行回退。最终实际版本、质量、时延、资料净增与远端 CI 只认 Owner 私有 `RELEASE_LOCK.json` 与 `OWNER_RC1_RESULT.md`，不继承旧报告的 PASS。

PR #30 继续 Draft；正式 HBOS 目录只读，不合并、不切 P1、不自动开放员工。自动生成仅 deepseek-flash；不用其他生成模型或付费子 Agent。独立服务源码不向公开仓上传完整历史。当前入口：[UAT6 RC1 可用候选](milestones/M1_KB_UAT6_RC1_可用候选.md)。

## 2026-10-19 UAT5 执行补充当前检查点

**运行补充（2026-10-19）：** Owner已授权整体Docker资源调整，现为10 GiB内存／4 GiB Swap，Docker Desktop界面恢复可操作。原44个运行容器及原ES恢复，其他原停止容器保持停止；原数据卷、索引UUID和应用配置语义保留。首轮有限计划已收束为359份完成、1份已知阅读器异常，跳过此前260份成功项；扩展255份全文技术版本已全部完成首次解析，有限工作进程已结束；各组按最多4份及至少1 GiB内存余量保护执行。当前无写入、Docker连接或必要模型网络权限拒绝。带时间戳的发布总量、15个Dataset数量和逐份收据在Owner本机闭合台账，解析完成不代表允许共享。

**UAT5_PARTIAL / LOCAL_UAT / OWNER_NOT_RUN / ROLLOUT_PENDING。** 当前隔离候选安装独立服务 **0.6.22**；原知识领域与独立前端保留。安装包逐文件核对一致，服务505项、知识前端154项检查通过；这些不代替真实业务及Owner验收。PR #30 保持Draft，不合并、不切P1、不开放正式员工。

已定位并修复完整原句仍遭拒绝的实际原因：提取结构标签与正文混合、条件在义务词规范化前提取、全角标点规范化后与片段边界不一致。数字、单位大小写、否定、真实条件、主宾关系、完整单元、生成后来源及权限复核继续保留。同源索引修复采用新版本与原件哈希、父绑定和当前发布比较校验，原件、原发布历史不删除。

新增封闭证据单元选择契约，由服务端按完整原文要点分别组织并引用，明确显示“按所引原文整理”。四个旧自然语言失败问题的最新逐题收据均获得可核验原文整理回答，8/8个来源重新打开；其中前三题在0.6.21、剩余一题在0.6.22完成，不能写成0.6.22全量基准通过。0.6.20原四题自由措辞仍0/4通过；原文整理不能计作模型自由归纳通过。原73题未重新大批重放。 Docker资源恢复后新增1个工程清单业务题使用deepseek-flash实测，回答及预期引用1/1通过、来源复开1/1；仍为原文整理模式，不能据单题证明全库自然归纳通过。

全目录闭合台账保持每个唯一内容一个去向，别名另列；不覆盖初始盘点。已发布、原件上传、原生解析、完整索引验证、OCR提取及最终共享质量分别计数。通过原件、身份、全文、向量和授权质量的具体资料继续发布；OCR、表格/图示、隐私及保密疑点继续逐份核对。既有成功项跳过，失败和不确定请求不自动重放。原OCR318份补齐2个缺失页后形成13695页结构记录，两处具体敏感线索经原页核对，1处为真实供应商联系方式待共享／脱敏判断，1处为表格数字拼接误报；另对0页阅读器异常资料完成25页离线OCR，单独保留冻结计划。工程3表的15工作表、1070非空单元格已逐页预览与独立值对照，明确保留作废／未签批／未生效及合并行关系；其中2份已用保留完整行关系的新文本版本索引并作为参考发布，原件及旧版本保留；另1份图例关联待明确。CAD112份已完成本地有界导出尝试，104份DXF仍待几何核验、5份达到输出上限、3份读取错误，未自动发布。

本机两次Docker虚拟机整体内存耗尽终止ES的内核global_oom证据已保存。此前批次在完整组末停止；最新Owner授权资源维护已恢复原容器、挂载和索引，现按有限批次续跑。整体Docker受控重启前已备份数据库与容器清单，P1路由、应用版本和既有数据不变。一个原PDF在原生阅读器读成0页的问题已完成保留原件的结构修复，尚不据此宣告完整质量通过。

三名获批候选测试账号的定向换密和旧会话撤销已完成；Owner已登录现有RAGFlow管理页，现有15个Dataset文件页面均有真实访问证据。收藏保存/重开/跨用户拒绝、既有历史重开、维护员允许与员工拒绝，以及既有隔离MCP连接的真实检索/来源链已复验；原UAT4隔离MCP令牌已按既有TTL到期；另用临时候选连接完成真实协议检索和来源展开并立即撤销，未更改个人配置或旧连接。

自动生成测试只用deepseek-flash；禁止Claude-opus-5及其他未批准模型、付费子Agent。员工默认gpt-6-luna、个人偏好、千问Embedding/1024维和默认零rerank保持。真实题目、原文、凭据、完整计数、批次及调用收据均只保存在Owner本机私有交付；当前剩余门槛仍包括自然归纳、更多资料质量及Owner人工验收。

## 当前知识专项：HBOS Knowledge UAT5 — 2026-10-15

**UAT5_PARTIAL / LOCAL_UAT / OWNER_NOT_RUN / ROLLOUT_PENDING。** 本轮以真实检索、回答和来源质量为验收依据。已修复跨部门候选汇总、单个异常片段拖垮检索、在线来源/会话续租及问答错误跨页面显示；增加公共法规分类和独立原文下载决策点，原件下载仍关闭。真实回答的自然归纳支持率、更多资料的逐份质量与授权仍有缺口，不能据 CI 或 HTTP200 宣布 READY。

全目录已完成递归哈希盘点、历史身份对账和分阶段质量检查；解析完成与已发布分别计数。仅精确获准且质量通过的子集可发布，个人/保密和授权冲突资料维持待核。测试仅 DeepSeek-Flash，员工默认 GPT-6-luna、原千问 Embedding/维度和默认零 rerank 保持。PR #30 保持 Draft，不合并，不切 P1。

本轮证据范围与剩余门槛见 [UAT5质量候选](milestones/M1_KB_UAT5_检索可靠性与全目录质量候选.md)；详细真实问题、原文、账号、目录和完整漏斗仅留 Owner 本机交付。

## 历史：HBOS Knowledge UAT4 — 2026-10-11

**LOCAL_UAT / REVIEWING / OWNER_NOT_RUN / ROLLOUT_PENDING。** 个人助手入口简化为客户端选择、一次私密安装和最近真实知识使用。状态只在本人连接实际检索并打开同一检索来源后更新；个人 Token 与无凭据使用规则分开存储。已批准的成功资料按精确子集分批发布，完整性未过关的资料保持待核；解析许可不能代替共享许可。原 15 份、UAT2 样式、四回答模型、千问 Embedding 和默认零外部 rerank 保留。

本轮事实、最终统计及制品边界见 [UAT4 验收候选](milestones/M1_KB_UAT4_极简接入与真实资料发布候选.md)；Owner 私有联合锁为数量、运行源码、CI 和 wheel 的最终依据。PR #30 保持 Draft，不合并、不切 P1、不开放正式员工。公司 HTTPS 入口待部署，本机地址仅用于本机 Owner 验收。

## 历史：HBOS Knowledge UAT2 — 2026-10-10

**UAT2_IMPLEMENTATION_CANDIDATE / PROTOTYPE_APPROVED / OWNER_NOT_RUN / ROLLOUT_PENDING。** Owner 已正式批准知识库交互设计 V1，本轮原型审批门禁已满足。知识模块按批准原型完成独立首页、资料目录、本人收藏/记录、六步 MCP 向导和维护员资料/上传/版本/反馈页面；接入原生 Frappe/API，保留 15 份真实共享资料、GPT-6-luna、千问 Embedding、用户权限及关闭原件下载。按两轮截图与实际操作复验，最终运行源码、构建资产和 CI 以本机 Owner 交付联合锁为准。人工产品验收与真实服务器上线是独立 Gate；PR #30 保持 Draft，不合并、不切 P1、不开放全员。

当前记录：[M1-KB-UAT2 完整业务与迁移候选](milestones/M1_KB_UAT2_完整业务与迁移候选.md)。下文 UAT1/N1 的财务阻断和旧终态仅为历史记录，不能覆盖本轮最新要求。PR #30 保持 Draft，P1 与员工开放范围不变。

## HBOS Knowledge UAT-1 当前候选 — 2026-10-10

**PARTIAL / ACCOUNTING_PENDING / LOCAL_UAT / COMPANY_ROLLOUT_PENDING。** 本轮直接实现并装配个人 MCP、页面维护、默认标准检索、有限会话和反馈闭环；未达到完整人工验收放行。旧事件的 Owner 风险例外已按原信封追加，但新增生成未知和在途 embedding 未结算使付费查询、问答、解析暂停，不扩大旧例外。

生产发布 13（原 12 + 本轮 1），人事/安全发布 0；旧 224 解析成功、78 失败保留。MCP 认证/发现/撤销可用；停止前 Hermes 的真实检索/来源通过，OpenClaw 完整问答未通过。维护 UI 的去重、质量、发布、下架/恢复及反馈处理通过，新资料完整解析和换版查询链待补。原生 API/索引不重建，批量 worker 和自动付费测试停止，Owner 1.5 元控制预留留在原两个信封内但当前受对账门槛阻断。

最终标准领域入口 132 项（114 领域 + 18 本地准入）、服务 185 项、前端 148 项分别通过，不能代替功能验收。PR #30 保持 Draft、人工验收前不合并；P1、main、其他 PR 和真实员工范围不改。

当前主记录：[M1-KB-UAT1 完整功能人工验收候选](milestones/M1_KB_UAT1_完整功能人工验收候选.md)；两轮审查和真实缺口在主记录中，以下 N1 / R2 条目为历史记录。

## 历史：HBOS Knowledge N1 夜间候选 — 2026-10-10

状态：N1_PARTIAL_WITH_INDEPENDENT_WORK_COMPLETED / ACCOUNTING_PENDING / LOCAL_CANDIDATE_ONLY。原生 rerank 协议适配进入固定 RAGFlow 的实际模型注册入口；严格校验本请求的索引、分数、usage 和 request_id，其他模型保持原实现。生产参考装配缺原预算绑定时拒绝调用。旧 UNKNOWN 没有结清依据，普通模型调用、旧失败项解析和新资料在线发布继续关闭，不能以离线适配或此前单次成功宣称业务恢复。

本轮完成知识目录的服务端分页及筛选、本人反馈与处理状态、统一搜索/问答输入、一般反馈、历史/收藏上下文重放及多部门明确选择。修复同版本撤权后的旧活动标题泄漏、跨请求身份清理和数据库并发收藏幂等。新资料仅本地准入、身份去重、隔离及冻结计划；真实原文、问题、账号、运行配置和费用证据不进入公共 Git 或开发包。

领域106、本地准入18、独立服务163（原冻结包162项，补充1项）、前端143项合同已运行通过；层级有重叠，不相加，合成测试不代替真实来源/答案质量。最终原生数据库、HTTP、浏览器、远端 CI 和安装制品证据分别在联合交付中核对。PR #30 继续 Draft；只有全部业务、审查、CI、制品和部署边界门槛同时通过才可合入产品分支。此次不切 P1 或开放员工，其他 PR 和 main 不变。


补充复核已完成：独立服务仅增加普通预算双 OS 进程锁入口握手回归，本地提交 `7485bae3073ce11511d7946578329a8090a8574e`；0.3.11 运行源码与原冻结 wheel 逐文件一致，删锁和子进程异常反例独立复核通过。两新目录发现703条路径；本地计划修订技术准入240条、200个新唯一内容，隔离463条。原238/198/465冻结及失败证据保留；修订未上传、入库、质量批准或发布，技术准入不宣称公司业务生效。补充原生 Chrome 键盘操作确认预算拦截，系统中文 IME 候选仍未核验，不能据此称完整在线验收通过。

本轮主记录：[M1-KB-N1 夜间连续候选](milestones/M1_KB_N1_夜间连续候选.md)。以下 R2.1 / R2 / R1 条目保留为历史事实。

## HBOS Knowledge R2.1 单次诊断 — 2026-10-10

PARTIAL / ACCOUNTING_PENDING / NOT_RELEASED。服务0.3.10增加维护入口专用的一次短合成rerank许可，绑定Owner指令、原预算/账本/配置、旧事件、原模型/空间/Key指纹、精确payload和有效期；同一锁中先消耗后发送，重放、并发、重启、SDK重试或重定向均不能形成第二次调用。许可/结果追加到原账本哈希链，旧calls与停止状态不改，新估算纳入原信封；成功不解锁普通调用或批次。嵌套/扁平结构计量包含查询在每篇文档中的重复贡献，并校验类型和长度。

本轮仅一次合成实测，结果 RERANK_SINGLE_PROBE_PASS；具体请求ID、用量、费用、操作与账本摘要仅在Owner层。核对现有客户端协议后，本次按该模型官方原生路径和嵌套结构精确诊断，provider/北京业务空间/Key/模型保持；普通检索配置未自动切换，旧403原因仍未知。单次成功不证明HBOS检索恢复、首组或整批质量通过。原12、原220、新成功4份、用户数据保持；224成功/78失败/0在途/新发布0，worker停止，无重解析、embedding/Flash调用、合并或P1切换。

必要新增8项一次性/两进程/重放/停止与计量反例通过，完整服务120项、原领域76与核心207项分别通过；既有前端和业务证据保留。后续需旧事件有依据对账，或Owner独立批准可核实上界的保守处置；再接入已验证原生协议，只重验失败的原固定检索及来源，补首组回归，之后按原累计预算有界推进。当前仍无新资料在线质量或精确子集发布的PASS。当前源码、安装wheel、联合锁和CI独立核对；不以它们代替业务验收。

## HBOS Knowledge R2.1 既有恢复记录 — 2026-10-09

状态：PARTIAL / STOPPED_UNVERIFIABLE_RERANK_USAGE / NOT_RELEASED。继续 Draft PR #30 与同一候选。Owner 已确认原模型额度恢复、允许按量付费并批准本轮累计预算；准确审批与费用记录仅在 Owner 层。优先原 embedding，Flash 仅备用，未探测或切换；原索引、provider、Key 与维度保持。

原 12 份曾完成实际召回、来源和一个代表问答，历史与收藏重新检索、跨用户打开拒绝通过。随后首组解析后的原资料回归遇到 rerank HTTP403，响应无可核实用量；计量器停止新增调用，worker 已安全停止，剩余组未入队。不能把较早的恢复成功写成当前持续可用，也不能把403统一断言为欠费：当前错误码、实际账单、账户余额均 UNKNOWN，准确请求ID在 Owner 收据中。

本次恢复起点220成功、82失败；原冻结批次首组4份已解析成功，物理ID、三字段metadata与原件hash均核对，但原资料在线回归阻塞，首组整体验收未通过。当前302上传=224成功+78失败+0在途，重复1另列，新发布0。224份离线文本/身份检查通过，逐份新资料在线召回和多部门答案质量仍 QUALITY_VERIFICATION_PENDING。敏感草稿继续排除，不阻塞其余批准资料。

只读索引全行hash对比确认原12份的159行、原220成功项的2994行、新成功4份的25行（含向量）完整保留；实际唯一索引行与后端chunk计数分开记录。原49条活动、7个用户指纹、文档/版本/绑定/空间逐字段保留。历史窗口只显示最近30项，不据窗口缺项断言删除。普通真实原批次重放仍12 NOOP、0写入。

服务0.3.9离线修复诊断覆盖：兼容嵌套/顶层code和type、Body/Header请求ID及冲突、Retry-After，非JSON403仍保存HTTP状态；token别名冲突或非整数值拒绝；非200合法usage只作观察，不能认定成功或实际账单。白名单、格式与长度限制隔离错误正文和凭据。旧停止守卫保留，SDK重试继续阻断；本次诊断修复不新增模型调用，也不能据合成输入推断实际403原因。原冻结清单、模型、维度与解析配置保持。

旧事件不改写；诊断补充、用量/金额对账、明确未执行不计费确认均绑定原请求、输入摘要、原行摘要与实际Owner证据，并在锁内追加哈希链事件。重复或并发相同对账只计一次；金额核实时token仍可UNKNOWN。账务结算与rerank恢复确认分别门禁，未知预留保持；禁止初始化覆盖旧ledger、直接READY或重开预算。恢复进程互斥，首组仅重验失败的原资料检索与来源，4份解析成功项不重做。剩余78项沿用原累计预算，最多20组、每组4份、并发1。

领域76、服务112、原核心207合成回归分别通过；前端89与原生合成发布10项既有证据保留；真实Chrome18项阻塞可用性检查通过（390/768/1440、目录/历史/收藏、状态读取、诊断权限、深链接仅预填、阻塞守卫，模型请求0）。配置与业务可用性分开，观察过期为UNKNOWN；当前费用收据未结算的阻断不会靠刷新清除。新资料来源、引用问答、发布和多部门前端仍未执行，不以这些回归或CI代替整批PASS。

普通发布不恢复下架或指回旧版；replace/restore需独立精确批准，首次发布冻结16字段、事务复核并写不可变收据。精确质量子集绑定原batch与质量摘要，冻结items不改。同内容改名复用身份；新内容经显式版本关系建立新版；同部门沿用确切Dataset。后续在本轮既有批准预算内有界连续推进，无需逐组批准，但必须先取得对应请求的诊断、用量/金额证据及独立rerank恢复确认，再完成失败回归。公共Git和开发包不含真实目录/题目/摘录/对象ID/账单/审批/凭据。不合并、不切换P1。

## HBOS Knowledge R2 — 2026-10-08

状态：REAL_CORPUS_SEARCH_AND_REFERENCE_ASK_CANDIDATE_PASS / NOT_RELEASED。承接 Draft PR #30 的 `codex/knowledge-autonomous-r1`，按最新 Owner 共享范围实现部门分类，无复杂部门 ACL。12 份已批准资料在固定本机 RAGFlow v0.27.0 完成解析，原始哈希、部门映射与实际解析证据仅保留 Owner 本机。

已完成原生登录/CSRF/启用状态、精确版本与下架再核验、真实检索、部门筛选、来源摘要、资料目录、按用户的历史/收藏和维护人反馈处理。受控来源保留 COMPANY_CONTROLLED，内部参考收录单独标记 CONTROLLED_REFERENCE_REVIEWED，不伪造 GMP 生效状态。gpt-6-luna 在获准的数据流下仅接收必要摘录，回答后再次核验来源，证据不足不调用模型。

原核心 207 项、领域 58 项、独立服务 14 项、前端 85 项及类型/构建通过；最终真实验收 14 项全部通过，原失败原因与修复重测证据保留。真实浏览器流程、窄屏与最终源码/制品锁分别记录。v0.27 Word positions 仅为片段序号，参考装配将未核验页码留空，避免错误定位。测试范围重叠，不相加。CI 修复已提交 `b47c6afa`，该提交两条 PR 工作流均 SUCCESS；最终功能 head 的远端 CI 独立跟踪。

本轮仅独立本机候选，未合并或切换现行 P1，未升级/重建旧 RAGFlow 存储，旧 synthetic lease 不延长。服务 0.3.1 通过本地独立提交与 wheel 联合固定；未提供服务远端，不伪造远端服务 PR。员工 MCP、复杂 ACL、公司服务器与生产 TLS 留在后续范围。当前任务依据已收到的 R2 文件和 Owner 最新目录/模型授权，不依赖丢失的旧总任务书。

执行说明见 `docs/milestones/M1_KB_R2_真实部门知识候选.md`。以下 R1 记录为历史事实，不能当作当前 R2 阻塞清单。

## 知识候选连续执行 R1 — 2026-10-08

状态：PARTIAL_CANDIDATE_VERIFIED / NOT_RELEASED；整批总任务尚未完成。专用分支 `codex/knowledge-autonomous-r1`，Draft PR #30，固定产品基线 `72e5b1728981b7ef102a2c9ee033ce0452c400e7`。已核验 K1C2 归档与独立评审；恢复已审候选到独立源码副本，修复 Binding 列/JSON/关联身份一致性与写入守卫、搜索网格和局部字号，并实现授权空间列表、范围选择与当前文档数量。

核心/进程内 HTTP 与新增领域回归 241 PASS，候选/保留 P1 契约 56 PASS，前端 83 PASS、typecheck/frappe 构建 PASS；新 Site 的元数据/跨连接版本/空间 HTTP 14 PASS，原生 HTTP/共享状态完整重跑 19 PASS，真实 Chrome 12 项检查 PASS。前端复制遗漏已纠正，以新构建产物复跑空间筛选、隔离标识、桌面/移动/键盘/依据/撤权/切人；114 项安装源码哈希及 6 项原生框架文件一致，6 个新服务出站连接拒绝。测试存在范围重叠，不作为总验收数量相加。

本批新登记 9 容器已停止、4 卷保留，95 个既有容器身份/镜像/启停/重启/网络/挂载核验一致；这不等于数据内容备份或个人 MCP 健康验收。原环境与 lease 不改，未合并或切换正式部署。独立服务 0.2.1 本地提交 `d28c7e9a3219fc94db234302e2be14451fa10d2e`，尚无提供的远端，不声称已建立服务仓 PR。

后端 GitHub CI FAIL：当前 OAuth 凭据缺 `workflow` scope，GitHub 拒绝更新工作流；修复补丁单独交付，应用检查和全新依赖环境的本地等价复测通过。远端前端与普通 bundle 构建 PASS；普通 bundle 不包含联合 service，不能据此部署知识功能。主任务书 `HBOS_KNOWLEDGE_AUTONOMOUS_MASTER_TASK_R1.md` 未随已提供三附件出现，本机按名称检索未找到，时间/资源/完整依赖与分仓目标未核对。真实 RAGFlow、受控模型问答、员工 MCP、历史/收藏/反馈/资料维护、旧库恢复、生产 IAM/TLS 与发布仍未完成；模型与 MCP 路由保持关闭。执行事实见 `docs/milestones/M1_KB_AUTO_R1_知识候选连续执行.md`；以下旧轮次条目保留为历史与其他业务范围。

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


### UAT5 执行补充：长文档书签校验修复（2026-10-16）

同一真实候选中，一份 PDF 已 DONE 且 39 个片段存在，三个保护身份一致；551 条原生合法书签触发旧 512 条上限，导致误隔离。修复只接纳有界、闭合结构的原生书签（最多4096条、标题总计131072字符），身份差异、未知元数据字段及无效结构继续拒绝。领域检查258项通过；原生已完成任务按状态读取恢复，不重复embedding。

无关资料发布引起进行中查询 SCOPE_REJECTED 的真实前后对照已通过：原授权与来源保持一致，新版为 ALLOWED。Owner 批准的三个非管理员候选账号已定向换密、清除旧会话并更新私有访问文件，偏好/MCP连接/知识历史ID未变。RAGFlow管理窗口已由Owner登录，实际Dataset及文件界面正在核对。整体仍为 UAT5_PARTIAL；PR30保持Draft，不切P1。


### UAT5 执行补充：同源完整索引修复候选（2026-10-16）

5个原失败案例的完整原件与当前索引逐一对照，均证实旧解析分隔配置删除句末标点；只有在诊断中剥离同一组标点后才覆盖100%，该诊断不作质量通过。原件SHA与保护身份均一致。新增同源完整文本索引的封闭校验：父版本、原件SHA、业务版次、文号、标题、权限空间和原Dataset保持一致，原物理索引保留，通过质量检查后由既有replace事务原子更新逻辑文档索引。不得用此路径恢复已撤回资料、改变业务事实或取得新授权。

领域检查263项、独立服务检查438项通过；5个来源的本机实际解析/引用/回答验证仍须完成。当时安装0.6.14的三原失败问答实测：3/3包含原预期来源、11/11来源可重新打开；1/3形成受支持自然回答、2/3仅来源可核验，零系统请求错误。该小样本不替代原73题命中率，也不能宣布UAT5_READY_FOR_OWNER。继续UAT5_PARTIAL、PR30 Draft与本机候选，不切P1。
