# Debugging & Troubleshooting Guide

## Common Issues & Solutions

---

## Issue 1: Container Exits Immediately

### Symptom:
```bash
$ docker run rif-runtime:v1.0.0 run --policy policy.yaml
# Container starts and exits instantly
$ docker ps -a
# STATUS: Exited (1) 2 seconds ago
```

### Diagnosis Workflow:

#### Step 1: Check Exit Code
```bash
# Get the exit code
docker inspect $(docker ps -lq) --format='{{.State.ExitCode}}'
# Exit codes:
# 0 = success
# 1 = runtime error
# 2 = usage error
# 3 = policy violation
# non-zero = failure
```

#### Step 2: Read Container Logs
```bash
# View logs from last container
docker logs $(docker ps -aq | head -1)

# Follow logs in real-time (if container still running)
docker logs -f rif-runtime-server

# View last 50 lines
docker logs --tail 50 rif-runtime-server

# Timestamps for debugging
docker logs --timestamps rif-runtime-server
```

#### Step 3: Inspect Container Details
```bash
# Full container inspection
docker inspect rif-runtime-server

# Specific fields
docker inspect --format='{{.State}}' rif-runtime-server
docker inspect --format='{{.Config.Cmd}}' rif-runtime-server
docker inspect --format='{{.HostConfig.RestartPolicy}}' rif-runtime-server

# Mount information
docker inspect --format='{{range .Mounts}}{{.Source}}→{{.Destination}}{{"\n"}}{{end}}' rif-runtime-server
```

#### Step 4: Check Environment Variables
```bash
# View environment inside container
docker run --rm rif-runtime:v1.0.0 env | sort

# Compare with expected
docker run --rm -e LOG_LEVEL=debug rif-runtime:v1.0.0 env | grep LOG_LEVEL
```

#### Step 5: Test Command Directly
```bash
# Run with verbose output
docker run -it rif-runtime:v1.0.0 run --policy /nonexistent/policy.yaml

# Run with bash for debugging
docker run -it --entrypoint /bin/sh rif-runtime:v1.0.0
$ cd /app && ls -la
$ ./rif-runtime version
```

### Common Causes & Fixes:

| Cause | Symptom | Fix |
|-------|---------|-----|
| **Missing input file** | `file not found` error | `docker run -v $(pwd)/policy.yaml:/etc/rif/policies/policy.yaml:ro` |
| **Wrong ENTRYPOINT** | Binary not found | Verify `ENTRYPOINT ["/app/rif-runtime"]` in Dockerfile |
| **Invalid arguments** | Exit code 2 (usage) | `docker run rif-runtime:v1.0.0 --help` to check syntax |
| **Permission denied** | File not readable | `docker run -u 0` to run as root; check volume permissions |
| **Out of memory** | Exit code 137 (OOM) | Increase `deploy.resources.limits.memory` in compose |

---

## Issue 2: Network Connectivity Between Containers

### Symptom:
```bash
# Container A tries to reach Container B
$ docker exec rif-runtime-server curl http://evidence-db:5432
# curl: (7) Failed to connect to evidence-db port 5432: Connection refused
```

### Diagnosis Workflow:

#### Step 1: Check Network Connectivity
```bash
# List all networks
docker network ls

# Inspect custom network
docker network inspect rif-runtime_rif-network

# Show connected containers
# Look for "Containers" section with all services
```

#### Step 2: Verify Containers are on Same Network
```bash
# Check which networks each container uses
docker inspect rif-runtime-server --format='{{.NetworkSettings.Networks}}'
docker inspect rif-evidence-db --format='{{.NetworkSettings.Networks}}'

# Both should show: map[rif-runtime_rif-network:...]
```

#### Step 3: Test DNS Resolution
```bash
# From rif-runtime container, resolve evidence-db
docker exec rif-runtime-server nslookup evidence-db

# Should return something like:
# Server: 127.0.0.11
# Address: 127.0.0.11#53
# Name: evidence-db
# Address: 172.25.0.3
```

#### Step 4: Test Connectivity with Ping
```bash
# Ping from rif-runtime to evidence-db
docker exec rif-runtime-server ping -c 3 evidence-db

# Should get responses:
# PING evidence-db (172.25.0.3) 56(84) bytes of data.
# 64 bytes from 172.25.0.3 (...): icmp_seq=1 time=0.123 ms
```

#### Step 5: Test Port Connectivity
```bash
# Install curl if needed
docker exec rif-runtime-server apk add --no-cache curl

# Test HTTP endpoint
docker exec rif-runtime-server curl -v http://evidence-db:5432

# Test with nc (netcat)
docker exec rif-runtime-server apk add --no-cache netcat-openbsd
docker exec rif-runtime-server nc -zv evidence-db 5432
```

#### Step 6: Check Firewall Rules
```bash
# On host machine, verify port is not blocked
sudo iptables -L -n | grep 5432

# Check if Docker daemon is routing traffic correctly
docker network inspect --verbose rif-runtime_rif-network
```

