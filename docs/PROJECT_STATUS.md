# Project Status

项目名称：新乡海滨智能运营管理平台。

## 当前状态

- 当前阶段：M0
- 当前轮次：M0-R3C Frappe HR / HRMS 安装验证
- 当前仓库定位：工程启动文档、AI 上下文、里程碑状态、计划、ADR、环境设计文档与最小 Docker 配置
- 当前实现状态：M0-R3A 已完成 Frappe / ERPNext / Docker 最小本地环境落地；M0-R3B 已完成 HRMS 安装前评估并通过 Codex 审查；M0-R3C 已完成 HRMS 安装验证，HRMS 已安装到本地 `frontend` site，基础 HR 模块可访问；当前未创建海滨自定义 App，未开发业务

## 状态更新制度

项目总状态必须在每轮任务收尾时同步更新。

- 如本轮改变项目状态，必须更新 `docs/PROJECT_STATUS.md`。
- 如本轮改变当前里程碑或轮次，必须更新 `docs/CURRENT_MILESTONE.md`。
- 如本轮属于某个里程碑，必须更新 `docs/milestones/M0.md` 或对应里程碑文件。
- 输出结果时必须说明状态文件是否已更新；如未更新，必须说明原因。

## 已确认架构方向

准确叫法：Frappe/ERPNext 开源底座 + Frappe 多 App 模块化架构 + 外部独立服务扩展。

长期架构：Frappe/ERPNext 开源底座 + 海滨自定义 Frappe App + 外部 AI/视频/算法服务 + Vue/React 驾驶舱 + 飞书集成 + Docker 部署。

主技术栈：Frappe Framework、ERPNext、Frappe HR、Python、JavaScript、MariaDB/MySQL 兼容体系、Redis、Docker、Docker Compose、Vue/React、ECharts、FastAPI。

## M0-R1 状态

状态：已完成并封板。

本轮目标：

- 创建根目录说明文档
- 创建 AI 协作上下文文档
- 创建当前里程碑文档
- 创建 M0 工程启动计划
- 创建四个基础 ADR

本轮未做：

- 未安装 Frappe/ERPNext/Frappe HR
- 未创建 Frappe bench
- 未创建任何 Frappe App
- 未创建 `hb_core_app`、`hb_attendance_app`、`hb_feishu_app`
- 未写 Docker Compose
- 未开发考勤业务
- 未接入飞书
- 未开发前端驾驶舱

## M0-R2 状态

状态：已完成并通过 Codex 审查，已提交。

本轮目标：

- 设计 Frappe / ERPNext / Docker 最小本地开发环境方案
- 设计最小服务清单、目录规划、端口规划、数据卷规划和环境变量分组
- 明确 M0-R3 才允许真正落地 `docker-compose.yml` 与 Frappe 环境

本轮未做：

- 未安装 Frappe/ERPNext/Frappe HR
- 未创建 Frappe bench
- 未创建任何 Frappe App
- 未创建 `hb_core_app`、`hb_attendance_app`、`hb_feishu_app`
- 未写 Docker Compose
- 未创建 `.env`
- 未启动容器
- 未开发考勤业务
- 未接入飞书
- 未开发前端驾驶舱

## M0-R2B 状态

状态：已完成并通过 Codex 审查，已提交。

本轮目标：

- 建立里程碑规划和状态文件机制
- 固化每轮收尾必须更新状态的规则
- 新增 `docs/milestones/README.md` 和 `docs/milestones/M0.md`
- 更新协作规则、项目状态、当前里程碑、阅读指南和 M0-R2 计划

本轮未做：

- 未安装 Frappe/ERPNext/Frappe HR
- 未创建 Frappe bench
- 未创建任何 Frappe App
- 未写 Docker Compose
- 未创建 `.env`
- 未创建 `.gitignore`
- 未启动容器
- 未开发考勤业务
- 未接入飞书
- 未开发前端驾驶舱

## M0-R2C 状态

状态：已完成。

本轮目标：

- 收口 M0-R2 批次状态台账
- 确认 M0-R3 未开始
- 创建一次 Git 提交

本轮未做：

- 未安装任何 skill
- 未执行飞书真实写入
- 未安装 Frappe/ERPNext/Frappe HR
- 未创建 Frappe bench
- 未创建任何 Frappe App
- 未写 Docker Compose
- 未创建 `.env`
- 未启动容器
- 未开发业务代码
- 未开发前端驾驶舱

