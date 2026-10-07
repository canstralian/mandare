import { expect, mock, test } from 'claude-code/testing'

function stubEvidence(on: any) {
  const saved = new Map<string, unknown>()
  on('store.get', ($, e) => ({ value: saved.get(e.key) }))
  on('store.set', ($, e) => {
    saved.set(e.key, e.value)
    return { value: undefined }
  })
  mock.clock(on, { now: 1_800_000_000_000 })
  return saved
}

test('passes recognized read-only calls without asking for authority', async ($, on) => {
  let toolCalls = 0
  on('tool.call', () => {
    toolCalls += 1
    return { result: 'ok' }
  })

  const result = await $.tool.call({ tool: 'Read', file_path: 'README.md' })
  expect(result).toEqual({ result: 'ok' })
  expect(toolCalls).toBe(1)
})

test('denies an unknown MCP operation before it reaches the provider', async ($, on) => {
  const saved = stubEvidence(on)
  let providerCalls = 0
  on('tool.call', () => {
    providerCalls += 1
    return { result: 'should not run' }
  })

  const result = await $.tool.call({ tool: 'mcp__mystery__teleport', target: 'prod' })
  expect(result.deny).toMatch(/unclassified tool/)
  expect(providerCalls).toBe(0)

  const ledger = saved.get('mandare.governance.evidence.v1') as any
  expect(ledger.records.at(-1).decision).toBe('deny_unknown_effect')
})

test('one-shot approval allows exactly that external mutation', async ($, on) => {
  const saved = stubEvidence(on)
  let executed = 0
  let questions = 0
  on('tool.call', ($, e) => {
    if (e.tool === 'AskUserQuestion') {
      questions += 1
      const question = e.questions[0].question
      return { result: { answers: { [question]: 'Approve once' } } }
    }
    executed += 1
    return { result: 'pushed' }
  })

  const result = await $.tool.call({ tool: 'Bash', command: 'git push origin feat/claude-governance-mod' })
  expect(result).toEqual({ result: 'pushed' })
  expect(questions).toBe(1)
  expect(executed).toBe(1)

  const ledger = saved.get('mandare.governance.evidence.v1') as any
  expect(ledger.records.map((r) => r.event)).toContain('governance.approved')
  expect(ledger.records.at(-1).event).toBe('execution.completed')
})

test('approval is not cached across a second identical mutation', async ($, on) => {
  stubEvidence(on)
  let questions = 0
  let executed = 0
  on('tool.call', ($, e) => {
    if (e.tool === 'AskUserQuestion') {
      questions += 1
      const question = e.questions[0].question
      const answer = questions === 1 ? 'Approve once' : 'Refuse'
      return { result: { answers: { [question]: answer } } }
    }
    executed += 1
    return { result: 'ok' }
  })

  const first = await $.tool.call({ tool: 'mcp__GitHub__create_issue', repository_full_name: 'canstralian/mandare', title: 'one' })
  const second = await $.tool.call({ tool: 'mcp__GitHub__create_issue', repository_full_name: 'canstralian/mandare', title: 'one' })

  expect(first).toEqual({ result: 'ok' })
  expect(second.deny).toMatch(/was not approved/)
  expect(questions).toBe(2)
  expect(executed).toBe(1)
})

test('governance infrastructure failure denies instead of failing open', async ($, on) => {
  on('store.get', () => ({ deny: 'store unavailable' }))
  let executed = 0
  on('tool.call', () => {
    executed += 1
    return { result: 'should not run' }
  })

  const result = await $.tool.call({ tool: 'Bash', command: 'git push origin main' })
  expect(result.deny).toMatch(/failed closed/)
  expect(executed).toBe(0)
})