### Common Causes & Fixes:

| Cause | Symptom | Fix |
|-------|---------|-----|
| **Different networks** | Cannot resolve hostname | Both services must have `networks: [rif-network]` |
| **Container not running** | Connection refused | `docker compose up -d` to start |
| **Port not exposed** | Cannot connect | Add `ports: ["5432:5432"]` to compose (for internal only, use volume) |
| **Service not listening** | Connection refused | Check service logs: `docker logs evidence-db` |
| **Firewall blocking** | No route to host | Disable firewall or add rule |
| **DNS not resolving** | Name or service unknown | Restart docker daemon: `sudo systemctl restart docker` |

### Manual Network Test:

```bash
# Create test containers on same network
docker run -d --name test1 --network rif-runtime_rif-network alpine sleep 1000
docker run -d --name test2 --network rif-runtime_rif-network alpine sleep 1000

# Test connectivity
docker exec test1 ping test2

# Cleanup
docker rm -f test1 test2
```

---

## Issue 3: Volume Permission Issues

### Symptom:
```bash
$ docker compose up
# Error: permission denied while trying to connect to Docker daemon socket

# Or:
# Container cannot write to volume
# Error: /app/evidence: permission denied
```

### Diagnosis Workflow:

#### Step 1: Check Volume Mounts
```bash
# List all mounts
docker inspect rif-runtime-server --format='{{range .Mounts}}{{.Source}}→{{.Destination}} ({{.Mode}}){{"\n"}}{{end}}'

# Example output:
# /home/user/data/evidence→/app/evidence (rw)
# /home/user/config/policies→/etc/rif/policies (ro)
```

#### Step 2: Check Host Permissions
```bash
# Check directory ownership
ls -la /home/user/data/evidence

# Should show something like:
# drwxr-xr-x 2 user user 4096 Jan 15 10:00 evidence

# Check file permissions
ls -la /home/user/data/evidence/file.json
```

#### Step 3: Check Container User
```bash
# Inside container, check current user
docker exec rif-runtime-server id
# uid=1000(rif) gid=1000(rif) groups=1000(rif)

# Check if user can write
docker exec rif-runtime-server touch /app/evidence/test.txt
```

#### Step 4: Check Directory Permissions on Host
```bash
# Check if host directory is readable by container user
stat /home/user/data/evidence

# Container user is UID 1000; host user should also be UID 1000
whoami
id

# If different, fix with chown
sudo chown 1000:1000 /home/user/data/evidence
```

### Common Causes & Fixes:

| Cause | Symptom | Fix |
|-------|---------|-----|
| **Host dir not writable** | Permission denied | `chmod 755 /path/to/evidence` or `sudo chown 1000:1000 /path/to/evidence` |
| **Container user wrong UID** | Cannot write as rif | `RUN adduser -D -u 1000 rif` in Dockerfile |
| **Volume mounted read-only** | Cannot write even as root | Remove `:ro` flag: `/etc/rif/policies:/etc/rif/policies:rw` |
| **SELinux/AppArmor blocking** | Permission denied even with correct perms | `docker run --security-opt label=disable` |
| **Volume owned by root** | Container cannot access | `docker compose exec rif-runtime-server sudo chown rif:rif /app/evidence` |

### Fix Permission Issues:

```bash
# On host machine
mkdir -p ./data/evidence
chmod 755 ./data/evidence
sudo chown $UID:$UID ./data/evidence

# Or run container as root to create/fix permissions
docker run --rm -u root -v $(pwd)/data:/data alpine sh -c "chown -R 1000:1000 /data"

# Verify
docker compose exec -u root rif-runtime-server chown rif:rif /app/evidence
```

---

## Issue 4: Image Build Failures

### Symptom:
```bash
$ docker compose build
# ERROR: failed to solve with frontend dockerfile.v0: failed to read dockerfile: 
# open /var/lib/docker/tmp/docker-build-XYZ/Dockerfile: no such file or directory
```

### Diagnosis Workflow:

#### Step 1: Check Build Context
```bash
# Verify Dockerfile exists
ls -la Dockerfile.prod

# Check .dockerignore for accidental exclusions
cat .dockerignore | grep -E "^go\.mod|^\.git"
```

#### Step 2: Verify Build Arguments
```bash
# Print build args
docker compose config | grep -A5 "args:"

# Test build manually
docker build --progress=plain -f Dockerfile.prod .
```

#### Step 3: Check for Layer Cache Issues
```bash
# Rebuild without cache
docker compose build --no-cache rif-runtime

# Clean dangling images
docker image prune -a
```

#### Step 4: Validate Dockerfile Syntax
```bash
# Validate syntax
hadolint Dockerfile.prod

# Or manually check:
grep -E "^(FROM|RUN|COPY|ADD|WORKDIR|USER)" Dockerfile.prod
```

### Common Causes & Fixes:

