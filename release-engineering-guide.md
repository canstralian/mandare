# Release Engineering Guide

## Versioning

Use semantic versioning.

## Release Flow

1. Freeze
2. Validate
3. Tag
4. Build
5. Sign
6. Publish
7. Verify

## Artifacts

- binaries
- containers
- manifests
- checksums
- signatures

## Rollback

- previous tag
- config compatibility
- evidence compatibility
- migration reversal

## Compatibility Matrix

Document:

- runtime
- API
- evidence bundle
- capability manifest
- policy schema

## Post-Release

- smoke test
- replay sample
- telemetry review
- incident watch
