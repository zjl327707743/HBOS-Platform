# HBOS 内容分布与承载清单

> 生成：2026-10-10 · 交付流程产出，**供 Owner 评估「哪些内容还没进产品分支、由谁承载」**
> 基准：`feature/hbos-portal-product` @ `ddbe9bf3`（下称 **base**）、`main` @ `e8afea3`
> 数据来源：`git ls-remote` / `git merge-tree` / GitHub API 实测（命令见 §7）；本表文件数量与 PR 汇总是历史快照，实际合并以重新核对的远端状态为准。
> 复核更新（2026-10-10）：PR #34 目前仍为 **Open / mergeable=false**，不是 Closed；已有 PR 承载但不能直接合并。Owner 已明确该批人员资料属于测试数据，本轮不把其隐私风险作为合并阻塞，账号凭据与业务写入安全门禁仍保留。

---

## 一、结论速览

**base 里已经装了大半个 HBOS。** 六个业务 App、两个前端工程、两个外部服务都在 base 上：

| base 已有 | 内容 |
| --- | --- |
| `apps/` | `hb_attendance_app`、`hb_inventory_app`、`hb_knowledge_app`、`hb_lims_app`、`hb_twin_app`、`hbos_portal` |
| `frontend/` | `hbos-lims-web`、`hbos-portal-web` |
| `services/` | `hbos_gateway`、`hbos_ocr` |

**还没进 base 的，只有下面三类：**

| # | 类别 | 规模 | 承载 | 冲突 |
| --- | --- | --- | --- | --- |
| **1** | **考勤线的 10 月增量**（我们） | 207 提交 / 296 文件 | **PR #34 Open，但存在合并冲突** | **109** |
| **2** | 三条他人在做的工作线 | 463 / 126 / 126 文件 | PR #37 / #33 / #30 | **0** |
| **3** | 一份文档类基线同步 | 7 文件 | PR #29 | 0 |

> **最需要注意的一点**：第 1 类考勤线已有 PR #34 可供审查，但当前差异不能直接合入。应从产品分支新建选择性移植 PR，原 #34 和源分支暂时保留作对照。

---

## 二、base 已有内容的边界（哪些「已经有」、哪些「没有」）

几个容易误判的点，逐一实测：

- **`apps/hb_stock_app`（库存隔离线产物，14 文件）不在 base**，只存在于 `feature/hbos-attendance-console` 与 `m1-fix-c-rest-leave` 两条远端分支。
- **base 的 `docs/attendance/` 只有 3 个文件**，**不含**那两份含真实姓名的名单（`HBOS班次名单_工号姓名对照表.md`、`..._工号姓名部门对照表.md`）。这两份只在考勤线上。
- **base 的 `apps/hbos_portal` 有 83 文件**（含完整 `auth/`、账号 DocType、`api/csrf.py`）；考勤线上的同名 App 只有 37 文件，且 **37 个路径全部是 base 的子集**——即考勤线在该 App 上没有独立内容。

---

## 三、未进 base 的分支（按工作线）

### 3.1 考勤线（**PR #34 Open，暂不可直接合并**）

| 分支 | 最后提交 | 规模 | PR |
| --- | --- | --- | --- |
| `feature/hbos-attendance-console` | 2026-10-10 | **207 提交 / 296 文件 / +48947 −680** | **#34 Open / mergeable=false**（待选择性移植） |
| `m1-fix-c-rest-leave` | 2026-09-24 | 164 提交 / 150 文件 | #9 **已关闭未合并** |
| `m1-fix-b5-ai-and-shifts` | 2026-09-07 | 36 提交 / 73 文件 | #7 已关闭未合并 |
| `m1-fix-b5-attendance-dashboard-fixes` | 2026-08-14 | 2 提交 / 60 文件 | 无 |

内容：考勤判定、调休模块、门户考勤适配、Desk 视觉层、以及 `apps/hb_stock_app`（库存隔离线，混在其中）。
冲突状况与裁定建议见 `docs/PR34_与Portal产品分支口径裁定单.md`（PR #35）。

