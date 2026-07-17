# 分支保护规则建议

## 推荐为 `main` 分支启用的保护规则

在 GitHub 仓库 → Settings → Branches → Add branch protection rule 中配置：

### 分支名称

```
main
```

### 保护规则

| 规则 | 推荐值 | 说明 |
|------|--------|------|
| Require a pull request before merging | ✅ 启用 | 禁止直接 push 到 main |
| Require approvals | ✅ 1 个 | 至少 1 人审查通过 |
| Dismiss stale pull request approvals when new commits are pushed | ✅ 启用 | 有新提交时旧审查失效 |
| Require review from Code Owners | ✅ 启用 | 需要 CODEOWNERS 审查 |
| Require status checks to pass before merging | ✅ 启用 | CI 通过才能合并 |
| Require branches to be up to date before merging | ✅ 启用 | 合并前必须与 main 同步 |
| Require conversation resolution before merging | ✅ 启用 | 所有评论已解决才能合并 |
| Do not allow bypassing the above settings | ✅ 启用 | 管理员也不能跳过 |
| Allow force pushes | ❌ 禁用 | 禁止强制推送 |
| Allow deletions | ❌ 禁用 | 禁止删除分支 |

### 推荐的 Status Check 列表

以下 CI 检查通过后才能合并（需要先配置对应的 CI workflow）：

- `docker-compose-config-check` — Docker Compose 配置校验
- `bench-test` — Frappe App 测试
- `secret-scan` — Secret 扫描

## 启用时机

- 当前 M1-FIX 阶段，只有 Owner 一人开发，可以暂缓
- 在新成员加入前必须启用
- 最晚在新成员创建第一个 PR 前启用

## 备注

分支保护规则只能在 GitHub 网页端配置，CLI 无法直接设置。Owner 需要登录 GitHub → 仓库 Settings → Branches → Add rule。
