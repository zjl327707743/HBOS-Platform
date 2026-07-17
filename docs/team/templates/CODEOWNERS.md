# CODEOWNERS 示例

将此文件复制到 `.github/CODEOWNERS` 即可启用。根据实际成员 GitHub 用户名修改。

> 注意：CODEOWNERS 文件路径必须是 `.github/CODEOWNERS`（在仓库根目录的 `.github` 文件夹内）。

```
# HBOS 项目 CODEOWNERS
# 当有人修改匹配的文件时，指定的 Owner 会自动被请求审查。

# 全局 Owner — 所有 PR 都需要 Owner 审查
* @owner-github-username

# 文档 — 文档修改由 Owner 审查
docs/** @owner-github-username

# 自定义 App — 各 App 负责人
apps/hb_attendance_app/** @owner-github-username @app-developer-username

# Docker/部署 — 基础设施变更需要特别注意
docker-compose.yml @owner-github-username
.env.example @owner-github-username

# CI/CD — CI 配置变更需要 Owner 审查
.github/** @owner-github-username
```

## 使用说明

1. 将 `@owner-github-username` 和 `@app-developer-username` 替换为实际的 GitHub 用户名
2. 将文件复制到 `.github/CODEOWNERS`
3. 提交并推送
4. 在 GitHub 仓库 Settings → Branches 中启用 "Require review from Code Owners"
