# TK-ENTRY-COMPAT-01：Twin 与现有知识模块

状态：PENDING_KNOWLEDGE_CONTRACT。Owner 已授权将本单交现有知识库窗口确认；尚未确认的字段不发送。

首个交互候选沿用 `/hbos/knowledge`，仅发送 `equipment_id`、`q`、`auto=1`。`q` 不改为 question。只有服务端已核、知识关联已允许且设备/模型 SHA/映射版本与当前选择完全一致时，才发送既有 `asset_id`/`component_id`。候选组及未知节点退回设备级查询；双机场景先明确当前设备。

请知识窗口确认：

1. 上述 L1 旧入口在当前知识候选中保持兼容；源码兼容、导航成功和真实检索分别记录。
2. L2 可选上下文未来采用何种传输形式与字段名，尤其 `step_id` 与 `process_step_id`，以及 scene/model/mapping/process revisions。未定之前 Twin 不发送这些新增字段。
3. 现有知识模块是否已有可复用的授权嵌入组件/服务，及错误、销毁和取消契约；未提供时保留扩展点，不复制问答、存储、证据或来源代理。
4. L3 返回定位仅在以后双方批准时实现，必须由用户点击，重核权限、成员、版本与业务映射；拒绝跨设备、未知或旧目标及任意脚本/URL。

本协调单仅请求协议答复，不授权修改共享文件或操作任何 P1/知识运行环境。若需修改 KnowledgeView、共享 contracts/API，需列具体文件、兼容性、唯一编辑者和回归，再由 Owner 批准。Twin 独立工作不等待新增协议。

当前知识实际检索：NOT_RUN。Twin 模型权限不能提升资料权限。不会让浏览器直连 Gateway/RAGFlow/MCP，不提供原文下载。

2026-10-09 完整 V1 续行：Twin 已保留 L1 的设备选择、既有参数与未核对象降级，并对导航失败提供局部提示。L2/L3 仍为 PENDING_KNOWLEDGE_CONTRACT，等待原知识窗口确认；本轮没有新增跨窗口消息、共同接口或真实检索操作。
