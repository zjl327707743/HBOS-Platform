# Current Milestone

## M0：工程启动与上下文治理

项目名称：新乡海滨智能运营管理平台。

## 当前轮次

M0-R3A：Frappe / Docker 最小环境落地。当前状态：BLOCKED。

权威计划文件：

- `docs/plans/M0-R2_Frappe_Docker最小环境方案设计.md`

权威状态文件：

- `docs/PROJECT_STATUS.md`
- `docs/CURRENT_MILESTONE.md`
- `docs/milestones/M0.md`

## 本轮范围

创建 Frappe / ERPNext / Docker 最小本地环境配置，并尝试拉取镜像、启动容器、初始化本地测试 site、验证 Frappe Desk。

交付内容：

- `docker-compose.yml`
- `.env.example`
- `.gitignore`
- `docs/deployment/M0-R3A_Frappe_Docker最小环境落地记录.md`
- 项目状态、当前里程碑和 M0 里程碑文件更新

## 本轮禁止事项

- 不创建 Frappe bench
- 不创建 `hb_core_app`、`hb_attendance_app`、`hb_feishu_app`
- 不安装自定义 Frappe App
- 不做业务代码
- 不开发考勤业务
- 不接飞书
- 不接飞书真实写入
- 不做前端驾驶舱
- 不引入外部源码
- 不 push

## 当前批次状态

- M0-R2 设计文档已完成并提交。
- M0-R2A 默认入口文档过期描述修复已完成。
- M0-R2B 里程碑状态管理规范已完成。
- M0-R2C AI Skill 路由文档纳入已完成。
- M0-R2D 中文提交与文档命名规范已完成。
- M0-R2E README 阶段描述修复与公共入口文件收尾规则补强已完成。
- M0-R3A 已开始，配置已准备；本轮已获授权执行 Docker 验证，但 `docker compose pull` 在 Docker Hub token 获取处失败，容器未启动，site 未初始化，Desk 未验证。

## 验收标准

- Docker 配置文件存在且不包含真实密钥
- `.env.example` 存在，`.env` 不被 Git 追踪
- 落地记录说明官方参考来源、版本矩阵、执行步骤和本轮镜像拉取阻塞原因
- `docs/PROJECT_STATUS.md` 和 `docs/milestones/M0.md` 同步 M0-R3A 状态
- 未创建自定义 App、未开发业务、未接飞书真实写入、未做前端驾驶舱

## 下一轮预告

下一步先确认 Docker Hub 网络和登录状态，再继续 M0-R3A 的镜像拉取、容器启动、site 初始化与 Desk 访问验证。
