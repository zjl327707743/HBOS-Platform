import type { TodoItem } from '@/api/todo'
import * as lims from '@/api/lims'
import * as stability from '@/api/stability'
import * as retention from '@/api/retention'

export interface TodoActionContext {
  navigate: (item: TodoItem) => void
  refresh: () => Promise<unknown>
  notifySuccess: (message: string) => void
  notifyError: (message: string) => void
}

type TodoActionHandler = (item: TodoItem) => Promise<unknown>

const DIRECT_ACTIONS: Record<string, TodoActionHandler> = {
  'testing:start_task': (item) => lims.startTask(item.source_name),
  'testing:review_result': (item) => lims.reviewResult(item.source_name),
  'testing:approve_result': (item) => lims.approveResult(item.source_name),
  'stability:complete_sampling': (item) => stability.completeSampling(item.source_name),
  'stability:start_testing': (item) => stability.startTesting(item.source_name),
  'stability:review_result': (item) => stability.reviewResult(item.source_name),
  'stability:approve_result': (item) => stability.approveResult(item.source_name),
  'retention:review_observation': (item) => retention.reviewObservationByName(item.source_name),
  'retention:submit_usage_apply': (item) => retention.submitUsageApply(item.source_name),
  'retention:confirm_stock': (item) => retention.confirmUsageStock(item.source_name),
  'retention:approve_usage': (item) => retention.approveUsage(item.source_name),
  'retention:execute_usage': (item) => retention.executeUsage(item.source_name),
  'retention:submit_disposal_apply': (item) => retention.submitDisposalApply(item.source_name),
  'retention:approve_disposal': (item) => retention.approveDisposal(item.source_name),
  'retention:continue_retention': (item) => retention.continueRetention(item.source_name),
  'retention:dispose_handle': (item) => retention.disposalHandle(item.source_name),
  'retention:dispose_monitor': (item) => retention.disposalMonitor(item.source_name),
}

const ROUTE_ACTIONS = new Set([
  'testing:submit_result',
  'stability:record_result',
  'stability:eval_trend',
  'stability:submit_result',
  'retention:record_observation',
])

function actionKey(item: TodoItem): string {
  return `${item.module}:${item.action}`
}

/**
 * Routes remain page navigation; direct actions call the same business API as
 * the source page and refresh only after that API has succeeded or failed.
 */
export async function runTodoAction(item: TodoItem, context: TodoActionContext): Promise<boolean> {
  const key = actionKey(item)
  if (item.execute_mode === 'route' || ROUTE_ACTIONS.has(key)) {
    context.navigate(item)
    return true
  }

  const handler = DIRECT_ACTIONS[key]
  if (!handler) {
    const error = `暂不支持待办动作：${item.action}`
    context.notifyError(error)
    await context.refresh()
    return false
  }

  try {
    await handler(item)
    context.notifySuccess(`${item.action_label}已完成：${item.source_name}`)
    await context.refresh()
    return true
  } catch (error) {
    await context.refresh()
    return false
  }
}
