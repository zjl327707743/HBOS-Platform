import { callFrappeMethod, callFrappePostMethod, clearFrappeCsrfToken } from './frappeClient'
import type { SecurityStatus } from './accountApi'
import { iamQuery, IamError } from './iamAccess'
import { knowledgeNativeSessionEnabled } from './knowledgeSessionMode'
export interface IamSecurity extends SecurityStatus { session_context: string; identity: { display_name: string; employee_number: string; department: string; login_name: string }; temporary_password_state: { pending: boolean; temporary: boolean; expires_at: string | null; generation: number; can_claim: boolean }; first_password_required: boolean }
export async function getIamSecurity(expectedUser?: string) {
  if (knowledgeNativeSessionEnabled()) {
    const status = await callFrappeMethod<SecurityStatus & { session_context: string; knowledge_session_contract: string }>('hb_knowledge_app.hb_knowledge.native_session.get_security')
    if (!status?.user || status.user === 'Guest' || (expectedUser && expectedUser !== status.user) || status.knowledge_session_contract !== 'native-v4-v1' || !/^[a-f0-9]{64}$/.test(status.session_context)) throw new IamError('无法确认知识库登录状态，请重新登录。')
    // The deployed V4 has no IAM temporary-password provisioning. These values
    // only satisfy the shell's display contract; all IAM actions stay denied.
    return { ...status, identity: { display_name: status.login_name, employee_number: '', department: '', login_name: status.login_name }, temporary_password_state: { pending: false, temporary: false, expires_at: null, generation: 0, can_claim: false }, first_password_required: false } satisfies IamSecurity
  }
  const status = await callFrappeMethod<IamSecurity>('hbos_portal.auth.accounts.get_security')
  const state = status?.temporary_password_state
  if (!status?.user || status.user === 'Guest' || (expectedUser && status.user !== expectedUser) || !/^[a-f0-9]{64}$/.test(status.session_context || '') || !state || typeof status.first_password_required !== 'boolean' || typeof state.pending !== 'boolean' || typeof state.temporary !== 'boolean' || typeof state.can_claim !== 'boolean' || !Number.isInteger(state.generation)) throw new IamError('无法确认本人账号安全状态，请重新登录或重试。')
  return status
}
export async function claimInitialPassword() {
  try { return await callFrappePostMethod<{ claimed: boolean; temporary_password?: string; expires_at?: string; generation: number }>('hbos_portal.auth.accounts.claim_initial_password') }
  finally { clearFrappeCsrfToken() }
}
export interface MyEmployeeStatus { status: 'linked' | 'unlinked' | 'conflict'; employee_id?: string; employee_number?: string; department?: string; position?: string | null; initial_password_pending?: boolean }
export const getMyEmployeeStatus = () => iamQuery<MyEmployeeStatus>('hbos_portal.api.iam_people.get_my_employee_status')
