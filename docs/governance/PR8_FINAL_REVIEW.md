# PR #8 / Inventory 最终验收

> 候选：PR #12 `integration/pr8-inventory-clean`
> 结论：**READY_FOR_PLATFORM_INTEGRATION**
> 说明：本结论只允许进入 `integration/hbos-platform-v1`，不代表直接合入 `main`。

## Gate 结果

| Gate | 结果 | 主要证据 |
| --- | --- | --- |
| Inventory 域边界 | PASS | 已剥离 #8 中 Feishu SSO / HRMS UI；候选仅保留 Inventory/OCR 与必要测试文档 |
| 质量放行主权 | PASS | Batch 放行字段只读；`quality_projection.project_release()` 为服务器端 LIMS 投影契约 |
| Warehouse/Company 权限 | PASS | 权限感知 Warehouse 查询；目标 Warehouse/Company/Stock Entry 服务端复核 |
| File 授权 | PASS | File read permission + owner + unattached + MIME/大小校验；归档复制 private File |
| Item 主数据 | PASS | Stock User 不再直接治理技术/质量主数据；需受权角色 |
| Batch/Item 一致性 | PASS | 已存在 Batch 必须匹配当前 Item |
| Schema vs Business Seed | PASS | `after_migrate` 仅 schema/UI；企业 UOM/Warehouse/Item Group 使用显式私有 profile |
| 站点业务布局 | PASS | 公开候选不再携带生产 203 货位 seed；布局走私有、幂等 business profile |
| OCR 内部认证 | PASS | recognize 强制 Bearer Token；空 token / 错 token 拒绝 |
| 字体可重建 | PASS | Noto Serif SC 下载 + sha256 + fontconfig 验证路径已建立 |
| CI / clean-site | PASS | Inventory/OCR 单测 + isolated clean-site install + 双 migrate + 关键字段检查 PASS |
| 平台公共文件边界 | PASS | 根 .env / Quality Gate / .gitignore / docker-compose 恢复平台基线；Inventory smoke 使用专属 CI compose |

## 实际 CI 结果

最终验收：
- PR #12：`mergeable=true`
- HBOS Inventory Integration Gate：run #15，PASS

Gate 实际确认：
- Inventory / OCR governance tests PASS
- Frappe / ERPNext / HRMS / Attendance / Inventory 可在隔离环境完成建站安装
- `bench migrate` 连续执行两次
- Item / Batch / Stock Entry 关键 HBOS 字段存在
- OCR 内部认证契约在测试中固定

## 架构结果

- ERPNext Item / Warehouse / Batch / Stock Entry 继续作为库存账本对象。
- `hb_inventory_app` 管仓储执行、查询、打印、扫码、入库辅助，不复制第二套库存账。
- 质量放行决定权不属于 Warehouse；Batch 字段是未来 LIMS 的只读投影。
- Inventory Clean Candidate 不拥有企业公共 Docker / env 最终版本。

## 平台阶段仍需联合验收

以下不阻断 Inventory 自身进入平台集成，但必须在 LIMS 候选进入后完成：

```text
Batch 待检
→ Warehouse 出库失败
→ LIMS 检验/批准/COA/放行
→ Batch LIMS 投影
→ Warehouse 出库成功
```

## 后续

1. 将 PR #12 squash 进入 `integration/hbos-platform-v1`。
2. 原始 PR #8 不作为 main 合并路径。
3. 转入 PR #10 LIMS Clean Candidate。
