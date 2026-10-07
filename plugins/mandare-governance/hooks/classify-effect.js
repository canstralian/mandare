export const Effect = Object.freeze({
  READ: 'READ',
  LOCAL_WRITE: 'LOCAL_WRITE',
  LOCAL_EXECUTION: 'LOCAL_EXECUTION',
  NETWORK_READ: 'NETWORK_READ',
  EXTERNAL_WRITE: 'EXTERNAL_WRITE',
  DESTRUCTIVE: 'DESTRUCTIVE',
  UNKNOWN: 'UNKNOWN',
})

const SAFE_BUILTINS = new Map([
  ['Read', Effect.READ],
  ['Glob', Effect.READ],
  ['Grep', Effect.READ],
  ['LS', Effect.READ],
  ['NotebookRead', Effect.READ],
  ['Skill', Effect.READ],
  ['AskUserQuestion', Effect.READ],
  ['TodoRead', Effect.READ],
  ['TaskOutput', Effect.READ],
  ['TaskGet', Effect.READ],
  ['TaskList', Effect.READ],
  ['ToolSearch', Effect.READ],
  ['LSP', Effect.READ],
  ['ListMcpResources', Effect.NETWORK_READ],
  ['ReadMcpResource', Effect.NETWORK_READ],
  ['ListMcpResourcesTool', Effect.NETWORK_READ],
  ['ReadMcpResourceTool', Effect.NETWORK_READ],
  ['ReadMcpResourceDirTool', Effect.NETWORK_READ],
  ['WebFetch', Effect.NETWORK_READ],
  ['WebSearch', Effect.NETWORK_READ],
  ['Edit', Effect.LOCAL_WRITE],
  ['Write', Effect.LOCAL_WRITE],
  ['MultiEdit', Effect.LOCAL_WRITE],
  ['NotebookEdit', Effect.LOCAL_WRITE],
  ['TodoWrite', Effect.LOCAL_WRITE],
  ['TaskCreate', Effect.LOCAL_WRITE],
  ['TaskUpdate', Effect.LOCAL_WRITE],
  ['TaskStop', Effect.LOCAL_WRITE],
  ['Task', Effect.LOCAL_EXECUTION],
  ['Agent', Effect.LOCAL_EXECUTION],
  ['KillShell', Effect.LOCAL_EXECUTION],
  ['EnterPlanMode', Effect.READ],
  ['ExitPlanMode', Effect.READ],
])

const DESTRUCTIVE_BASH = [
  /(?:^|[;&|]\s*)rm\s+-(?:[A-Za-z]*r[A-Za-z]*f|[A-Za-z]*f[A-Za-z]*r)\b/i,
  /\bgit\s+reset\s+--hard\b/i,
  /\bgit\s+clean\b[^\n;&|]*\s-f(?:\s|$)/i,
  // Force pushes: long flags (with optional =value), short clusters containing f, and +refspecs.
  /\bgit\s+push\b[^\n;&|]*\s(?:--force(?:-with-lease|-if-includes)?(?:=\S*)?|-[A-Za-z]*f[A-Za-z]*)(?:\s|$)/i,
  /\bgit\s+push\b[^\n;&|]*\s\+\S/i,
  // Remote ref deletion or mirroring: --delete/-d, :ref refspecs, --mirror, --prune.
  /\bgit\s+push\b[^\n;&|]*\s(?:--delete|-d|--mirror|--prune)(?:\s|$)/i,
  /\bgit\s+push\b[^\n;&|]*\s:\S/i,
  /\bterraform\s+destroy\b/i,
  /\bkubectl\s+delete\b/i,
  /\b(?:drop\s+(?:database|table)|truncate\s+table)\b/i,
  /\bmkfs(?:\.[A-Za-z0-9_-]+)?\b/i,
  /\bdd\b[^\n;&|]*\bof=\/dev\//i,
]

const EXTERNAL_WRITE_BASH = [
  /\bgit\s+push\b/i,
  /\bgh\s+(?:pr|issue|release)\s+(?:create|merge|close|reopen|comment|review|edit|delete)\b/i,
  /\b(?:npm|pnpm)\s+publish\b/i,
  /\byarn\s+npm\s+publish\b/i,
  /\btwine\s+upload\b/i,
  /\bdocker\s+push\b/i,
  /\bkubectl\s+(?:apply|create|patch|replace|rollout\s+restart|scale)\b/i,
  /\bterraform\s+apply\b/i,
  /\bcurl\b[^\n;&|]*(?:-X|--request)[\s=]*(?:POST|PUT|PATCH|DELETE)\b/i,
  // curl sends a body (implicit POST/PUT) with -d/-F/-T, alone or in a short-option cluster.
  // Case-sensitive on purpose: -f (fail) and -D (dump headers) are not body flags.
  /\bcurl\b[^\n;&|]*\s(?:-[A-Za-z]*[dFT]|--data|--form|--upload-file|--json)/,
  /\bwget\b[^\n;&|]*\s--(?:post-data|post-file|body-data|body-file|method)\b/i,
  // gh api: an explicit non-GET method, or field/input flags without an explicit method (implicit POST).
  /\bgh\s+api\b[^\n;&|]*(?:-X|--method)[\s=]*(?!GET\b)[A-Za-z]+/i,
  /\bgh\s+api\b(?![^\n;&|]*(?:-X|--method))[^\n;&|]*\s(?:-f|-F|--field|--raw-field|--input)(?:[\s=]|$)/,
  /\b(?:scp|sftp)\b/i,
  /\brsync\b[^\n;&|]*\s[^\s]+@[^:]+:/i,
]

