# Execution Contracts

## ExecutionManifest

Immutable description of an execution.

## ExecutionRecord

Immutable execution outcome.

## AgentResult

Output of exactly one Agent Stage.

## EffectRecord

Immutable receipt proving an external mutation.

## ExecutionReceipt

Canonical receipt for completed execution.

## ReplayReport

Verification that replay reproduced recorded history.

## EvidenceBundle

Collection of runtime artifacts generated during execution.

## Runtime Rules

- Every execution has one manifest.
- Every stage produces one artifact.
- Every effect produces one EffectRecord.
- Replay never re-executes Agent or Effect stages.
- Evidence is append-only.
