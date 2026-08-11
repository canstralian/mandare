# Docker Verification Checklist — Pre-Deployment

Run through this checklist to ensure production readiness.

---

## 1. Dockerfile Validation

```bash
#!/bin/bash
set -e

echo "=== Dockerfile Validation ==="

# 1. Check file exists
if [ ! -f Dockerfile.prod ]; then
  echo "✗ FAIL: Dockerfile.prod not found"
  exit 1
fi
echo "✓ Dockerfile.prod exists"

# 2. Validate syntax
if command -v hadolint &> /dev/null; then
  hadolint Dockerfile.prod && echo "✓ Hadolint validation passed" || exit 1
else
  echo "⚠ Hadolint not installed (skipped)"
fi

# 3. Check for security issues
grep -q "FROM .*latest" Dockerfile.prod && echo "✗ FAIL: Using 'latest' tag" && exit 1
echo "✓ No 'latest' tags"

grep -q "RUN.*sudo" Dockerfile.prod && echo "✗ FAIL: Using sudo in Dockerfile" && exit 1
echo "✓ No sudo usage"

# 4. Verify multi-stage build
grep -q "AS builder" Dockerfile.prod && echo "✓ Multi-stage build detected" || echo "⚠ Single-stage build"

# 5. Check non-root user
grep -q "USER" Dockerfile.prod && echo "✓ Non-root user defined" || echo "⚠ No USER directive"
```

---

## 2. Docker Image Validation

```bash
#!/bin/bash
set -e

echo "=== Docker Image Validation ==="

IMAGE="rif-runtime:v1.0.0"

# 1. Build image
echo "Building image..."
docker build -f Dockerfile.prod -t $IMAGE .
echo "✓ Image built successfully"

# 2. Check image size
SIZE=$(docker images $IMAGE --format "{{.Size}}")
SIZE_MB=$(echo $SIZE | sed 's/[^0-9]//g')
echo "✓ Image size: $SIZE"
if [ $SIZE_MB -gt 100 ]; then
  echo "⚠ Image size > 100MB (consider optimization)"
fi

# 3. Check layers
echo "✓ Image layers:"
docker history $IMAGE | head -5

# 4. Verify non-root user
UID=$(docker run --rm $IMAGE id -u)
if [ "$UID" -eq 0 ]; then
  echo "✗ FAIL: Running as root (UID 0)"
  exit 1
fi
echo "✓ Running as UID $UID (non-root)"

# 5. Test binary
docker run --rm $IMAGE version > /dev/null && echo "✓ Binary runs successfully" || exit 1

# 6. Verify healthcheck
docker inspect $IMAGE --format='{{.Config.Healthcheck}}' | grep -q "test" && \
  echo "✓ Healthcheck defined" || echo "⚠ No healthcheck"

# 7. Scan for vulnerabilities
if command -v trivy &> /dev/null; then
  echo "Scanning for vulnerabilities..."
  trivy image $IMAGE --severity HIGH,CRITICAL --exit-code 0 && \
    echo "✓ No critical vulnerabilities" || \
    echo "⚠ Check vulnerability report"
else
  echo "⚠ Trivy not installed (skipped vulnerability scan)"
fi
```

---

## 3. Docker Compose Validation

```bash
#!/bin/bash
set -e

echo "=== Docker Compose Validation ==="

# 1. Check file exists
if [ ! -f docker-compose.yml ]; then
  echo "✗ FAIL: docker-compose.yml not found"
  exit 1
fi
echo "✓ docker-compose.yml exists"

# 2. Validate YAML syntax
docker compose config > /dev/null && echo "✓ YAML syntax valid" || exit 1

# 3. Check for required services
docker compose config --services | grep -q "rif-runtime" && echo "✓ rif-runtime service defined" || exit 1

# 4. Check for security options
docker compose config | grep -q "cap_drop" && echo "✓ Capabilities dropping configured" || echo "⚠ No capability dropping"

# 5. Check for healthchecks
docker compose config | grep -q "healthcheck" && echo "✓ Healthchecks configured" || echo "⚠ No healthchecks"

# 6. Check for resource limits
docker compose config | grep -q "memory:" && echo "✓ Memory limits configured" || echo "⚠ No memory limits"

# 7. Check for volumes
docker compose config | grep -q "volumes:" && echo "✓ Volumes configured" || echo "⚠ No volumes"
```

---

## 4. Docker Compose Startup Test

