# Dependency locks

Hash-pinned, fully-resolved dependency sets compiled from `pyproject.toml`.
Every CI job installs from these. Nothing here is edited by hand.

| File | Compiled from | Contents |
|---|---|---|
| `runtime.txt` | `[project.dependencies]` | Runtime set only |
| `dev.txt` | `[project.dependencies]` + `[dev]` extra | Runtime + full toolchain |

## Why hashes

`--generate-hashes` records the digest of every artefact. `pip install
--require-hashes` then refuses anything whose bytes do not match. This is what
makes `pip-audit` and any downstream provenance attestation meaningful: they
describe a resolution CI can actually reproduce, rather than whatever the index
happened to serve that morning.

It also fixes the cache. `actions/setup-python`'s `cache: pip` keys on a
dependency file; pointing it at `pyproject.toml` or `requirements.txt` keys it
on files that hold *ranges*, so the key never changes when an upstream release
does and a job can go green against stale wheels. Every workflow here sets
`cache-dependency-path: requirements/dev.txt`, so the key is the resolution.

## Regenerating

After any change to `[project.dependencies]` or the `[dev]` extra:

```bash
make lock
```

The `lock-sync` job in `.github/workflows/merge-gate.yml` recompiles and fails
on any diff, so a dependency edit that skips this step cannot merge.

`pip-compile` reuses the versions already pinned in the output file unless
`--upgrade` is passed, so regenerating is a no-op when nothing changed. To
deliberately pull in new upstream releases:

```bash
make lock-upgrade
```

## Installing

The editable install is separate and carries `--no-deps` on purpose: pip
rejects a mixed hashed/unhashed requirement set, and an editable install cannot
be hashed. Dependencies come from the lock; the project is layered on top.

```bash
python -m pip install --require-hashes -r requirements/dev.txt
python -m pip install -e . --no-deps
```

## What is deliberately not locked

`requirements.txt` and `requirements-dev.txt` at the repository root stay
unconstrained. They are what the `Dockerfile` and
`scripts/cloud-agent-install.sh` install, and what the `clean-clone` job
installs with no lock and no cache. That job is the only one that sees what a
new consumer resolves today, which is the signal a lock is designed to
suppress. Both paths are tested; they answer different questions.
