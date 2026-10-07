# 知识候选连续执行 R1

当前状态：IN_PROGRESS。

K1C2 原归档 SHA-256：`839a32b40503ee255d15c82c2444e89c0ab95d35f038a2d83f80c1c08e12fce5`。1197 项内部校验、1090 项源码校验一致；原件不改写。固定 HBOS 产品基线为 `72e5b1728981b7ef102a2c9ee033ce0452c400e7`，main 为 `e8afea39d7af948191a637a1201007f42caa9b4b`；2026-10-08 开始时远端读取确认，#15/#29 均 Open Draft。

## 已实现与分层验证

- 原 K1C1/K1C2 会话证明、共享预算、引用持久化、内部认证与受限前端源码纳入知识候选分支。
- R-META-01：数据库列拥有 Binding 身份；JSON 必须逐项一致。校验 Space、canonical Document、Version 所属、current_version、Backend、物理 Dataset/Document、binding_ref 和 backend+Dataset+Document pair_key。写入禁止改写已有身份；读取冲突行失败关闭，无静默修复，其他有效 Binding 继续可用。新增必填字段只迁移全新登记的合成 Site；现存数据不能自行回填或迁移。
- R-UI-01：保留 label 与原生输入关联，以局部 sr-only 样式移出网格；加入键盘可见焦点；局部字号继承既有 52/30/20/16/14/12 tokens。全局母版不重画。
- 新 Python 3.12.13 环境：原核心重放 207 PASS，新增行/空间回归 34 PASS（合计 241）；这不是数据库或员工验收。候选/保留 P1 契约 56 PASS，前端 83 PASS，typecheck 和 frappe 数据模式构建 PASS。
- 授权空间列表只返回角色+动作+范围完整交集；安全标题、当前 canonical Document+Version 去重计数，不发送上游请求，不依赖模型准入。返回前再读取独立 authority；撤权或空间变化使旧列表失败关闭。前端实际调用 get_spaces，单选过滤随会话代际清空，不以空列表生成公共范围。
- 新数据库/跨连接元数据/空间 HTTP 首轮 14 PASS；真实 Chrome 首轮 10 项检查 PASS。最终同步复跑中。
- CI 补齐 hash 锁定的候选契约依赖与实际包入口；原 P1 断言保留在固定基线传输副本上，副本仅在 tests。新增候选拒绝旧 constructor、静态 policy 和缺服务调用的测试，不给生产运行时增加旧接口。安全字符串投影共用 HBOS 领域包实现，独立 service 引用同一实现，不复制分叉。

## 装配和剩余门禁

`knowledge_service` 是独立安装的通用包，候选制品必须与本分支代码一起固定交付。默认正式装配关闭；测试桥、测试客户端、HTTP 例外不代表通用生产 profile。原合成 lease 不续期；新运行独立创建有限 lease。

正式 IAM/真实员工授权、旧知识库恢复、真实引擎验证、模型准入与外发、员工 MCP 及 TLS/生产可用性结果按层另列。原资料/索引/配置/凭证不挂载、不复制；P1 和个人 MCP 不启停。源代码进入 Draft PR，所有合并和正式发布保留 Owner Gate。

主任务书未找到，完整时间/资源/任务依赖与独立服务 Git 远端尚未核对。本条不代表整批任务已完成，当前只固定已实际实现并分层验证的候选。