## M0-R2A 状态

状态：已完成并通过 Codex 审查，已提交。

本轮目标：

- 修复默认入口文档中的过期当前轮次描述
- 确保状态入口指向当前真实进度

## M0-R2D 状态

状态：已完成。

本轮目标：

- 新增并纳入 `docs/AI技能路由规范.md`
- 明确已确认可用 skill 与候选 skill 的边界
- 将 skill 路由规则接入 `CLAUDE.md`、`AGENTS.md`、`docs/AI_CONTEXT.md` 和 `docs/READING_GUIDE.md`
- 固化 Git 提交描述优先中文的规则
- 固化新增文档名称优先中文或中英混合的规则
- 将 M0-R2 批次新增英文文档改为中文或中英混合文件名

本轮未做：

- 未安装 Frappe/ERPNext/Frappe HR
- 未创建 Frappe bench
- 未创建任何 Frappe App
- 未写 Docker Compose
- 未创建 `.env`
- 未创建 `.gitignore`
- 未启动容器
- 未开发考勤业务
- 未执行飞书真实写入
- 未开发前端驾驶舱

## M0-R2E 状态

状态：已完成。

本轮目标：

- 修复 `README.md` 中过期的阶段描述
- 在协作规则中补强公共入口文件收尾检查规则
- 同步项目状态、当前里程碑和 M0 里程碑台账
- 创建一次 Git 提交

本轮未做：

- 未安装 Frappe/ERPNext/Frappe HR
- 未创建 Frappe bench
- 未创建任何 Frappe App
- 未写 Docker Compose
- 未创建 `.env`
- 未创建 `.gitignore`
- 未启动容器
- 未开发考勤业务
- 未执行飞书真实写入
- 未开发前端驾驶舱

## M0-R3A 状态

状态：COMPLETED。

本轮目标：

- 创建 Frappe / ERPNext / Docker 最小本地环境配置
- 创建 `.env.example`、`.gitignore` 和落地记录文档
- 基于官方 `frappe/frappe_docker` 资料确认版本和服务结构
- 拉取镜像、启动容器、初始化本地测试 site、验证 Frappe Desk

当前结果：

- 已创建最小 Docker 配置和落地记录
- 已基于官方 `pwd.yml` 确认服务结构与镜像 tag
- 原执行时本机执行 `docker --version && docker compose version` 返回 `zsh:1: command not found: docker`
- 本轮 M0-R3A-VERIFY 已获用户授权继续执行真实 Docker 本地启动验证
- 本轮确认 `docker --version` 和 `docker compose version` 已可用
- 已从 `.env.example` 生成本地 `.env`，`.env` 被 `.gitignore` 忽略且未被 Git 追踪
- 已执行 `docker compose pull`，但在拉取镜像时失败：Docker Hub token 获取返回 EOF
- M0-R3A-PULL-RETRY 已重试 `docker compose pull` 并成功拉取 `redis:6.2-alpine`、`mariadb:11.8`、`frappe/erpnext:v16.26.2`
- 首次 `docker compose up -d` 遇到宿主机 `8080` 端口占用，仅调整本地 `.env` 的 `HTTP_PORT=8081` 后启动成功；`.env` 未被 Git 追踪
- `create-site` 已成功完成，测试 site 为 `frontend`
- `bench version` 验证：ERPNext `16.26.2`，Frappe `16.25.0`
- Frappe Desk 登录页已通过 `http://localhost:8081/login` 验证，返回 `HTTP 200`

本轮未做：

- 未创建 `hb_core_app`
- 未创建 `hb_attendance_app`
- 未创建 `hb_feishu_app`
- 未安装自定义 Frappe App
- 未安装 Frappe HR / HRMS
- 未开发考勤业务
- 未执行飞书真实写入
- 未开发前端驾驶舱
- 未写 Python/JavaScript/TypeScript 业务代码
- 未引入第三方业务源码
- 未 push
- 未配置 remote
- 未提交真实密钥

## M0-R3B 状态

状态：COMPLETED。

本轮目标：

- 评估 Frappe HR / HRMS 官方信息、v16 分支 / tag 与当前环境的兼容性
- 比较现有容器 / bench 内安装与自定义镜像 / 扩展 Compose 流程两种候选方案
- 给出 M0-R3C 推荐安装方式、边界、风险和回滚建议
- 更新项目状态、当前里程碑和 M0 里程碑台账
- 根据 Codex 审查结论收口 M0-R3B 状态

