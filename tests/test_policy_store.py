from rif_runtime.configuration.policies import PolicyRule, PolicyStore


def test_policy_store_upsert_and_delete(tmp_path):
    store = PolicyStore(str(tmp_path / "policies.json"))

    rule = PolicyRule(
        id="test_rule",
        effect="deny",
        action="http.request",
        target="example.com",
    )

    store.upsert(rule)
    assert any(r.id == "test_rule" for r in store.list())

    assert store.delete("test_rule") is True
    assert not any(r.id == "test_rule" for r in store.list())
