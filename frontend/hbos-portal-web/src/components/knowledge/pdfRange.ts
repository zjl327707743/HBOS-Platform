/** Authenticated bounded PDF reads; no whole-file fetch or authorization cache. */
export const PDF_RANGE_CHUNK_BYTES = 1024 * 1024
const MAX_FILE_BYTES = 768 * 1024 * 1024
const MAX_COALESCED_BYTES = 32 * 1024 * 1024
type Fetcher = (url: string, options: RequestInit) => Promise<Response>
type Options = { fetcher?: Fetcher; renew?: () => Promise<string | null>; onAccessLost?: () => void }

function sameOrigin(url: string) {
  const base = globalThis.location?.href || 'http://localhost/'
  const parsed = new URL(url, base)
  if (!['http:', 'https:'].includes(parsed.protocol) || parsed.origin !== new URL(base).origin) throw new Error('FILE_UNAVAILABLE')
  return url
}

export class PdfRangeSource {
  private url: string
  private length = 0
  private closed = false
  private accessLost = false
  private controllers = new Set<AbortController>()
  private renewing: Promise<void> | null = null
  private readonly fetcher: Fetcher
  constructor(url: string, private readonly options: Options = {}) {
    // Native Window.fetch rejects PdfRangeSource as its receiver. Keep the
    // browser API call on globalThis; test fetchers retain their own contract.
    this.url = sameOrigin(url); this.fetcher = options.fetcher || ((url,options)=>globalThis.fetch(url,options))
  }

  close() {
    this.closed = true
    for (const controller of this.controllers) controller.abort()
    this.controllers.clear()
  }

  private active() {
    if (this.closed) throw new DOMException('Aborted', 'AbortError')
  }

  private denied(): never {
    if (!this.accessLost) { this.accessLost = true; this.options.onAccessLost?.() }
    throw new Error('FILE_UNAVAILABLE')
  }

  private async renew() {
    this.active()
    if (!this.renewing) {
      this.renewing = Promise.resolve().then(async () => {
        const next = await this.options.renew?.()
        this.active()
        if (!next) this.denied()
        this.url = sameOrigin(next)
      }).finally(() => { this.renewing = null })
    }
    await this.renewing
  }

  /** A cached PDF page must still pass current authority before it is drawn. */
  async revalidate() {
    this.active()
    if (this.options.renew) await this.renew()
    else await this.request(0, 1)
  }

  async initialize() {
    this.active()
    if (this.length) throw new Error('FILE_UNAVAILABLE')
    const initialData = await this.request(0, PDF_RANGE_CHUNK_BYTES)
    if (new TextDecoder('ascii').decode(initialData.subarray(0, 5)) !== '%PDF-') throw new Error('NOT_A_PDF')
    return { length: this.length, initialData }
  }

  async read(begin: number, end: number): Promise<Uint8Array> {
    this.active()
    if (!Number.isSafeInteger(begin) || !Number.isSafeInteger(end) || begin < 0 || end <= begin || end > this.length || end - begin > MAX_COALESCED_BYTES) throw new Error('FILE_UNAVAILABLE')
    const output = new Uint8Array(end - begin)
    for (let start = begin; start < end; start += PDF_RANGE_CHUNK_BYTES) {
      const chunk = await this.request(start, Math.min(end, start + PDF_RANGE_CHUNK_BYTES))
      this.active(); output.set(chunk, start - begin)
    }
    return output
  }

  private async request(begin: number, end: number): Promise<Uint8Array> {
    for (let retry = 0; retry < 3; retry++) {
      this.active()
      const url = this.url, controller = new AbortController()
      this.controllers.add(controller)
      let timedOut = false
      const timer = setTimeout(() => { timedOut = true; controller.abort() }, 45_000)
      try {
        const response = await this.fetcher(url, { credentials: 'same-origin', cache: 'no-store', redirect: 'error', signal: controller.signal,
          headers: { Range: `bytes=${begin}-${end - 1}` } })
        this.active()
        if (response.status === 401 || response.status === 403) {
          await response.body?.cancel()
          if (retry < 2 && this.options.renew) {
            if (url === this.url) await this.renew()
            continue
          }
          this.denied()
        }
        if (response.status !== 206) { await response.body?.cancel(); throw new Error('FILE_UNAVAILABLE') }
        const match = /^bytes (\d+)-(\d+)\/(\d+)$/.exec(response.headers.get('Content-Range') || '')
        if (!match) { await response.body?.cancel(); throw new Error('FILE_UNAVAILABLE') }
        const first = Number(match[1]), last = Number(match[2]), total = Number(match[3])
        const expected = Math.min(end, total) - begin
        if (!Number.isSafeInteger(total) || total < 5 || total > MAX_FILE_BYTES || first !== begin || last + 1 !== Math.min(end, total) || expected < 1 || expected > PDF_RANGE_CHUNK_BYTES || this.length && total !== this.length) {
          await response.body?.cancel(); throw new Error('FILE_UNAVAILABLE')
        }
        const declared = response.headers.get('Content-Length')
        if (declared !== null && Number(declared) !== expected) { await response.body?.cancel(); throw new Error('FILE_UNAVAILABLE') }
        const reader = response.body?.getReader()
        if (!reader) throw new Error('FILE_UNAVAILABLE')
        const output = new Uint8Array(expected)
        let offset = 0
        while (true) {
          const part = await reader.read(); this.active()
          if (part.done) break
          if (offset + part.value.length > expected) { await reader.cancel(); throw new Error('FILE_UNAVAILABLE') }
          output.set(part.value, offset); offset += part.value.length
        }
        if (offset !== expected) throw new Error('FILE_UNAVAILABLE')
        this.length = total
        return output
      } catch (error) {
        if (timedOut) throw Object.assign(new Error('FILE_UNAVAILABLE'), { cause: error })
        throw error
      } finally {
        clearTimeout(timer); this.controllers.delete(controller)
      }
    }
    throw new Error('FILE_UNAVAILABLE')
  }
}
