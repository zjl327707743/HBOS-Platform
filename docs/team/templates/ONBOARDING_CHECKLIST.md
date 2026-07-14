# 新成员入职检查清单

## Owner 侧（入职前）

- [ ] 在 GitHub 仓库 Settings → Collaborators 中添加新成员
- [ ] 授予适当的权限（Developer 角色）
- [ ] 通过安全渠道发送 `.env` 文件
- [ ] 确认新成员电脑满足最低要求：
  - [ ] macOS / Windows WSL2 / Linux
  - [ ] 至少 16GB 内存
  - [ ] 至少 50GB 可用磁盘空间
  - [ ] 管理员权限（安装 Docker Desktop）
- [ ] 发送团队文档链接（`docs/team/README.md`）
- [ ] 安排 30 分钟的环境搭建协助时间

## 新成员（第一天）

### 环境搭建

- [ ] 安装 Docker Desktop
- [ ] 安装 Git
- [ ] 安装 VS Code
- [ ] Clone 仓库
- [ ] 获取并配置 `.env`
- [ ] 获取 HRMS 源码
- [ ] 拉取 Docker 镜像
- [ ] 启动 Docker 环境
- [ ] 验证 Desk 可访问
- [ ] 验证 HR Workspace 可访问
- [ ] 运行测试确认环境正常

### 文档阅读

- [ ] 阅读 `docs/team/README.md`（索引）
- [ ] 阅读 `docs/team/01_项目真实结构与代码归属审计.md`
- [ ] 阅读 `docs/team/12_常用Git与Docker命令解释.md`
- [ ] 阅读 `docs/team/03_Git与GitHub多人协作规范.md`
- [ ] 阅读 `docs/team/07_新成员入职与本地环境上手手册.md`
- [ ] 浏览 Frappe Desk 界面

### 第一次练习

- [ ] 创建个人 feature 分支
- [ ] 做一个小修改（如修改文档）
- [ ] 提交并推送
- [ ] 创建第一个 PR
- [ ] 等待审查
- [ ] 合并

## 新成员（第一周）

- [ ] 阅读 `docs/team/05_开源代码二次开发与升级规范.md`
- [ ] 阅读 `docs/team/10_团队日常开发SOP.md`
- [ ] 阅读 `docs/team/09_安全密钥与敏感数据规范.md`
- [ ] 了解 Frappe DocType 和自定义 App 开发流程
- [ ] 完成第一个小任务并提交 PR
- [ ] 参加团队周会

## 新成员（第一个月）

- [ ] 阅读 `docs/team/06_Frappe自定义内容与数据库迁移规范.md`
- [ ] 阅读 `docs/team/08_版本发布回滚备份与环境管理.md`
- [ ] 了解项目架构和 ADR 决策记录
- [ ] 独立完成一个完整的功能开发周期
- [ ] 参与代码审查