### 3.2 其他团队/工作线（**各自有 PR，且都以 base 为 BASE、0 冲突**）

| 分支 | PR | 作者 | 规模 | 主题 |
| --- | --- | --- | --- | --- |
| `pr-m2-r11` | **#37** | HavenWane | 463 文件 / +68227 −1288 | 人员与权限管理阶段落地（含 Twin V1 / IAM-0 合并与权限安全修复） |
| `p4/production-dashboard` | **#33** | iamiin | 126 文件 / +28827 −108 | 生产看板前端复刻 + 独立取数 / AI 分析服务 |
| `codex/knowledge-autonomous-r1` | **#30** | Azrael | 152 文件（2026-10-10 新版；具体行数以 PR 最新 diff 为准） | 知识工作台 UAT2 候选（Draft，本轮暂缓） |
| `docs/governance-product-baseline-20261006` | **#29** | Azrael | 7 文件 / +64 −14 | 同步产品分支当前基线、安全补丁部署状态与团队获取说明 |

> 这四条 **`merge-tree` 实测 0 冲突**，各自独立可合。**不属于本工作线，不应混入考勤 PR。**

### 3.3 已入 base 的（历史，分支多数已被自动删除）

`#32`（Owner 自主合并治理）、`#31`（Twin V1）、`#28`（ESS 敏感导出）、`#27`（LIMS 原生写守卫）、`#26`（月度上传鉴权）、`#25`（IAM-0 承接）、`#24`（Portal 合并收口）、`#21`（统一账号发布）——均已 **MERGED**，来源分支因 `delete_branch_on_merge=true` 已被自动删除。

仍留在远端的已入 base 分支：

| 分支 | 说明 |
| --- | --- |
| `feature/hbos-portal-product` | base 自身（PR #15 正把它合入 `main`，仍 OPEN） |
| `feature/hbos-attendance-console-v2` | 内容已入 base（`ddbe9bf`） |
| `feature/twin-experience-v1` | #31 已合并；分支被**要求保留** |
| `archive/twin-experience-v1-a38345ed-20261010` | 指向冻结候选 HEAD 的留存引用 |

### 3.4 仍留在远端的已关闭 / 已合并分支（未随 PR 自动删除的残留）

| 分支 | 原 PR | 规模 | 状态 |
| --- | --- | --- | --- |
| `codex/m2-r8-public-pr` | #10 | 1 提交 / 331 文件 | CLOSED **未合并** |
| `feature/m3-warehouse-and-feishu-login` | #8 | 51 提交 / 113 文件 | CLOSED **未合并** |
| `governance/iam0-permission-baseline-20261001` | #22 | 23 提交 / 217 文件 | CLOSED **未合并** |
| `governance/iam0-permission-baseline-20261001-v2` | #23 | 1 提交 / 11 文件 | CLOSED **未合并** |
| `m2-r8` | — | 87 提交 / 348 文件 | 无 PR |
| `integration/pr10-lims-clean` | #13 | 1 提交 / 56 文件 | 已合并（分支留存） |
| `integration/pr8-inventory-clean` | #12 | 5 提交 / 100 文件 | 已合并（分支留存） |
| `audit/pr10-lims-deep-review`、`audit/pr8-inventory-deep-review` | — | 2 / 51 提交 | 审计留档，无 PR |
| `p4/inventory-frontend-audit` | — | 27 提交 / 76 文件 | 无 PR |
| `docs/pr34-base-ruling` | **#35** | 2 提交 / 1 文件 | **OPEN（裁定单）** |
| `docs/pr34-portal-base-ruling-20261010` | #36 | 1 提交 | CLOSED，**远端分支已删除**（基点错误的那版） |

### 3.5 已合入 `main` 的

`#20`、`#19`、`#17`、`#16`、`#14`、`#6`、`#5`、`#4`、`#3`、`#2`、`#1` 均 **MERGED into main**。

---

## 四、PR 全景（全 37 条，按状态）

