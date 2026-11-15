/** One credential-free instruction for clients that support HTTP MCP OAuth. */
export function oauthConnectionGuidance(endpoint: string, example: string): string {
  const url = new URL(endpoint)
  if (url.pathname !== '/mcp' || url.username || url.password || url.search || url.hash
    || (url.protocol !== 'https:' && !(url.protocol === 'http:' && ['localhost', '127.0.0.1', 'knowledge-r2.localhost', 'knowledge-rebuild.localhost'].includes(url.hostname)))) {
    throw new Error('连接地址无效。')
  }
  return `请把 HBOS 企业知识库接入为 Streamable HTTP MCP 服务：${url.href}
使用此客户端自带的 OAuth 登录流程，通过服务发现发起 S256 PKCE 授权，并在浏览器由我本人确认 HBOS 账号和权限。令牌由客户端私密保存，不要要求我把凭据、Cookie 或模型密钥贴进对话。
请先核实你的 MCP/OAuth 支持及实际配置命令；不支持时明确说明兼容限制，不虚构安装或授权成功。
授权后真实执行一次 search_knowledge，再用 get_evidence 打开其中一条来源；返回资料名、版本和查询结果。仅列出工具不算查询成功。
试问：${example}
以后涉及企业制度、SOP、工艺或安全数字时，先查本人当前可访问的已发布资料，说明来源和版本；资料不足时如实说明。ask_knowledge 会调用 HBOS 已批准的回答模型。`
}

/** The login return route accepts a pending nonce, never an arbitrary target URL. */
export function oauthConsentReturnPath(query: Record<string, unknown>): string | null {
  const nonce = query.request_id
  if (Object.keys(query).some(key => key !== 'request_id') || typeof nonce !== 'string' || !/^[A-Za-z0-9_-]{43}$/.test(nonce)) return null
  return `/api/method/hb_knowledge_app.hb_knowledge.oauth_api.begin?request_id=${encodeURIComponent(nonce)}`
}
