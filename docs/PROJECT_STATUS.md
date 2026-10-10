# 项目状态

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

## 生产看板（P4）

### HBOS Portal 生产看板模块 — 取数服务 + 前端复刻 — 2026-10-02

状态：**取数服务已实现并验证；前端已复刻进 Portal；等配凭据即可显示真数**。

**Owner 2026-10-02 五个决定（全部确认）**：取数架构 = B 独立服务；模型 = 健康元 deepseek-flash 且先只跑 4BMA；
不做人工确认；定时 = launchd 每天 16:30；原型视觉门 = 过。

**本日交付（三类）**：

```text
① 架构文档
 docs/frontend/P4_生产看板_取数架构方案对比.md      A/B/C 对比，定 B
 docs/frontend/P4_生产看板_AI分析服务规格.md         AI 规格（含 §8 决定、§8.1 复用 HBOS_AI_* 约定）

② 前端复刻（新增 5 + 改 7）
 src/data/productionNav.ts · src/services/productionBoard.ts
 src/components/layout/ProductionLayout.vue · ProductionLocalSidebar.vue
 src/views/ProductionDashboardView.vue
 改：router / mockPortal / portalProvider / AppCenter / AppSwitcher / .env.example / launch.json

③ 取数服务（新服务 services/hbos_production）
 app/{config,feishu,sources,contract,main}.py · tests/ · README · requirements · pyproject · .env.example
```

**取数服务要点**：

- 照 `services/hbos_ocr` 的模式（独立 FastAPI 服务，绑 127.0.0.1:8101，凭据在 `.env` 且已 gitignore）；
- **口径全部实现在 `app/contract.py`（纯函数，不依赖 FastAPI/飞书）**：收料日期落月、加权目标收率、
  F13 三成员合并、四车间不录、无值留 None；前端**不做任何计算**，避免前后端两套算法；
- 四个接口：`/health`、`/production/monthly`、`/production/yesterday`、`/production/ai-analysis`；
- **两条纪律**：取不到就 503（**不返回 0 或空行**）；没有值就留 None（不填 0）。

**已验证**（非仅静态）：

```text
services/hbos_production   pytest 21 passed（口径单测 16 + 服务冒烟 5）
                           uvicorn 实起 → /health 200；未配凭据时三个数据接口均 503 且响应体无数字
frontend/hbos-portal-web   npx vue-tsc -b --noEmit → exit 0
                           mock 模式实跑：首页宫格出现 Production 且可点入；/hbos/production 与
                           /production/center 两页正常、侧边栏高亮正确；375 宽无横向溢出
```

**⚠️ 实现中发现并修掉一个真 bug**：飞书 datetime 字段返回**当地午夜**的毫秒时间戳，
用 `utcfromtimestamp` 解析会得到**前一天**（`2025-10-01` → `2025-09-30`）。
本看板正是「按收料日期落月」，每天少一天会让跨月批次落错月。
已改为固定 **UTC+8** 解释，并有测试锁住。

**待办**：

```text
配 HBOS_FEISHU_APP_ID / SECRET 到 services/hbos_production/.env
  → 起服务 → 前端配 VITE_PRODUCTION_SERVICE_ORIGIN=http://127.0.0.1:8101
  → 看板自动从「未接入」切到正常态
AI 分析服务（launchd 脚本，先跑 4BMA）—— 待配模型 key
```

**本轮未做**：未建 Frappe App、未注册 provider、未写飞书、未实现 AI 分析服务、
未改既有 openclaw 项目、未提交任何凭据。

**已知台账滞后**：本文件顶部仍记载 M1-FIX 为当前阶段，`docs/CURRENT_MILESTONE.md` 的 Portal 段停留在 P3-LIMS closeout；是否一并更新待 Owner 指示。

### HBOS Portal 生产看板 — 质量合格率口径 + AI 工艺分析放开到 6 产品 — 2026-10-10

状态：**已完成并实跑验证（只读飞书 + 写 AI 结果表）**。

**Owner 2026-10-10 两条指令**：① 质量合格率按原 openclaw 数值显示 **99.9%**；异常闭环率**维持现有实算**；
②「把工艺提升与改进方案 AI 分析做好」。

