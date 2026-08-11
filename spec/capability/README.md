# spec/capability

Contract for declaring what a capability (agent, device, or skill) is authorized to
do: its authority set, resource pinning, and budgets.

`capability_manifest.schema.json` is migrated unchanged from
`contracts/rif_familiar/capability_manifest.schema.json` — the first concrete
instance of this contract, originally scoped to the RIF Familiar / Field Observer
device. It seeds this directory rather than being rewritten, per ADR-0008's
instruction to migrate existing contracts rather than duplicate them.

Runtime implementation: `src/rif_runtime/mcp/capabilities.py`.