当前结论：

- 当前环境为 ERPNext `16.26.2`、Frappe `16.25.0`，site 为 `frontend`，Desk 地址为 `http://localhost:8081/login`
- 当前仅安装 `frappe` 和 `erpnext`，未安装 HRMS
- 官方 `frappe/hrms` 存在 `version-16` 分支和 v16 tag；`version-16` 依赖声明要求 Frappe / ERPNext `>=16.0.0,<17.0.0`
- 从主版本范围看，HRMS `version-16` 与当前 Frappe / ERPNext v16 环境方向一致；具体 tag / branch 仍需 M0-R3C 实际安装验证
- 推荐 M0-R3C 在备份和可回滚前提下安装 HRMS，并只验证 HRMS App 和基础 HR 模块可访问
- M0-R3B 已通过 Codex 审查，状态已从 REVIEWING 收口为 COMPLETED

本轮未做：

- 未安装 Frappe HR / HRMS
- 未创建 `hb_core_app`
- 未创建 `hb_attendance_app`
- 未创建 `hb_feishu_app`
- 未安装自定义 Frappe App
- 未开发考勤业务
- 未执行飞书真实写入
- 未开发前端驾驶舱
- 未写 Python/JavaScript/TypeScript 业务代码
- 未修改 `docker-compose.yml`、`.env.example`、`.gitignore`
- 未提交真实密钥
- 未 push

## M0-R3C 状态

状态：COMPLETED。

本轮目标：

- 将 M0-R3B 从 REVIEWING 收口为 COMPLETED
- 备份当前 `frontend` site 并记录安装前环境状态
- 基于官方 `frappe/hrms` 的 `version-16` 分支安装 Frappe HR / HRMS
- 验证 HRMS App 已安装，基础 HR 模块可在 Desk 中访问
- 记录安装命令、日志摘要、版本、验证结果、风险与回滚方式

当前结果：

- 安装前已完成 site 备份，备份位于 Docker volume 内的 `/home/frappe/frappe-bench/sites/frontend/private/backups/`
- HRMS 来源为官方 `frappe/hrms` 仓库 `version-16` 分支，分支 commit 为 `666bf10a9271421abc361bded124d2d961a977e3`
- 已执行 `bench get-app hrms --branch version-16`
- 已执行 `bench --site frontend install-app hrms`
- 已执行 `bench --site frontend migrate`
- 已执行最小必要服务刷新
- 安装后 `bench version` 显示 `hrms 16.12.0 version-16 (666bf10)`
- 安装后 `bench --site frontend list-apps` 显示 `hrms 16.12.0 version-16`
- Desk 登录页 `http://localhost:8081/login` 返回 `HTTP 200`
- 登录后 `/app/hr`、`/app/hr-setup`、`/app/employee`、`/app/leave-application`、`/app/shift-and-attendance` 均可访问并返回 `HTTP 200`
- HR Workspace 已包含 `HR Setup`、`Leaves`、`Shift & Attendance`、`Recruitment` 等入口

已知风险：

- 本轮采用现有容器 / bench 内安装验证，适合 M0-R3C 验证，不代表长期可复现部署方案已经完成。
- 当前 Compose 的 `configurator` 会基于镜像内 `apps` 目录重写 `sites/apps.txt`；后续如要长期保留 HRMS，应治理自定义镜像或 Compose 持久化策略。

本轮未做：

- 未创建 `hb_core_app`
- 未创建 `hb_attendance_app`
- 未创建 `hb_feishu_app`
- 未创建任何海滨自定义 Frappe App
- 未开发考勤业务规则
- 未配置飞书
- 未执行飞书真实写入
- 未开发前端驾驶舱
- 未写 Python/JavaScript/TypeScript 业务代码
- 未修改 Frappe/ERPNext/HRMS 核心源码
- 未修改 `docker-compose.yml`
- 未修改 `.env.example`
- 未提交 `.env`
- 未提交真实密钥
- 未 push

## 下一步

下一轮建议交给 Codex 做 M0-R3C 审查；审查通过后再规划 M0-R3D：HRMS 能力盘点与 M1 考勤一期边界设计，不在本轮启动。
