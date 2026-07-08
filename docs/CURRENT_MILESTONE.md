# Current Milestone

## M1：平台入口、身份与考勤一期准备

项目名称：新乡海滨智能运营管理平台。

## 当前轮次

M1-R7：飞书登录、领导 Demo 与 M1 收口准备。当前状态：COMPLETED。

M1-R6C：异常识别与异常说明流程最小实现。当前状态：COMPLETED。

M1-R6B：脱敏打卡流水导入最小实现。当前状态：COMPLETED。

M1-R6A：Excel 导入与异常流程落地方案 / Gate 判定。当前状态：COMPLETED。

M1-R5：HRMS 配置基线、考勤工作台与月度汇总 Demo。当前状态：COMPLETED。

M1-REQ-DESIGN-DRAFT-CLOSEOUT：M1 需求设计草案审查通过后状态收口。当前状态：COMPLETED。

M1 考勤一期仍在推进中。M0 已完成并封板。M0-REMOTE 已完成 GitHub Private remote 创建、`origin` 绑定和 `main` 首次 push。M1 当前状态：IN_PROGRESS。M1-R0 已通过 Codex 独立审查并收口为 COMPLETED。M1-R1 已通过 Codex 独立审查并收口为 COMPLETED。M1-R2 已通过 Codex 独立审查并收口为 COMPLETED。M1-R3 已通过 Codex 审查，实际结论为 PARTIAL / BLOCKED，最终状态收口为 BLOCKED。M1-R3A 已通过 Codex 审查并收口为 COMPLETED。M1-R3B 已通过 Codex 审查并收口为 COMPLETED。M1-R3B-FIX 已通过 Codex 审查并收口为 COMPLETED。M1-R3C 已通过 Codex 审查并收口为 COMPLETED，结论为 PARTIAL / GAP_IDENTIFIED。M1-R3D 已通过 Codex 审查并收口为 COMPLETED，结论为 Gap 四类分类、均不需要立即创建 hb_attendance_app。M1-R3E 已通过 Codex 审查并收口为 COMPLETED。M1-R3F 已通过 Codex 审查并收口为 COMPLETED。M1-REQ-DESIGN-DRAFT 已通过 Codex 审查并收口为 COMPLETED。M1-R4 已通过 Codex 审查并收口为 COMPLETED。M1-R5 已通过 Codex 审查并收口为 COMPLETED。M1-R6A 为 COMPLETED。M1-R6B 为 COMPLETED。M1-R6C 为 COMPLETED。M1-R7 当前为 COMPLETED。M1-R8 为 PLANNED（可选缓冲轮）。

权威计划文件：

- `docs/plans/M0-R2_Frappe_Docker最小环境方案设计.md`

权威状态文件：

- `docs/PROJECT_STATUS.md`
- `docs/CURRENT_MILESTONE.md`
- `docs/milestones/M0.md`

## 本轮范围

只做 M1-R7：飞书登录 + 领导 Demo + M1 收口准备。不得 closeout R7（只进入 REVIEWING），不得启动 M1 总收口。

交付内容：

- `docs/milestones/M1_R7_飞书登录领导Demo与M1收口准备.md`（本轮主文档）
- 飞书 OAuth 登录方案设计、配置参数表、验证 blocker 记录
- 飞书身份 → Frappe User → Employee 自动匹配规则
- 领导汇总 Demo 指标定义、数据来源、Query Report 设计
- 领导月报查看/导出路径
- M1 Demo 演示路径整理
- M1 收口准备项清单（不执行）
- 项目状态、当前里程碑和里程碑索引文件更新

本轮实际结果：

- 飞书 OAuth 登录方案设计完成（Social Login Key 配置参数表、User/Employee 匹配规则、未匹配处理、本地管理员兜底、权限边界）。
- 飞书 OAuth 端到端验证未执行（blocker：飞书平台侧 + 网络侧 + 安全侧条件未满足）。
- 领导汇总 Demo 4 个核心指标定义、Query Report SQL 和 Dashboard 设计已固化。
- 月报查看（4 条路径）和导出（4 种方式）已整理。
- M1 Demo 完整演示路径（10 个环节）已整理。
- M1 收口准备项（10 项）和 Owner 决策项（5 项）清单已列出。
- M1 12 条验收标准逐条对照已完成。
- M1 closeout 未启动，M2 未启动。
- 本轮未创建 App、未创建 DocType、未修改核心源码、未提交 Excel / CSV / secret。

## 本轮禁止事项

- 不 closeout R7
- 不启动 M1 总收口
- 不接飞书工作台
- 不接飞书请假
- 不接真实考勤机
- 不部署公司内网/云服务器
- 不启动大型 Vue 前端
- 不重写 R6A / R6B / R6C
- 不创建 `hb_core_app`、`hb_attendance_app`、`hb_feishu_app`
- 不创建 `hb_hr_app`
- 不创建自定义 DocType
- 不做业务代码
- 不修改 Frappe / ERPNext / HRMS 核心源码
- 不执行 `docker compose down -v`
- 不删除 volume
- 不重建 `frontend` site
- 不重新安装 HRMS
- 不修改 `docker-compose.yml`、`.env.example`
- 不提交 `.env`、备份、密钥、数据库、日志、缓存或运行时产物
- 不提交 Excel / CSV / 真实数据
- 不提交飞书 App ID / App Secret
- 不伪造飞书登录成功