const NETWORK_READ_BASH = [
  /\bgit\s+(?:fetch|ls-remote)\b/i,
  /\bcurl\b/i,
  /\bwget\b/i,
  /\bgh\s+(?:api|pr|issue|release|run|repo)\s+(?:view|list|status|checks|diff)\b/i,
  /\bgh\s+api\b/i,
]

const MCP_DESTRUCTIVE = new Set([
  'delete', 'destroy', 'purge', 'drop', 'wipe',
])

const MCP_WRITE = new Set([
  'create', 'update', 'write', 'patch', 'put', 'post', 'send', 'forward',
  'merge', 'close', 'reopen', 'add', 'remove', 'archive', 'restore', 'approve',
  'dismiss', 'resolve', 'unresolve', 'enable', 'disable', 'upload',
  'deploy', 'publish', 'trigger', 'cancel', 'invite', 'assign', 'label', 'comment',
  'react', 'convert', 'mark', 'move', 'rename', 'set', 'submit', 'reply',
])

const MCP_READ = new Set([
  'get', 'fetch', 'list', 'search', 'read', 'find', 'query', 'view', 'inspect',
  'compare', 'download', 'check', 'lookup', 'validate', 'verify', 'status', 'diff',
  'history', 'show', 'describe', 'count',
])

export function classifyToolCall(tool, input = {}) {
  if (tool === 'Bash') return classifyBash(String(input.command ?? ''))
  if (SAFE_BUILTINS.has(tool)) return SAFE_BUILTINS.get(tool)
  if (/^mcp__/i.test(tool)) return classifyMcp(tool)
  return Effect.UNKNOWN
}

export function classifyBash(command) {
  if (!command.trim()) return Effect.UNKNOWN
  if (DESTRUCTIVE_BASH.some((pattern) => pattern.test(command))) return Effect.DESTRUCTIVE
  if (EXTERNAL_WRITE_BASH.some((pattern) => pattern.test(command))) return Effect.EXTERNAL_WRITE
  if (NETWORK_READ_BASH.some((pattern) => pattern.test(command))) return Effect.NETWORK_READ
  return Effect.LOCAL_EXECUTION
}

export function classifyMcp(tool) {
  const operation = String(tool).split('__').filter(Boolean).at(-1)?.toLowerCase() ?? ''
  const tokens = operation.split(/[_-]+/).filter(Boolean)
  if (tokens.some((token) => MCP_DESTRUCTIVE.has(token))) return Effect.DESTRUCTIVE
  if (tokens.some((token) => MCP_WRITE.has(token))) return Effect.EXTERNAL_WRITE
  if (tokens.some((token) => MCP_READ.has(token))) return Effect.NETWORK_READ
  return Effect.UNKNOWN
}

export function toolInput(event) {
  const input = {}
  for (const [key, value] of Object.entries(event ?? {})) {
    if (['tool', 'tool_use_id', 'agentId', 'agent_id'].includes(key)) continue
    input[key] = value
  }
  return input
}

export function stableStringify(value) {
  if (value === null || typeof value !== 'object') return JSON.stringify(value)
  if (Array.isArray(value)) return '[' + value.map(stableStringify).join(',') + ']'
  return '{' + Object.keys(value).sort().map((key) => JSON.stringify(key) + ':' + stableStringify(value[key])).join(',') + '}'
}

export function approvalSummary(tool, input) {
  if (tool === 'Bash') {
    const command = String(input.command ?? '').replace(/\s+/g, ' ').trim()
    return command.length > 180 ? command.slice(0, 177) + '...' : command || 'empty command'
  }
  const operation = String(tool).split('__').filter(Boolean).at(-1) ?? tool
  const resource = input.repository_full_name ?? input.repo_full_name ?? input.path ?? input.branch_name ?? input.branch ?? ''
  return resource ? `${operation} on ${String(resource).slice(0, 120)}` : operation
}
