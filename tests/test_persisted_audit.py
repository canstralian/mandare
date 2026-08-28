from mandare.runtime import MandareRuntime
from mandare.schemas import PolicyRequest


def test_persisted_summary_counts_decisions():
    r = MandareRuntime()
    r.evaluate(
        PolicyRequest(
            actor="agent:test",
            action="http.request",
            target="https://api.anthropic.com",
        )
    )
    summary = r.persisted_summary()
    assert summary["decisions_total"] >= 1
    assert "allow" in summary["decisions_by_result"]


def test_audit_summary_has_live_and_persisted_sections():
    r = MandareRuntime()
    audit = r.audit_summary()
    assert "live" in audit
    assert "persisted" in audit
    assert "environment" in audit
