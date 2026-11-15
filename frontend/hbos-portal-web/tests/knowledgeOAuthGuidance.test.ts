import { describe, expect, it } from 'vitest'
import { oauthConnectionGuidance, oauthConsentReturnPath } from '@/services/knowledgeOAuthGuidance'
import { guidanceHasNoSecret } from '@/services/knowledgeHelp'

describe('one-copy OAuth connection instructions', () => {
  it('contains discovery, human consent and real source verification without a credential', () => {
    const text = oauthConnectionGuidance('http://localhost:18550/mcp', '查找当前 SOP 并打开来源。')
    expect(guidanceHasNoSecret(text)).toBe(true)
    expect(text).toContain('S256 PKCE')
    expect(text).toContain('search_knowledge')
    expect(text).toContain('get_evidence')
    expect(text).toContain('由我本人确认')
    expect(text).not.toContain('Bearer ')
    expect(text).not.toContain('{credential}')
  })
  it.each(['http://public.example/mcp', 'https://user:secret@example.org/mcp',
    'https://example.org/mcp?token=secret', 'https://example.org/mcp#secret',
    'https://example.org/admin'])('rejects a credential-bearing or incorrect endpoint: %s', endpoint => {
    expect(() => oauthConnectionGuidance(endpoint, '查资料')).toThrow()
  })
})

it.each(["knowledge-r2.localhost", "knowledge-rebuild.localhost"])("supports actual private localhost endpoint %s", (host) => { expect(oauthConnectionGuidance(`http://${host}:18550/mcp`, "查找资料")).toContain(`http://${host}:18550/mcp`) })

it('login return binds one pending nonce to the fixed consent endpoint', () => {
  expect(oauthConsentReturnPath({ request_id: 'a'.repeat(43) })).toContain('oauth_api.begin?request_id=')
  for (const query of [{ request_id: 'https://other.example' }, { request_id: ['a'.repeat(43)] }, { request_id: 'a'.repeat(43), redirect: '//other.example' }]) expect(oauthConsentReturnPath(query)).toBeNull()
})
