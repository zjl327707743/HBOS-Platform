# PR #8 Inventory 深度审计

> 审计对象：PR #8 `feature/m3-warehouse-and-feishu-login`  
> 审计 HEAD：`d621f4817d3409329d094aeb8c8ddb88e446e563`  
> 结论：BLOCKED — 不能直接合入 main；应先形成 Inventory Clean Candidate。  
> 原则：保留 `hb_inventory_app` 与 OCR 的业务成果，但剥离非仓储域改动，并修复数据主权、权限和可重建性问题。

---

## 0. 增量复核（2026-09-24）

原审计 HEAD 为 `d621f481...`。当前 PR #8 HEAD 已推进到 `7872afbb...`，新增 2 个提交，仅涉及：

- `.github/workflows/hbos-quality-gate.yml`
- `scripts/setup_fonts.sh`
- M3-R6 方案文档
- 新成员环境手册

未发现 Inventory 业务主体代码变化，因此本审计其余 P0/P1 继续有效。

增量结论：

- **I8-P0-10 字体不可重建：部分关闭。** 已新增 Noto Serif SC 获取/sha256 校验/安装脚本，并在 CI 真实执行 fontconfig 验证。正式关闭条件调整为：Inventory Clean Candidate 的 Docker/clean-site smoke 中容器侧 `fc-list :lang=zh` 与 PDF 中文渲染均 PASS。
- **I8-P0-11 CI 不覆盖 Inventory/OCR：部分关闭。** 当前 CI 已新增 `hb_inventory_app` 契约测试、OCR validate/c2_extract 单测和字体可重建检查。但仍缺 Warehouse/Company 权限、File 授权、Batch item mismatch、OCR 内部认证、clean-site migrate、LIMS→Batch→Warehouse 联合集成测试，因此仍为 Merge Blocker。


## 1. 建议保留的主体

- `apps/hb_inventory_app/**`
- ERPNext Item / Warehouse / Batch / Stock Entry 复用路线
- 仓库工作台、查询报表、二维码、打印格式
- 入库拍照识别工作流
- `services/hbos_ocr/**` 的本地识别架构
- 出库门禁的“由质量放行结果驱动”原则

不建议推倒重写。

---

## 2. 必须从 Inventory 候选剥离

PR #8 同时修改 `hb_attendance_app`，包含：

- 飞书 OAuth 登录
- HRMS 汉化/改名
- Desktop / boot 行为

这些属于平台登录 / HR / Attendance 域，不属于 Inventory。

Inventory Clean Candidate 中不得夹带：
- `apps/hb_attendance_app/**` 的本 PR 变更
- 飞书 SSO 逻辑
- HRMS UI 汉化逻辑

这些成果可保留到单独的 Platform Auth / Attendance 治理轮次，但不能由 Inventory PR 携带进入平台。

---

## 3. P0 / Merge Blockers

### I8-P0-01：质量放行权威源冲突

当前 Inventory 在 Batch 上维护：

- `hbos_release_status`
- `hbos_release_date`
- `hbos_certificate_no`
- `hbos_certificate_file`

并由 Warehouse `release_gate.py` 直接信任这些字段决定是否允许出库。

问题：
- 字段当前不是 read_only，具有 Batch 写权限的人可直接人工修改。
- PR #10 LIMS 的 `release_sample()` 当前不会同步这些字段。
- 因而可能出现：
  - LIMS 已放行，但 Warehouse 仍认为待检；
  - 或 Batch 被人工改成已放行，而 LIMS 实际未放行。

G1/G2 决策：
- LIMS 是质量放行权威源。
- Batch 上的 release/certificate 字段保留，但定义为 **LIMS 放行投影**。
- Warehouse 只读这些字段，不拥有修改权。
- 字段应 read_only，并有服务器端防篡改守卫。
- 由正式 Quality Integration Service 写入。
- 必须增加 `hbos_lims_reference` / release source reference。
- 跨模块测试必须覆盖“待检不可出库 → LIMS 放行 → Batch 投影 → 可出库”。

### I8-P0-02：仓库 API 绕过 ERPNext Warehouse / Company 权限

`get_intake_context()` 的 `_leaf_warehouses()` 使用 `frappe.get_all("Warehouse")`，会列出所有叶子仓库，不应用用户权限。

`create_intake_draft()` 又：
- 按传入 Warehouse 推导 Company；
- 对 Stock Entry 设置 `ignore_permissions`；
- 允许 Stock User / Stock Manager / System Manager 调用。

结果：只要具有该页面角色，理论上可针对不属于自己的 Company / Warehouse 创建草稿，绕过 ERPNext 原生 user permission。

必须：
- Warehouse 列表使用权限感知查询或显式 `has_permission` / User Permission 过滤。
- 服务端再次验证调用者对目标 Warehouse / Company / Stock Entry 的权限。
- 不允许以 `ignore_permissions` 作为“页面可用”的常规替代。
- 如需专用操作权限，新增明确 HBOS Warehouse Operator role / service policy。

