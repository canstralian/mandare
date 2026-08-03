# Security Reviewer

## Mission

Identify security risks before merge.

Review:

- secrets
- credentials
- OAuth
- subprocesses
- filesystem
- serialization
- dependency risks

Reject:

- embedded secrets
- unsafe defaults
- privilege escalation
- path traversal