| 状态 | 数量 | 编号 |
| --- | --- | --- |
| **OPEN** | **7** | #37 #35 #34 #33 #30 #29 #15 |
| MERGED | 22 | #32 #31 #28 #27 #26 #25 #24 #21 #20 #19 #17 #16 #14 #13 #12 #11 #6 #5 #4 #3 #2 #1 |
| CLOSED 未合并 | 8 | #36 #23 #22 #18 #10 #9 #8 #7 |

（合计 37 条。）

**OPEN 的 7 条里，#34 与 #35 属考勤工作线**；#35 含四份文档，#34 为待移植的业务来源。其余分属其他团队或产品主线。

---

## 五、三个「洞」（无人承载或无人可见）

1. **考勤线 #34 存在但不能直接合并** —— 207 提交仍在 `feature/hbos-attendance-console`，必须建立以当前产品 Base 为起点的新移植 PR；不能把 #34 的 296 文件全部作为合并解冲突内容。
2. **4 条已关闭未合并的旧考勤分支**（`m1-fix-c-rest-leave` / `m1-fix-b5-ai-and-shifts` / `m1-fix-b5-attendance-dashboard-fixes` / `m2-r8`）仍在远端，内容与考勤线大量重叠，**早晚要做去重裁定**。
3. **`delete_branch_on_merge=true` 之下的风险**：考勤线是那 207 提交在远端的**唯一载体**。将来一旦有 PR 从它合并，GitHub 会自动删除来源分支；若届时未先打留存引用，**新检出将失去这些提交**（本地副本除外）。

---

## 六、建议

| 优先级 | 动作 |
| --- | --- |
| 高 | **建立考勤选择性移植 PR**——保留 #34 作为审查与历史对照来源，不做整体冲突合并。 |
| 中 | 在 `feature/hbos-attendance-console` 上打一个留存引用（tag 或归档分支），对冲 `delete_branch_on_merge` 的风险。 |
| 中 | 裁定 4 条旧考勤分支的去留——与考勤线内容重叠，留着会持续制造「哪个才是权威」的困惑。 |
| 低 | 清理已合并但留存的分支（`integration/pr8-inventory-clean`、`integration/pr10-lims-clean`、`feature/twin-experience-v1` 等）——`feature/twin-experience-v1` 被 Owner 要求保留，其余可评估。 |

---

## 七、附：取证命令（可复现）

```bash
B=origin/feature/hbos-portal-product

# base 已有的 apps / frontend / services
git ls-tree --name-only $B apps/ ; git ls-tree --name-only $B frontend/ ; git ls-tree --name-only $B services/

# 各远端分支相对 base 的提交数与文件数
for r in $(git branch -r --format='%(refname:short)' | grep -v 'origin/HEAD'); do
  printf '%-50s 提交 %-5s 文件 %-5s\n' "${r#origin/}" \
    "$(git rev-list --count $B..$r)" "$(git diff --name-only $B...$r | wc -l)"
done

# 谁已入 base / main
git merge-base --is-ancestor <branch> $B && echo 已入base
git merge-base --is-ancestor <branch> origin/main && echo 已入main

# 合并冲突数（决定「能否直接合」）
git merge-tree --write-tree $B origin/pr-m2-r11 | grep -c '^CONFLICT'   # 0
git merge-tree --write-tree $B origin/feature/hbos-attendance-console | grep -c '^CONFLICT'  # 109

# hb_stock_app 在哪
for r in $(git branch -r --format='%(refname:short)' | grep -v 'origin/HEAD'); do
  n=$(git ls-tree -r --name-only "$r" -- apps/hb_stock_app 2>/dev/null | wc -l); [ "$n" -gt 0 ] && echo "$r: $n"
done

# PR 全状态
gh pr list --state all    # 或走 REST: /repos/<owner>/<repo>/pulls?state=all
```

---

## 八、边界声明

- 本清单**只做盘点**：未修改任何分支、未解决冲突、未合并任何 PR、未删除任何分支或引用。
- **未动运行态**：未执行 `migrate`、未重建容器、未写数据库、未跑 Frappe 测试。
- 已核对：本文件不含真实工号、真实姓名或密钥——**全为 0**。
- 数据为 **2026-10-10** 的实测快照；仓库当日活跃（有他人在推新分支与 PR），后续会变。
