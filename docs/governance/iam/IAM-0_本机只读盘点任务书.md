# IAM-0 本机只读盘点任务书

## 可直接交给本机 Agent 的任务

你执行 HBOS 统一身份与权限治理 IAM-0，仅做源码及实际 Site 只读盘点。仓库 `zjl327707743/HBOS-Platform`；参考冻结源码 `5ec35ec8510303a1c36475e80d33d57c9255d5d6`。上游账号分支为 `codex/portal-unified-account-release`，PR #21；本任务不继续修改该分支。

先读 CLAUDE.md、AGENTS.md、docs/AI_CONTEXT.md、docs/PROJECT_STATUS.md、docs/CURRENT_MILESTONE.md，再定向读本目录与 M1_IAM0 主记录。已选 P1 为固定本地使用环境：沿用现有启动配置和 Compose 元数据只读反查实际 Site、数据库、来源目录、制品 source_commit/build_id，不重新让 Owner 选择已确认的环境。P1 不等于公司服务器生产，不能作为临时测试库。发现启动配置、HTTP制品标识、Site、DB 对应不一致时，停止相关连接，交付冲突清单；不猜测、不切换其他候选库。

## 强制边界

不得 reset/clean/stash/checkout 现有工作区，不改挂载或 release_root，不拉起/重建/停止服务，不安装依赖，不新建 App/DocType，不 migrate，不运行补丁，不建账号、不授予/撤销角色、不改 Employee/部门，不换绑或交接身份，不改密码/MFA/Secret，不触发登录、验证码、同步、排班、导出或业务动作，不刷新/清空缓存会话，不复制数据库，不删卷。

已有本人飞书登录成功和具名交接机制必须保留，不重复要求配置。盘点不是登录验证，不用 Administrator 代替真实权限测试，不伪造合成身份为真人。真实跨账号/越权/写操作测试不在原 Site 做。

## A. 来源与工具

只读记录 HEAD、分支、工作区脏/净状态、六 App 实际安装/源码版本、Frappe/ERPNext/HRMS 精确版本与制品映射。源码脏时不处理它；仅标 SOURCE_DIRTY，明确已提交文件和运行挂载的差异，不把脏源码当远端 Authority。

在现有源码副本运行本 PR 的 `iam_source_inventory.py`，不用把工具安装进 Frappe App。命令中的 SHA 必须是刚核对的实际完整 SHA；工具不会替你核验 Git。

```bash
python3 -B -m unittest discover -s scripts/governance/tests -v
python3 -B scripts/governance/iam_source_inventory.py \
  --repo "$VERIFIED_SOURCE_ROOT" --source-commit "$VERIFIED_SOURCE_SHA"
```

上述变量必须由实际配置与只读 Git 查询获得；不要照抄某个历史本地路径。输出重定向到仓库以外的私有目录。工具只扫描固定的六 App Python 根目录，排除 tests/fixtures/test_*，不跟随已发现的符号链接，不导入执行源码，不连接 Site。缺根目录、语法错误、文件上限等均标 PARTIAL；未发现 marker 不等于安全。只有人工补全委托函数、hooks、DocType、报表、前端和直接 DB 路径后才能讨论覆盖。

## B. 实际 Site 最小权限盘点

先建立独立只读数据库连接/只读事务；优先使用已有只读凭证，不新建数据库用户或修改 GRANT。仅用现有安全渠道读取连接所需凭据到进程内存，不输出 site_config 全文、不 show-config、不把密码放 argv/聊天/日志。不能建立或验证只读约束就停止数据库盘点，不降级为“先查询后 rollback 就安全”。不通过 Web 登录采集，以免额外创建会话/触发业务 hooks。

MariaDB 参考事务形式是 `START TRANSACTION READ ONLY`，结束 `ROLLBACK`；这是事务模式不是授权审计。实际 DB/driver/事务状态须先核对；只允许固定 SELECT/元数据读取，不执行写操作来测试只读模式，不执行 DDL/临时表/存储过程/OUTFILE、不调用业务函数，不做锁表。不存在的表/列记 SCHEMA_GAP，不自动迁移。设置现有客户端的读取超时和结果上限，分页完整性不足记 PARTIAL；不无限制 SELECT *。

[MariaDB START TRANSACTION 官方说明](https://mariadb.com/docs/server/reference/sql-statements/transactions/start-transaction)。数据库/OS 正常访问日志可能记录读取；要求是业务/配置不变，不宣称主机完全零写入。

按 schema 发现后白名单取字段，分组记录以下项目：

| 类别 | 只读内容 | 限制 |
| --- | --- | --- |
| User | 启用、用户类型、角色模板、角色授予关联 | 不读 password/new_password/api_secret/重置票据；身份仅私有映射 |
| Role / Has Role / Role Profile | desk_access、disabled及实际存在的标记、角色成员关系 | 报告角色定义与实际授予，勿仅看 profile |
| DocPerm / Custom DocPerm | DocType、role、permlevel、读写提交取消/导入导出打印分享等标志 | 区分原生与自定义覆盖；不是两表机械相加 |
| User Permission | 允许类型、允许值、适用DocType、下级范围 | 真实允许值私有化；空范围语义单列 |
| System Settings | apply_strict_user_permissions 等明确权限设置（存在时） | 不导出全部 Singles/site_config |
| DocShare | 用户/Everyone、目标类型、读写分享标志 | 文档名用稳定代号；不得导出业务正文 |
| Employee / Department / Company | User关联、状态、组织树、主次任职可用性 | 不取姓名、手机、工号、住址、薪资、请假理由 |
| Warehouse / LIMS归属字段 | 结构/字段定义、可用的组织归属及缺失计数 | 不导出库存/检验结果；归属缺失只统计 |
| 外部身份/账号安全/交接 | DocType结构、启用绑定/完整性计数、已完结管理交接计数 | 不读open_id/identity_key/验证码/token/会话明文；不重跑账号流程 |
| 知识/孪生策略 | 已批准配置的能力种类、主体/范围数量、default_internal启用、revision | 不导出原始JSON/文档ID/设备私有清单、路径、网关凭证或资料 |
| File / Report / Page | 权限相关元数据、public/private和未归属计数 | 不取文件内容/原件路径、不生成附件/报表 |

如需角色—用户—范围关联分析，使用本机随机代号 U001/D001/W001 等；真实映射只在 Git 外受保护文件，权限 0600，不提交。跨表同一对象使用同一代号；不要用可枚举邮箱/工号的无盐 SHA 冒充匿名化。

## C. 输出（全部 LOCAL ONLY）

生成 1）环境/版本一致性表，2）角色与岗位候选映射，3）User—Role—范围关联及冲突摘要，4）Custom DocPerm/Share/空范围例外，5）需复核 API/SQL/ignore_permissions 路径表，6）IAM-1 实现分工与可验证验收计划。公开只回报状态、总计和缺口编号，不回传真实身份及业务明细。

每项检查用 PASS/FAIL/NOT_RUN/PARTIAL/SCHEMA_GAP；PASS 指明是读取完整、配置符合约定，还是合成行为测试，不混淆。schema/权限表盘点不能证明实际 API 隔离。记录开始/结束时间、工具版本、源SHA、只读保护方式与查询范围；凭据和可识别人信息不上报。

## 停止点和下一授权

完成只读盘点后停止，不自动建 Grant/改权限/迁移/部署。输出差异与建议，待角色矩阵和现有权限迁移映射评审后才进入 IAM-2 的隔离实现。可完成部分先交付，不因某个 Site 连接失败放弃源码盘点，也不得为了拿到 PASS 放宽范围或改动原环境。
