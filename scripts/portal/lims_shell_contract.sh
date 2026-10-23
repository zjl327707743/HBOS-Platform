#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT_DIR"

ROUTER="frontend/hbos-portal-web/src/router/index.ts"
SIDEBAR="frontend/hbos-portal-web/src/components/layout/AppLocalSidebar.vue"
MOBILE="frontend/hbos-portal-web/src/components/layout/MobileAppNav.vue"
HEADER="frontend/hbos-portal-web/src/components/layout/GlobalHeader.vue"
CAPABILITIES="frontend/hbos-portal-web/src/services/limsCapabilities.ts"
MANIFEST="apps/hb_lims_app/hb_lims_app/hbos_lims/portal/manifest.py"
LIMS_LAYOUT="frontend/hbos-portal-web/src/components/layout/LimsLayout.vue"
DASHBOARD="frontend/hbos-portal-web/src/views/LimsDashboardView.vue"
TASK_BOARD="frontend/hbos-portal-web/src/views/LimsTaskBoardView.vue"
RESULT_LIST="frontend/hbos-portal-web/src/views/LimsResultListView.vue"
RESULT_ENTRY="frontend/hbos-portal-web/src/views/LimsResultEntryView.vue"
LEDGER="frontend/hbos-portal-web/src/views/LimsLedgerView.vue"
AUDIT="frontend/hbos-portal-web/src/views/LimsAuditView.vue"
COA="frontend/hbos-portal-web/src/views/LimsCoaView.vue"
SPECIFICATIONS="frontend/hbos-portal-web/src/views/LimsQualityStandardsView.vue"
RETENTION="frontend/hbos-portal-web/src/views/LimsRetentionWorkbenchView.vue"
STABILITY="frontend/hbos-portal-web/src/views/LimsStabilityWorkbenchView.vue"

fail() {
  echo "LIMS SHELL CONTRACT FAIL: $*" >&2
  exit 1
}

grep -Fq "component: LimsLayout" "$ROUTER" || fail "真实 LIMS 路由没有使用 LimsLayout"
grep -Fq "path: 'samples/new'" "$ROUTER" || fail "缺少样品登记稳定路由"
grep -Fq "path: 'ledger'" "$ROUTER" || fail "缺少 LIMS ledger 稳定路由"
grep -Fq "path: 'coa'" "$ROUTER" || fail "缺少 LIMS COA 稳定路由"
grep -Fq "path: 'specifications'" "$ROUTER" || fail "缺少 LIMS 质量标准稳定路由"
grep -Fq "path: 'retains'" "$ROUTER" || fail "缺少 LIMS 留样工作台稳定路由"
grep -Fq "path: 'retains/samples'" "$ROUTER" || fail "缺少 LIMS 留样台账稳定路由"
grep -Fq "path: 'stability'" "$ROUTER" || fail "缺少 LIMS 稳定性工作台稳定路由"
grep -Fq "path: 'stability/schedule'" "$ROUTER" || fail "缺少 LIMS 稳定性计划稳定路由"

if grep -Fq '<b>5</b>' "$SIDEBAR" || grep -Fq '<b>2</b>' "$SIDEBAR" || grep -Fq '<b>3</b>' "$SIDEBAR"; then
  fail "LIMS Local Sidebar 仍包含写死的 Mock 数字"
fi

grep -Fq "RouterLink" "$SIDEBAR" || fail "桌面 LIMS 导航仍不是稳定路由链接"
grep -Fq "RouterLink" "$MOBILE" || fail "移动 LIMS 导航仍不是稳定路由链接"
grep -Fq "limsCapabilities" "$SIDEBAR" || fail "桌面 LIMS 导航没有统一 capability 门控"
grep -Fq "limsCapabilities" "$MOBILE" || fail "移动 LIMS 导航没有统一 capability 门控"
grep -Fq "view=my-testing" "$SIDEBAR" || fail "桌面任务导航没有使用 view 查询契约"
grep -Fq "view=my-testing" "$MOBILE" || fail "移动任务导航没有使用 view 查询契约"
grep -Fq 'exact-active-class="active"' "$MOBILE" || fail "移动抽屉没有使用精确激活态"
grep -Fq "router-link-exact-active" "frontend/hbos-portal-web/src/styles/global.css" || fail "移动抽屉没有精确激活态样式"
grep -Fq "resolveLimsShellCapabilities" "frontend/hbos-portal-web/src/services/limsCapabilities.ts" || fail "缺少 LIMS capability projection"
grep -Fq "IMPLEMENTED_PAGE_TARGETS" "$CAPABILITIES" || fail "LIMS capability projection 未按已实现页面目标门控"

# Management V0 remains closed until LIMS publishes an explicit, permission-
# aware Provider target. A future implementation must add the contract first;
# the shell must never infer a generic Frappe Desk URL from this placeholder.
if grep -Fq '"management"' "$MANIFEST"; then
  fail "管理后台 capability 在 Provider 目标契约就绪前被提前发布"
fi
if grep -Fq "path: 'management'" "$ROUTER"; then
  fail "LIMS 在 Provider 目标就绪前注册了管理后台路由"
fi
if grep -Fq "managementRoute=" "$LIMS_LAYOUT"; then
  fail "LIMS Shell 在 Provider 目标就绪前接入了管理后台目标"
