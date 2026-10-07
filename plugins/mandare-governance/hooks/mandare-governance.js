import { Effect, MAX_REVIEW_CHARS, classifyToolCall, reviewText, stableStringify, toolInput } from './classify-effect.js'

/** @typedef {import('claude-code').Hook<'tool.call'>} ToolCallHook */
/** @typedef {Parameters<ToolCallHook>[0]} Engine */
/** @typedef {Parameters<ToolCallHook>[1]} ToolCallEvent */
/** @typedef {Record<string, string | number | null>} EvidenceRecord */
/** @typedef {{ version: 1, records: EvidenceRecord[] }} EvidenceLedger */

const EVIDENCE_KEY = 'mandare.governance.evidence.v1'
const MAX_EVIDENCE_RECORDS = 512
const APPROVE = 'Approve once'
const REFUSE = 'Refuse'
const PASS_THROUGH = new Set([Effect.READ, Effect.LOCAL_WRITE, Effect.LOCAL_EXECUTION, Effect.NETWORK_READ])
const APPROVABLE = new Set([Effect.EXTERNAL_WRITE, Effect.DESTRUCTIVE])

/**
 * What the guard does with an effect: an allowlist, so any value the
 * classifier was not written to return (undefined, a typo) is denied
 * rather than passed through.
 *
 * @param {unknown} effect
 * @returns {'pass' | 'approve' | 'deny'}
 */
export function disposition(effect) {
  if (PASS_THROUGH.has(/** @type {any} */ (effect))) return 'pass'
  if (APPROVABLE.has(/** @type {any} */ (effect))) return 'approve'
  return 'deny'
}

/** @param {string} value */
async function sha256(value) {
  const bytes = new TextEncoder().encode(value)
  const digest = await crypto.subtle.digest('SHA-256', bytes)
  return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, '0')).join('')
}

/**
 * SHA-256 over the tool, the call id and the canonical arguments.
 *
 * @param {ToolCallEvent} e
 */
export async function fingerprintEvent(e) {
  const input = toolInput(e)
  const canonical = stableStringify({
    tool: e.tool,
    toolUseId: e.tool_use_id ?? null,
    input,
  })
  return { input, fingerprint: await sha256(canonical) }
}

/**
 * @param {Engine} $
 * @param {EvidenceRecord} record
 */
async function appendEvidence($, record) {
  const existing = /** @type {Partial<EvidenceLedger> | undefined} */ (await $.store.get(EVIDENCE_KEY))
  /** @type {EvidenceLedger} */
  const ledger = existing && existing.version === 1 && Array.isArray(existing.records)
    ? /** @type {EvidenceLedger} */ (existing)
    : { version: 1, records: [] }
  const previous = ledger.records.at(-1)?.hash ?? null
  const timestampMs = await $.clock.now()
  const payload = {
    sequence: Number(ledger.records.at(-1)?.sequence ?? 0) + 1,
    timestampMs,
    previous,
    ...record,
  }
  const hash = await sha256(stableStringify(payload))
  const records = [...ledger.records, { ...payload, hash }].slice(-MAX_EVIDENCE_RECORDS)
  await $.store.set(EVIDENCE_KEY, { version: 1, records })
}

/**
 * @param {Engine} $
 * @param {ToolCallEvent} e
 * @param {Parameters<ToolCallHook>[2]} next
 */
async function guardToolCall($, e, next) {
  const input = toolInput(e)
  const effect = classifyToolCall(e.tool, input)

  const action = disposition(effect)
  if (action === 'pass') {
    return next(e)
  }

  const bound = await fingerprintEvent(e)
  await appendEvidence($, {
    event: 'governance.classified',
    tool: e.tool,
    effect,
    inputHash: bound.fingerprint,
    decision: 'pending',
  })

  if (action === 'deny') {
    await appendEvidence($, {
      event: 'governance.denied',
      tool: e.tool,
      effect,
      inputHash: bound.fingerprint,
      decision: 'deny_unknown_effect',
    })
    return {
      deny: `Mandare denied unclassified tool ${e.tool}. Add an explicit effect classification before using it.`,
    }
  }

  const review = reviewText(e.tool, bound.input)
  if (review === null) {
    await appendEvidence($, {
      event: 'governance.denied',
      tool: e.tool,
      effect,
      inputHash: bound.fingerprint,
      decision: 'deny_unreviewable',
    })
    return {
      deny: `Mandare denied ${effect}: the invocation is longer than ${MAX_REVIEW_CHARS} characters, too long to show for approval. Split it into smaller calls.`,
    }
  }

  let answer = REFUSE
  try {
    answer = await $.ui.ask(
      `Mandare classified this as ${effect}. Approve this exact invocation once?\n${review}\nsha256:${bound.fingerprint.slice(0, 16)}`,
      [APPROVE, REFUSE],
    )
  } catch {
    // Dismissed, non-interactive, or unavailable UI remains refusal.
  }

  if (answer !== APPROVE) {
    await appendEvidence($, {
      event: 'governance.denied',
      tool: e.tool,
      effect,
      inputHash: bound.fingerprint,
      decision: 'refused_or_unattended',
    })
    return { deny: `Mandare denied ${effect}: this exact invocation was not approved.` }
  }

  await appendEvidence($, {
    event: 'governance.approved',
    tool: e.tool,
    effect,
    inputHash: bound.fingerprint,
    decision: 'approved_once',
  })

  const result = await next(e)
  await appendEvidence($, {
    ...executionOutcome(result),
    tool: e.tool,
    effect,
    inputHash: bound.fingerprint,
  })
  return result
}

/**
 * How an approved call ended beneath the guard, for the evidence record.
 *
 * @param {{ deny?: unknown, isError?: unknown } | undefined} result
 */
function executionOutcome(result) {
  if (result?.deny) return { event: 'execution.denied_downstream', decision: 'downstream_deny' }
  if (result?.isError) return { event: 'execution.failed', decision: 'error' }
  return { event: 'execution.completed', decision: 'completed' }
}

/**
 * Runs in the guard's place when it throws, outruns its budget, or is not run
 * because the call was raised beneath its own frame (re-entry).
 *
 * It must never throw: a handler that throws leaves the hook absent, and an
 * absent tool.call guard fails open. Every path that cannot prove the call is
 * safe to continue answers with a deny.
 *
 * @type {import('claude-code').CatchHandler<ToolCallHook>}
 */
export const failClosed = async ($, e, next) => {
  const kind = String(next?.error?.kind ?? 'unknown')
  try {
    // The guard already passed the call beneath before failing. A deny now would
    // undo nothing, so replay the settled answer instead of misreporting it.
    if (next.called) return next(e)

    // Re-entry: the guard was not run and its own $ calls reject, so no live
    // approval is possible. Only effects that never need approval may continue.
    if (kind === 're-entry') {
      const effect = classifyToolCall(e.tool, toolInput(e))
      if (disposition(effect) === 'pass') return next(e)
      return {
        deny: `Mandare denied ${effect} raised beneath its own guard: no live approval is possible there. No authority was granted.`,
      }
    }
  } catch {
    // Fall through to the deny below.
  }
  return {
    deny: `Mandare governance failed closed before execution: ${kind}. No authority was granted.`,
  }
}

/** @param {import('claude-code').On} on */
export function register(on) {
  on('tool.call', guardToolCall).catch(failClosed)
}
