# .env.example 字段建议

当前项目的 `.env.example` 位于项目根目录。以下列出每个字段的用途和填写建议。

> 注意：`.env.example` 是模板文件，可以提交 Git。`.env` 是真实配置文件，绝对不能提交 Git。

## 当前 .env.example 字段说明

| 变量名 | 用途 | 示例值 | 是否敏感 |
|--------|------|--------|----------|
| `COMPOSE_PROJECT_NAME` | Docker Compose 项目名称，用于区分多个环境 | `hbos-dev` | 否 |
| `ERPNEXT_VERSION` | Frappe/ERPNext Docker 镜像版本 | `v16.26.2` | 否 |
| `SITE_NAME` | Frappe 站点名称 | `frontend` | 否 |
| `FRAPPE_SITE_NAME_HEADER` | Nginx 站点名称头 | `frontend` | 否 |
| `HTTP_PORT` | 前端访问端口 | `8080` | 否 |
| `MARIADB_HOST` | 数据库容器名 | `db` | 否 |
| `DB_PORT` | 数据库端口 | `3306` | 否 |
| `DB_ROOT_PASSWORD` | 数据库 root 密码 | 随机生成 | ⚠️ 是 |
| `MYSQL_ROOT_PASSWORD` | MySQL root 密码（兼容） | 同 DB_ROOT_PASSWORD | ⚠️ 是 |
| `REDIS_CACHE` | Redis 缓存地址 | `redis-cache:6379` | 否 |
| `REDIS_QUEUE` | Redis 队列地址 | `redis-queue:6379` | 否 |
| `SOCKETIO_PORT` | WebSocket 端口 | `9000` | 否 |
| `ADMIN_PASSWORD` | Frappe 管理员密码 | 随机生成 | ⚠️ 是 |
| `UPSTREAM_REAL_IP_ADDRESS` | 上游真实 IP | `127.0.0.1` | 否 |
| `UPSTREAM_REAL_IP_HEADER` | IP 头名称 | `X-Forwarded-For` | 否 |
| `UPSTREAM_REAL_IP_RECURSIVE` | 递归 IP 查找 | `off` | 否 |
| `PROXY_READ_TIMEOUT` | 代理读取超时 | `120` | 否 |
| `CLIENT_MAX_BODY_SIZE` | 最大上传文件 | `50m` | 否 |

## 未来可能需要添加的字段

| 变量名 | 用途 | 是否敏感 |
|--------|------|----------|
| `FEISHU_APP_ID` | 飞书应用 ID | ⚠️ 是 |
| `FEISHU_APP_SECRET` | 飞书应用密钥 | ⚠️ 是 |
| `GITHUB_TOKEN` | CI 使用的 GitHub Token | ⚠️ 是 |
| `DB_BACKUP_PATH` | 数据库备份路径 | 否 |
| `LOG_LEVEL` | 日志级别 | 否 |
| `ENVIRONMENT` | 环境标识（dev/staging/prod） | 否 |

## 新成员如何获取 .env

1. Owner 通过安全渠道（飞书私聊、1Password、加密文件）发送 `.env` 文件
2. 新成员将 `.env` 放在项目根目录
3. 检查 `.env` 是否被 `.gitignore` 忽略（当前已配置）
4. 不要将 `.env` 通过邮件、群聊、Git 等不安全方式传输

## 密码生成建议

本地开发环境可以使用以下命令生成随机密码：

```bash
# 生成 16 位随机密码
openssl rand -base64 16
```

生产环境必须使用更强的密码，建议使用密码管理器生成。