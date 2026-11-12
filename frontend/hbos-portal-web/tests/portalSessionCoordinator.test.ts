import { beforeEach, expect, it, vi } from 'vitest'
const bus=vi.hoisted(()=>{
  const channel={postMessage:vi.fn(),onmessage:null as null|((event:{data:string})=>void)}
  class FakeBroadcast { constructor(){return channel} }
  Object.defineProperty(window,'BroadcastChannel',{configurable:true,writable:true,value:FakeBroadcast})
  return channel
})
const api=vi.hoisted(()=>({logout:vi.fn(),security:vi.fn(),caps:vi.fn(),clear:vi.fn(),bootstrap:vi.fn()}))
vi.mock('@/stores/portal',()=>({usePortalStore:()=>({clearSession:api.clear,bootstrap:api.bootstrap,user:{id:'A'}})}))
vi.mock('@/services/iamAccount',()=>({getIamSecurity:api.security}))
vi.mock('@/services/iamAccess',()=>({iamSession:{revision:'r1'},clearIamAccess:vi.fn(),applyIamAccess:vi.fn(),fetchIamAccess:api.caps}))
vi.mock('@/services/frappeClient',()=>({invalidateFrappeRequests:vi.fn(),blockFrappeWrites:vi.fn(),isUnauthenticatedError:()=>false,FrappeRequestError:class extends Error {},logoutFrappeSession:api.logout}))
import {attachPortalSession,portalSession,resetPortalSession,signOutPortalSession} from '@/services/portalSessionCoordinator'
beforeEach(()=>{vi.clearAllMocks();resetPortalSession(false)})
it('R04/R05: another tab stays masked while logout is pending; it never bootstraps the old cookie',async()=>{
 const detach=attachPortalSession();bus.onmessage!({data:'suspend'});await Promise.resolve()
 expect(portalSession.phase).toBe('unconfirmed');expect(api.security).not.toHaveBeenCalled();expect(api.bootstrap).not.toHaveBeenCalled()
 bus.onmessage!({data:'signed_out'});expect(portalSession.phase).toBe('guest');expect(api.bootstrap).not.toHaveBeenCalled();detach()
})
it('R04: logout broadcasts suspension first and only announces signed out after server confirmation',async()=>{
 let done!:()=>void;api.logout.mockImplementationOnce(()=>new Promise<void>(resolve=>{done=resolve}))
 const pending=signOutPortalSession();expect(bus.postMessage).toHaveBeenLastCalledWith('suspend');expect(portalSession.phase).toBe('logging_out')
 done();await pending;expect(bus.postMessage).toHaveBeenLastCalledWith('signed_out');expect(portalSession.phase).toBe('guest')
})
it('R04: failed server logout keeps all other tabs suspended and never claims success',async()=>{
 api.logout.mockRejectedValueOnce(new Error('network'));await expect(signOutPortalSession()).rejects.toThrow()
 expect(bus.postMessage).toHaveBeenCalledTimes(1);expect(bus.postMessage).toHaveBeenCalledWith('suspend');expect(portalSession.phase).toBe('unconfirmed')
})