fi
if grep -Fq '/desk' "$ROUTER" || grep -Fq ':8080' "$ROUTER"; then
  fail "LIMS 管理入口不得跳转 Frappe Desk 或 8080"
fi

grep -Fq "LimsDashboardView" "$ROUTER" || fail "真实 LIMS 路由未注册 Dashboard V2"
grep -Fq "portal.summaryMetrics" "$DASHBOARD" || fail "Dashboard 未消费 Portal Provider 指标"
grep -Fq "portal.tasks" "$DASHBOARD" || fail "Dashboard 未消费 Portal Provider 任务"
grep -Fq "scopeLabel" "$DASHBOARD" || fail "Dashboard 未展示 Provider 权限范围"
grep -Fq "LimsTaskBoardView" "$ROUTER" || fail "真实 LIMS 路由未注册 Task Board V1"
grep -Fq "'my-testing'" "$TASK_BOARD" || fail "Task Board 未声明待检视图契约"
grep -Fq "statusFilter" "$TASK_BOARD" || fail "Task Board 未实现状态筛选"
grep -Fq "priorityFilter" "$TASK_BOARD" || fail "Task Board 未实现优先级筛选"
grep -Fq "handleRowKeydown" "$TASK_BOARD" || fail "Task Board 未实现键盘任务导航"
grep -Fq "getPortalTaskPage" "$TASK_BOARD" || fail "Task Board 未消费 Provider 任务"
grep -Fq "LimsResultListView" "$ROUTER" || fail "真实 LIMS 路由未注册 Result List V1"
grep -Fq "LimsResultEntryView" "$ROUTER" || fail "真实 LIMS 路由未注册 Result Entry V1"
grep -Fq "LimsLedgerView" "$ROUTER" || fail "真实 LIMS 路由未注册 Result Ledger V1"
grep -Fq "LimsAuditView" "$ROUTER" || fail "真实 LIMS 路由未注册 Audit V1"
grep -Fq "listLimsResults" "$RESULT_LIST" || fail "Result List 未消费 LIMS 结果服务"
grep -Fq "getLimsResult" "$RESULT_ENTRY" || fail "Result Entry 未消费 LIMS 结果详情服务"
grep -Fq "submitLimsResult" "$RESULT_ENTRY" || fail "Result Entry 未接入结果提交领域服务"
grep -Fq "canWrite" "$RESULT_ENTRY" || fail "Result Entry 未门控写操作"
grep -Fq "listLimsLedger" "$LEDGER" || fail "Result Ledger 未消费 LIMS 台账服务"
grep -Fq "listLimsAudit" "$AUDIT" || fail "Audit 未消费 LIMS 审计服务"
grep -Fq "LimsCoaView" "$ROUTER" || fail "真实 LIMS 路由未注册 COA 只读视图"
grep -Fq "LimsQualityStandardsView" "$ROUTER" || fail "真实 LIMS 路由未注册质量标准只读视图"
grep -Fq "listLimsCoas" "$COA" || fail "COA 视图未消费 LIMS 报告服务"
grep -Fq "getLimsCoa" "$COA" || fail "COA 视图未消费 LIMS 报告详情服务"
grep -Fq "listLimsSpecifications" "$SPECIFICATIONS" || fail "质量标准视图未消费 LIMS 标准服务"
grep -Fq "getLimsSpecification" "$SPECIFICATIONS" || fail "质量标准视图未消费 LIMS 标准详情服务"
grep -Fq "LimsRetentionWorkbenchView" "$ROUTER" || fail "真实 LIMS 路由未注册留样工作台"
grep -Fq "getLimsRetention" "$RETENTION" || fail "留样工作台未消费留样领域投影"
grep -Fq "观察任务" "$RETENTION" || fail "留样工作台缺少观察任务视图"
grep -Fq "使用申请" "$RETENTION" || fail "留样工作台缺少使用申请视图"
grep -Fq "处理申请" "$RETENTION" || fail "留样工作台缺少处理申请视图"
grep -Fq "LimsStabilityWorkbenchView" "$ROUTER" || fail "真实 LIMS 路由未注册稳定性工作台"
grep -Fq "getLimsStability" "$STABILITY" || fail "稳定性工作台未消费稳定性领域投影"
grep -Fq "趋势分析" "$STABILITY" || fail "稳定性工作台缺少趋势分析视图"
grep -Fq "取样与检测计划" "$STABILITY" || fail "稳定性工作台缺少取样与检测计划视图"
grep -Fq "样品入箱台账" "$STABILITY" || fail "稳定性工作台缺少样品入箱台账视图"
grep -Fq "group-logo-url" "frontend/hbos-portal-web/src/components/layout/LimsLayout.vue" || fail "LIMS Shell 未接入集团标识"
test -f "frontend/hbos-portal-web/public/assets/branding/healthgen-group.png" || fail "缺少健康元集团品牌资产"
test -f "frontend/hbos-portal-web/public/assets/branding/haibin-company.png" || fail "缺少海滨公司品牌资产"
if grep -Fq "Management Console" "$HEADER"; then
  fail "LIMS Shell 页头仍包含英文管理按钮"
fi
if grep -Fq "进入管理后台" "$HEADER"; then
  fail "LIMS Shell 页头仍包含未接线的管理后台入口"
fi

echo "LIMS SHELL CONTRACT PASS"
