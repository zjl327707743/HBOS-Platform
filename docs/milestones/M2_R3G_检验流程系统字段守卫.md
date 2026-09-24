# M2-R3G 检验流程系统字段守卫

## 状态

| 项 | 值 |
| --- | --- |
| 轮次 | M2-R3G（M2-R3/R6 检验流程的守卫补漏轮，不新增业务功能） |
| 分支 | `m2-r8` |
| 代码提交 | `c8dcfcb` |
| 部署 | 2026-09-24 已生效（重启 `backend` / `scheduler` / `queue-short` / `queue-long`；代码走 bind mount，无 DocType 变更故未执行迁移） |
| 状态 | DEPLOYED / 待 Owner 验收 |
| 主文档 | 本文件 |

## 1. 缺口

M2-R3/R6 交付的检验流程 5 个 DocType（`HBOS Sample` / `HBOS Sample Task` / `HBOS Test Result` / `HBOS COA` / `HBOS Specification`）按方案 8.6 保留 DocType 层 create/write，但**没有 R7/R8 那样的系统字段守卫**。后果：

非特权用户（如 LIMS Analyst）可经 `frappe.client.set_value` 或通用 `frappe.client.insert` 直写状态与签署字段，**完全绕过 `lims_service` 的状态机、SoD、锁协议与电子签名写入**——即伪造审批。

以 `HBOS Test Result` 为例，一次正规批准（`approve_result`）要做 6 件事：角色作用域授权、前置状态校验（仅「已复核」可批准）、OOS 守卫、稳定性同步校验、写电子签名三件套（`approver` / `approved_signature` / `approved_at`）、联动推进 Task 与 Sample 状态并记审计。直写则只改一个字段，产出一条**「已批准但没有审批人、没有签名、样品仍停在检验中」的畸形记录**，审计里只留一条普通「修改」。

成因已在代码层逐项确认：

- `HBOS Test Result` 的 `RESULT_LOCKED_FIELDS` 守住了结果值/限度/检验人，**但 `result_status` 不在其中**，控制器拦不住；
- DocPerm 对该 DocType 向 `LIMS Analyst` / `LIMS Manager` 开放 create/write（实测），故权限层也放行；
- 一个非特权用户即可完成，无需任何越权提权。

## 2. 为什么此前未被发现

R7/R8 两个板块**各自**落地了同款守卫（`HBOS Retention Sample._guard_system_fields`、`stability_guards.guard_system_fields`），R8 的 `stability_guards` 文档头甚至明确写着「表单直改、`frappe.client.set_value` 等低层写入一律拦截」——**机制早已存在且被验证过，只是没有回头补到更早的 M2-R3/R6 上**。本轮即按该既有机制补齐，不发明新做法。

## 3. 本轮改动

| 改动 | 说明 |
| --- | --- |
| `workflow_contract.py` | 新增 5 个系统字段集常量（命名带 `HBOS_` 前缀，避免与稳定性板块同名常量混淆） |
| `guards.py`（新增） | 中性入口，再导出 `stability_guards.guard_system_fields`；**实现保持唯一，未改动 R8 文件与其契约测试** |
| 5 个 DocType 控制器 | `validate()` 首行接线守卫；`HBOS Sample Task` 原为 `pass` 空控制器，本轮补上 |
| `lims_service.py` | 23 个保存点补 `doc.flags.allow_system_fields = True`（与 R8 `stability_service` 同一写法：服务层显式声明系统字段写入授权，守卫据此放行） |

## 4. 字段集口径（共 26 字段）

口径与 R8 `RESULT_SYSTEM_FIELDS` 一致：**状态 + 签署 + 版本链**。业务判定数据（`verdict` / `result_value` 等）**不在其中**——那类字段由既有 `RESULT_LOCKED_FIELDS` 在提交后锁定，属另一机制，不混。

| DocType | 状态 | 签署 / 归属 | 版本链 |
| --- | --- | --- | --- |
| `HBOS Test Result` | `result_status` | `submitted_signature` `submitted_at` `reviewer` `reviewed_signature` `reviewed_at` `approver` `approved_signature` `approved_at` | `superseded_by` `is_oos_candidate` |
| `HBOS COA` | `report_status` | `qa_reviewer` `qa_reviewed_at` `published_by` `published_at` `pdf_attachment` | — |
| `HBOS Sample Task` | `status` | `assignee` `assigned_by` `assigned_date` | `result` |
| `HBOS Sample` | `status` | — | `oos_locked` |
| `HBOS Specification` | `status` | `effective_date` | — |

## 5. 验证证据

### 5.1 离线门禁（宿主机）

```
python3 -m pytest tests   →  404 passed, 10 skipped
```

原 395 项 + 本轮新增 9 项契约。新增项中关键一条是「**受守卫 DocType 的每个保存点必须有服务放行标记**」的 AST 防回归扫描——将来任何人在 `lims_service` 新增保存点却漏加标记，离线即失败（漏加会在运行期被守卫拦下并中断业务流程）。

### 5.2 实机（容器内真实 Frappe 会话，非特权用户）

```
HBOS_FRAPPE_SMOKE=1 FRAPPE_SITE=frontend python -m pytest tests/test_lims_guards_runtime.py
→  9 passed
```

- **正向全链**（三种角色真实切换，全程非 Administrator）：建标准 → 生效 → 样品登记 → 生成任务 → 分配 → 开始检验 → 提交 → 复核 → 批准 → 生成 COA → QA 审核 → 发布 → 样品放行，**全通**；
- **负向 ×7**：直写 `HBOS Test Result.result_status` / `approver`、`HBOS Sample.status` / `oos_locked`、`HBOS Sample Task.status`、`HBOS COA.report_status`、`HBOS Specification.status`，以及 `frappe.client.insert` 直插「已批准」结果 —— **全部被拦**；
- **对照 ×1**：直写 `HBOS Sample.remarks`（非系统字段）**仍成功**，证明不是一刀切全锁。