## 当前批次状态

- M0-R2 设计文档已完成并提交。
- M0-R2A 默认入口文档过期描述修复已完成。
- M0-R2B 里程碑状态管理规范已完成。
- M0-R2C AI Skill 路由文档纳入已完成。
- M0-R2D 中文提交与文档命名规范已完成。
- M0-R2E README 阶段描述修复与公共入口文件收尾规则补强已完成。
- M0-R3A 已完成：镜像拉取成功，容器启动成功，测试 site 初始化成功，Frappe Desk 登录页验证成功。
- M0-R3B 已完成评估并通过 Codex 审查。
- M0-R3C 已完成：HRMS 已安装到 `frontend` site，`hrms 16.12.0 version-16` 已验证，Desk 与基础 HR 模块可访问。
- M0-R3C-FIX 已完成：HRMS 资源 404、Frappe HR 图标缺失和 Roster 白屏已修复，`/hr/roster/` 已验证渲染 Roster 月视图。
- M0-R3D 已完成能力盘点与 M1 考勤一期边界设计。
- M0-R3E 已完成 HRMS 环境可复现性收口并通过 Codex 审查。
- M0 已完成并封板。
- M0-REMOTE 已完成 GitHub Private remote 创建、`origin` 绑定和 `main` 首次 push。
- M1-R0 已完成平台入口、账号体系、角色权限、飞书 SSO 可行性、中文化 / 本地化诊断方案，并已通过 Codex 独立审查，状态为 COMPLETED。
- M1-R1 已通过 Codex 独立审查并收口为 COMPLETED。
- M1-R2 已通过 Codex 独立审查并收口为 COMPLETED。
- M1-R3 已通过 Codex 审查，实际结论为 PARTIAL / BLOCKED，最终状态为 BLOCKED。
- M1-R3A 为 COMPLETED。
- M1-R3B 为 COMPLETED。
- M1-R3B-FIX 为 COMPLETED。
- M1-R3C 为 COMPLETED。
- M1-R3D 为 COMPLETED。
- M1-R3E 为 COMPLETED。
- M1-R3F 为 COMPLETED。
- M1-REQ-DESIGN-DRAFT 为 COMPLETED。
- M1-R4 当前状态为 COMPLETED，已通过 Codex 审查并收口。
- M1-R5 当前状态为 COMPLETED，已通过 Codex 审查并收口。
- M1-R6A 当前状态为 COMPLETED，已通过 Codex 审查并收口。
- M1-R6B 当前状态为 COMPLETED，已通过 Codex 审查并收口。
- M1-R6C 当前状态为 COMPLETED。
- M1-R7 当前状态为 COMPLETED，已通过 Codex 审查并 closeout。
- M1-R8 当前状态为 PLANNED（可选缓冲轮，不预先承诺一定执行）。

## 验收标准

- M1-R2 已通过 Codex 独立审查并收口为 COMPLETED
- M1-R3 已通过 Codex 审查并收口为 BLOCKED，不得标记为 COMPLETED
- M1-R3A 已通过 Codex 审查并收口为 COMPLETED
- M1-R0 飞书登录目标已保留为：飞书登录为主，HBOS 内部 User 自动映射，Frappe 权限体系承接系统权限和审计
- M1 状态已同步为 IN_PROGRESS
- M1-R3B 已通过 Codex 审查并收口为 COMPLETED
- M1-R3B-FIX 已通过 Codex 审查并收口为 COMPLETED
- M1-R3C 已通过 Codex 审查并收口为 COMPLETED，结论为 PARTIAL / GAP_IDENTIFIED
- M1-R3D 已通过 Codex 审查并收口为 COMPLETED，结论为 Gap 四类分类、均不需要立即创建 hb_attendance_app
- M1-R3E 已通过 Codex 审查并收口为 COMPLETED
- M1-R3F 已通过 Codex 审查并收口为 COMPLETED
- M1-REQ-DESIGN-DRAFT 已通过 Codex 审查并收口为 COMPLETED
- M1-R4 当前状态为 COMPLETED，已通过 Codex 审查并收口
- M1-R5 当前状态为 COMPLETED，Codex 审查 PASS 后完成 closeout 收口
- M1-R6A 当前状态为 COMPLETED，已通过 Codex 审查并收口。
- M1-R6B 当前状态为 COMPLETED，已通过 Codex 审查并收口。
- M1-R6C 当前状态为 COMPLETED，已通过 Codex 审查并 closeout。
- M1-R7 当前状态为 COMPLETED，已通过 Codex 审查并 closeout。
- M1-R8 保持 PLANNED（可选缓冲轮）
- 本轮未创建自定义 App / DocType / 核心源码变更；方案设计和文档交付为主

## 下一轮预告

M1-R7 已通过 Codex 审查并 closeout 为 COMPLETED。下一步需 Owner 授权后，才可进入 M1 总收口 / M1 closeout。M1 closeout 为 PLANNED / 待授权 / 未启动。
