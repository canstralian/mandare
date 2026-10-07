import { expect, mock, test } from 'claude-code/testing'
import { failClosed } from '../hooks/mandare-governance.js'

function caught(kind: string | undefined, called: boolean, beneath: () => unknown = () => ({ result: 'beneath' })) {
  let calls = 0
  const next: any = (_e: unknown) => {
    calls += 1
    return Promise.resolve(beneath())
  }
  next.called = called
  next.error = kind === undefined ? undefined : { kind }
  return { next, calls: () => calls }
}

test('re-entry lets a read continue: no approval is needed for it', async () => {
  const { next, calls } = caught('re-entry', false)
  const result = await failClosed({}, { tool: 'Read', file_path: 'README.md' }, next)
  expect(result).toEqual({ result: 'beneath' })
  expect(calls()).toBe(1)
})

test('re-entry denies an external write: no live approval is possible beneath the guard', async () => {
  const { next, calls } = caught('re-entry', false)
  const result: any = await failClosed({}, { tool: 'Bash', command: 'git push origin main' }, next)
  expect(result.deny).toMatch(/EXTERNAL_WRITE raised beneath its own guard/)
  expect(calls()).toBe(0)
})

test('re-entry denies an unclassified tool', async () => {
  const { next, calls } = caught('re-entry', false)
  const result: any = await failClosed({}, { tool: 'mcp__new__teleport' }, next)
  expect(result.deny).toMatch(/UNKNOWN/)
  expect(calls()).toBe(0)
})

test('a throw before the call was passed on denies', async () => {
  for (const kind of ['throw', 'timeout']) {
    const { next, calls } = caught(kind, false)
    const result: any = await failClosed({}, { tool: 'Read', file_path: 'x' }, next)
    expect(result.deny).toMatch(new RegExp(`failed closed before execution: ${kind}`))
    expect(calls()).toBe(0)
  }
})

test('a failure after the call ran replays its settled answer instead of misreporting it', async () => {
  const { next, calls } = caught('throw', true, () => ({ result: 'pushed' }))
  const result = await failClosed({}, { tool: 'Bash', command: 'git push origin main' }, next)
  expect(result).toEqual({ result: 'pushed' })
  expect(calls()).toBe(1)
})

test('the handler itself never throws: a malformed event or next still denies', async () => {
  const hostile = {
    get tool(): string {
      throw new Error('getter exploded')
    },
  }
  const { next, calls } = caught('re-entry', false)
  const result: any = await failClosed({}, hostile, next)
  expect(result.deny).toMatch(/failed closed/)
  expect(calls()).toBe(0)

  const bare: any = () => Promise.resolve({ result: 'x' })
  const noError: any = await failClosed({}, { tool: 'Bash', command: 'git push' }, bare)
  expect(noError.deny).toMatch(/failed closed before execution: unknown/)
})

test('engine: evidence failure after execution does not hide that the call ran', async ($, on) => {
  const saved = new Map<string, any>()
  on('store.get', (_$: any, e: any) => ({ value: saved.get(e.key) }))
  on('store.set', (_$: any, e: any) => {
    if (String(e.value?.records?.at(-1)?.event).startsWith('execution.')) return { deny: 'disk full' }
    saved.set(e.key, e.value)
    return { value: undefined }
  })
  mock.clock(on, { now: 1 })
  let executed = 0
  on('tool.call', (_$: any, e: any) => {
    if (e.tool === 'AskUserQuestion') return { result: { answers: { [e.questions[0].question]: 'Approve once' } } }
    executed += 1
    return { result: 'pushed' }
  })

  const result = await $.tool.call({ tool: 'Bash', command: 'git push origin feature/x' })

  expect(executed).toBe(1)
  expect(result).toEqual({ result: 'pushed' })
})

test('engine: approval prompt that cannot be shown denies the call', async ($, on) => {
  const saved = new Map<string, any>()
  on('store.get', (_$: any, e: any) => ({ value: saved.get(e.key) }))
  on('store.set', (_$: any, e: any) => {
    saved.set(e.key, e.value)
    return { value: undefined }
  })
  mock.clock(on, { now: 1 })
  let executed = 0
  on('tool.call', (_$: any, e: any) => {
    if (e.tool === 'AskUserQuestion') return { deny: 'non-interactive: no one to ask' }
    executed += 1
    return { result: 'should not run' }
  })

  const result: any = await $.tool.call({ tool: 'Bash', command: 'rm -rf build' })

  expect(result.deny).toMatch(/DESTRUCTIVE: this exact invocation was not approved/)
  expect(executed).toBe(0)
  expect(saved.get('mandare.governance.evidence.v1').records.at(-1).decision).toBe('refused_or_unattended')
})
