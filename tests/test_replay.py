from pathlib import Path

import pytest

from rif_runtime.replay import ReplayEngine

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "replay"


@pytest.mark.parametrize(
    ("fixture_name", "decisions", "denials", "nodes", "edges", "posture"),
    [
        ("empty.jsonl", 0, 0, 0, 0, "normal"),
        ("normal.jsonl", 2, 0, 4, 2, "normal"),
        ("elevated.jsonl", 4, 3, 5, 4, "elevated"),
        ("restricted.jsonl", 11, 10, 13, 11, "restricted"),
        ("locked.jsonl", 21, 20, 23, 21, "locked"),
    ],
)
def test_recover_from_fixture(
    fixture_name: str,
    decisions: int,
    denials: int,
    nodes: int,
    edges: int,
    posture: str,
) -> None:
    state = ReplayEngine(str(FIXTURES / fixture_name)).recover()

    assert state.historical_decisions == decisions
    assert state.historical_denials == denials
    assert state.graph_nodes == nodes
    assert state.graph_edges == edges
    assert state.last_posture == posture


def test_recover_missing_file_returns_empty_state(tmp_path: Path) -> None:
    state = ReplayEngine(str(tmp_path / "missing.jsonl")).recover()

    assert state.historical_decisions == 0
    assert state.historical_denials == 0
    assert state.graph_nodes == 0
    assert state.graph_edges == 0
    assert state.last_posture == "normal"


def test_replay_graph_accepts_preloaded_rows() -> None:
    engine = ReplayEngine(str(FIXTURES / "normal.jsonl"))
    rows = engine._rows()

    graph = engine.replay_graph(rows)

    assert graph.summary() == {"nodes": 4, "edges": 2}
