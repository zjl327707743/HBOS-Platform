# Current Milestone

## M0：工程启动与上下文治理

项目名称：新乡海滨智能运营管理平台。

## 当前轮次

M0 第一轮工程启动。

## 本轮范围

只创建项目工程骨架和 AI 上下文管理文档。

交付内容：

- 根目录协作入口文档
- `docs/` 下的 AI 上下文、项目状态、当前里程碑、阅读指南
- M0 工程启动计划
- 基础 ADR

## 本轮禁止事项

- 不安装、不运行、不生成 Frappe/ERPNext
- 不创建 `hb_core_app`、`hb_attendance_app`、`hb_feishu_app`
- 不写 Docker Compose
- 不做业务代码
- 不开发考勤业务
- 不接飞书
- 不做前端驾驶舱
- 不浏览或搬运大量 Obsidian 长文

## 验收标准

- 指定文档全部存在
- 文档明确项目名称、架构叫法、长期架构和主技术栈
- AI 上下文读取规则写入 `CLAUDE.md`、`AGENTS.md`、`docs/AI_CONTEXT.md`、`docs/READING_GUIDE.md`
- M0 第一轮边界和禁止事项清楚可见
- 未出现 Frappe 安装、App 创建、Docker Compose 或业务代码

## 下一轮预告

M0-R2 再规划 Frappe/Docker 环境，不在本轮实现。
