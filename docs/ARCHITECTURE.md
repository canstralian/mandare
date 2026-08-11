# RIF Runtime Architecture

Agent → Policy Engine → Decision → Reflexive Loop → Posture → Governance Graph → Persistent Memory → Audit API

Trust Model:
- Deny by default (GaC target; see CHANGELOG for legacy engine gaps)
- Environment governed execution
- Reflexive posture adaptation
- Persistent audit trail

**v1.0 diagrams and MVP-vs-target table:** [architecture-v1.md](architecture-v1.md)  
**Contracts:** `spec/events`, `spec/replay`, `spec/governance`  
**Compatibility:** [COMPATIBILITY.md](COMPATIBILITY.md)
