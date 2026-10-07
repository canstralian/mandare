import { Effect, approvalSummary, classifyToolCall, stableStringify, toolInput } from './classify-effect.js'

const EVIDENCE_KEY = 'mandare.governance.evidence.v1'
const GUARDED_EFFECTS = new Set([Effect.EXTERNAL_WRITE, Effect.DESTRUCTIVE, Effect.UNKNOWN])
const MAX_EVIDENCE_RECORDS = 512
const APPROVE = 'Approve once'
const REFUSE = 'Refuse'

async function sha256(value) {
  const bytes = new TextEncoder().encode(value)
  const digest = await crypto.subtle.digest('SHA-256', bytes)
  return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, '0')).join('')
}

async function fingerprintEvent(e) {
  const input = toolInput(e)
  const canonical = stableStringify({
    tool: e.tool,
    toolUseId: e.tool_use_id ?? null,
    input,
  })
  return { input, fingerprint: await sha256(canonical) }
}

async function appendEvidence($, record) {
  const existing = await $.store.get(EVIDENCE_KEY)
  const ledger = existing && existing.version === 1 && Array.isArray(existing.records)
    ? existing
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

async function guardToolCall($, e, next) {
  const input = toolInput(e)
  const effect = classifyToolCall(e.tool, input)

  if (!GUARDED_EFFECTS.has(effect)) {
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

  if (effect === Effect.UNKNOWN) {
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

  let answer = REFUSE
  try {
    const summary = approvalSummary(e.tool, bound.input)
    answer = await $.ui.ask(
      `Mandare classified this as ${effect}. Approve this exact invocation once?\n${summary}\nsha256:${bound.fingerprint.slice(0, 16)}`,
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
    event: result?.deny ? 'execution.denied_downstream' : result?.isError ? 'execution.failed' : 'execution.completed',
    tool: e.tool,
    effect,
    inputHash: bound.fingerprint,
    decision: result?.deny ? 'downstream_deny' : result?.isError ? 'error' : 'completed',
  })
  return result
}

/**
 * Runs in the guard's place when it throws, outruns its budget, or is not run
 * because the call was raised beneath its own frame (re-entry).
 *
 * It must never throw: a handler that throws leaves the hook absent, and an
 * absent tool.call guard fails open. Every path that cannot prove the call is
 * safe to continue answers with a deny.
 */
export async function failClosed($, e, next) {
  const kind = String(next?.error?.kind ?? 'unknown')
  try {
    // The guard already passed the call beneath before failing. A deny now would
    // undo nothing, so replay the settled answer instead of misreporting it.
    if (next.called) return next(e)

    // Re-entry: the guard was not run and its own $ calls reject, so no live
    // approval is possible. Only effects that never need approval may continue.
    if (kind === 're-entry') {
      const effect = classifyToolCall(e.tool, toolInput(e))
      if (!GUARDED_EFFECTS.has(effect)) return next(e)
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

export function register(on) {
  on('tool.call', guardToolCall).catch(failClosed)
}
