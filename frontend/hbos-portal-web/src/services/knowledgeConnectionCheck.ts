import type { ConnectionInfo } from './p1Api'
export type ConnectionCheck = 'pending' | 'passed' | 'failed'
export interface ConnectionChecks { authentication:ConnectionCheck; tools:ConnectionCheck; search:ConnectionCheck; evidence:ConnectionCheck; error:string }
const controlledTools = ['list_knowledge_spaces','search_knowledge','get_evidence','ask_knowledge']
/** MCP JSON-RPC 信封；自检只读取 error/result 两个字段。 */
interface JsonRpcEnvelope { error?: unknown; result?: unknown }
/** A user-initiated check through the real MCP endpoint. Never calls ask_knowledge. */
export async function checkKnowledgeConnection(info:ConnectionInfo,token:string,query:string,signal:AbortSignal,onUpdate:(value:ConnectionChecks)=>void):Promise<ConnectionChecks> {
  const checks:ConnectionChecks={authentication:'pending',tools:'pending',search:'pending',evidence:'pending',error:''}
  let id=0,phase:keyof Omit<ConnectionChecks,'error'>='authentication'
  const endpoint=new URL(info.endpoint)
  if (endpoint.origin!==window.location.origin || endpoint.pathname!=='/mcp') throw new Error('请从受控知识库地址测试本人连接。')
  async function rpc(method:string,params:unknown) {
    const response=await fetch(endpoint.href,{method:'POST',headers:{'Content-Type':'application/json',Accept:'application/json, text/event-stream',Authorization:'Bearer '+token,'X-HBOS-Self-Check':'1'},body:JSON.stringify({jsonrpc:'2.0',id:++id,method,params}),signal,credentials:'omit',redirect:'error'})
    if (!response.ok) throw new Error(response.status===401?'本人连接未认证或已撤销，请重新创建。':'连接服务暂不可用，请稍后重试。')
    const raw=await response.text()
    let value: JsonRpcEnvelope
    try { value=JSON.parse(raw) } catch { const lines=raw.split('\n').filter(line=>line.startsWith('data:')); value=JSON.parse(lines[lines.length-1]?.slice(5).trim() || '{}') }
    if (value.error || !value.result) throw new Error('连接调用失败，请核对客户端配置。')
    return value.result
  }
  function payload(result: unknown) {
    const row = result as { structuredContent?: unknown; content?: Array<{ type?: string; text?: string }> }
    const value = (row.structuredContent ?? JSON.parse(row.content?.find((c)=>c.type==='text')?.text || '{}')) as { ok?: unknown; data?: unknown }
    if (!value.ok || !value.data) throw new Error('知识查询未完成，请核对资料范围或稍后重试。')
    return value.data
  }
  function update() { if (!signal.aborted) onUpdate({...checks}) }
  try {
    payload(await rpc('tools/call',{name:'list_knowledge_spaces',arguments:{}}));checks.authentication='passed';update()
    phase='tools';const list=await rpc('tools/list',{}) as { tools?: Array<{ name?: string }> }
    const names=(list.tools || []).map((t)=>t.name)
    if (names.length!==4 || controlledTools.some(name=>!names.includes(name))) throw new Error('受控工具列表不匹配，请联系维护人。')
    checks.tools='passed';update()
    // Server readiness only. Browser self-check never searches or verifies a client.

  } catch (error) {
    if (signal.aborted) return checks
    checks[phase]='failed';checks.error=error instanceof Error?error.message:'连接检测未完成。';update()
  }
  return checks
}
