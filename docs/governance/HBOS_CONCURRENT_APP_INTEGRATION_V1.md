# HBOS 多 APP 并行开发与分批集成规范 V1

> 生效范围：`feature/hbos-portal-product` 的 Portal、Attendance、Inventory、LIMS、Production、Twin、Knowledge 等并行开发工作。
> 生效日期：2026-10-10。治理规范，不代表任何 PR 的业务验收、生产部署或真实用户授权。
> 本文与 `CONTRIBUTING.md` 的合并审批规则并行适用；如冲突，以更严格的安全门禁及最新 Owner 决定为准。

## 0. 我们解决的问题

2026-10-10 联合审查中，#34 考勤相对产品基线出现 109 处合并冲突；#33 生产含库存历史提交共 126 文件；#37 人员权限和 LIMS 涉及 463 文件；彼此改动 `router/index.ts`、`frappeClient.ts`、`Portal AppCenter` 等共享文件。根因是分支长期漂移、跨域内容打包、共享入口多人同时编辑，而不只是 Git 工具不熟练。

目标：**先统一源头，再独立开发，分域小 PR，按队列合入，源代码与运行环境分开**。

## 1. 唯一当前集成目标

- Portal 相关新功能：以 GitHub 最新 `origin/feature/hbos-portal-product` 为基线创建**新的短期分支**，PR base 必须为 `feature/hbos-portal-product`。
- `main` 是独立生产就绪线；只有 Portal 及业务集成 Gate 正式获批后才提 main PR。禁止将旧 `main` 直接当作 Portal 开发基线。
- 每轮合并前重新读取远端 base/head 的**完整 SHA**，校验 changed files、CI、Review/Request Changes、mergeable；不能把 PR 创建时的旧 BASE 当成最新。
- 不强推/重写共享分支，不在不干净的本地目录 pull、checkout 或自动 migrate；不删除他人的工作、Docker 卷或未提交改动。
- 合并只在目标 PR 的 GitHub 门禁允许时执行 Squash Merge；审批、非作者 Review、高风险门禁仍按 `CONTRIBUTING.md` 执行，Owner 自主合并仅限文档/隔离的低中风险场景。

## 2. 模块所有权（App 主权）

| 领域 | 业务主要目录 | 数据与动作 Authority | 跨域协作接口 |
| --- | --- | --- | --- |
| Portal 平台组 | `apps/hbos_portal`、Portal 全局 Shell、路由/导航/共享客户端 | 身份展示、APP Registry、汇总调度（**不承接领域业务状态**） | 版本化 Manifest / Access / Summary / Tasks / Search / Deep Link |
| 考勤 | `apps/hb_attendance_app`、考勤专属 Vue 视图 | 考勤业务规则、判定与范围权限 | 考勤 API + Provider |
| 仓库 | `apps/hb_inventory_app`、仓库专属 Vue 视图 | 入出库、库存、质量放行约束 | 仓库 API + Provider |
| LIMS | `apps/hb_lims_app`、LIMS 专属 Vue 视图 | 检验/复核/放行和职责分离 | LIMS API + Provider |
| 生产 | `services/hbos_production*`、生产专属 Vue 视图 | 生产统计与 AI 分析，不可隐式共享员工权限 | 经过用户鉴权与范围检查的后端 Gateway/BFF |
| 知识/孪生 | `apps/hb_knowledge_app`、`apps/hb_twin_app` + 独立服务/资产 | 资料授权、模型/遥测授权、私有资源分发 | 不允许浏览器绕过身份/文件授权；领域服务自行鉴权 |

任何 App 的业务权限不能仅在前端控制，也不能因为“Vue 自己渲染”就绕开服务器。Frappe Session 是当前统一身份；独立 FastAPI 必须具备受信身份转递、应用授权与对象范围校验，前端 CORS 不是鉴权。高危操作和迁移必须独立复核。

## 3. 共享文件的“单写入口”

以下属于平台共享面，**领域团队不能在长期功能分支中反复整文件覆盖**：

- `frontend/hbos-portal-web/src/router/index.ts`、`src/services/frappeClient.ts`、`src/services/portalProvider.ts`
- `frontend/hbos-portal-web/src/components/portal/AppCenter.vue`、`src/components/global/AppSwitcher.vue`
- `frontend/hbos-portal-web/src/styles/global.css`、`src/stores/portal.ts`
- `apps/hbos_portal/hbos_portal/services/bootstrap.py`、Registry / Provider Contract
- `AGENTS.md`、`CLAUDE.md`、根 `README.md`、`docs/PROJECT_STATUS.md`、CI 工作流

应用团队原则上只提交本域增量；共享入口由**平台集成人员**在单独、短小的接入 PR 中修改，并在 PR 描述列出访问控制测试。APP 专属前端路由/导航/样式优先模块化，避免日常直接改全局 CSS。确需改共享文件时，事先在 PR 中登记变更接口并与平台组约定集成顺序。

## 4. PR 粒度与提交合同

