import { Effect, approvalSummary, classifyToolCall, stableStringify, toolInput } from './classify-effect.js'

const EVIDENCE_KEY = 'mandare.governance.evidence.v1'
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

  if (![Effect.EXTERNAL_WRITE, Effect.DESTRUCTIVE, Effect.UNKNOWN].includes(effect)) {
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

export function register(on) {
  on('tool.call', guardToolCall).catch(async ($, e, next) => {
    return {
      deny: `Mandare governance failed closed before execution: ${next.error.kind}. No authority was granted.`,
    }
  })
}
