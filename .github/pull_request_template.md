## 任务目标

<!-- 这个 PR 要达成什么？关联的 Issue 或任务编号 -->

## 变更范围

<!-- 改了什么文件、为什么改 -->

## 未做范围

<!-- 明确说明哪些不在本次变更中，避免审查范围蔓延 -->

## 测试与验证

<!-- 测试命令和测试结果 -->

- [ ] 本地测试通过：`docker compose exec backend python3 -m unittest discover -s apps/hb_attendance_app/tests -v`
- [ ] 测试结果：

```
<!-- 粘贴测试输出 -->
```

## 数据库或迁移影响

- [ ] 无数据库影响
- [ ] 有 DocType 变更（需 migrate）
- [ ] 有 Patch（需 migrate）
- [ ] 说明：

## 配置资产影响

- [ ] 无影响
- [ ] 修改了 `docker-compose.yml`
- [ ] 修改了 `.env.example`
- [ ] 修改了 CI 配置
- [ ] 说明：

## 安全与敏感数据检查

- [ ] 无 `.env` 或密钥文件
- [ ] 无数据库 dump 或备份
- [ ] 无真实 Excel 或 CSV 数据
- [ ] 无真实员工或考勤数据
- [ ] 无日志或证书文件

## Docker 影响

- [ ] 无影响
- [ ] 需要重建容器
- [ ] 需要重新拉取镜像
- [ ] 说明：

## 文档更新

- [ ] 无需更新文档
- [ ] 已同步更新：
  - [ ] `docs/team/`
  - [ ] `README.md`
  - [ ] `CLAUDE.md` / `AGENTS.md`

## 审查人关注点

<!-- 希望 reviewer 重点审查的部分 -->

## 是否涉及 Owner 授权的新阶段

- [ ] 否
- [ ] 是，说明：