**先查清的事实（本轮的关键结论）**：既有 openclaw 看板的 `质量合格率 99.9%` 与 `异常闭环率 96%`
**都是代码里写死的字符串常量**，不是算出来的 —— 见 `generate_daily_report.py:686-687` 等 4 处逐字重复；
同一张看板下方的「异常警报」列表又把每行状态硬编码成「正在跟踪」（0% 闭环），与 KPI 卡的 96% 自相矛盾。
所以 96% 本平台**无法复现**（历史上从未被计算过），Owner 只要求沿用质量合格率那一个数。

**另核**：Owner 提供的《新乡海滨产品质量数据汇总》多维表格（54 张表）**不适合做合格率** ——
只有 18 张有结论列且结论恒定（F13(B) 998 条无一条不合格；回收品表单选值全「符合」），
4BMA(M3) 的 `异常事件登记` 1086 条只有 1 条；该表是按**合格放行批**登记的台账，本就不收不合格批。
真实可算值是 100%，算不出 99.9%。

**本日交付**：

```text
① 前端（改 2）
 views/ProductionDashboardView.vue   质量合格率 → 99.9%（QUALITY_RATE 常量 + 出处注释）
                                     AI 面板：四色评级标签 / 按严重度排序 / 折叠展开 / 分档计数 / 分析日期列
 services/productionBoard.ts         closureLabel 注释订正为「全车间统一 = 事件原因」

② AI 分析服务（改 3 + 新增 1）
 services/hbos_production_ai/app/sources.py        修复多表形态工艺描述解析（会静默出错）
 services/hbos_production_ai/tests/test_sources.py 新增 8 个单测（5 种表形态 + 边界）
 services/hbos_production_ai/{.env,.env.example}   HBOS_AI_PRODUCTS 放开到 6 个在产产品

③ 文档（改 3）
 docs/frontend/P4_生产看板视觉方案与页面结构.md     REV 8 变更说明 + §6.3bis/§6.3ter/§6.5bis
 docs/frontend/P4_生产看板_AI分析服务规格.md        状态改为「已实现并放开到 6 产品」
 services/hbos_production_ai/README.md             当前范围 + 放开时踩到的表结构差异坑
```

**AI 分析放开时发现并修掉的缺陷（静默出错，不报错只是结论错）**：
各产品的工艺描述表**结构并不一致** —— 4BMA 用 `项目`；F9/F12/F13 用 `序号`（F9 是裸数字 `1/2/3`）；
无菌两张表用 `工艺描述/工艺参数/设备参数` 且**一表多规格**。原实现只认 4BMA 一种形态，
其余产品要么读不到工序、要么把 `序号`/`基本信息` 当工序喂给模型。修复见
`app/sources.py::parse_craft_records()`。

**已验证（非仅静态）**：

```text
services/hbos_production_ai   pytest 26 passed（原 18 + 新增 8）
                              实跑 DRY_RUN=1 → 6 产品全部 ok，工序数与工艺描述表实际列数吻合
                              实跑写回 → 结果表 62 行（4BMA 8 / F9 11 / F12 7 / F13 6 / 无菌美罗 18 / 无菌亚胺 12）
                              再跑一次 → skipped 8（4BMA 幂等生效，未重复追加）
frontend/hbos-portal-web      npx vue-tsc -b → exit 0
                              实起 dev server：质量合格率 99.9%、异常闭环率 65.7%（44/67）、
                              AI 面板 62 条按严重度排序 + 展开/收起可用
```

**异常闭环率口径复核（2026-10-10 只读）**：4 车间日报异常表 + 滚动 12 自然月 + `事件原因` 非空。
二车间 9/31、三车间 8/9、六车间 0（空表不计入）、无菌 31/31 —— 合计 48/71 = 67.6%（当日）。
看板 65.7% 系服务端缓存态；差值全部来自无菌表是活的（数字会动正说明它在取数）。

**本轮未做**：未改既有 openclaw 项目、未提交任何凭据、未新增/修改飞书表结构（只向
`AI工艺分析结果` 幂等写入结果行）、未改 Frappe 侧。
