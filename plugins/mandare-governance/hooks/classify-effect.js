/** @typedef {typeof Effect[keyof typeof Effect]} EffectClass */
/** @typedef {Record<string, unknown>} ToolInput */

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

// git, gh and rm are analysed token by token (see classifyCommandTokens), so
// global options such as `git -C dir push` or wrappers such as `sudo` cannot
// hide them. These patterns cover the remaining tools.
const DESTRUCTIVE_BASH = [
  /\bterraform\s+destroy\b/i,
  /\bkubectl\s+delete\b/i,
  /\b(?:drop\s+(?:database|table)|truncate\s+table)\b/i,
  /\bmkfs(?:\.[A-Za-z0-9_-]+)?\b/i,
  /\bdd\b[^\n;&|]*\bof=\/dev\//i,
]

const EXTERNAL_WRITE_BASH = [
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
  /\b(?:scp|sftp)\b/i,
  /\brsync\b[^\n;&|]*\s[^\s]+@[^:]+:/i,
]

const NETWORK_READ_BASH = [
  /\bcurl\b/i,
  /\bwget\b/i,
]

/** @type {EffectClass[]} */
const RANK = [Effect.LOCAL_EXECUTION, Effect.NETWORK_READ, Effect.EXTERNAL_WRITE, Effect.DESTRUCTIVE]

/**
 * @param {EffectClass} a
 * @param {EffectClass} b
 * @returns {EffectClass}
 */
function stronger(a, b) {
  return RANK.indexOf(b) > RANK.indexOf(a) ? b : a
}

// Options that take a separate value, per command, so the value is not read as the subcommand.
const GIT_VALUE_OPTIONS = new Set(['-C', '-c', '--git-dir', '--work-tree', '--namespace', '--config-env', '--super-prefix'])
const GH_VALUE_OPTIONS = new Set(['-R', '--repo', '--hostname'])

// gh subcommands that only read. Any other gh subcommand needs approval.
const GH_READ = new Set([
  'view', 'list', 'ls', 'status', 'checks', 'diff', 'watch', 'download', 'clone', 'checkout',
  'browse', 'token', 'get', 'help', 'version',
])

/**
 * Index of the first non-option token at or after `from`.
 *
 * @param {string[]} tokens
 * @param {number} from
 * @param {Set<string>} valueOptions
 */
function skipOptions(tokens, from, valueOptions) {
  let i = from
  for (let token = tokens[i]; token?.startsWith('-'); token = tokens[i]) {
    i += valueOptions.has(token) ? 2 : 1
  }
  return i
}

/** @param {string[]} args @param {string} letter @param {string} long */
function hasFlag(args, letter, long) {
  return args.some((arg) => arg === long || arg.startsWith(long + '=') || (/^-[A-Za-z]+$/.test(arg) && arg.includes(letter)))
}

/** @param {string[]} args */
function classifyGit(args) {
  const at = skipOptions(args, 0, GIT_VALUE_OPTIONS)
  const sub = args[at]
  const rest = args.slice(at + 1)
  if (sub === 'push') {
    const removes = rest.some((arg) => /^--(?:force|delete|mirror|prune)/.test(arg) || /^-[A-Za-z]*[fd][A-Za-z]*$/.test(arg))
      || rest.some((arg) => /^[+:]./.test(arg))
    return removes ? Effect.DESTRUCTIVE : Effect.EXTERNAL_WRITE
  }
  if (sub === 'send-email') return Effect.EXTERNAL_WRITE
  if (sub === 'reset' && rest.includes('--hard')) return Effect.DESTRUCTIVE
  if (sub === 'clean' && hasFlag(rest, 'f', '--force')) return Effect.DESTRUCTIVE
  if (sub === 'fetch' || sub === 'ls-remote') return Effect.NETWORK_READ
  return Effect.LOCAL_EXECUTION
}

