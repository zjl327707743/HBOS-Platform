# HBOS 版本更新记录（M1-FIX-B5 功能补漏批次）

> 分支：`m1-fix-b5-ai-and-shifts`
> 基线：本地 `main` = `58a293b`（相对 `origin/main` 领先 32 个提交）
> 生成日期：2026-09-04
> 目的：记录本批次相对「上次上传」新增的全部内容，便于后续查版本、回归与验收。方法核对以 `git log origin/main..HEAD` 为准。

---

## 一句话总结

在 M1-FIX-B5 基础上，本次交付三大块功能 —— **① 规则看板**（班次/名单/参数可视化）、**② 班次人员维护表导出**（Excel）、**③ 月度考勤汇总 AI 复核**（大模型复核异常），以及支撑它们的**班次体系核心代码首次入库**、**运行环境 B5 后续业务改进入库**、**环境与文档入库**，另含若干筛选/导出 bug 修复。

> 注意：本分支依赖的 `pairing.py` 等班次系统核心文件**自始未版本化**，本次已一并纳入版本控制（commit `ff0c3c1`），此后脱离工作区即可独立 checkout 使用。

---

## 一、规则看板（班次管理页新增 Tab）

| 提交 | 内容 |
|---|---|
| `bd71a3b` | 设计文档：规则看板设计（M1-FIX-B5） |
| `64da0aa` | 名单常量从 `api.py` 抽到纯模块 `rule_lists.py`（re-export，判定逻辑零改动，离线可测） |
| `1f2b4d6` | 规则看板静态数据构建器 `rules_board.py`（内置班次/名单/配对参数/优先级链） |
| `ffd2705` | 白名单端点 `get_rules_board`（规则记录 + 绑定人数实时计算） |
| `464c7cf` | 规则看板 Tab + 5 分区渲染（优先级链/规则表/内置班次/名单卡片/配对参数） |
| `090bee9` | 名单卡片展开显示姓名、班次规则按部门分区、B5 台账同步 |

**功能**：班次管理页「规则看板」Tab，将三类规则可视化 —— ① 规则表记录（含绑定人数，生效/停用可展开）；② 内置默认班次 8 种；③ 名单规则（行政/豁免/无菌/四班次/安全/食堂/上下班打卡机 SN）卡片 + 展开姓名；④ 配对算法参数；⑤ 判定优先级链。

## 二、班次维护表导出（规则看板新增按钮）

| 提交 | 内容 |
|---|---|
| `0b1f100` | 设计文档：班次人员维护表导出 |
| `5613fd3` | 归行纯函数 `roster_classify.py`（优先级 豁免>绑定>名单>通用倒班，离线可测） |
| `84bb0a0` | 导出端点 `roster_export.export_shift_roster`（5-sheet xlsx） |
| `26f37ed` | 名单 sheet 只列在职建档成员，去除离职/无档空行 |
| `b286ec5` | 规则看板「导出班次人员维护表」按钮 |

- 5 个 sheet：部门-班次-人员（主表，按部门×班次体系有人的组合）+ 豁免人员 + 特殊班次 + 行政班名单 + 说明。
- 姓名含工号；豁免不进主表；未建档/离职工号不列空行。
- 文件：`HBOS班次人员维护表_YYYYMMDD.xlsx`。

## 三、月度考勤汇总 AI 复核

| 提交 | 内容 |
|---|---|
| `77f4050` | 设计文档：月度 AI 复核（enable_ai 临时列） |
| `f5ba417` | 实施计划 |
| `57a5888` | AI 纯函数模块 `ai_review.py`（prompt/返回解析/env，顶层无 frappe 可离线测） |
| `5d11b5a` | 月度汇总 enable_ai 过滤 + AI复核列 + `ai_review_preview` 端点 |
| `11d23e0` | AI复核按钮（确认人次）+ 导出透传 enable_ai |
| `cb633d5` | 台账/主文档同步（含 export_exceptions 首入库说明） |

**功能**：月度考勤汇总报表点「AI复核」→ 确认异常员工人次 → 逐人调真实大模型（OpenAI 兼容 + env `HBOS_AI_*`）复核迟到/早退/缺勤，每行生成「日期｜结论（属实/存疑/非异常）｜理由」；随 CSV/Excel 导出；再次筛选 AI 列消失、每次点击重新复核。
**运行环境验证已通**（deepseek-v4-flash 实测返回规范），需 backend 配置 `HBOS_AI_BASE_URL/API_KEY/MODEL` 方可调用。

## 四、班次体系核心首次入库（补齐版本缺失）

| 提交 | 内容 |
|---|---|
| `ff0c3c1` | 配对 `pairing.py` / 内置班次 `shift_rules.py` / 排班 `rotation_schedule.py`/`schedule_import.py` + HBOS Shift Rule / HBOS Employee Shift / HBOS Employee Schedule DocType + 人员管理页 + 翻译 + 配套测试 |

关键在于功能代码依赖的班次体系核心从未入库，本次首次纳入，分支脱离工作区文件即可独立。

## 五、运行环境 B5 后续业务改进入库

| 提交 | 内容 |
|---|---|
| `ea59fa4` | 豁免单一源（api.EXEMPT_NUMS）、打卡流水来源过滤/中文口径、仪表盘豁免去重、中文化（后台 create_site ui）、得力云定时同步等 |

## 六、环境与文档入库

| 提交 | 内容 |
|---|---|
| `3ab5a02` | docker-compose（assets-data 挂载/时区/飞书/得力/env透传）、.gitignore 翻译例外、README/AI_CONTEXT/HBOS判定规则、docs/attendance 名单对照表、docs/plans 班次方案、tools 复现脚本 |
| `261a78d` | backend 增加 `HBOS_AI_*` 环境变量透传（月度 AI 复核用） |

## 七、连续性/筛选修复

| 提交 | 内容 |
|---|---|
| `de3a113` | AI 复核单批复核上限 20 人，防同步全量调用超代理超时（浏览器转圈/断开） |
| `8d1d052` | 移除 6 个过滤的 change 复位监听，修复「点 8 月看不到」 |
| `58a293b` | 年日期范围过滤仅双方都提供且 from<=to 时生效，修复「筛选时间空结果/界面消失」 |

## 部署/运行提示

1. **AI 复核**：backend 容器须配置 env `HBOS_AI_BASE_URL` / `HBOS_AI_API_KEY` / `HBOS_AI_MODEL`（`.env`，不入 git），重启 `docker compose up -d backend` 后生效。
2. 月度导出与 AI 复核的排序、过滤都在服务端完成。

## 测试

- 离线 `unittest` 全量 32→110 通过（新增规则看板/导出/AI 复核契约）。
- 真实 LLM 调用已验证连通（无症状部署版）。
- 报表筛选修复经 nginx + 服务端实测验证。

---

*以上内容依据 `git log origin/main..HEAD`（32 提交）整理；如需逐文件 diff 可 `git diff origin/main..HEAD` 查看。*