import { afterEach, expect, test, vi } from 'vitest'
import { knowledgeNativeSessionEnabled } from './knowledgeSessionMode'

afterEach(() => { vi.unstubAllEnvs(); window.history.replaceState({}, '', '/') })
test('native V4 adapter is explicit and confined to knowledge routes and their login return', () => {
  window.history.replaceState({}, '', '/hbos/knowledge')
  expect(knowledgeNativeSessionEnabled()).toBe(false)
  vi.stubEnv('VITE_KNOWLEDGE_NATIVE_SESSION', '1')
  expect(knowledgeNativeSessionEnabled()).toBe(true)
  for (const path of ['/hbos/knowledge/document/123', '/hbos/login?redirect_to=%2Fhbos%2Fknowledge%2Foauth%3Frequest_id%3Dtest']) {
    window.history.replaceState({}, '', path); expect(knowledgeNativeSessionEnabled()).toBe(true)
  }
  for (const path of ['/hbos/admin', '/hbos/profile', '/hbos/login', '/hbos/login?redirect_to=https%3A%2F%2Fexample.org', '/hbos/knowledge-other']) {
    window.history.replaceState({}, '', path); expect(knowledgeNativeSessionEnabled()).toBe(false)
  }
})