/** @param {string[]} args */
function classifyGh(args) {
  const at = skipOptions(args, 0, GH_VALUE_OPTIONS)
  const group = args[at]
  if (group === undefined || group === 'search' || GH_READ.has(group)) return Effect.NETWORK_READ
  if (group === 'api') return classifyGhApi(args.slice(at + 1))
  const subAt = skipOptions(args, at + 1, GH_VALUE_OPTIONS)
  const sub = args[subAt]
  if (sub === 'delete') return Effect.DESTRUCTIVE
  if (sub !== undefined && GH_READ.has(sub)) return Effect.NETWORK_READ
  return Effect.EXTERNAL_WRITE
}

/**
 * gh api: an explicit non-GET method, or field/input flags without an explicit
 * method (implicit POST), writes.
 *
 * @param {string[]} args
 */
function classifyGhApi(args) {
  let method = null
  args.forEach((arg, i) => {
    const m = /^(?:-X|--method)=?(.*)$/.exec(arg)
    if (m) method = (m[1] || args[i + 1] || '').toUpperCase()
  })
  if (method !== null) return method === 'GET' ? Effect.NETWORK_READ : Effect.EXTERNAL_WRITE
  const sendsFields = args.some((arg) => /^(?:-f|-F|--field|--raw-field|--input)(?:=|$)/.test(arg) || /^-[fF]./.test(arg))
  return sendsFields ? Effect.EXTERNAL_WRITE : Effect.NETWORK_READ
}

/** @param {string[]} args */
function classifyRm(args) {
  const recursive = hasFlag(args, 'r', '--recursive') || hasFlag(args, 'R', '--recursive')
  return recursive && hasFlag(args, 'f', '--force') ? Effect.DESTRUCTIVE : Effect.LOCAL_EXECUTION
}

/**
 * Looks at every position in a command segment, not only the first word, so
 * `sudo rm -rf`, `xargs git push` and `bash -c 'git push'` are still seen.
 * A mention such as `echo git push` is over-classified; that costs a prompt.
 *
 * @param {string[]} tokens
 * @returns {EffectClass}
 */
function classifyCommandTokens(tokens) {
  let effect = /** @type {EffectClass} */ (Effect.LOCAL_EXECUTION)
  tokens.forEach((token, i) => {
    const program = token.split('/').at(-1)
    const args = tokens.slice(i + 1)
    if (program === 'git') effect = stronger(effect, classifyGit(args))
    else if (program === 'gh') effect = stronger(effect, classifyGh(args))
    else if (program === 'rm') effect = stronger(effect, classifyRm(args))
    else if (program === 'find' && args.includes('-delete')) effect = stronger(effect, Effect.DESTRUCTIVE)
  })
  return effect
}

/**
 * Command segments, split at shell separators and substitution boundaries,
 * each as whitespace tokens with quotes and backslashes removed.
 *
 * @param {string} command
 * @returns {string[][]}
 */