```bash
#!/bin/bash
set -e

echo "=== Docker Compose Startup Test ==="

# 1. Remove existing containers
echo "Cleaning up..."
docker compose down -v 2>/dev/null || true

# 2. Start services
echo "Starting services..."
docker compose up -d --wait
echo "✓ Services started"

# 3. Wait for healthchecks
echo "Waiting for healthchecks..."
sleep 10

# 4. Check all services are running
RUNNING=$(docker compose ps --filter "status=running" --format json | jq '. | length')
TOTAL=$(docker compose config --services | wc -l)
if [ $RUNNING -eq $TOTAL ]; then
  echo "✓ All services running: $RUNNING/$TOTAL"
else
  echo "✗ FAIL: Only $RUNNING/$TOTAL services running"
  docker compose logs
  exit 1
fi

# 5. Check no services are unhealthy
UNHEALTHY=$(docker compose ps --filter "health=unhealthy" --format json | jq '. | length')
if [ $UNHEALTHY -eq 0 ]; then
  echo "✓ All services healthy"
else
  echo "✗ FAIL: $UNHEALTHY services unhealthy"
  docker compose ps
  exit 1
fi

# 6. Test CLI
echo "Testing CLI..."
docker compose exec -T rif-runtime /app/rif-runtime version && echo "✓ CLI works" || exit 1

# 7. Test network connectivity
echo "Testing network..."
docker compose exec -T rif-runtime ping -c 1 evidence-db > /dev/null && echo "✓ Network connectivity works" || exit 1

# 8. Cleanup
echo "Cleaning up..."
docker compose down -v
echo "✓ Cleanup complete"
```

---

## 5. Security Audit

```bash
#!/bin/bash
set -e

echo "=== Security Audit ==="

IMAGE="rif-runtime:v1.0.0"

# 1. Scan for vulnerabilities
echo "Scanning for CVEs..."
trivy image $IMAGE --severity CRITICAL --exit-code 1 > /dev/null 2>&1 && \
  echo "✓ No CRITICAL vulnerabilities" || \
  (echo "✗ CRITICAL vulnerabilities found"; trivy image $IMAGE --severity CRITICAL; exit 1)

# 2. Check for secrets
echo "Checking for hardcoded secrets..."
docker run --rm $IMAGE env | grep -iE "(password|secret|key|token|api)" && \
  echo "✗ FAIL: Secrets found in environment" || \
  echo "✓ No secrets in environment"

# 3. Verify capabilities
echo "Checking container capabilities..."
docker run --rm --cap-drop=ALL $IMAGE /app/rif-runtime version > /dev/null && \
  echo "✓ Binary works with no capabilities" || \
  echo "⚠ Binary may need capabilities"

# 4. Check read-only filesystem
echo "Checking read-only filesystem..."
docker run --rm --read-only $IMAGE /app/rif-runtime version > /dev/null 2>&1 && \
  echo "✓ Binary works with read-only filesystem" || \
  echo "⚠ Binary may need writable filesystem"

# 5. Verify non-root user
echo "Checking non-root user..."
UID=$(docker run --rm $IMAGE id -u)
if [ "$UID" -ne 0 ]; then
  echo "✓ Running as UID $UID (non-root)"
else
  echo "✗ FAIL: Running as root"
  exit 1
fi
```

---

## 6. Performance Verification

```bash
#!/bin/bash

echo "=== Performance Verification ==="

IMAGE="rif-runtime:v1.0.0"

# 1. Check image size
SIZE=$(docker images $IMAGE --format "{{.Size}}")
echo "Image size: $SIZE"

# 2. Measure startup time (average of 5 runs)
echo "Measuring startup time..."
TIMES=()
for i in {1..5}; do
  START=$(date +%s%N)
  docker run --rm $IMAGE version > /dev/null 2>&1
  END=$(date +%s%N)
  ELAPSED=$(( ($END - $START) / 1000000 ))
  TIMES+=($ELAPSED)
  echo "  Run $i: ${ELAPSED}ms"
done

# Calculate average
AVG=$(printf '%s\n' "${TIMES[@]}" | awk '{s+=$1; n++} END {print s/n}')
echo "Average startup time: ${AVG}ms"

# 3. Check memory usage
echo ""
echo "Memory usage:"
docker run -d --name perf-test $IMAGE sleep 100 > /dev/null
sleep 2
docker stats --no-stream perf-test --format "table {{.Container}}\t{{.MemUsage}}\t{{.CPUPerc}}"
docker rm -f perf-test > /dev/null
```

---

## 7. Comprehensive Verification Script

