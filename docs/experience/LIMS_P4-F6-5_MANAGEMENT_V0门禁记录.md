# LIMS P4-F6-5 管理后台 V0 门禁记录

状态：**暂不开放（缺少明确 Provider 目标）**
日期：2026-09-30

## 结论

本阶段不在 5178 Portal 注册“管理后台”路由，也不把用户带到 Frappe Desk、8080 或其他后台地址。

当前 LIMS 尚未提供可供 Portal 消费的管理 Provider 方法、管理 API、只读投影或独立语义权限能力。现有管理维护服务包含写操作，不能被前台凭一个入口直接复用。因此 `management` 不进入 LIMS manifest capability，桌面侧栏和移动菜单继续隐藏管理入口。

## 已核对边界

- `get_manifest()` 未发布 `management` capability；
- Provider 没有 `management()` 适配方法；
- Portal capability 常量和分发器没有为管理后台创建数据目标；
- `LimsLayout` 未传入 `managementRoute`；
- Vue 路由没有 `/hbos/lims/management`、`/desk` 或 `:8080` 跳转；
- LIMS 现有业务页继续使用同源 `/hbos/lims/*`，结果录入等领域写操作仍由既有领域服务和后端权限负责。

## 重新开放条件

后续只有在以下内容完成并经 Owner 审查后，才可以重新评估 Management V0：

1. LIMS 领域 Owner 提供明确的 Provider 目标和稳定路径；
2. 明确只读/写入边界、语义权限、SoD、签署和审计契约；
3. 增加后端 API、Provider projection、manifest capability 与契约测试；
4. 完成中文优先的页面原型、权限态、错误态和视觉回归；
5. 通过 Owner Review 后再接入桌面侧栏和移动菜单。

在这些条件满足前，任何“管理后台”按钮都必须保持隐藏或进入安全的待设计页，不得推断为 Frappe Desk 地址。

## 验证

- `bash scripts/portal/lims_shell_contract.sh`：应保持 `LIMS SHELL CONTRACT PASS`；
- `PYTHONPATH=. python3 -m unittest tests.test_portal_management_gate tests.test_portal_provider_contract`：覆盖 manifest、Provider 和权限边界。
