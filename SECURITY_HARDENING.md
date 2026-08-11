# Security Hardening Guide for RIF Runtime

## 1. Container Capabilities (Principle of Least Privilege)

### Drop ALL, Add Back Only What's Needed

In `docker-compose.yml`:

```yaml
cap_drop:
  - ALL
cap_add:
  - NET_BIND_SERVICE  # Only if binding to port < 1024
```

**Why**: By default, containers have dangerous capabilities like:
- CAP_SYS_ADMIN: Can mount filesystems, read kernel memory
- CAP_NET_ADMIN: Can modify network settings
- CAP_SYS_MODULE: Can load kernel modules

**RIF Runtime needs**: None (runs as user 1000, doesn't need special capabilities)

### Verify Capabilities:

```bash
docker inspect rif-runtime-server --format='{{.HostConfig.CapAdd}}'
docker inspect rif-runtime-server --format='{{.HostConfig.CapDrop}}'
```

---

## 2. Read-Only Root Filesystem

### In docker-compose.yml:

```yaml
rif-runtime:
  read_only: true
  tmpfs:
    - /tmp
    - /app/evidence  # If writing to filesystem
```

**Why**: Prevents attackers from modifying system files or installing malware.

**Trade-off**: Application must write to `/tmp` or volumes; cannot modify root FS.

**For RIF Runtime**:
- ✅ Binary is read-only (good)
- ✅ Evidence stored in volume (good)
- ✅ Configuration from volumes (good)

### Verify:

```bash
docker run --rm -it rif-runtime:v1.0.0 sh -c "touch /file-test" 2>&1 | grep "Permission denied"
```

Should fail with "Permission denied".

---

## 3. Non-Root User

### Dockerfile:

```dockerfile
RUN adduser -D -u 1000 -s /sbin/nologin rif
USER rif
```

**Why**: 
- Limits damage if container is compromised
- Cannot escalate to root
- Cannot access sensitive system files

**Verify**:

```bash
docker run rif-runtime:v1.0.0 id
# Output: uid=1000(rif) gid=1000(rif) groups=1000(rif)
```

---

## 4. Security Options

### In docker-compose.yml:

```yaml
rif-runtime:
  security_opt:
    # Prevent new privilege escalation via setuid/setgid
    - no-new-privileges:true
```

**Why**: Prevents privilege escalation through setuid binaries or sudo-like mechanisms.

---

## 5. Image Scanning for Vulnerabilities

### Using Trivy (Recommended):

```bash
# Install Trivy (macOS)
brew install aquasecurity/trivy/trivy

# Scan image for vulnerabilities
trivy image rif-runtime:v1.0.0

# Output:
# rif-runtime:v1.0.0 (alpine 3.19)
# ================================
# Total: 0 vulnerabilities
```

### Using Grype (Alternative):

```bash
# Install Grype
curl -sSfL https://raw.githubusercontent.com/anchore/grype/main/install.sh | sh -s -- -b /usr/local/bin

# Scan
grype rif-runtime:v1.0.0
```

### In CI/CD (GitHub Actions Example):

```yaml
- name: Run Trivy scan
  uses: aquasecurity/trivy-action@master
  with:
    image-ref: rif-runtime:v1.0.0
    format: sarif
    output: trivy-results.sarif
    severity: CRITICAL,HIGH

- name: Upload Trivy results
  uses: github/codeql-action/upload-sarif@v2
  with:
    sarif_file: trivy-results.sarif
```

---

## 6. Base Image Security

### Keep Alpine Updated:

```dockerfile
# Good: pinned to minor version (security updates included)
FROM alpine:3.19

# Avoid: floating tag (unpredictable)
# FROM alpine:latest

# Avoid: too-old version (many vulnerabilities)
# FROM alpine:3.10
```

### Use Alpine Security Advisory:

```bash
# Check for known CVEs in Alpine packages
curl -s https://secdb.alpinelinux.org/ | jq '.[] | select(.pkgname == "ca-certificates")'
```

### Multi-Stage Dockerfile Reduces Attack Surface:

```dockerfile
# Good: only runtime dependencies in final image
FROM golang:1.21-alpine AS builder
# ... build ...

FROM alpine:3.19
COPY --from=builder /build/rif-runtime /app/rif-runtime
# builder stage discarded; no build tools in final image
```

---

## 7. Secret Management

### ❌ WRONG: Hardcoding Secrets in Dockerfile

```dockerfile
# DON'T DO THIS
ENV DB_PASSWORD=supersecret123
RUN echo "password=${DB_PASSWORD}" > /app/config.txt
```

**Why**: Secrets are baked into the image and visible to anyone with access.

### ✅ RIGHT: Docker Secrets (Swarm Mode)

```bash
# Create secret
echo "supersecret123" | docker secret create db_password -

# Use in docker-compose.yml
secrets:
  db_password:
    external: true

services:
  rif-runtime:
    secrets:
      - db_password
    environment:
      # Secret mounted to /run/secrets/db_password
      - DB_PASSWORD_FILE=/run/secrets/db_password
```

### ✅ RIGHT: Environment Variables (Kubernetes/Cloud)

```bash
# Pass at runtime
docker run -e DB_PASSWORD="$(pass show db/prod)" rif-runtime:v1.0.0
```

### ✅ RIGHT: External Vault (HashiCorp Vault, AWS Secrets Manager)

```go
// In application code
secret, err := vault.GetSecret("database/password")
```

### ✅ RIGHT: .env File (Development Only)

```bash
# .env file (never committed)
DB_PASSWORD=dev-password

# Load in compose
docker compose up  # Loads .env automatically
```

---

## 8. Network Security

### Isolate Containers with Bridge Network:

```yaml
networks:
  rif-network:
    driver: bridge

services:
  rif-runtime:
    networks:
      - rif-network
  evidence-db:
    networks:
      - rif-network
```

**Why**: 
- Containers can talk to each other by name
- Containers on other networks cannot access these services
- Prevents lateral movement in case of compromise

### Verify Network Isolation:

```bash
docker network inspect rif-runtime_rif-network
# Containers on network are isolated from others
```

### Disable Host Network Access:

```yaml
# DON'T USE (security risk)
network_mode: host

# USE (default, safer)
networks:
  - rif-network
```

**Why**: `host` mode bypasses network isolation; container can sniff all host traffic.

---

## 9. Registry Security

### Use Private Registry for Proprietary Images:

```bash
# Login to private registry
docker login docker.io

# Tag image with registry
docker tag rif-runtime:v1.0.0 docker.io/myorg/rif-runtime:v1.0.0

# Push to registry
docker push docker.io/myorg/rif-runtime:v1.0.0

# Pull from registry
docker pull docker.io/myorg/rif-runtime:v1.0.0
```

### Sign Images (Docker Content Trust):

```bash
# Enable DCT
export DOCKER_CONTENT_TRUST=1

# Sign and push
docker push myorg/rif-runtime:v1.0.0
# Prompts for signing key

# Verify signature on pull
docker pull myorg/rif-runtime:v1.0.0
```

---

## 10. Logging & Monitoring

### Centralized Logging:

```yaml
rif-runtime:
  logging:
    driver: "awslogs"  # or splunk, datadog, etc.
    options:
      awslogs-group: "/ecs/rif-runtime"
      awslogs-region: "us-east-1"
      awslogs-stream-prefix: "ecs"
```

**Why**: Logs outside container; cannot be deleted by attacker.

### Docker Event Monitoring:

```bash
# Monitor container events in real-time
docker events --filter type=container

# In another terminal, restart container
docker restart rif-runtime-server
# See: container restart event in first terminal
```

---

## 11. Security Checklist

Run this before production deployment:

```bash
#!/bin/bash
set -e

IMAGE="rif-runtime:v1.0.0"

echo "=== Security Audit for $IMAGE ==="

# 1. Scan for vulnerabilities
echo "✓ Scanning for vulnerabilities..."
trivy image "$IMAGE" --severity HIGH,CRITICAL --exit-code 1

# 2. Check for non-root user
echo "✓ Checking non-root user..."
UID=$(docker run --rm "$IMAGE" id -u)
if [ "$UID" -ne 0 ]; then
  echo "  ✓ Running as UID $UID (non-root)"
else
  echo "  ✗ FAIL: Running as root"
  exit 1
fi

# 3. Check for read-only filesystem
echo "✓ Checking read-only filesystem..."
docker run --rm "$IMAGE" touch /test-file 2>&1 | grep -q "Permission denied" && \
  echo "  ✓ Root filesystem is read-only" || \
  echo "  ⚠ Root filesystem is writable"

# 4. Check base image
echo "✓ Checking base image..."
BASE=$(docker inspect "$IMAGE" --format='{{index .RepoDigests 0}}')
echo "  Base image: $BASE"

# 5. Verify layers
echo "✓ Checking image layers..."
LAYERS=$(docker inspect "$IMAGE" --format='{{len .RootFS.Layers}}')
echo "  Total layers: $LAYERS"

# 6. Check for secrets
echo "✓ Checking for secrets in image..."
docker run --rm "$IMAGE" env | grep -iE "(password|secret|key|token)" && \
  echo "  ✗ FAIL: Secrets found in environment" || \
  echo "  ✓ No secrets in environment"

echo ""
echo "=== Security Audit Complete ==="
```

---

## 12. Runtime Security in Production

### Use Docker Security Scanning:

```bash
# Enable vulnerability scanning (Docker Hub)
# 1. Go to https://hub.docker.com/r/myorg/rif-runtime/settings
# 2. Enable "Vulnerability Scanning"
# 3. Images are scanned on push
```

### AppArmor/SELinux (Linux Host):

```bash
# Create AppArmor profile
cat > /etc/apparmor.d/docker-rif-runtime <<EOF
#include <tunables/global>

profile docker-rif-runtime flags=(attach_disconnected,mediate_deleted) {
  #include <abstractions/base>
  capability setuid,
  capability setgid,
  deny @{HOME}/.ssh/** rwkl,
  deny @{HOME}/.gnupg/** rwkl,
}
EOF

# Load profile
apparmor_parser -r /etc/apparmor.d/docker-rif-runtime

# Use in docker-compose.yml
security_opt:
  - apparmor=docker-rif-runtime
```

---

## Summary of Security Best Practices

| Practice | Implementation | Benefit |
|----------|----------------|---------|
| Drop CAPs | `cap_drop: [ALL]` | Prevent privilege escalation |
| Non-root | `USER rif` | Limit damage from compromise |
| Read-only FS | `read_only: true` | Prevent malware installation |
| No new privs | `no-new-privileges:true` | Block setuid escalation |
| Scan images | `trivy image` | Detect CVEs early |
| Secrets management | Docker secrets or vault | Prevent credential leakage |
| Network isolation | Custom bridge network | Prevent lateral movement |
| Logging | Centralized logging | Detect and audit attacks |
| Runtime monitoring | Docker events | Real-time security alerts |

