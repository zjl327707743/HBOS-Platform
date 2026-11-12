# M1-IAM0：统一身份与权限治理启动

日期：2026-10-01。授权：Owner 在权限设计讨论后回复“可以进行下一阶段”。这是并行治理启动，不关闭原账号/考勤/库存里程碑。

## Authority 与状态

参考仓库 `zjl327707743/HBOS-Platform`；上游 PR #21；冻结 source `5ec35ec8510303a1c36475e80d33d57c9255d5d6`，tree `93a877d456cc363b153763fba4ba85766b737448`。实际 Site/build 来源仍待本机核对；不把 PR 描述里 eee1c5e 的运行证据自动转移到新 HEAD。

IAM-0 文档/工具：REVIEWING。关键路径源码核对：REVIEWED_SELECTED_PATHS。源码工具合成单测：11/11 PASS。全仓扫描：NOT_RUN。实际 Site 盘点：NOT_RUN。权限隔离运行验收：NOT_RUN。业务权限实现/数据库变更/上线：NOT_STARTED。

## 本轮交付

[治理入口](../governance/iam/README.md)；代码证据、统一授权ADR、角色动作范围矩阵、本机只读盘点任务书、36项隔离测试规范，以及不连接数据库的 Python 源码盘点工具和11项合成测试。

本轮未修改 apps/、frontend/、hooks、角色/DocType、部署配置或现有工作流。只新增治理资料与离线工具；真实数据、凭据、身份名单和私有报告没有进入交付。

## 公共入口与协作

已定向读取 AGENTS.md、CLAUDE.md、docs/AI_CONTEXT.md、docs/PROJECT_STATUS.md、docs/CURRENT_MILESTONE.md、README.md、docs/READING_GUIDE.md、docs/milestones/M1_START_GATE.md（账号门禁相关段落）；现有账号工作流记录保持。PROJECT_STATUS 与 README 仅增加并行 IAM 入口；CURRENT_MILESTONE 的全局账号轮次不改，由本独立主记录登记 IAM-0，避免把账号收尾替换成权限已完成。IAM 阶段门禁由 IAM-2 文档管理，不回写既有账号测试结果。

只通过独立 Draft PR 交付，不合并、不直接推上游或main，不改Owner本地环境。已确认的P1固定环境与本人飞书登录成果保留。

## 下一项执行

本机 Agent 执行 [IAM-0 只读盘点任务书](../governance/iam/IAM-0_本机只读盘点任务书.md)，输出 LOCAL ONLY 的来源与权限差异。未拿到实际配置和矩阵批准前，不开始Grant迁移或给公司全员开放。
