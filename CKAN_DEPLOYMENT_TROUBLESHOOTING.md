# CKAN ARM64 Deployment: Troubleshooting & Solutions

## Context
- **Platform:** Mac ARM64 (Apple Silicon)
- **Stack:** CKAN 2.10.x, Solr, PostgreSQL, Redis, Dashboard (Docker Compose)

## Main Issues & Solutions

### 1. Solr/CKAN Connectivity & ARM64 Compatibility
- **Problem:** Solr container not ready or not ARM64 compatible, CKAN fails to connect.
- **Solution:**
  - Built a custom Solr ARM64 image with the correct CKAN schema.xml.
  - Added a `wait-for-solr.sh` script to ensure CKAN starts only after Solr is healthy.

### 2. CKAN Web UI Not Accessible (API OK)
- **Problem:** CKAN API endpoint worked, but the web UI was not visible. Logs showed `PermissionError: [Errno 13] Permission denied: '/var/lib/ckan/default'`.
- **Root Cause:** Docker volume `/var/lib/ckan` was root-owned, so CKAN (running as non-root) could not write cache/assets.
- **Solution:**
  - Patched Dockerfile to create the directory, but volume mount still caused root ownership.
  - Patched entrypoint (`wait-for-solr.sh`) to `chown -R ckan:ckan /var/lib/ckan` at every container start.
  - Added `gosu` to Dockerfile and used `exec gosu ckan "$@"` to run CKAN as the correct user.

### 3. Healthchecks & Robustness
- **Problem:** Healthchecks for Solr and CKAN were unreliable.
- **Solution:**
  - Simplified and tuned healthchecks for all services.
  - Ensured all dependencies (Solr, DB, Redis) are healthy before CKAN starts.

### 4. Port Mapping & uWSGI
- **Problem:** uWSGI was not listening on the correct interface/port.
- **Solution:**
  - Set uWSGI to listen on `0.0.0.0:5000` in `ckan-uwsgi.ini`.
  - Docker Compose maps `5001:5000` for host access.

## Key Files Changed
- `ckan-src/docker/Dockerfile`: Added `gosu`, fixed permissions, improved build for ARM64.
- `ckan-src/docker/wait-for-solr.sh`: Now fixes volume permissions and runs CKAN as `ckan` user.
- `ckan-src/ckan-uwsgi.ini`: Ensures uWSGI listens on all interfaces.
- `docker-compose.yml`: Ensures correct port mapping and healthchecks.

## Final Checklist
- [x] CKAN API and web UI accessible at http://localhost:5001
- [x] Dashboard accessible at http://localhost:8501
- [x] All containers healthy and robust to restarts
- [x] All fixes and documentation committed and pushed to GitHub

## Lessons Learned
- Always fix permissions for Docker volumes at runtime, not just build time.
- Use `gosu` or `su-exec` to run as the correct user in containers.
- Healthchecks and wait scripts are essential for multi-service orchestration.
- Document every error and solution for future reproducibility.

---

For more details, see commit history and comments in the Dockerfile and entrypoint scripts.
