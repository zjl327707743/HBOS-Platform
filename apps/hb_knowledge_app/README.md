# HBOS Knowledge

HBOS 知识资料准入、权限策略、Gateway 适配与有限证据交付。

真实原文、切片、向量、Gateway 凭据与私有导入清单不存入本仓库。

## N1 联合装配要求

参考候选依赖独立 `hbos_knowledge_service` 0.3.11。联合交付包含其固定提交、源码与 wheel；仅安装本仓库的 App 或普通 Portal bundle 不足以启用知识服务。安装顺序为同一环境中的独立服务 wheel、被测知识 App，再装配现有 Portal。

生产参考服务必须设置 `HBOS_KNOWLEDGE_NATIVE_BUDGET_CONFIG`，指向经批准的原 native 配置及相邻原 ledger；缺失或无效绑定返回 `UNAVAILABLE` 并阻止检索。只读状态不结清费用或解锁旧 UNKNOWN。generation 启动脚本必须在 `uvicorn.run` 前用 `HBOS_RECOVERY_PROVIDER_BUDGET` 安装 `install_from_environment()` 物理发送计量器；恢复时验证原 ledger 存在，不初始化覆盖它。

固定 RAGFlow 的 API 导入 `api.apps` 后调用独立服务的 `install_ragflow_extension(config_path, expected_source_sha256=...)`。部署锁须给出被批准的原生模块摘要；该函数同时校验原生源码、路由配置和适配源码，重复调用也不跳过检查。原生路径只应用于指定模型，其他模型保留原实现。

无知识配置的 Portal 保持原应用入口契约。在线资料解析、检索、引用问答和发布需要额外的预算与资料质量门槛；代码或 bundle 构建成功不代表这些门槛通过。私有配置、资料和账本由 Owner 本地独立绑定，不打入代码或制品。