### I8-P0-03：File 读取 / 重挂缺少对象级权限

`_read_file(file_url)`：
- 只按 `file_url` 找 File；
- 读取内容前没有 `doc.check_permission("read")`；
- private File 也可被服务读取。

`_attach_photo(file_url, file_name)`：
- 可按任意 File docname / file_url 定位；
- 使用 `ignore_permissions` 修改 `attached_to_doctype/name`；
- 可把已有附件从其他业务对象“改挂”到 Stock Entry。

必须：
- 只接受当前会话刚上传且调用者有 read 权限的 File。
- 校验 File owner / permission / attached state。
- 已挂到其他单据的 File 禁止直接 re-parent；需要时复制为新 File。
- 限制 mime type 为受支持图片并校验大小。
- 不能只凭猜到的 private file_url / file name 读取或改挂。

### I8-P0-04：Stock User 可修改 Item 技术/质量主数据

`_fill_item_master_gaps()` 允许 Stock User 通过裸 SQL 补写：

- `Item.hbos_storage_condition`
- `Item.hbos_workshop`
- `Item.hbos_shelf_life_type`

并明确绕过 Item 权限。

其中“储存条件 / 效期类型”属于质量/技术主数据，Warehouse 不应拥有。

必须：
- Stock User 只可提交建议值。
- 正式写入至少要求 Item Manager / Stock Manager + 专门授权，或进入 Master Data Review。
- 避免裸 SQL 直接改正式主数据；使用受控 service + audit/version。
- 不能以 Comment 代替真正权限和审计。

### I8-P0-05：已存在 Batch 未校验所属 Item

`_ensure_batch(batch_no, item_code, ...)` 若 Batch 已存在，只读取扩展字段，没有先校验 `Batch.item == item_code`。

必须：
- 已存在 Batch 的 item 必须与当前 item_code 完全一致，否则立即拒绝。
- 增加回归测试，防止同一个 batch_no 被错误复用于另一个 Item。

### I8-P0-06：203 个核心货位 clean-site 不可重建

PR 描述中 M3-R1 已建立约 203 个货位 / 212 节点。

但 `hb_inventory_app.after_migrate` 只确保 8 个六车间 Warehouse；203 个货位依赖：

- `scripts/M3R1_建立货位主数据.py`
- `scripts/M3R1_货位清单.json`
- 人工 docker cp + bench execute

所以：
- 现有开发 site 能运行；
- 新 clone / 新 site 并不能通过 install + migrate 得到相同仓库结构。

必须明确二选一：
1. 若 203 货位是系统受控配置：放入版本化 seed / setup profile，并提供幂等显式初始化；
2. 若属于环境业务数据：从公开代码移出，放入受控私有配置，并提供导入流程。

不得继续处于“代码仓库里有 JSON，但安装流程不会执行”的中间状态。

### I8-P0-07：after_migrate 混入业务主数据

当前 `after_migrate` 自动创建 / 修改：
- UOM
- Warehouse
- Item Group
- Custom Field
- Workspace

应拆分：

Schema Migration：
- DocType
- Custom Field
- Workspace / Report / Print Format

Business Seed：
- Company-specific UOM
- Warehouse / Bin
- Item Group

Business Seed 必须显式、幂等、可审计，不应每次 bench migrate 自动治理企业主数据。

### I8-P0-08：公司与仓库根节点硬编码

当前：
- `COMPANY = "hb"`
- `WAREHOUSE_ROOT = "All Warehouses - HB"`

clean site / 多公司环境可能失败或写错公司。

必须：
- 由 HBOS Inventory Settings / Site Config / explicit setup profile 提供。
- 初始化前校验 Company、abbr、root warehouse。
- 不允许静默写到错误 Company。

### I8-P0-09：OCR 服务在 0.0.0.0 场景无认证

FastAPI：
- `/api/v1/recognize` 无认证；
- backend 可由请求指定；
- 默认 127.0.0.1 尚可，但 Docker 访问宿主机时文档允许改为 0.0.0.0。

一旦监听 0.0.0.0，网络内任何可达客户端都能调用识别服务。

必须：
- Frappe → OCR 使用内部 shared token / mTLS 中至少一种；
- 默认拒绝无认证 recognize；
- 网络层仍限制内网；
- health 可根据需要只暴露最小信息。

### I8-P0-10：字体依赖不可重建

PDF 中文依赖 `./runtime/fonts`，但 `runtime/` 被 gitignore，字体不进入仓库。

当前新 clone：
- Compose 可启动；
- 中文 PDF 仍可能静默丢字。