### 5.3 部署后端到端（经 nginx → gunicorn，非特权用户 LIMS Manager）

以 `r7c-mgr@test.local`（LIMS Manager，无 System Manager）持 API 凭据经真实 HTTP 发起：

| 请求 | 结果 |
| --- | --- |
| `POST frappe.client.set_value` 把样品 `status` 改成「已拒绝」 | **HTTP 417** · `字段「status」为系统字段，只能通过业务操作（服务方法）修改，禁止直接编辑。` · `_exc_source: hb_lims_app` |
| `POST frappe.client.set_value` 把标准 `status` 改成「已废止」 | **HTTP 417** · 同上 |
| `POST frappe.client.set_value` 写 `remarks`（对照组） | **HTTP 200** · `modified_by: r7c-mgr@test.local` |

事后核对未篡改：样品仍为「已登记」、标准仍为「已生效」（对照组的 `remarks` 随探测样品一并删除）。

### 5.4 平台无回归

- 部署后 HTTP 冒烟 **17/18** 通过（`/hbos-lims` 全路由 + 两个 App logo 资源均 200；唯一 403 为未认证调用 `get_csrf_token`，属预期）；
- 重启仅涉及执行 LIMS Python 的服务，**未动 `frontend` / `websocket`**，避免 nginx SPA fallback 与容器内 assets 软链需重注入的连带风险；
- 本轮为后端改动，**未重建、未覆盖任何前端资产**。

### 5.5 验证痕迹清理

5 个 DocType 与 COA 附件 **0 残留**（实测查询）；临时 API 凭据已清空（`api_key` / `api_secret` 置 `null`）；探测样品及其关联数据已删除。审计日志为 append-only 设计，其留痕按设计保留、不清理。

## 6. 未纳入范围（相邻缺口，本轮口径为「窄」）

两项与本次同类的缺口**本轮未处理**，已在 `docs/PROJECT_STATUS.md` 登记：

1. **M2-R3 无删除拦截**：`HBOS Sample` / `Task` / `Test Result` / `COA` / `Specification` 均无 `on_trash` 守卫，删除只留审计不拦截（`audit_on_trash` 仅记不拦），受控检验记录可被真删。R7/R8 均已有删除拦截。
2. **M2-R3 无运行期一致性扫描**：R8 方案 8.6 有每日扫描检出 `frappe.db.set_value` / 裸 SQL 这类**绕过 `validate` 的低层直写**；M2-R3 没有对应手段（守卫本身覆盖不到这一类，这是设计已知边界）。

另需说明：`HBOS Retention Product`（R7）向 `LIMS Manager` 开放 create/write 但无守卫——其唯一受控字段 `is_active` 不构成状态机，未纳入本轮。前端 `api/lims.ts` 的 `createDoc` / `updateDoc` 两个通用转发口**本轮未改**：其可达面由 DocPerm 决定，跨 App 写入本就不可达（`Customer` / `Company` / `Holiday` 的写权限仅 `Sales*` / `HR*` / `System Manager`），加前缀断言收益有限。

## 7. 涉及文件

**改动**
- `apps/hb_lims_app/hb_lims_app/hbos_lims/workflow_contract.py`
- `apps/hb_lims_app/hb_lims_app/hbos_lims/lims_service.py`
- `apps/hb_lims_app/hb_lims_app/hbos_lims/doctype/hbos_sample/hbos_sample.py`
- `apps/hb_lims_app/hb_lims_app/hbos_lims/doctype/hbos_sample_task/hbos_sample_task.py`
- `apps/hb_lims_app/hb_lims_app/hbos_lims/doctype/hbos_test_result/hbos_test_result.py`
- `apps/hb_lims_app/hb_lims_app/hbos_lims/doctype/hbos_coa/hbos_coa.py`
- `apps/hb_lims_app/hb_lims_app/hbos_lims/doctype/hbos_specification/hbos_specification.py`

**新增**
- `apps/hb_lims_app/hb_lims_app/hbos_lims/guards.py`
- `apps/hb_lims_app/tests/test_lims_guards_contract.py`（离线契约 9 项）
- `apps/hb_lims_app/tests/test_lims_guards_runtime.py`（实机验证 9 项）

**未改动**：`stability_guards.py` 与全部 R8 契约测试（`stability_guards` 一行未动，其源码文本断言用例照常通过）。

## 8. 边界与不做事项

- 未新增 DocType、未改字段定义、未改权限矩阵、未改状态机表；
- 未改动 R7/R8 任何代码与测试；
- 未触碰前端（无 Vue 改动、无资产重建）；
- 未执行 `bench migrate`（无 schema 变更）；未执行 `docker compose down -v`、未删 volume、未重建 site；
- 未处理第 6 节两项相邻缺口。

## 9. Owner 验收重点

1. 检验流程日常操作（登记 → 任务 → 检验 → 复核 → 批准 → COA → 放行）**手感应与本轮之前完全一致**——守卫只拦「绕过服务方法的直写」，不拦正规流程；
2. 若曾有人直接改过 `HBOS Test Result` 等表单上的状态字段（`read_only` 之外的路径），现在会收到「字段为系统字段…」的提示——这是预期的收紧；
3. `LIMS Analyst` / `LIMS Manager` / `LIMS Reviewer` 的角色语义未变，仅系统字段的写入路径收归服务方法；
4. 若认可，下一步可决定是否启动第 6 节两项相邻缺口的独立轮次。
