import { vi } from 'vitest'
Object.defineProperty(window, 'matchMedia', { value: vi.fn(() => ({
  matches: false, addListener() {}, removeListener() {}, addEventListener() {}, removeEventListener() {},
})) })
globalThis.ResizeObserver = class { observe() {} unobserve() {} disconnect() {} }
window.scrollTo = () => undefined
