import axios from 'axios'

export interface ProviderFailure {
  appId: string
  appTitle: string
  message: string
}

/** 使用面向用户的提示和关联编号，不渲染服务器堆栈或原始响应。 */
export function portalErrorMessage(error: unknown, fallback: string): string {
  let trace: unknown
  if (error && typeof error === 'object' && 'traceId' in error) trace = error.traceId
  if (axios.isAxiosError(error)) {
    const data = error.response?.data
    trace ??= data?.message?.error?.trace_id ?? data?.error?.trace_id ?? data?.trace_id
  }
  return typeof trace === 'string' && /^[\w.:/-]{1,128}$/.test(trace)
    ? `${fallback}（关联编号：${trace}）`
    : fallback
}

export function providerFailureMessage(errors: ProviderFailure[]): string | null {
  return errors.length ? errors.map((error) => `${error.appTitle}：${error.message}`).join('；') : null
}
