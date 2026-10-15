# LIMS P4-F6-1 Shell 实现记录

状态：**P4-F6-1 SHELL IMPLEMENTATION IN PROGRESS / REAL INTEGRATION PENDING**
日期：2026-09-29
范围：`frontend/hbos-portal-web` 的 LIMS Shell、品牌、能力门控和稳定路由守卫

## 1. 本轮交付

- LIMS Shell 接入海滨公司标识与健康元集团标识；真实 Portal branding 返回的海滨标识优先，本地品牌资产作为无 logo 时的受控兜底。
- 全局页头在 LIMS 上下文显示“海滨实验室 / HBOS / LIMS”，集团标识位于页头右侧；移动端隐藏非关键集团标识以保持操作空间。
- LIMS Shell 展示经过清洗的 Portal 初始化错误，不向用户暴露 Frappe 方法名。
- `limsCapabilities` 改为“Provider 数据能力 × 已实现页面目标”的交集，Provider 有 `summary` / `tasks` 不再自动开放待设计页面。
- LIMS 路由增加 capability 元数据；真实模式直接访问尚未实现的业务路径时回到“页面待设计”状态，不跳转 8080。
- 管理菜单文案统一为中文；LIMS 页头和个人设置不再显示英文管理按钮。
- Shell 契约脚本新增品牌资产、页面目标门控和英文管理按钮检查。

## 2. 当前能力门控

| 数据模式 | 已实现页面目标 | Shell 可见入口 |
| --- | --- | --- |
| Mock | `dashboard` | 工作台与原型首页 |
| Frappe | 暂无业务页面目标 | 仅 LIMS Shell；业务入口保持待设计 |

Provider 的 `summary`、`tasks`、`search` 仍然可用作数据能力，但不会单独生成前台导航。Dashboard / Task Board 必须在各自 Vue 页面和真实集成检查完成后，再逐项加入页面目标集合。

## 3. 安全边界

- 本轮不修改 LIMS 业务流程、DocType、权限、SoD、电子签名或后端写 API。
- 本轮不开放 Result Entry、复核、批准、COA 发布、样品登记等写操作。
- 不复制原型中的业务数字到真实模式；Mock 数据仅在 Mock 模式使用。
- 不改变 `/hbos/lims/*` 同源前台路由，不恢复到 8080 跳转。

## 4. 验证

```text
npm run build
→ vue-tsc -b + vite build PASS

bash scripts/portal/lims_shell_contract.sh
→ LIMS SHELL CONTRACT PASS

Provider / LIMS contract tests
→ 150 passed, 1 skipped

git diff --check
→ PASS
```

真实 Frappe 集成仍未取得结果：本机没有运行 5178 / 8080，启动脚本因 `docker: command not found` 无法启动 Frappe。未写入业务数据，未伪造集成通过结果。

## 5. 下一步

在 Docker/Frappe 运行环境恢复后，先执行 Provider 集成检查；通过后进入 Dashboard V2 数据接入，再实现 Task Board V1。两个页面均需沿用本记录的双品牌、中文优先、页面目标能力门控和只读/写入边界。
