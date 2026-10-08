# HBOS Knowledge R2 真实部门知识候选

状态：REVIEWING / NOT_RELEASED。延续 Draft PR #30，部门是分类；本轮批准的内部资料由具备入口资格的启用用户共享阅读。复杂部门 ACL 和员工 MCP 留在后续范围。

## 已实现行为

- 独立真实参考装配沿用既有 HBOS 决策、签名内部 HTTP 与唯一 knowledge_service 检索核心，没有另造网关。
- 固定 RAGFlow v0.27.0 源码与旧存储，在一致性备份、遗留队列无待执行任务核验后启动 API/worker；未初始化旧库、升级或清队列。
- 按部门建私有 Dataset；冻结批次哈希，DOC 本地转换并比对，上传、三字段 metadata 回读、解析完成和 chunks 分开记录；支持中断恢复、同批幂等和精确部门 ID 映射。
- HBOS canonical Document、immutable Version 与 Backend Binding 精确对应真实 Dataset/Document。每次消费保持版本、下架、解析和原生登录状态再核验。
- 页面提供部门筛选、资料目录、真实检索、必要摘录与来源面板；不提供原件下载。COMPANY_CONTROLLED 来源不改贴普通资料，内部收录状态与受控生效审批明确区分。
- 历史和收藏按原生用户持久保存逻辑引用，重新打开必须通过当前资料和后端 metadata 核验，再执行新检索。不会把历史摘要当现行资料。
- 反馈保存待处理记录，维护人通过原生 System Manager 权限列出并更新处理状态。维护接口不放宽普通 Portal 的特权账号排除规则。
- 获准问答使用独立配置的 gpt-6-luna，只发送当前已核验摘录；无依据不调用模型。模型之后再核验来源，关闭工具、个人 Chat、跨库隐式检索与模型记忆回退。参考回答不替代现行规程或质量决策。

## 验证与交付边界

原核心、领域、前端及新增服务安全测试分别记录，不累加重叠范围。真实业务层覆盖两名候选原生阅读账号范围相同、Guest/无资格/停用/CSRF、三类检索、空结果、来源、跨用户记录、收藏、维护反馈、下架/版本/backend metadata 篡改、上游故障恢复、真实问答和追问。

CI 工作流修复已在同一功能分支提交，并获两条 PR workflow 成功。最终 head、wheel、运行镜像和页面资产哈希由 Owner 本地 SOURCE_RUNTIME_LOCK 记录。普通 Portal bundle 没有独立知识服务，不能把它当作完整联合部署包。独立服务未提供远端，保留本地提交、wheel 和去资料/去凭据源码归档；不能声称服务远端 PR 已存在。

本轮只运行 Owner 本机独立候选。未合并 PR，未发布 release，未切换现行 P1；真实资料、原件、manifest、运行 DB、模型 Key、账号或截图不提交 Git。旧 synthetic lease 不延长。生产 TLS、公司服务器部署与真人员工身份接入仍需后续范围，本轮 QA 账号不冒充真实员工验收。

## API 与复测

员工入口沿用 `hb_knowledge_app.hb_knowledge.api`：`get_status/get_spaces/get_documents/search/resolve_evidence/ask/get_activity/save_bookmark/open_saved/remove_saved/submit_feedback`。反馈维护使用 `get_feedback_queue/review_feedback`，由原生 System Manager 约束。

源码回归执行 `scripts/knowledge/run_domain_contracts.py` 和 Portal 的 `npm test`、真实 Frappe 模式构建。独立 service 测试必须在匹配 HBOS 领域包已安装的联合环境运行；Owner 本机真实验收脚本包含可逆故障测试，只允许操作已登记 R2 候选，不能移植到现行 P1 执行。

最终定位核对：RAGFlow v0.27 Word chunks 的 positions 为片段序号，不能作为原件页码。服务 0.3.1 将本参考语料未经核验的页码保持 null，界面显示未标注；必要摘录和精确文档/版本绑定继续有效。新增专项回归并重新执行真实闭环。
