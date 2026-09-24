# PR #9 Attendance Policy 私有数据迁移手册

> 目的：把原 #9 源码里的人员名单迁移到 `HBOS Attendance Policy Assignment`，
> 同时确保真实姓名/工号不继续进入公开 Git。

## 原则

- 策略类型属于代码。
- 员工归属属于业务数据。
- 导出的 seed JSON 是私有数据，禁止放入仓库、Issue、PR、聊天截图或 CI artifact。
- 新环境默认不内置任何真实人员归属。
- 生产升级必须在重新启用考勤 scheduler 前完成导入和抽样核对。

## 1. 从原 #9 快照导出

在管理员本地创建临时 worktree，固定使用已经审计过的原始 #9 HEAD：

```bash
git worktree add /tmp/hbos-pr9-legacy 93ae18a96d0db90746b0b99dee11f73079797ac1
cd /tmp/hbos-pr9-legacy
PYTHONPATH=apps/hb_attendance_app python - <<'PY'
import json
from pathlib import Path

from hb_attendance_app.hbos_attendance.rule_lists import (
    ADMIN_NUMS, FOOD_NUMS, SAFETY_NUMS, EXEMPT_NUMS,
    LATE_EXEMPT_NUMS, ANOMALY_HIDDEN_NUMS,
)
from hb_attendance_app.hbos_attendance.pairing import (
    SPECIAL_SHIFT_NUMS, FOUR_SHIFT_NUMS,
)
from hb_attendance_app.hbos_attendance.rotation_schedule import ROTATION_GROUPS

policy_sets = {
    "ADMIN": ADMIN_NUMS,
    "FOOD": FOOD_NUMS,
    "SAFETY": SAFETY_NUMS,
    "EXEMPT": EXEMPT_NUMS,
    "LATE_EXEMPT": LATE_EXEMPT_NUMS,
    "ANOMALY_HIDDEN": ANOMALY_HIDDEN_NUMS,
    "SPECIAL_SHIFT": SPECIAL_SHIFT_NUMS,
    "FOUR_SHIFT": FOUR_SHIFT_NUMS,
}

rows = []
for policy_type, members in policy_sets.items():
    for employee_number in sorted(members):
        rows.append({
            "employee_number": employee_number,
            "policy_type": policy_type,
            "enabled": 1,
        })

for group in ROTATION_GROUPS:
    for segment in group.get("segments", []):
        for employee_number, anchor_shift in segment.get("members", {}).items():
            rows.append({
                "employee_number": employee_number,
                "policy_type": "ROTATION_3DAY",
                "enabled": 1,
                "effective_from": segment["anchor_date"].isoformat(),
                "group_name": group.get("name", ""),
                "anchor_shift": anchor_shift,
            })

out = Path("/tmp/hbos_attendance_policy_seed.json")
out.write_text(json.dumps({"assignments": rows}, ensure_ascii=False, indent=2))
print("private seed written:", out, "rows=", len(rows))
PY
```

不要把输出文件移动进仓库目录。

## 2. 安装 Clean Candidate

切回治理分支并完成正常安装 / migrate，使以下 DocType 已存在：

`HBOS Attendance Policy Assignment`

## 3. 导入私有 seed

将 seed 放到只有管理员可读的本地路径，然后执行：

```bash
bench --site frontend execute \
  hb_attendance_app.hbos_attendance.policy_migration.import_policy_seed \
  --kwargs '{"path":"/tmp/hbos_attendance_policy_seed.json"}'
```

导入器按：

`Employee + policy_type + effective_from`

幂等 upsert。

## 4. 验证

至少核对：

- total / created / updated / unmatched / invalid；
- 各策略人数与升级前一致；
- 三日轮转人员相位抽样一致；
- 行政班、特殊班次、豁免、只豁免迟到等典型员工行为一致；
- 未匹配记录必须人工核实，不能静默丢弃。

在核对完成前：

- 保持 `HBOS_FEISHU_SYNC_ENABLED=0`
- 保持 `HBOS_DELICLOUD_SYNC_ENABLED=0`
- 不执行历史考勤批量重算。

## 5. 清理

验证结束后删除私有 seed：

```bash
rm -f /tmp/hbos_attendance_policy_seed.json
git worktree remove /tmp/hbos-pr9-legacy
```

该 seed 不属于代码资产，也不进入最终 integration/main。
