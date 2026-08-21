# Dependency locks

The repository maintains two generated, hash-pinned dependency sets compiled from `pyproject.toml`:

| File | Contents |
|---|---|
| `runtime.txt` | Runtime dependencies |
| `dev.txt` | Runtime dependencies plus the development toolchain |

The locked CI jobs install these with `pip install --require-hashes`. The `clean-clone` job intentionally does **not** use the locks; it tests what a fresh consumer resolves from the declared ranges.

## Why hashes

`pip-compile --generate-hashes` records artefact digests. `pip install --require-hashes` then refuses an artefact whose digest is not present in the lock.

This improves reproducibility of the locked CI path. It is not by itself a complete software-supply-chain provenance system.

## Regenerate

After changing project dependencies:

```bash
make lock
```

The `lock-sync` job in `.github/workflows/merge-gate.yml` recompiles both locks and fails if the working tree changes.

To deliberately resolve newer versions within the declared ranges:

```bash
make lock-upgrade
```

## Install the locked environment

```bash
python -m pip install --require-hashes -r requirements/dev.txt
python -m pip install -e . --no-deps
```

The editable project install is layered separately because the local project itself is not a hashed wheel in this workflow.

## Unconstrained consumer path

The repository also retains root-level `requirements.txt` and `requirements-dev.txt` for the unconstrained installation path used by the clean-clone workflow and container/bootstrap paths.

This creates two deliberate signals:

- **locked path:** can the repository reproduce the exact dependency resolution it has chosen?
- **unconstrained path:** does the project still work against current upstream resolutions?

Both matter, and neither should be mistaken for a signed or independently attested software supply chain.
