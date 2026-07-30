"""The governance circuit is shared across FastAPI's sync threadpool.

Every decision must land exactly once in the log, and posture must end on the
rung the denial volume implies -- no lost updates from interleaved
read-modify-write of self.posture.
"""

from concurrent.futures import ThreadPoolExecutor

from rif_runtime.configuration.policies import PolicyRule, PolicyStore
from rif_runtime.configuration.store import JsonStore
from rif_runtime.runtime import RIFRuntime
from rif_runtime.schemas import PolicyRequest, Posture
from rif_runtime.storage.jsonl import JsonlStore


def _isolated_runtime(tmp_path) -> RIFRuntime:
    runtime = RIFRuntime()
    runtime.decisions_store = JsonlStore(tmp_path / "decisions.jsonl")
    runtime.posture_store = JsonlStore(tmp_path / "posture_history.jsonl")
    runtime.evidence_store = JsonlStore(tmp_path / "evidence.jsonl")
    return runtime


def test_concurrent_evaluations_record_every_decision(tmp_path):
    runtime = _isolated_runtime(tmp_path)
    total = 60

    def evaluate(i: int):
        return runtime.evaluate(
            PolicyRequest(
                actor=f"agent:{i}",
                action="http.request",
                target=f"https://blocked{i}.example.com",
            )
        )

    with ThreadPoolExecutor(max_workers=12) as pool:
        decisions = list(pool.map(evaluate, range(total)))

    assert len(decisions) == total
    assert runtime.decisions_store.count() == total
    # 60 denials in the window puts the runtime at the top of the ladder.
    assert runtime.posture == Posture.locked


def test_concurrent_evaluations_produce_a_monotonic_posture_history(tmp_path):
    runtime = _isolated_runtime(tmp_path)

    def evaluate(i: int):
        return runtime.evaluate(
            PolicyRequest(
                actor="agent:test",
                action="http.request",
                target=f"https://blocked{i}.example.com",
            )
        )

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(evaluate, range(40)))

    rows = runtime.posture_store.read_all()
    ladder = [p.value for p in Posture]
    ranks = [ladder.index(row["new_posture"]) for row in rows]
    assert ranks == sorted(ranks), f"posture history de-escalated: {rows}"
    # Each transition's old_posture must be the previous row's new_posture.
    for previous, current in zip(rows, rows[1:]):
        assert current["old_posture"] == previous["new_posture"]


def test_concurrent_policy_upserts_do_not_lose_rules(tmp_path):
    store = PolicyStore(str(tmp_path / "policies.json"))
    rule_count = 40

    def upsert(i: int):
        return store.upsert(
            PolicyRule(
                id=f"rule_{i}",
                effect="deny",
                action="http.request",
                target=f"host{i}.example.com",
            )
        )

    with ThreadPoolExecutor(max_workers=12) as pool:
        list(pool.map(upsert, range(rule_count)))

    ids = {rule.id for rule in store.list()}
    assert {f"rule_{i}" for i in range(rule_count)} <= ids


def test_json_store_concurrent_writes_never_raise(tmp_path):
    # JsonStore is the shared atomic-write helper. A fixed "<name>.tmp" scratch
    # file let one writer rename the file another was about to rename, raising
    # FileNotFoundError; each write now gets its own temp file.
    store = JsonStore(tmp_path / "state.json", {"rules": []})

    def write(i: int) -> None:
        store.write({"rules": [{"id": f"rule_{i}"}]})

    with ThreadPoolExecutor(max_workers=12) as pool:
        list(pool.map(write, range(60)))

    # Whichever writer landed last, the file is complete and parseable -- never
    # truncated or half-written -- and no stray temp files remain.
    assert store.read()["rules"][0]["id"].startswith("rule_")
    assert list(tmp_path.glob("*.tmp")) == []
