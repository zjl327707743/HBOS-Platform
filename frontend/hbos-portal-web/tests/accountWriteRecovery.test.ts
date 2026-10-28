import { afterEach, describe, expect, it, vi } from 'vitest'
import { accountWriteAction, clearPendingAccountWrite, readPendingAccountWrite, rememberPendingAccountWrite } from '@/services/accountWriteRecovery'

const id = '0cce9579-64a0-4b01-b579-c17ae713962a'
afterEach(() => { sessionStorage.clear(); vi.restoreAllMocks() })

describe('pending security write receipts', () => {
  it('restores the same account request after a component reload without storing a password or target', async () => {
    expect(rememberPendingAccountWrite('actor@example.test', 'password', id)).toBe(true)
    vi.resetModules()
    const reloaded = await import('@/services/accountWriteRecovery')
    expect(reloaded.readPendingAccountWrite('actor@example.test')).toMatchObject({ user: 'actor@example.test', kind: 'password', requestId: id })
    const stored = JSON.parse(sessionStorage.getItem('hbos:pending-account-write:v1')!)
    expect(Object.keys(stored).sort()).toEqual(['createdAt', 'kind', 'requestId', 'user'])
  })

  it('refuses to overwrite an unresolved request and clears it only after reconciliation', () => {
    rememberPendingAccountWrite('actor@example.test', 'recovery', id)
    expect(rememberPendingAccountWrite('actor@example.test', 'recovery', '7b026b90-37ee-4a17-8a6a-a763907e549a')).toBe(false)
    expect(readPendingAccountWrite('actor@example.test')?.requestId).toBe(id)
    clearPendingAccountWrite('actor@example.test')
    expect(readPendingAccountWrite('actor@example.test')).toBeNull()
  })

  it('never exposes a previous account request to a different account or after logout', () => {
    rememberPendingAccountWrite('actor-A@example.test', 'unlink', id)
    expect(readPendingAccountWrite('actor-B@example.test')).toBeNull()
    expect(readPendingAccountWrite('actor-A@example.test')).toBeNull()
    rememberPendingAccountWrite('actor-A@example.test', 'unlink', id)
    clearPendingAccountWrite()
    expect(readPendingAccountWrite('actor-A@example.test')).toBeNull()
  })

  it('rejects malformed metadata and reports unavailable storage without accepting a receipt', () => {
    sessionStorage.setItem('hbos:pending-account-write:v1', JSON.stringify({ user: 'actor@example.test', kind: 'password', requestId: 'invalid', createdAt: Date.now() }))
    expect(readPendingAccountWrite('actor@example.test')).toBeNull()
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => { throw new DOMException('unavailable') })
    expect(rememberPendingAccountWrite('actor@example.test', 'password', id)).toBe(false)
  })

  it('does not let a late completion for an old actor remove the current actor receipt', () => {
    rememberPendingAccountWrite('actor-B@example.test', 'recovery', id)
    clearPendingAccountWrite('actor-A@example.test')
    expect(readPendingAccountWrite('actor-B@example.test')?.requestId).toBe(id)
  })

  it('does not let a late request clear a newer receipt for the same account', () => {
    const newer = '7b026b90-37ee-4a17-8a6a-a763907e549a'
    rememberPendingAccountWrite('actor@example.test', 'recovery', newer)
    clearPendingAccountWrite('actor@example.test', id)
    expect(readPendingAccountWrite('actor@example.test')?.requestId).toBe(newer)
  })
})

describe('durable receipt action mapping', () => {
  it('maps the UI recovery kind to the administrator recovery_issue action', () => {
    expect(accountWriteAction('password')).toBe('password')
    expect(accountWriteAction('unlink')).toBe('unlink')
    expect(accountWriteAction('recovery')).toBe('recovery_issue')
  })
})
