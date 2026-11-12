# Knowledge RC14 V2 员工体验候选

状态：REVIEWING / LOCAL_UAT / OWNER_NOT_RUN / ROLLOUT_PENDING。仅隔离候选；PR #30 保持 Draft。

本轮三个真实外部执行入口为 DeepSeek Harness 官方 CLI（deepseek-v4-1-flash）、Claude Desktop GUI（外层路由核验 deepseek-v4-1-flash）、ZCode 官方 CLI（GLM-5.3-Flash）。D 文件提供后端、权限和最终集成由 Codex Main 负责。ZCode 有真实局部代码成果，但最终运行超时且未交结果 JSON；不记为完整交付。Main 的审查修正单独归属。

本轮补齐 worker ack/handle_task/DB 终态闭环、早页正文与中英关键词保留、受控文件能力与短票据，以及四步助手连接和系统内帮助。下载独立于阅读权限，未配置即拒绝；候选只给精确测试账号、文档、版本和哈希的窄授权。Office 本机派生预览失败时保留文字阅读，chunk 页序不冒充原件页码。不新增 MCP 全文或下载工具。

真实验收分开记录：实现、部署、真实业务验收、Owner 人工验收。测试数、生成成功或 HTTP200 均不等于业务通过。旧24题和新增4个冻结问法在同一最终语料与配置下各执行一次，严格关键点、来源和数字条件判断；失败与修复复测分列。

普通队列按源哈希、部门和当前发布状态对账；初始60份只经单消费者及限时清单许可推进。解析完成不等于发布，净新增、技术换版、别名、共享例外分别计数。原始资料只读。

实际制品、源码、配置、资料快照、CI、账单未知项与回退锁，以 Owner 私有 RC14_EMPLOYEE_EXPERIENCE 交付记录为准。公司上线仍需单独批准，不合并、不切 P1、不开放员工、不改正式 HBOS。