function commandSegments(command) {
  return command
    .split(/[;&|\n()`{}]|\$\(/)
    .map((segment) => segment.split(/\s+/).map((token) => token.replace(/['"\\]/g, '')).filter(Boolean))
    .filter((tokens) => tokens.length > 0)
}

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

// Names that say the operation runs whatever it is given. A read verb beside one
// of these proves nothing (`query_database` runs SQL), so the call is UNKNOWN.
const MCP_OPEN_ENDED = new Set([
  'execute', 'exec', 'run', 'sql', 'rpc', 'graphql', 'mutation', 'command', 'eval', 'script',
  'invoke', 'database', 'db',
])

const MCP_READ = new Set([
  'get', 'fetch', 'list', 'search', 'read', 'find', 'query', 'view', 'inspect',
  'compare', 'download', 'check', 'lookup', 'validate', 'verify', 'status', 'diff',
  'history', 'show', 'describe', 'count',
])

/**
 * @param {string} tool
 * @param {ToolInput} [input]
 * @returns {EffectClass}
 */
export function classifyToolCall(tool, input = {}) {
  if (tool === 'Bash') return classifyBash(String(input.command ?? ''))
  if (SAFE_BUILTINS.has(tool)) return SAFE_BUILTINS.get(tool) ?? Effect.UNKNOWN
  if (/^mcp__/i.test(tool)) return classifyMcp(tool)
  return Effect.UNKNOWN
}

/**
 * @param {string} command
 * @returns {EffectClass}
 */
export function classifyBash(command) {
  if (!command.trim()) return Effect.UNKNOWN
  let effect = commandSegments(command).map(classifyCommandTokens).reduce(stronger, Effect.LOCAL_EXECUTION)
  if (DESTRUCTIVE_BASH.some((pattern) => pattern.test(command))) effect = stronger(effect, Effect.DESTRUCTIVE)
  if (EXTERNAL_WRITE_BASH.some((pattern) => pattern.test(command))) effect = stronger(effect, Effect.EXTERNAL_WRITE)
  if (NETWORK_READ_BASH.some((pattern) => pattern.test(command))) effect = stronger(effect, Effect.NETWORK_READ)
  return effect
}

/**
 * @param {string} tool
 * @returns {EffectClass}
 */
export function classifyMcp(tool) {
  const operation = String(tool).split('__').filter(Boolean).at(-1) ?? ''
  const tokens = operation.replace(/([a-z0-9])([A-Z])/g, '$1_$2').toLowerCase().split(/[_-]+/).filter(Boolean)
  if (tokens.some((token) => MCP_DESTRUCTIVE.has(token))) return Effect.DESTRUCTIVE
  if (tokens.some((token) => MCP_WRITE.has(token))) return Effect.EXTERNAL_WRITE
  if (tokens.some((token) => MCP_OPEN_ENDED.has(token))) return Effect.UNKNOWN
  if (tokens.some((token) => MCP_READ.has(token))) return Effect.NETWORK_READ
  return Effect.UNKNOWN
}

/**
 * @param {object | null | undefined} event
 * @returns {ToolInput}
 */
export function toolInput(event) {
  /** @type {ToolInput} */
  const input = {}
  for (const [key, value] of Object.entries(event ?? {})) {
    if (['tool', 'tool_use_id', 'agentId', 'agent_id'].includes(key)) continue
    input[key] = value
  }
  return input
}

/**
 * @param {unknown} value
 * @returns {string}
 */
export function stableStringify(value) {
  if (value === null || typeof value !== 'object') return JSON.stringify(value)
  if (Array.isArray(value)) return '[' + value.map(stableStringify).join(',') + ']'
  const record = /** @type {Record<string, unknown>} */ (value)
  return '{' + Object.keys(record).sort().map((key) => JSON.stringify(key) + ':' + stableStringify(record[key])).join(',') + '}'
}

export const MAX_REVIEW_CHARS = 4000

// C0/C1 controls (except tab and newline), zero-width and bidirectional
// formatting characters can make a terminal draw something other than what runs.
const UNSAFE_DISPLAY = /[\u0000-\u0008\u000b-\u001f\u007f-\u009f\u200b-\u200f\u2028\u2029\u202a-\u202e\u2066-\u2069\ufeff]/g

/**
 * The whole invocation as a human must see it to approve it: a Bash command
 * verbatim, any other tool as its name and canonical arguments. Characters that
 * could alter how a terminal draws the text are shown as escapes.
 *
 * Returns null when the text is longer than a prompt can show for review; the
 * guard then denies instead of asking someone to approve what they cannot see.
 *
 * @param {string} tool
 * @param {ToolInput} input
 * @returns {string | null}
 */
export function reviewText(tool, input) {
  const raw = tool === 'Bash' ? String(input.command ?? '') : `${tool} ${stableStringify(input)}`
  const visible = raw.replace(UNSAFE_DISPLAY, (ch) => `\\u{${ch.codePointAt(0)?.toString(16)}}`)
  return visible.length > MAX_REVIEW_CHARS ? null : visible
}
