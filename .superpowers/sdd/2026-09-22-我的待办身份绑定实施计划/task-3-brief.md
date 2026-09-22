## Task 3：接入稳定性待办与有效截止日

### 范围

- 扩展 `todo_service.py` 的稳定性时间点与稳定性结果 provider。
- 复用 `stability_service._enrich_schedule()` 返回的 `effective_sample_due`、`effective_test_due` 与逾期派生值；数据库字段列表不得查询不存在的 `effective_*_due`。
- `source_test_result` 非空的稳定性结果不生成任何人工待办。
- 稳定性结果动作遵守分析人、复核人、批准人的职责分离。
- 通过可执行行为测试与全量后端测试，提交中文 commit。

### 交付边界

- 不新增稳定性持久化 DocType。
- 不在待办服务增加统一写动作入口；动作仍由稳定性原服务执行并复核。
- 时间点 provider 只产生当前状态下的唯一可执行动作。
