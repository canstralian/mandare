# Semgrep workflow remediation

## Evidence and disposition

Baseline: head `cdd3f966cc5451f6242fd7c2032f093b337d87e6`, synthetic merge `12fee511194500ad432803d0e373adbf202f6292`, [Semgrep run 42535062789](https://github.com/canstralian/mandare/actions/runs/42535062789). The full scan reported 35 findings: 34 mutable action references across nine workflows and one low-confidence masking audit warning. The run retains its original SARIF for seven days.

All 34 mutable references are replaced with verified upstream commit SHAs. Each keeps the same action major version and inputs. Annotated tags were peeled to their commit objects; a tag-object SHA is not used as an action pin. Dependency Review's v4 reference is an upstream branch, not a tag. Previously immutable action references remain unchanged.

The exact `yaml.github-actions.security.audit.unsafe-add-mask-workflow-command.unsafe-add-mask-workflow-command` warning in `image.yml` is a source-specific audit false positive. Its rule matches every `add-mask` directive and describes malicious workflow code stopping runner command processing. This source creates a new 16-byte random OpenSSL nonce, encoded as 32 hexadecimal characters, solely for the per-run smoke container. It is not a stored repository, production, or provider credential, and is not attacker-controlled input. The same job provisions and consumes this nonce; code already able to execute in that job does not gain access to a separate credential authority from this mask directive. Masking remains intact as defense in depth. A preceding comment suppresses only this exact rule at this one directive; no rule pack, file or directory is excluded. Reassess this exception if the source becomes a reusable or external credential.

The scanner now uses `--error` so unsuppressed findings fail its step. A temporary synthetic workflow containing a mutable reference and an unreviewed mask directive must produce both rules and exit status 1 before the repository scan runs. The fixture is never executed as a workflow and is removed afterward. Finding summaries, retained SARIF and GitHub SARIF upload still run after scanner failure. Scan packs remain `p/python`, `p/security-audit`, `p/secrets` and `p/github-actions`.

## Verified pin provenance

| Action reference | Commit SHA | Upstream reference |
| --- | --- | --- |
| gitleaks/gitleaks-action@v2 | `ff98106e4c7b2bc287b24eaf42907196329070c7` | [refs/tags/v2](https://github.com/gitleaks/gitleaks-action/tree/v2) |
| aquasecurity/trivy-action@v0.36.0 | `ed142fd0673e97e23eac54620cfb913e5ce36c25` | [refs/tags/v0.36.0](https://github.com/aquasecurity/trivy-action/tree/v0.36.0) |
| docker/setup-buildx-action@v3 | `8d2750c68a42422c14e847fe6c8ac0403b4cbd6f` | [refs/tags/v3](https://github.com/docker/setup-buildx-action/tree/v3) |
| actions/setup-python@v6 | `ece7cb06caefa5fff74198d8649806c4678c61a1` | [refs/tags/v6](https://github.com/actions/setup-python/tree/v6) |
| codecov/codecov-action@v5 | `0fb7174895f61a3b6b78fc075e0cd60383518dac` | [refs/tags/v5](https://github.com/codecov/codecov-action/tree/v5) |
| actions/setup-python@v5 | `a26af69be951a213d495a4c3e4e4022e16d87065` | [refs/tags/v5](https://github.com/actions/setup-python/tree/v5) |
| actions/checkout@v4 | `11d5960a326750d5838078e36cf38b85af677262` | [refs/tags/v4](https://github.com/actions/checkout/tree/v4) |
| docker/build-push-action@v6 | `10e90e3645eae34f1e60eeb005ba3a3d33f178e8` | [refs/tags/v6](https://github.com/docker/build-push-action/tree/v6) |
| github/codeql-action@v4 | `33d7b85da1a04171e211befe2c739303b9a4c066` | [refs/tags/v4](https://github.com/github/codeql-action/tree/v4) |
| actions/checkout@v6 | `d23441a48e516b6c34aea4fa41551a30e30af803` | [refs/tags/v6](https://github.com/actions/checkout/tree/v6) |
| softprops/action-gh-release@v2 | `3bb12739c298aeb8a4eeaf626c5b8d85266b0e65` | [refs/tags/v2](https://github.com/softprops/action-gh-release/tree/v2) |
| actions/upload-artifact@v4 | `ea165f8d65b6e75b540449e92b4886f43607fa02` | [refs/tags/v4](https://github.com/actions/upload-artifact/tree/v4) |
| actions/dependency-review-action@v4 | `2031cfc080254a8a887f58cffee85186f0e49e48` | [refs/heads/v4](https://github.com/actions/dependency-review-action/tree/v4) |

Upstream action metadata was retrieved at each commit (Trivy uses `action.yaml`; the others use `action.yml`). Pinning fixes action identity, not transitive downloads, runtime dependencies, or the security of upstream code.

## Validation boundary

Local validation checks YAML syntax, exact pin mappings, unchanged workflow structure apart from intended Semgrep enforcement/evidence additions and the single audit annotation, and shell syntax. The GitHub Semgrep run must establish the actual final finding count and exit status; workflow presence is not a passing scan. Build and smoke, other scanners and Merge Gate require results tied to the final head. Release and bootstrap workflows are not dispatched by this remediation. No merge, release or deployment is authorized by a passing scan.
