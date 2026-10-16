# HBOS Knowledge

HBOS 知识资料准入、权限策略、Gateway 适配与有限证据交付。

真实原文、切片、向量、Gateway 凭据与私有导入清单不存入本仓库。

## 当前 UAT5 联合候选

知识页面继续使用已批准的 Portal 结构。独立服务源码候选为 `hbos_knowledge_service` 0.6.8；实际安装提交、wheel、镜像、静态资源和业务统计以 Owner 本机联合锁为准。本仓库不包含该独立服务源码，普通 Portal bundle 不能单独启用真实知识链路。

原生 Frappe Session 负责员工身份；本 App 的 `hb_knowledge/api.py` 负责员工 API、授权与发布，`mcp_api.py` 和 `connections.py` 负责本人连接认证及四工具分发。独立服务的 `knowledge_service.hbos_gateway.mcp_runtime:app` 承接 `/mcp`，由 `mcp_host.py` 回调 Frappe dispatch，复用 list spaces、search、resolve evidence 和 ask，没有第三套知识 MCP。前端的 `services/knowledgeInstaller.ts` 只写私有客户端配置及无凭据规则，不改变用户自己的模型选择。

本轮普通已授权工作采用 `AUDIT_ONLY` 计量，旧费用 `UNKNOWN` 不作为新的统一硬阻塞，也不重设历史预算或账本。出站仍必须安装原物理发送审计及服务器模型白名单；真实提供方权限、限流、错误、身份和资料共享门禁继续有效。员工默认 `gpt-6-luna`，Embedding 保持原千问及1024维，rerank默认关闭；真实测试只使用获准的 DeepSeek-Flash。

导入可分为“只上传原件”和随后显式解析：只上传不会入解析队列或调用模型。新、已核验的原生文字 PDF 可保留原 PDF 文件供管理后台查看，并使用精确冻结的 newline 配置；原文哈希、抽取证明与确切 Dataset/Document 在线核对。旧已索引项不会因新配置自动重传、重解析或换向量。解析完成不等于质量通过或员工发布，OCR、表格语境、敏感项与版本冲突逐文件留有处理结果。员工原件下载保持关闭，管理后台读取不扩大员工权限。

RAGFlow固定版本、API/UI及存储位置以同实例本机核验为准。全目录入库与自然回答修复分别验收，不能用上传数、HTTP200或CI替代引用支持质量。当前仍为 `UAT5_PARTIAL`；PR #30保持Draft、不合并、不切P1。

## 历史 N1 联合装配要求（保留原记录）

以下0.3.11及费用阻塞说明记录N1时点，不能覆盖上面的UAT5 `AUDIT_ONLY` 边界。

参考候选依赖独立 `hbos_knowledge_service` 0.3.11。联合交付包含其固定提交、源码与 wheel；仅安装本仓库的 App 或普通 Portal bundle 不足以启用知识服务。安装顺序为同一环境中的独立服务 wheel、被测知识 App，再装配现有 Portal。

生产参考服务必须设置 `HBOS_KNOWLEDGE_NATIVE_BUDGET_CONFIG`，指向经批准的原 native 配置及相邻原 ledger；缺失或无效绑定返回 `UNAVAILABLE` 并阻止检索。只读状态不结清费用或解锁旧 UNKNOWN。generation 启动脚本必须在 `uvicorn.run` 前用 `HBOS_RECOVERY_PROVIDER_BUDGET` 安装 `install_from_environment()` 物理发送计量器；恢复时验证原 ledger 存在，不初始化覆盖它。

固定 RAGFlow 的 API 导入 `api.apps` 后调用独立服务的 `install_ragflow_extension(config_path, expected_source_sha256=...)`。部署锁须给出被批准的原生模块摘要；该函数同时校验原生源码、路由配置和适配源码，重复调用也不跳过检查。原生路径只应用于指定模型，其他模型保留原实现。

无知识配置的 Portal 保持原应用入口契约。在线资料解析、检索、引用问答和发布需要额外的预算与资料质量门槛；代码或 bundle 构建成功不代表这些门槛通过。私有配置、资料和账本由 Owner 本地独立绑定，不打入代码或制品。
