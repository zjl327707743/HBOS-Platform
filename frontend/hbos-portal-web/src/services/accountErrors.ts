import { FrappeRequestError } from './frappeClient'
export function accountErrorMessage(error: unknown, fallback = '操作未完成，请稍后重试。'): string {
  return error instanceof FrappeRequestError ? error.message : fallback
}
export function isUncertainWrite(error: unknown): boolean {
  return !(error instanceof FrappeRequestError) || ['NETWORK_ERROR', 'SERVICE_ERROR'].includes(error.code)
}
