from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from .evidence import EvidenceLedger
from .governance.posture import posture_for_denials
from .graph.memory import GovernanceGraph
from .schemas import PolicyDecision


@dataclass
class RecoveredState:
    historical_decisions: int
    historical_denials: int
    graph_nodes: int
    graph_edges: int
    last_posture: str


@dataclass
class ReplayVerification:
    """Integrity report for a decisions.jsonl forensic pass.

    Does not mutate live runtime state. ``deterministic`` is true when two
    independent recovers from the same snapshot yield identical RecoveredState.
    ``chain_ok`` reflects the additive v1 hash-chain (legacy-only logs pass).
    """

    row_count: int
    valid_decisions: int
    invalid_rows: int
    errors: list[str] = field(default_factory=list)
    recovered: RecoveredState | None = None
    deterministic: bool = False
    chain_ok: bool = True
    legacy_rows: int = 0
    v1_rows: int = 0

    def as_dict(self) -> dict[str, Any]:
        out = asdict(self)
        return out


class ReplayEngine:
    def __init__(self, decisions_path: str = "data/decisions.jsonl"):
        self.decisions_path = Path(decisions_path)

    def _rows(self) -> list[dict[str, Any]]:
        import json

        if not self.decisions_path.exists():
            return []

        rows: list[dict[str, Any]] = []
        for line_no, line in enumerate(
            self.decisions_path.read_text(encoding="utf-8").splitlines(),
            start=1,
        ):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                # Surface corrupt lines later via verify(); recover() still
                # needs a clean snapshot, so re-raise with location.
                raise ValueError(
                    f"invalid JSON in {self.decisions_path} at line {line_no}: {exc}"
                ) from exc
        return rows

    def replay_graph(self, rows: list[dict[str, Any]] | None = None) -> GovernanceGraph:
        """Rebuild the governance graph, optionally from an already-loaded log.

        Passing ``rows`` lets a caller that has already read the decision log
        reuse that snapshot instead of re-reading the file.
        """
        graph = GovernanceGraph()
        for row in self._rows() if rows is None else rows:
            graph.record_decision(self._decision_from_row(row))
        return graph

    def recover(self) -> RecoveredState:
        # Read the log once and derive both the counts and the graph from that
        # single snapshot: decisions.jsonl is appended to concurrently, so two
        # separate reads could report totals that disagree with each other.
        rows = self._rows()
        graph = self.replay_graph(rows)
        denials = sum(1 for row in rows if row.get("decision") == "deny")
        return RecoveredState(
            historical_decisions=len(rows),
            historical_denials=denials,
            graph_nodes=graph.summary()["nodes"],
            graph_edges=graph.summary()["edges"],
            last_posture=posture_for_denials(denials).value,
        )

    def verify(self) -> ReplayVerification:
        """Validate every row, hash-chain causality, and recover() determinism.

        Invalid rows are reported explicitly (no silent skip). Callers that
        need a hard gate can assert
        ``invalid_rows == 0 and deterministic and chain_ok``.
        """
        import json

        errors: list[str] = []
        valid = 0
        row_count = 0

        if not self.decisions_path.exists():
            empty = RecoveredState(0, 0, 0, 0, posture_for_denials(0).value)
            return ReplayVerification(
                row_count=0,
                valid_decisions=0,
                invalid_rows=0,
                errors=[],
                recovered=empty,
                deterministic=True,
                chain_ok=True,
                legacy_rows=0,
                v1_rows=0,
            )

        for line_no, line in enumerate(
            self.decisions_path.read_text(encoding="utf-8").splitlines(),
            start=1,
        ):
            if not line.strip():
                continue
            row_count += 1
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                errors.append(f"line {line_no}: JSONDecodeError: {exc}")
                continue
            try:
                self._decision_from_row(row)
                valid += 1
            except (ValidationError, KeyError, TypeError, ValueError) as exc:
                errors.append(f"line {line_no}: {type(exc).__name__}: {exc}")

        invalid = row_count - valid
        recovered: RecoveredState | None = None
        deterministic = False
        chain_ok = False
        legacy_rows = 0
        v1_rows = 0

        if invalid == 0:
            # Chain walk requires a clean JSON snapshot; skip when row parse
            # already failed so corrupt lines are reported once, explicitly.
            chain = EvidenceLedger(self.decisions_path).verify_chain()
            legacy_rows = chain.legacy_rows
            v1_rows = chain.v1_rows
            chain_ok = chain.chain_ok
            if not chain_ok:
                errors.extend(chain.errors)

            first = self.recover()
            second = self.recover()
            recovered = first
            deterministic = first == second
            if not deterministic:
                errors.append(
                    f"non-deterministic recover(): first={first!r} second={second!r}"
                )

        return ReplayVerification(
            row_count=row_count,
            valid_decisions=valid,
            invalid_rows=invalid,
            errors=errors,
            recovered=recovered,
            deterministic=deterministic,
            chain_ok=chain_ok,
            legacy_rows=legacy_rows,
            v1_rows=v1_rows,
        )

    def _decision_from_row(self, row: dict[str, Any]) -> PolicyDecision:
        # model_validate preserves persisted timestamps (and accepts both ISO
        # and the legacy space-separated form from json.dumps(..., default=str)).
        # Additive v1 envelope fields are ignored by PolicyDecision (extra=ignore).
        return PolicyDecision.model_validate(row)
