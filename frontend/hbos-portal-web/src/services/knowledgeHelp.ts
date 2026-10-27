/**
 * Credential-free assistant help content for the four-step connection wizard.
 *
 * Help entries are filtered by the live ConnectionInfo.tools list.
 * Copy is model-neutral: the chat model is whatever the user configures in
 * their own assistant, and no default model alias is advertised.
 * Tokens never appear in any copied prompt; they enter only private client configuration.
 */

export const ASSISTANT_TOOLS = ['list_knowledge_spaces', 'search_knowledge', 'get_evidence', 'ask_knowledge'] as const

export interface AssistantToolHelp {
  name: string
  purpose: string
  example: string
}

export const TOOL_HELP: AssistantToolHelp[] = [
  {
    name: 'list_knowledge_spaces',
    purpose: '列出当前账号已授权的资料范围（部门空间），用于确认可查询的边界。',
    example: '我有哪些部门的知识库可以查询？',
  },
  {
    name: 'search_knowledge',
    purpose: '在授权范围内检索公司制度、SOP 与生产质量资料，返回依据条目。',
    example: '搜索培养箱使用前检查的相关 SOP。',
  },
  {
    name: 'get_evidence',
    purpose: '打开某条依据的核对信息：标题、文号、版本状态与摘录，用于引用前核验。',
    example: '把刚才第二条依据的版本和文号给我核对一下。',
  },
  {
    name: 'ask_knowledge',
    purpose: '仅在明确要求由 HBOS 生成回答时调用；回答会附带可展开的来源列表。',
    example: '请 HBOS 根据公司资料总结一下这部分要求。',
  },
]

/** Credential-free usage prompt copied into the user's assistant rules. */
export function credentialFreePrompt(): string {
  return [
    '涉及新乡海滨公司制度、SOP、生产、质量、安全或人事问题时，先调用 HBOS 的 list_knowledge_spaces、search_knowledge，再用 get_evidence 核对来源。',
    '列出真实标题和版本状态；资料不足时明确说明没有可核验的企业依据，不编造内部事实。',
    '不调用 get_source、原件下载或全文枚举。',
    '只有用户明确要求 HBOS 生成回答时才调用 ask_knowledge；回答使用哪个对话模型由用户自己的客户端设置决定，HBOS 不指定默认模型。',
    '禁止将 MCP 凭据、配置文件或连接令牌发送给任何模型或写入提示词。',
  ].join('\n')
}

export interface ConnectionStepHelp {
  step: 1 | 2 | 3 | 4
  title: string
  detail: string
}

export const CONNECTION_STEPS: ConnectionStepHelp[] = [
  { step: 1, title: '选择助手', detail: '选择你使用的助手客户端（OpenClaw 或 Hermes）；版本要求以连接设置中显示的支持版本为准。' },
  { step: 2, title: '连接知识库', detail: '复制“说明+无密钥提示词”写入助手规则；令牌只填写到助手的私密认证设置，也可通过高级安装文件导入；绝不进入提示词或对话。' },
  { step: 3, title: '实际试用', detail: '在自己的助手中提一个真实公司知识问题；只有服务端记录到真实工具调用并成功复开来源，才算完成知识查询。' },
  { step: 4, title: '使用帮助', detail: '查看四个工具的用途、例句与常见问题；没有资料时助手应说明缺少可核验依据，而不是编造。' },
]

export interface FaqEntry {
  question: string
  answer: string
}

export const CONNECTION_FAQ: FaqEntry[] = [
  {
    question: '为什么复制内容里没有我的连接令牌？',
    answer: '令牌只填写到助手的私密 MCP 认证设置（高级安装文件在成功导入后删除）；复制出的说明和提示词永远不含凭据，可以安全粘贴给他人查看或存档。',
  },
  {
    question: '助手回答“没有找到资料”怎么办？',
    answer: '先确认问题属于已共享的部门范围；用 list_knowledge_spaces 查看可查范围，再换关键词重试。没有可核验依据时，正确的表现是明确告知，而不是给出未经核实的答案。',
  },
  {
    question: '怎样撤销助手的访问？',
    answer: '在“连接管理”中撤销对应连接，撤销后该助手立即无法继续访问公司知识；重新连接需要重新创建连接并导入新的私密安装文件。',
  },
  {
    question: '回答使用什么模型？',
    answer: '对话模型由你自己在助手中的设置决定，HBOS 不绑定默认模型；公司知识部分始终来自已授权资料并附来源，可以逐条点开核对。',
  },
]
