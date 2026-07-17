# Release 检查清单

## 发布前检查

### 代码检查

- [ ] 所有目标 PR 已合并到 main
- [ ] 本地 main 与 origin/main 同步
- [ ] CI 全部通过
- [ ] 无未解决的审查意见
- [ ] 代码已通过 Codex 审查（如适用）

### 测试检查

- [ ] `bench run-tests` 通过
- [ ] 手动测试关键流程通过
- [ ] 无已知阻断性 Bug

### 数据库检查

- [ ] 所有 migration 已执行
- [ ] 数据库备份已完成
- [ ] 数据库迁移可回滚

### 文档检查

- [ ] CHANGELOG 已更新
- [ ] 版本矩阵已更新
- [ ] 相关文档已更新

### 版本号

- [ ] 按 SemVer 规则确定版本号
- [ ] 版本号在 `pyproject.toml` 中更新
- [ ] 版本号在 `hooks.py` 中更新（如适用）

## 发布步骤

1. 更新版本号
2. 更新 CHANGELOG
3. 提交：`chore: 发布 vX.Y.Z`
4. 打 Tag：`git tag -a vX.Y.Z -m "Release vX.Y.Z"`
5. 推送：`git push && git push --tags`
6. 创建 GitHub Release
7. 通知团队

## CHANGELOG 格式

```markdown
# Changelog

## [v0.2.0] - 2026-07-XX

### Added
- 新增 XXX 功能

### Changed
- 修改 XXX 行为

### Fixed
- 修复 XXX 问题

### Deprecated
- XXX 已弃用，将在 v0.3.0 移除

### Security
- 修复 XXX 安全漏洞
```

## 发布后检查

- [ ] GitHub Release 页面可访问
- [ ] Tag 正确指向发布 commit
- [ ] 通知团队成员更新
- [ ] 更新项目状态文档（如需要）