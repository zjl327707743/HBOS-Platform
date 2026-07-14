# 仓库版本矩阵模板

## 当前版本矩阵

| 组件 | 版本 | 固定方式 | 来源 | 备注 |
|------|------|----------|------|------|
| Frappe Framework | 16.25.0 | Docker 镜像 | `frappe/erpnext:v16.26.2` | 不单独升级 |
| ERPNext | 16.26.2 | Docker 镜像 | `frappe/erpnext:v16.26.2` | 不单独升级 |
| HRMS | 16.12.0 | Git tag | `frappe/hrms` version-16 | 需手动更新 |
| hb_attendance_app | 0.0.1 | Git tag | 本项目 | 自定义 App |
| MariaDB | 11.8 | Docker 镜像 | `mariadb:11.8` | 已固定 |
| Redis | 6.2-alpine | Docker 镜像 | `redis:6.2-alpine` | 已固定 |

## 版本更新记录

| 日期 | 组件 | 旧版本 | 新版本 | 操作人 | 备注 |
|------|------|--------|--------|--------|------|
| 2026-07-06 | ERPNext | — | v16.26.2 | Owner | 初始环境搭建 |
| 2026-07-06 | HRMS | — | v16.12.0 | Owner | 初始安装 |
| 2026-07-10 | hb_attendance_app | — | 0.0.1 | Owner | M1-FIX-B 创建 |

## 依赖升级检查清单

升级任何组件前，必须完成以下检查：

- [ ] 阅读该组件的 CHANGELOG / Release Notes
- [ ] 检查是否有 breaking changes
- [ ] 检查与当前环境的兼容性
- [ ] 在本地开发环境先测试
- [ ] 备份数据库
- [ ] 记录升级前后的版本
- [ ] 准备回滚方案

## 镜像版本固定策略

所有 Docker 镜像必须使用精确版本标签，禁止使用：

- `latest` 标签
- 浮动版本号
- `:v16` 等不精确标签

例外：只有在紧急修复且确认兼容性后，才可以在限定范围内使用。