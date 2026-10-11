# HBOS Knowledge UAT3 — 四模型与真实助手验收候选

状态：**UAT3_READY_FOR_OWNER / LOCAL_UAT / OWNER_NOT_RUN / COMPANY_ROLLOUT_PENDING**。此状态限于下面已实测的本机关键流程和固定客户端版本，不表示人工验收、合并、P1 切换或公司服务器上线。

本轮承接 UAT2 原型与数据。真实登录入口为 http://knowledge-r2.localhost:18350/hbos/login；PR #30 必须保持 Draft。独立服务为本地 0.5.0 提交及 wheel，无已批准远端，不声称服务已公开发布。

## 已实施与真实验证

- 服务端模型白名单只有 gpt-6-luna、deepseek-flash、gemini-3.8-flash、kimi-k3，默认 gpt-6-luna。员工只选别名，密钥和最终端点由独立服务统一管理。已有企业代理目录精确包含四别名，后三个各完成一次短合成问候；代理内部最终供应商和金额仍为 UNKNOWN。
- 确定性一般问题走 Service 通用分支，显示“未使用知识库”，空引用，不检索或带入企业片段和他人历史。企业问题走原受控检索、来源复核、最多一次选定模型生成，显示“已使用知识库”或“依据不足”。权限、原件、索引、模型错误保持独立错误，不自动换模型。
- A/B 两个普通账号实际验证问候、培养箱、未来奖金、缺失资料、明确未授权原件拒绝；F13 包装及自然追问有真实引用，版本待核状态没有被伪造。搜资料生成 0、rerank 0；历史恢复、来源、个人偏好、收藏新增/取消、反馈与维护回复均已实测。
- 真实 Chrome 390/768/1440 无溢出。Chrome 原生 compositionstart/update/end 和 isComposing 组合态期间提交 0；实际 A 状态响应在 B 登录后才送达，没有覆盖 B 偏好。物理操作系统输入法人工复核仍留给 Owner，不与 Chrome 组合态证据混淆。
- 网页 MCP 自检只做认证/工具发现，显示 SERVER_READY，不能充当客户端证明。实际 OpenClaw 2026.7.1-2、Hermes 0.20.6 的已安装原生 MCP 运行时分别完成一次 search_knowledge 与 get_evidence，服务器记录连接、挑战和检索/来源请求收据。客户端自己的 LLM 没有启动。收据证明绑定凭据/挑战调用，不声称应用本体密码学认证。
- 单个下载文件安装安全配置与不含凭据的 AGENTS 使用规则，备份并保留原设置，文件 0600，成功后删除安装文件；Token 未放入提示词、shell 参数、Git 或公共日志。验收使用隔离客户端目录，旧 Owner MCP 配置未改。
- Portal 退出不撤销独立 Token；本轮新建 Hermes Token 撤销后立即 401。旧个人连接未撤销。OpenClaw 的已实测连接保留供本机复核。
- 维护账号实际上传一个明确“不得发布”的合成文本，只对该单个文件启动受控 worker，完成解析、来源预览和数字/否定语/身份质量核对后停止；没有发布或修改 15 份共享资料。既有 333 条原生文档元数据完整保留，仅增加一个未发布合成文档。

## 调用治理与证据范围

真实发送由 Python 启动守卫在 requests/httpx 同步/异步发送前校验精确 URL、model ID、授权密钥 SHA、输出上限、重定向、重试及调用上下文。未知外部 HTTP、替代传输和未审计外部 TCP 默认拒绝。并发 2、每进程每分钟 30、异常熔断；每个授权请求的生成发送在持久文件锁中只领取一次。历史财务 UNKNOWN 不阻断正常业务，原账本记录保留且只追加。

元数据账本不保存 Key、完整问题、prompt、企业片段或回答正文。按 SEND_INTENT 计一次发送，OUTCOME 不重复计数；记录别名、实际请求 model ID、provider 标签、请求归属、时间、结果和可用用量，SHA 链经过校验。实际本轮回答发送：gpt-6-luna 12，另外三个各 1；原 qwen3.7-text-embedding 51（Portal 查询 40、MCP 查询 8、单个合成解析 3），1024 维与配置保持。rerank、未批准模型、额外 Claude/gpt-5.4/Cohere、付费子 Agent 和批量模型评测均 0。

守卫范围是已登记候选 Python 进程，不控制任意管理员进程、另行启动的客户端 LLM 或 Codex 宿主推理计费；宿主实际底层模型和计费归属未能核验，记 UNKNOWN。静态发送路径清单说明潜在能力，不冒充已发生调用。

## 两轮审查及仍待人工确认

第一轮修复通用阶段状态机、签名计划内嵌 schema、Frappe 出网依赖、向导状态区分与 Hermes Python 环境问题。第二轮补强跨 worker/重启持久生成领取、内部重定向拒绝、明确未授权原件先拒绝、旧历史模型缺失不补造，以及来源请求收据展示。原始失败和脚本选择器错误证据保留；没有付费自动重试或删失败场景凑 PASS。

395 项 Python、170 项 Vue、typecheck/frappe 静态构建通过。禁止真实网络 fixture 已写入领域与独立服务测试仓库。最终 commit、CI、wheel、静态构建、运行安装源码的锁以本机去秘密交付的 DELIVERY_LOCK 和 PR 检查为准，不把旧 CI 当成新 HEAD 通过。

Owner 的 20–30 分钟人工产品验收、物理 OS 输入法、客户端自己的 LLM 对话、生产 HTTPS/服务器上线未执行。为保留原 15 份资料，本轮未重做真实资料发布/下架/换版；此子项记 NOT_RUN，不以合成合同或上传/解析 PASS 替代。

依据本轮 Owner 明确要求，AGENTS.md、CLAUDE.md、PROJECT_STATUS.md、CURRENT_MILESTONE.md、AI_CONTEXT.md、前端实现规范和主题 token/typography 均保持原哈希。旧状态台账不更新；新轮次事实由本文、README/READING_GUIDE 增量入口和本机交付锁承载。此安排服从用户指令，不触发重复审批。