| Cause | Symptom | Fix |
|-------|---------|-----|
| **File not in build context** | COPY fails | `ls` the file; check `.dockerignore` |
| **Wrong working directory** | COPY path error | Verify `WORKDIR /build` before `COPY` |
| **Insufficient disk space** | Build fails silently | `docker system df` to check; `docker system prune` to clean |
| **Network timeout** | Cannot download packages | `docker compose build --no-cache` to retry; check internet |
| **Out of memory** | Build fails with OOM | Increase Docker memory: Docker Desktop → Preferences → Resources |
| **go.mod not in build context** | Module not found | `COPY go.mod ./` must be in build directory |

### Clean Build:

```bash
# Remove all Docker artifacts
docker system prune -a --volumes

# Rebuild from scratch
docker compose build --no-cache rif-runtime

# Verify image
docker images | grep rif-runtime
```

---

## Issue 5: Container Health Check Failures

### Symptom:
```bash
$ docker compose up
# rif-runtime-server status: unhealthy

$ docker ps
# STATUS: Up 2 minutes (unhealthy)
```

### Diagnosis Workflow:

#### Step 1: Check Health Status
```bash
# Detailed health status
docker inspect rif-runtime-server --format='{{.State.Health}}'

# Shows:
# {HealthStatus:unhealthy FailingStreak:3 Log:[...]}
```

#### Step 2: View Health Check Logs
```bash
# Last 5 health checks
docker inspect rif-runtime-server --format='{{range .State.Health.Log}}{{.Output}}{{"\n"}}{{end}}'
```

#### Step 3: Manual Health Check
```bash
# Manually run the healthcheck command
docker exec rif-runtime-server /app/rif-runtime version

# See actual output and exit code
echo $?  # 0 = success, non-zero = failed
```

#### Step 4: Check Service Status
```bash
# Is the service actually running?
docker exec rif-runtime-server ps aux | grep rif-runtime

# Can it respond to requests?
docker exec rif-runtime-server curl -v http://localhost:8000/health
```

### Common Causes & Fixes:

| Cause | Symptom | Fix |
|-------|---------|-----|
| **Service not ready** | Health check fails immediately | Increase `start_period` in healthcheck |
| **Port not listening** | Cannot connect to health endpoint | Check service logs; verify port in Dockerfile |
| **Wrong health check command** | Command exits with non-zero | Test command manually: `docker exec ... <command>` |
| **Timeout too short** | Intermittent failures | Increase `timeout` in healthcheck |

### Fix Health Checks:

```yaml
# In docker-compose.yml
healthcheck:
  test: ["CMD", "/app/rif-runtime", "version"]
  interval: 30s
  timeout: 10s           # Increased from 5s
  retries: 5             # Increased from 3
  start_period: 30s      # Increased from 10s
```

---

## General Debugging Commands

### View Container Output in Real-Time
```bash
docker logs -f rif-runtime-server --tail 50
```

### Execute Commands Inside Container
```bash
# Interactive shell
docker exec -it rif-runtime-server /bin/sh

# Single command
docker exec rif-runtime-server env | sort
docker exec rif-runtime-server ls -la /app
```

### Inspect Network Namespace
```bash
# Container's network interfaces
docker exec rif-runtime-server ip addr show

# Container's routing table
docker exec rif-runtime-server ip route show

# Open ports
docker exec rif-runtime-server netstat -tlnp
```

### Monitor Resource Usage
```bash
# Live resource stats
docker stats rif-runtime-server

# Shows: CPU %, memory usage, network I/O, block I/O
```

### Debugging with Docker Compose
```bash
# Validate compose file
docker compose config

# Dry run (don't actually start)
docker compose up --dry-run

# Verbose logging
docker compose -v up

# Specific service logs
docker compose logs evidence-db
```

### Interactive Debugging
```bash
# Start container with shell instead of running the app
docker run -it --entrypoint /bin/sh rif-runtime:v1.0.0

# Inside the container
$ ls -la /app
$ cat /app/rif-runtime | file -  # Check binary format
$ /app/rif-runtime --help        # Test the binary
```

---

## Troubleshooting Checklist

- [ ] Container is running: `docker ps | grep rif-runtime-server`
- [ ] Check logs: `docker logs rif-runtime-server`
- [ ] Verify exit code: `docker inspect ... --format='{{.State.ExitCode}}'`
- [ ] Test network connectivity: `docker exec rif-runtime-server ping evidence-db`
- [ ] Check volume mounts: `docker exec rif-runtime-server ls -la /app/evidence`
- [ ] Verify environment: `docker exec rif-runtime-server env | grep LOG_LEVEL`
- [ ] Test healthcheck: `docker exec rif-runtime-server /app/rif-runtime version`
- [ ] Check resource limits: `docker stats rif-runtime-server`
- [ ] Validate compose file: `docker compose config`
- [ ] Review security options: `docker inspect --format='{{.HostConfig}}'`

