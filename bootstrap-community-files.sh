#!/usr/bin/env bash
set -euo pipefail

mkdir -p .github/ISSUE_TEMPLATE

cat > CONTRIBUTING.md <<'CONTRIB'
# Contributing to RIF Runtime

Thank you for your interest in RIF Runtime.

RIF Runtime is a governance-first execution substrate for intelligent systems...

...
CONTRIB

cat > SECURITY.md <<'SECURITY'
# Security Policy

Security is a primary design objective of RIF Runtime.

...
SECURITY

cat > CODE_OF_CONDUCT.md <<'CODE'
# Code of Conduct

This project adopts the Contributor Covenant Code of Conduct v2.1.

...
CODE

cat > .github/pull_request_template.md <<'PR'
## Summary

Describe the change.

...
PR

cat > .github/ISSUE_TEMPLATE/bug_report.md <<'BUG'
---
name: Bug Report
about: Report incorrect runtime behaviour
---

...
BUG

cat > .github/ISSUE_TEMPLATE/feature_request.md <<'FEATURE'
---
name: Feature Request
about: Suggest an improvement
---

...
FEATURE

cat > .github/ISSUE_TEMPLATE/config.yml <<'CONFIG'
blank_issues_enabled: false

contact_links:
  - name: Questions & Discussions
    url: https://github.com/canstralian/rif-runtime/discussions
    about: Ask questions or discuss ideas.

  - name: Security Reports
    url: https://github.com/canstralian/rif-runtime/security
    about: Report security vulnerabilities privately.
CONFIG

echo "✅ Community health files created."
