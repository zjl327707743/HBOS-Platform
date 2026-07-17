# 开源依赖清单模板

## 核心依赖

| 依赖 | 版本 | 许可证 | 许可证链接 | 使用方式 | 是否修改 | 风险 |
|------|------|--------|------------|----------|----------|------|
| Frappe Framework | 16.25.0 | MIT | https://github.com/frappe/frappe/blob/develop/LICENSE | Docker 镜像 | 否 | 低 |
| ERPNext | 16.26.2 | GPLv3 | https://github.com/frappe/erpnext/blob/develop/license.txt | Docker 镜像 | 否 | 中（GPLv3） |
| Frappe HR (HRMS) | 16.12.0 | GPLv3 | https://github.com/frappe/hrms/blob/version-16/license.txt | 源码绑定挂载 | 否 | 中（GPLv3） |
| MariaDB | 11.8 | GPLv2 | https://mariadb.com/kb/en/mariadb-license/ | Docker 镜像 | 否 | 低 |
| Redis | 6.2-alpine | BSD 3-Clause | https://redis.io/docs/about/license/ | Docker 镜像 | 否 | 低 |

## Python 依赖（间接）

Frappe/ERPNext/HRMS 的 Python 依赖由 Docker 镜像内部管理，不直接管理。如需添加新依赖，应在自定义 App 的 `pyproject.toml` 中声明。

## JavaScript 依赖（间接）

Frappe/ERPNext/HRMS 的 JS 依赖由 Docker 镜像内部管理。自定义 App 的 JS 依赖通过 Frappe 的 `build.json` 管理。

## 许可证义务摘要

| 许可证 | 内部使用 | 修改源码 | 分发 | SaaS 提供 |
|--------|----------|----------|------|-----------|
| MIT | ✅ 无限制 | ✅ 允许 | ✅ 允许（需保留版权声明） | ✅ 无限制 |
| GPLv3 | ✅ 无限制 | ✅ 允许（需公开修改） | ⚠️ 需提供源码 | ⚠️ 需提供源码 |
| GPLv2 | ✅ 无限制 | ✅ 允许（需公开修改） | ⚠️ 需提供源码 | ⚠️ 需提供源码 |
| BSD 3-Clause | ✅ 无限制 | ✅ 允许 | ✅ 允许（需保留版权声明） | ✅ 无限制 |

## 定期检查

- [ ] 每季度检查一次许可证合规性
- [ ] 新增依赖前检查许可证
- [ ] 升级前检查许可证变更
- [ ] 对外分发前重新检查所有许可证

## 注意事项

1. GPLv3 有"传染性"：如果修改了 GPLv3 代码并分发，必须公开修改后的源码
2. 内部使用（不对外分发）GPL 代码的义务较少
3. 通过 API/网络调用使用 GPL 服务（SaaS）的许可证义务有争议，建议咨询法律顾问
4. 本清单不构成法律建议，仅用于工程风险提示