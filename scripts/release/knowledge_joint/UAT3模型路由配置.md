# UAT3 私有模型边界

这是源码联合包的部署说明；服务器部署和 Owner 人工验收仍需另行执行。不得拿本说明新建知识库、迁移现有数据或切换 P1。

运行中的 BFF、独立服务、原生 RAGFlow API 和受控维护 worker 都必须在启动时安装 `knowledge_service.model_egress`。缺少配置或依赖时退出 78。初始化和回滚 profile 仅做数据库管理，不能执行任何模型任务。

私有目录由运维保管，权限 0700；密钥文件 0600，不进入源码包。四个回答别名固定为 gpt-6-luna、deepseek-flash、gemini-3.8-flash、kimi-k3。只有独立服务能拥有 GENERATION 路由。BFF 路由必须为空；原生 RAGFlow 只能包含原有 qwen3.7-text-embedding 的精确 HTTPS URL、model ID 和密钥 SHA-256。外部 rerank 不加入任何白名单。

新增配置文件：`model-registry.json`、`egress-bff.json`、`egress-service.json`、`egress-native.json`。前者按别名配置经过核验的 `model_id`、`base_url`、`provider`、`verified:true`、`data_flow_approved:true` 与 `key_file`/`key_path` 引用；它不需要存储新的员工 Key。未核验的别名不加入 models 对象，界面会显示暂不可用。

egress 文件的 `routes` 数组只允许经核验的条目：`alias`、`model_id`、`url`、`kind`（GENERATION 或 EMBEDDING）、`provider`、`verified:true`、生成路由的 `data_flow_approved:true`、`key_sha256`。另设 `internal_hosts`（明确的数据库、Redis、BFF、服务、RAGFlow 主机）、`caller` 与持久 `audit_path`。egress 和 registry 的 URL/model/key 引用必须相符。不要猜测模型映射或复制未批准的旧模型配置。

审计目录应授予实际服务 UID，0700；日志 0600，保留追加日志与历史账本。一次请求最多一次生成，无自动重试、无失败换模型。原生后台解析、原生 Chat、Vision、GraphRAG、RAPTOR 与其他 SDK 路径仍经过同一出网守卫，未批准生成会在发送前拒绝。索引保持原 embedding 配置和 1024 维，不重嵌入。

该守卫约束已启动的候选 Python 进程，不能声称控制宿主 Codex 的推理计费、任意管理员进程或另行启动的员工客户端模型。客户端验收只运行原生 MCP 工具运行时，不启动它们自己的 LLM。
