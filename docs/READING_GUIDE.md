# Reading Guide

本指南用于限制 AI 在新乡海滨智能运营管理平台中的默认阅读范围，避免上下文膨胀和误读旧资料。

## 默认读取文件

每轮任务默认只读：

- `CLAUDE.md`
- `AGENTS.md`
- `docs/AI_CONTEXT.md`
- `docs/PROJECT_STATUS.md`
- `docs/CURRENT_MILESTONE.md`

每轮任务开始前必须说明读取了哪些文档。

## 禁止默认递归读取

禁止默认递归读取整个 `docs/`。

默认不读取以下目录：

- `docs/archive`
- `docs/research`
- `docs/legacy`

除非用户明确要求，否则不要浏览或搬运大量 Obsidian 长文。

## 条件读取规则

只有任务明确涉及当前里程碑时，才读取：

- `docs/plans/m0_engineering_bootstrap.md`

只有架构决策变更时，才读取：

- `docs/adr/`

## 当前里程碑提醒

M0 第一轮只做文档和目录骨架。

不得安装、运行或生成 Frappe/ERPNext；不得创建海滨 Frappe App；不得写 Docker Compose；不得开发业务代码。