必须：
- 在自定义 HBOS 镜像中安装可再分发中文字体，或由部署步骤自动、可验证地安装。
- CI / smoke test 检查 `fc-list :lang=zh`。
- 不接受“新环境人工复制字体”作为长期生产方案。

### I8-P0-11：#8 的 CI 绿色不代表 Inventory 已测试

当前 GitHub Quality Gate 主要跑 Attendance 离线测试。
PR #8 的 Inventory / OCR 测试只在 PR 描述中声明本地执行，没有被 GitHub CI 作为 merge gate 强制执行。

必须新增：
- hb_inventory_app tests
- release_gate tests
- permission tests
- File authorization tests
- clean-site migrate test
- OCR Web/auth tests
- Inventory Docker smoke

---

## 4. 飞书 SSO：不进入 Inventory Clean Candidate

当前实现有独立安全问题，应另立 Platform Auth 治理：

### AUTH-P0-01 OAuth state 未验证
redirect 生成 state 中的随机 token 没有服务端保存/签名，callback 也不校验。
必须使用 session-bound / signed state，并一次性消费。

### AUTH-P0-02 redirect_to 未限制
state 中的 `redirect_to` 最终直接作为 Location。
必须只允许站内相对路径 / 明确 allowlist，禁止开放重定向。

### AUTH-P0-03 自动创建 Desk User
任何成功通过该飞书 App OAuth 的身份都可能被自动创建为 Frappe User，并赋 `Desk User`。
正式平台应先完成：
- 已有 User / Employee 映射；
- 或经审批的自动开通策略；
- 默认不因首次 OAuth 自动获得 Desk 权限。

以上能力可以保留，但不能以当前实现随 Inventory 进入平台。

---

## 5. P1 / Owner Decision

### I8-P1-01：扫码页对所有登录用户开放完整库存信息

`/hbos_bin` 当前只拦 Guest，任何登录用户可查看：
- Item / Batch
- 数量
- 效期
- 供应商 / 原厂批号
- 放行 / 合格证状态等

早期 Owner 已明确“不脱敏”。

平台化后需重新确认：
- 是否仍允许全公司所有登录用户；
- 或改为 Warehouse / Quality / Production 指定角色。

建议在企业总工作台上线前改成显式角色策略。

### I8-P1-02：PDF 自动生成失败只日志 + msgprint

入库提交成功后，货位卡/待检证生成失败不会回滚库存，这是合理的可用性取舍。

但正式环境建议增加：
- generation_status
- retry queue / 待办
- 可审计失败状态

不能只依赖瞬时 msgprint / Error Log 才知道受控文件没生成。

### I8-P1-03：内部 IP / 货位布局出现在 PUBLIC repo 文档

仓库文档含内网地址与真实货位结构。
不是代码执行漏洞，但属于公开仓库信息治理，应由 Owner 决定哪些企业基础设施 / 布局允许公开。

---

## 6. 设计上值得保留的部分

以下设计方向良好，应避免治理时误删：

- 不自动创建未知 Item。
- OCR 只生成草稿 Stock Entry，不直接入账。
- OCR 结果可人工复核。
- OCR 图片不长期落盘，日志不记录图片/批号/品名。
- PDF File 使用 `is_private=1`。
- Inventory API 已有集中 `_require_permission()` 思路。
- 前端多数动态字符串已通过 `escape_html` 处理。
- ERPNext 原生 Stock Entry / Batch / Warehouse / Item 继续作为账本主对象，不复制第二套库存余额。

---

## 7. Inventory Clean Candidate 目标树

建议后续建立：

`integration/pr8-inventory-clean`

仅携带：

```text
apps/hb_inventory_app/**
services/hbos_ocr/**
必要 inventory docs/tests
```

不直接携带：
- hb_attendance_app 的 Feishu SSO / HRMS UI 改动
- PR #8 自己的 docker-compose 最终版本（平台 integration 阶段重建统一 compose）
- 未治理的企业业务 seed

---

## 8. Inventory Definition of Done

只有全部满足才标记 READY_FOR_PLATFORM_INTEGRATION：

- [ ] Release fields 变为 LIMS 投影、不可人工篡改
- [ ] Warehouse/Company user permission PASS
- [ ] File object authorization PASS
- [ ] Stock User 不可直接治理 Item 质量主数据
- [ ] Existing Batch item mismatch test PASS
- [ ] 货位主数据初始化策略明确且 clean-site 可复现
- [ ] after_migrate 与 business seed 分离
- [ ] Company / root warehouse 可配置
- [ ] OCR 内部认证 PASS
- [ ] 中文字体部署可复现
- [ ] Inventory / OCR CI 成为强制门禁
- [ ] Feishu SSO 从 Inventory 候选剥离
- [ ] 与 LIMS 的待检→放行→出库联合测试 PASS

通过只表示可以进入 `integration/hbos-platform-v1`，不代表可直接 merge main。
