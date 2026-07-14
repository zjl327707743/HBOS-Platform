# 数据库 Migration 检查清单

## 创建 Migration 前

- [ ] 确认 Migration 是必要的（不是简单的配置变更）
- [ ] 确认是数据迁移还是 Schema 迁移
- [ ] 确认迁移范围（只影响必要的表）
- [ ] 在本地开发环境先测试
- [ ] 备份当前数据库

## Migration 编写

- [ ] Patch 文件放在 `hb_attendance_app/patches/` 目录
- [ ] 文件名使用有意义的名称
- [ ] 在 `patches.txt` 中注册
- [ ] Patch 文件包含 `execute` 函数
- [ ] 使用 `frappe.db.sql()` 或 Frappe ORM
- [ ] 添加错误处理
- [ ] 添加日志输出（`frappe.logger()`）

## Migration 测试

- [ ] 在本地执行 `bench --site frontend migrate`
- [ ] 确认 Migration 成功执行
- [ ] 确认数据正确
- [ ] 测试回滚脚本（如果编写了）
- [ ] 重复执行 Migration 不会出错（幂等性）

## Migration 提交前

- [ ] patches.txt 已更新
- [ ] 没有提交真实数据
- [ ] 没有硬编码密码
- [ ] 迁移脚本有回滚说明

## Migration 部署

- [ ] 通知所有团队成员
- [ ] 在低峰期执行
- [ ] 备份数据库
- [ ] 执行 `bench --site frontend migrate`
- [ ] 验证迁移结果
- [ ] 记录迁移执行时间

## 回滚

如果 Migration 失败：

1. 停止所有写操作
2. 恢复数据库备份
3. 通知团队
4. 分析失败原因
5. 修复 Migration
6. 重新执行

## Migration 顺序规则

- 新 Migration 必须添加到 `patches.txt` 末尾
- 不要修改已执行的 Migration 文件
- 如果需要修改，创建新的 Migration
- 多人同时开发时，通过 PR 合并顺序确定 Migration 顺序