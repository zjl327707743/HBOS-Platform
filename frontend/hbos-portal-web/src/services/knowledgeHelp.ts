/**
 * Credential-free assistant help for the connection journey.
 *
 * The text a user copies is safe to paste into their own assistant: it names
 * the public MCP endpoint, the exact client command, the example question and
 * the usage rules. It never contains a token, a password or a model key - the
 * one personal credential is written into the client's own private settings
 * after the user confirms, and is never part of a prompt.
 */

export const ASSISTANT_TOOLS = ['list_knowledge_spaces', 'search_knowledge', 'get_evidence', 'ask_knowledge'] as const

export interface AssistantToolHelp {
  name: string
  purpose: string
  example: string
}

export const TOOL_HELP: AssistantToolHelp[] = [
  { name: 'list_knowledge_spaces', purpose: '列出当前账号可查阅的资料范围，用来看清可以问到哪一步。', example: '我有哪些部门的知识库可以查询？' },
  { name: 'search_knowledge', purpose: '在可查阅范围内检索制度、SOP 与生产质量资料，返回依据条目。', example: '搜索培养箱使用前检查的相关 SOP。' },
  { name: 'get_evidence', purpose: '打开某条依据的核对信息：标题、文号、版本与摘录。', example: '把刚才第二条依据的版本和文号核对一下。' },
  { name: 'ask_knowledge', purpose: '仅在明确要求由 HBOS 生成回答时调用；回答附带可展开的来源。', example: '请 HBOS 根据公司资料总结这部分要求。' },
]

/** Rules the assistant should follow. No endpoint, no credential, no model name. */
export function credentialFreePrompt(): string {
  return [
    '涉及新乡海滨公司的制度、SOP、生产、质量、安全或人事问题时，先调用 HBOS 的 list_knowledge_spaces 与 search_knowledge，再用 get_evidence 核对来源。',
    '列出真实标题与版本；资料不足时明确说明没有可核验的企业依据，不编造内部事实。',
    '不调用原件下载或全文批量导出类操作。',
    '只有用户明确要求 HBOS 生成回答时才调用 ask_knowledge；对话使用哪个模型由用户自己的客户端决定。',
    '不要询问、记录或转述 MCP 凭据；凭据只保存在客户端的安全设置里。',
  ].join('\n')
}

export interface ConnectionGuidance {
  client: 'OpenClaw' | 'Hermes'
  endpoint: string
  /** Exact client command with a placeholder for the personal credential. */
  command: string
  rules: string
  example: string
  version: string
}

/**
 * The one block a user copies. Everything here is public: an endpoint, a command
 * with an obvious placeholder, rules and an example question.
 */
export function connectionGuidance(input: ConnectionGuidance): string {
  const placeholder = '<你的本人凭据>'
  return [
    `# 连接 HBOS 知识库（${input.client}${input.version ? ' ' + input.version : ''}）`,
    '',
    '1) 在终端执行下面这条命令，把占位符换成 HBOS 为你本人生成的一次性凭据（只粘贴到终端，不要发给我）：',
    input.command.replace('{credential}', placeholder),
    '',
    `2) 服务器地址：${input.endpoint}（HTTP / Streamable HTTP）。`,
    '',
    '3) 在助手中提问这个例句，确认能返回真实来源：',
    `   ${input.example}`,
    '',
    '4) 请遵守以下使用规则：',
    input.rules.split('\n').map(line => '   - ' + line).join('\n'),
    '',
    '完成上面第 3 步并打开一条来源后，回到 HBOS 连接页面即可看到“已连接”。',
  ].join('\n')
}

/** True when the text is safe to paste anywhere (no credential, no long random token). */
export function guidanceHasNoSecret(text: string): boolean {
  return !/hbos_mcp_/.test(text) && !/Bearer\s+[A-Za-z0-9._~+/-]{20,}/.test(text)
}

export const CONNECTION_FAQ: { question: string; answer: string }[] = [
  {
    question: '为什么复制的内容里没有我的凭据？',
    answer: '凭据等于你的身份，只写进助手自己的安全设置。复制出的说明和规则不含任何凭据，可以安全地发给助手看。',
  },
  {
    question: '助手说“没有找到资料”怎么办？',
    answer: '先用 list_knowledge_spaces 看可查范围，再换一个更具体的说法。没有可核验依据时，助手应明确说明，而不是编造。',
  },
  {
    question: '怎样停止助手的访问？',
    answer: '在本页“连接管理”里撤销这条连接，撤销后该助手立即无法继续访问；需要时再创建一条新的。',
  },
  {
    question: '这里显示“已连接”代表什么？',
    answer: '代表你本人的这条连接真实完成过一次资料检索并打开了其中一条来源。它不代表助手对你所有问题的回答都正确。',
  },
]
