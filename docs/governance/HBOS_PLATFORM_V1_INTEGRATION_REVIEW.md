# HBOS Platform v1 三 App 集成验收

> 分支：`integration/hbos-platform-v1`  
> 状态：INTEGRATION TESTING  
> 目标：Attendance + Inventory + LIMS 通过最终平台门禁后，以一个平台 PR 进入 `main`。

## 已进入平台集成的治理候选

- Attendance：G1 A-J PASS，clean-site / rollback / idempotency / policy seed PASS。
- Inventory：Clean Candidate PASS，Inventory Integration Gate PASS。
- LIMS：G3 Clean Candidate PASS，LIMS Python / Vue / clean-site / LIMS→Batch→Warehouse release chain PASS。

原始 PR #8 / #9 / #10 均为历史来源，不再作为最终 main 合并路径。

## 最终根部署契约

根 `docker-compose.yml` 必须从零安装并运行：

1. frappe
2. erpnext
3. hrms
4. hb_attendance_app
5. hb_inventory_app
6. hb_lims_app

同时要求：

- 三个 HBOS App 在 backend / workers / scheduler 使用同一代码树。
- 外部 Feishu / DeliCloud / AI 默认关闭。
- OCR 通过内部 Bearer Token 连接宿主机/内网服务。
- Inventory PDF 所需 Noto Serif SC 可重建且容器可见。
- 连续执行两次 `bench migrate` 幂等。

## 最终 Platform Gate

必须通过：

- 根 Compose clean-site 从零建站；
- 六个 App 全部出现在 `bench list-apps`；
- 双 migrate；
- Attendance G1 DB integration checks；
- LIMS physical schema；
- 待检 Batch → Warehouse 拦截；
- Published COA + LIMS Release → ERPNext Batch projection；
- 放行后 Warehouse 出库门禁通过；
- LIMS Vue unit + production build；
- 中文字体容器 smoke。

## 合并规则

全部 PASS 后：

1. 创建 `integration/hbos-platform-v1 -> main` 最终 PR；
2. 只通过最终平台 PR 合入 main；
3. 推荐 Squash Merge，main 保持清晰平台里程碑；
4. 原始 #8/#9/#10 关闭为 superseded 历史 PR。
