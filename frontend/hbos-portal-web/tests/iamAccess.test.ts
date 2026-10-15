import { beforeEach, expect, it, vi } from 'vitest'
vi.mock('@/services/frappeClient', () => ({callFrappeMethod:vi.fn(),callFrappePostMethod:vi.fn()}))
import { callFrappeMethod } from '@/services/frappeClient'
import { validateCapabilities, unwrapIam, loadIamAccess, clearIamAccess, canIam, iamSession } from '@/services/iamAccess'
const valid={schema_version:1,subject_user:'employee-a',policy_revision:'r1',capabilities:['iam.people.read']}
beforeEach(()=>{vi.resetAllMocks();clearIamAccess()})
it('rejects schema, unknown capability and a different current subject',()=>{expect(()=>validateCapabilities({...valid,schema_version:2})).toThrow();expect(()=>validateCapabilities({...valid,capabilities:['unregistered.allow']})).toThrow();expect(()=>validateCapabilities(valid,'employee-b')).toThrow()})
it('never treats an error envelope as a successful local result',()=>{expect(()=>unwrapIam({ok:false,error:{code:'FORBIDDEN',message:'无权'}})).toThrow('无权');expect(()=>unwrapIam({ok:true})).toThrow()})
it('closes previously loaded permissions on a failed refresh',async()=>{vi.mocked(callFrappeMethod).mockResolvedValueOnce({ok:true,data:valid});await loadIamAccess('employee-a');expect(canIam('iam.people.read')).toBe(true);vi.mocked(callFrappeMethod).mockRejectedValueOnce(new Error('offline'));await expect(loadIamAccess('employee-a')).rejects.toThrow();expect(canIam('iam.people.read')).toBe(false)})
it('discards a response from a session cleared while awaiting the server',async()=>{let done!:(value:unknown)=>void;vi.mocked(callFrappeMethod).mockImplementationOnce(()=>new Promise(resolve=>{done=resolve}) as never);const pending=loadIamAccess('employee-a');clearIamAccess();done({ok:true,data:valid});await expect(pending).rejects.toThrow();expect(iamSession.ready).toBe(false)})