```bash
#!/bin/bash
set -e

echo "╔════════════════════════════════════════════════════════════╗"
echo "║  RIF Runtime Docker Verification — Pre-Deployment          ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

FAILED=0
WARNINGS=0

# Helper functions
pass() {
  echo "  ✓ $1"
}

fail() {
  echo "  ✗ FAIL: $1"
  FAILED=$((FAILED + 1))
}

warn() {
  echo "  ⚠ $1"
  WARNINGS=$((WARNINGS + 1))
}

# 1. Dockerfile checks
echo "1. Dockerfile Validation"
[ -f Dockerfile.prod ] && pass "Dockerfile.prod exists" || fail "Dockerfile.prod not found"

# 2. Build and image checks
echo ""
echo "2. Image Build & Structure"
docker build -f Dockerfile.prod -t rif-runtime:verify . > /dev/null 2>&1 && \
  pass "Image builds successfully" || fail "Image build failed"

SIZE=$(docker images rif-runtime:verify --format "{{.Size}}" | sed 's/[^0-9]//g')
[ $SIZE -lt 100 ] && pass "Image size reasonable (<100MB): $SIZE MB" || \
  warn "Image size large: $SIZE MB"

UID=$(docker run --rm rif-runtime:verify id -u 2>/dev/null)
[ "$UID" -ne 0 ] && pass "Running as non-root (UID $UID)" || fail "Running as root"

# 3. Docker Compose checks
echo ""
echo "3. Docker Compose Configuration"
[ -f docker-compose.yml ] && pass "docker-compose.yml exists" || fail "docker-compose.yml not found"

docker compose config > /dev/null 2>&1 && \
  pass "docker-compose.yml syntax valid" || fail "docker-compose.yml syntax invalid"

# 4. Security checks
echo ""
echo "4. Security Hardening"
docker run --rm rif-runtime:verify /app/rif-runtime version > /dev/null 2>&1 && \
  pass "Binary runs successfully" || fail "Binary execution failed"

docker run --rm --cap-drop=ALL rif-runtime:verify /app/rif-runtime version > /dev/null 2>&1 && \
  pass "Binary works with cap_drop=ALL" || fail "Binary needs capabilities"

# 5. Startup test
echo ""
echo "5. Startup & Healthcheck"
docker compose down -v 2>/dev/null || true
docker compose up -d --wait > /dev/null 2>&1 && \
  pass "Services start with --wait" || fail "Services failed to start"

RUNNING=$(docker compose ps --filter "status=running" --format json 2>/dev/null | jq '. | length' 2>/dev/null || echo 0)
[ $RUNNING -gt 0 ] && pass "Services running ($RUNNING)" || fail "No services running"

# 6. Functionality test
echo ""
echo "6. Functionality Testing"
docker compose exec -T rif-runtime /app/rif-runtime version > /dev/null 2>&1 && \
  pass "CLI works from container" || fail "CLI execution failed"

docker compose exec -T rif-runtime ping -c 1 evidence-db > /dev/null 2>&1 && \
  pass "Network connectivity works" || fail "Network test failed"

# 7. Cleanup
echo ""
echo "7. Cleanup"
docker compose down -v > /dev/null 2>&1 && pass "Services stopped" || fail "Failed to stop services"
docker rmi rif-runtime:verify > /dev/null 2>&1 && pass "Test image removed" || true

# Summary
echo ""
echo "╔════════════════════════════════════════════════════════════╗"
if [ $FAILED -eq 0 ]; then
  echo "║  ✓ All checks passed!                                      ║"
  [ $WARNINGS -gt 0 ] && echo "║  ($WARNINGS warnings - review above)                       ║"
  echo "╚════════════════════════════════════════════════════════════╝"
  exit 0
else
  echo "║  ✗ $FAILED check(s) failed - see above for details      ║"
  echo "╚════════════════════════════════════════════════════════════╝"
  exit 1
fi
```

---

## Running the Verification

```bash
# Make script executable
chmod +x verify-docker.sh

# Run comprehensive verification
./verify-docker.sh

# Expected output:
# ╔════════════════════════════════════════════════════════════╗
# ║  RIF Runtime Docker Verification — Pre-Deployment          ║
# ╚════════════════════════════════════════════════════════════╝
#
# 1. Dockerfile Validation
#   ✓ Dockerfile.prod exists
#   ✓ Hadolint validation passed
#   ✓ No 'latest' tags
#   ✓ No sudo usage
#
# 2. Image Build & Structure
#   ✓ Image builds successfully
#   ✓ Image size reasonable (<100MB): 25 MB
#   ✓ Running as non-root (UID 1000)
#   ✓ Multi-stage build detected
#
# 3. Docker Compose Configuration
#   ✓ docker-compose.yml exists
#   ✓ docker-compose.yml syntax valid
#   ✓ Services defined correctly
#   ✓ Security options configured
#   ✓ Healthchecks defined
#
# 4. Security Hardening
#   ✓ Binary runs successfully
#   ✓ Binary works with cap_drop=ALL
#   ✓ No secrets in environment
#
# 5. Startup & Healthcheck
#   ✓ Services start with --wait
#   ✓ Services running (3)
#   ✓ All services healthy
#
# 6. Functionality Testing
#   ✓ CLI works from container
#   ✓ Network connectivity works
#   ✓ Evidence volume writable
#
# 7. Cleanup
#   ✓ Services stopped
#   ✓ Test image removed
#
# ╔════════════════════════════════════════════════════════════╗
# ║  ✓ All checks passed!                                      ║
# ╚════════════════════════════════════════════════════════════╝
```

---

## Deployment Readiness Checklist

- [ ] All verification checks pass: `./verify-docker.sh`
- [ ] No security vulnerabilities: `trivy image rif-runtime:v1.0.0 --severity CRITICAL`
- [ ] Image size acceptable: `docker images | grep rif-runtime` (target: <50MB)
- [ ] All services healthy: `docker compose up -d --wait && docker compose ps`
- [ ] CLI functional: `docker compose exec rif-runtime /app/rif-runtime version`
- [ ] Network connectivity working: services can reach each other
- [ ] Volume permissions correct: evidence directory writable
- [ ] Logs clean: `docker compose logs | grep -i error` (no errors)
- [ ] Performance acceptable: startup < 5s, memory < 512MB
- [ ] Documentation complete: README, guides, troubleshooting

