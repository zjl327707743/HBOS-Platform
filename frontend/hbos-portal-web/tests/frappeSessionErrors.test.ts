import { beforeEach, expect, it, vi } from 'vitest'
const http = vi.hoisted(()=>({get:vi.fn(),post:vi.fn()}))
vi.mock('axios', async importOriginal => {
  const actual = await importOriginal<typeof import('axios')>()
  const { createTrackedAxios } = await import('./helpers/axiosAdapter')
  return { ...actual, default: { ...actual.default, create: (options?: import('axios').CreateAxiosDefaults) => createTrackedAxios(actual.default, http, options) } }
})
import { normalizeFrappeError, callFrappeMethod, callFrappePostMethod, logoutFrappeSession, invalidateFrappeRequests, blockFrappeWrites, FrappeRequestError } from '@/services/frappeClient'
const error=(status:number,detail:string)=>({isAxiosError:true,response:{status,data:{exc_type:detail,exception:detail,_server_messages:JSON.stringify([JSON.stringify({message:'请先重新验证本人身份。'})])}}})
const fact=(authenticated:boolean)=>({data:{message:{authenticated,session_context:authenticated?'a'.repeat(64):null,csrf_token:authenticated?'token':null}}})
beforeEach(()=>{vi.clearAllMocks();invalidateFrappeRequests();blockFrappeWrites(false)})
it.each([403,417])('R03: confirmed Guest %s outranks account validation messages', status=>{expect(normalizeFrappeError(error(status,'PermissionError not whitelisted'), 'hbos_portal.auth.accounts.get_security', {authenticated:false}).code).toBe('UNAUTHENTICATED')})
it('R03: logged-in unregistered method is a Chinese diagnostic, not a false logout or framework leak',()=>{const e=normalizeFrappeError(error(417,'Failed to get method hbos_portal.internal /home/private.py'), 'invalid.method',{authenticated:true});expect(e.code).toBe('SERVICE_ERROR');expect(e.message).toContain('诊断编号');expect(e.message).not.toMatch(/hbos_portal|private.py/)})
it('R03: business forbidden, proof, password/OTP, CSRF, rate, network and unknown identity remain distinct',()=>{
  expect(normalizeFrappeError(error(403,'PermissionError'), 'business.read',{authenticated:true}).code).toBe('FORBIDDEN')
  expect(normalizeFrappeError(error(417,'AuthenticationError'), 'business.save',{authenticated:true}).code).toBe('PROOF_REQUIRED')
  expect(normalizeFrappeError(error(401,'AuthenticationError'),'login').code).toBe('INVALID_CREDENTIALS')
  expect(normalizeFrappeError(error(401,'AuthenticationError'),'login_mfa').code).toBe('INVALID_CREDENTIALS')
  expect(normalizeFrappeError(error(400,'CSRFTokenError')).code).toBe('CSRF_MISMATCH')
  expect(normalizeFrappeError(error(429,'RateLimitExceededError')).code).toBe('RATE_LIMITED')
  expect(normalizeFrappeError({isAxiosError:true}).code).toBe('NETWORK_ERROR')
  expect(normalizeFrappeError(error(417,'not whitelisted')).code).toBe('SESSION_UNCONFIRMED')
})
it('R03: ambiguous real framework error performs only the minimal probe',async()=>{http.get.mockRejectedValueOnce(error(417,'not whitelisted')).mockResolvedValueOnce(fact(false));await expect(callFrappeMethod('hbos_portal.auth.accounts.get_security')).rejects.toMatchObject({code:'UNAUTHENTICATED'});expect(http.get).toHaveBeenLastCalledWith('/api/method/hbos_portal.auth.accounts.get_request_security',expect.anything())})
it('R2: an exhausted read conflict stays a query retry message and makes no automatic client replay',async()=>{
  http.get.mockRejectedValueOnce({isAxiosError:true,response:{status:409,data:{message:{ok:false,error:{code:'READ_CONFLICT',message:'读取遇到暂时冲突，请重试查询。'}}}}})
  await expect(callFrappeMethod('business.read')).rejects.toMatchObject({code:'READ_CONFLICT',message:'读取遇到暂时冲突，请重试查询。'})
  expect(http.get).toHaveBeenCalledTimes(1);expect(http.post).not.toHaveBeenCalled()
})
it('R04: confirmed Guest logout succeeds without a POST',async()=>{http.get.mockResolvedValueOnce(fact(false));await logoutFrappeSession();expect(http.post).not.toHaveBeenCalled()})
it('R04: logout alone retries once on native CSRF rotation and confirms Guest',async()=>{http.get.mockResolvedValueOnce(fact(true)).mockResolvedValueOnce(fact(true)).mockResolvedValueOnce(fact(false));http.post.mockRejectedValueOnce(error(400,'CSRFTokenError')).mockResolvedValueOnce({data:{}});await logoutFrappeSession();expect(http.post).toHaveBeenCalledTimes(2)})
it('R04: unknown server revocation stays uncertain; ordinary writes never replay',async()=>{http.get.mockResolvedValueOnce(fact(true));http.post.mockRejectedValueOnce({isAxiosError:true});await expect(logoutFrappeSession()).rejects.toMatchObject({code:'NETWORK_ERROR'});http.get.mockResolvedValueOnce({data:{message:{ok:true,data:{csrf_token:'token'}}}});http.post.mockRejectedValueOnce(error(400,'CSRFTokenError'));await expect(callFrappePostMethod('business.save',{})).rejects.toMatchObject({code:'CSRF_MISMATCH'});expect(http.post).toHaveBeenCalledTimes(2)})
it('R05: late responses and writes under an unconfirmed identity cannot reach callers',async()=>{let done!:(value:unknown)=>void;http.get.mockImplementationOnce(()=>new Promise(r=>{done=r}));const pending=callFrappeMethod('business.read');await vi.waitFor(()=>expect(done).toBeTypeOf('function'));invalidateFrappeRequests();done({data:{message:{private:'old'}}});await expect(pending).rejects.toMatchObject({code:'STALE_RESPONSE'});blockFrappeWrites(true);await expect(callFrappePostMethod('business.save')).rejects.toBeInstanceOf(FrappeRequestError);expect(http.post).not.toHaveBeenCalled()})
it('R05: a late old-session authentication failure cannot expire the new session or even probe it',async()=>{
  let reject!:(e:unknown)=>void;http.get.mockImplementationOnce(()=>new Promise((_,r)=>{reject=r}));const expired=vi.fn();window.addEventListener('hbos:session-expired',expired)
  const pending=callFrappeMethod('business.read');await vi.waitFor(()=>expect(reject).toBeTypeOf('function'));invalidateFrappeRequests();reject(error(401,'AuthenticationError'))
  await expect(pending).rejects.toMatchObject({code:'STALE_RESPONSE'});expect(expired).not.toHaveBeenCalled();expect(http.get).toHaveBeenCalledTimes(1);window.removeEventListener('hbos:session-expired',expired)
})
it('R04/R05: logout CSRF retry never terminates a different replacement session',async()=>{
  http.get.mockResolvedValueOnce(fact(true)).mockResolvedValueOnce({data:{message:{authenticated:true,session_context:'b'.repeat(64),csrf_token:'new'}}});http.post.mockRejectedValueOnce(error(400,'CSRFTokenError'))
  await expect(logoutFrappeSession()).rejects.toMatchObject({code:'SESSION_UNCONFIRMED'});expect(http.post).toHaveBeenCalledTimes(1)
})