- 一个 PR 只对应**一个领域/一个业务目标**；库存和生产不得因开发分支历史顺带合成一个 PR，LIMS 和 IAM/恢复工具不应无理由同包。
- 提交前 `git diff --name-status <base>...HEAD` 与 `git log <base>..HEAD` 核对：不得含别人业务历史、敏感环境、无关 DocType 或旧的全局配置。
- PR 必须写清楚 base/head、文件范围、数据权威、权限边界、数据库迁移、Feature Flag 默认值、测试与失败项、部署/回滚影响及本轮不做事项。
- 必测：服务端同域允许和越域拒绝、Portal/Desk 直接 API 旁路、会话失效、列表/导出/附件（如适用）、跨 APP 业务联锁；不能用静态 UI 隐藏替代拒绝验证。
- 每次新提交都会使旧的 CI/审查结论过期；必须按新的 HEAD 重新跑。业务真实数据/站点与独立服务部署必须有单独 Gate。
- 项目当前的测试人员资料由 Owner 指定为测试用途，本轮不单独触发历史隐私清理任务；有效凭据、权限边界、生产部署仍遵循原规定。

## 5. 日常同步 SOP（所有开发成员都要执行）

```bash
# 只在自己的 Git 工作目录执行；先检查，再同步远端
git status --short
git fetch origin --prune
git rev-parse origin/feature/hbos-portal-product
git log --oneline -5 origin/feature/hbos-portal-product

# 启动新 Portal 功能前，基于当天最新产品主线创建短期分支
git switch -c feat/inventory-small-fix origin/feature/hbos-portal-product

# 开 PR 前审查自身差异
git diff --stat origin/feature/hbos-portal-product...HEAD
git log --oneline origin/feature/hbos-portal-product..HEAD
```

- 如果 `git status` 非空：**先保护改动**（自己提交或在明确确认后另建 worktree），不要无条件 stash/reset/clean，更不要强行 pull。
- 自己的短期私有分支遇到新 base：可在确认没有他人协作、且理解历史改写后使用 `git rebase origin/feature/hbos-portal-product`。已共享、多人推送或已建 PR 的分支优先新建干净分支并`cherry-pick`**仅属于本域的明确提交**；不得将整条过时分支当成补丁直接 merge。
- 旧分支含大规模冲突时：以新 base 为骨架选择性移植，逐文件区分业务增量与安全回退；禁止 `git checkout --theirs .` / `git checkout --ours .` 全局覆盖。
- 产品分支每次合并后，所有人至少**执行 git fetch origin 并评估与其任务的差异**，不要机械地 `git pull` 到每个正在编辑的分支。新任务必须从新 base 创建分支。
- 数据库 migrate、Docker 重建、独立服务更新仅在本人明确授权的**隔离环境**执行；不得因拉代码自动修改共享或实际业务 Site。

## 6. 分批集成队列与防碰撞

1. 先提交 PR 清单/冻结 HEAD；并行开发的共享文件进入短期“集成窗口”，只允许指定集成人员提交。
2. 对每个 PR 检查 GitHub Review、CI、授权/迁移/数据范围、与产品 HEAD 差异；风险越高审查越严格。
3. **一次仅合并一个合格 PR**，核对 Squash SHA 和原产品状态；如失败立即停止下一项，不继续盲合。
4. 重新 fetch 新产品 HEAD，下一候选重新执行 CI/冲突检查；历史 SUCCESS 不继承。
5. 已合入不代表员工功能上线；Owner 在隔离 UAT 通过后另行批准部署。
6. 对需要保留的功能源分支，在自动删除前设置经批准的远端保留引用；否则按合并后的短期分支治理移除。

## 7. 当前冲突收口原则（2026-10-10）

- #35 仅提供考勤移植设计；#34 源分支保持对照，按 Base 加固骨架重新移植考勤业务，**不做大包冲突整体合并**。
- #33 的库存与生产分别审查；生产浏览器直连未授权服务的方案必须先补后端授权并保留指标数据来源。
- #37 新组织 DocType 与旧 Portal CI 的“账号 DocType 四项”门禁存在职责边界冲突；先裁定归属、迁移与授权，再扩展门禁；不得随手关闭检测。
- #30 知识库处于独立推进，本次集成窗口保持不改动。
- 以上是开发顺序与审查规则，**不是**对未修复 PR 的预先合并批准。

## 8. 新人/Agent 发版前 8 项检查

```text
[ ] 我基于最新 Portal SHA，而不是 main 的旧源码
[ ] 本 PR 不混入其它 APP 的多月历史
[ ] 我只改本域文件，共享文件已向平台组报备
[ ] 新入口遵守后端 Access/Provider，不建立前端“无授权”例外
[ ] 关键 API 检查 Frappe 当前用户、范围和业务状态
[ ] 测试在干净源/固定 SHA 上重跑，失败不记 PASS
[ ] DocType / 服务 / Feature Flag / migrate / 回滚影响独立列出
[ ] PR 合并后，团队拉新产品 HEAD，但绝不自动破坏本地工作树
```
