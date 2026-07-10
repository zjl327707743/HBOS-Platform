# M1-FIX-B2：导入口径、安全与准确性修复

状态：COMPLETED。

本轮只修复导入安全与准确性，不启动 M1-FIX-C/D/E 或 M2，不 closeout M1。

## 已修复

- 移除生产 RPC 的 `local_path`，只接受当前用户有读取权限的私有 `.xlsx` File；文件上限 10MB。
- 严格拆分逐条原始打卡流水与月度汇总：前者才写入 `Employee Checkin` 并尝试 HRMS Auto Attendance；后者只暂存对账数据，不生成打卡或 Attendance。
- 单边打卡只标记上班/下班缺卡，不再合成虚假 IN/OUT；关闭无条件本地 fallback。
- 新增 Attendance 来源、导入批次、兜底、计算版本与原始引用的自定义字段；报表不再由 `device_id` 反推来源。
- 删除含硬编码本地真实路径的临时 `import_runner.py`；补充脱敏离线回归测试。
- M1-FIX-B2-FIX：修复 `考勤结果.py` 报表 `source` 变量作用域 bug（`source` 赋值被误缩进在 `if row.early_exit:` 块内，导致 `early_exit=False` 时 `UnboundLocalError`）。

## 未做

- 未实现异常三级流程、月报/领导 Demo、飞书 OAuth、完整员工/主管页面。
- 未提交真实 Excel、密钥、数据库或运行产物。

## 审查记录

- B2 初审（Claude）：FAIL。`考勤结果.py` 报表 `source` 变量作用域 bug，`early_exit=False` 时 `UnboundLocalError`。
- B2-FIX 复审（Claude）：PASS。`source` 已移至 `if row.early_exit` 外部，新增 AST 静态验证测试，报表空条件执行正常。
- B2 closeout（Codex）：COMPLETED。全部 9 项回归测试通过，Python 编译通过，`bench migrate` 通过，`考勤结果` 和 `打卡流水` 报表空条件执行正常。

## 验证

- `python3 -m unittest apps.hb_attendance_app.tests.test_import_contract apps.hb_attendance_app.tests.test_attendance_result_report`（9 tests OK）
- Python 编译检查、`bench --site frontend migrate`、考勤结果报表空条件执行、打卡流水报表空条件执行。
