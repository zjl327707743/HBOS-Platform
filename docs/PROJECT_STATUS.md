# Project Status

项目名称：新乡海滨智能运营管理平台。

## 当前状态

- 当前阶段：M0
- 当前轮次：M0-R3A Frappe / Docker 最小环境落地
- 当前仓库定位：工程启动文档、AI 上下文、里程碑状态、计划、ADR、环境设计文档与最小 Docker 配置
- 当前实现状态：M0-R3A 已完成 Frappe / ERPNext / Docker 最小本地环境落地；Docker 镜像已拉取，容器已启动，测试 site 已初始化，Frappe Desk 登录页已验证

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

## 下一步

下一轮建议交给 Codex 做 M0-R3A-PULL-RETRY 审查；审查通过后再规划 M0-R3B 或后续环境治理事项，不在本轮启动。
