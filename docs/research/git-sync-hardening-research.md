# Git Sync Hardening — Research & Design Decisions

## Why Git?

Git was chosen (and retained after review) as the sync transport because:

1. **Already in place** — proven in production across real drone fleets
2. **Offline-first** — drones can operate with cached code if network is down
3. **Audit trail** — every change has author, timestamp, and diff
4. **Conflict resolution** — built-in merge/rebase tooling
5. **Standard tooling** — SSH keys, branch protection, CI/CD all work natively
6. **Incremental updates** — only diffs are transferred, not full codebase

### Alternatives Considered

| Approach | Pros | Cons | Verdict |
|----------|------|------|---------|
| API-based config push | Real-time, no git dependency | No audit trail, custom sync logic, no offline fallback | Deferred (future TODO) |
| rsync | Simple, fast | No versioning, no conflict handling, no audit | Rejected |
| Container image push | Atomic updates | Heavy (full image per change), slow on cellular | Rejected for config; OK for major releases |
| Ansible/Salt | Mature fleet management | Heavy dependency, complex setup for small teams | Overkill |

## Industry Comparison

| System | Sync Method | Notes |
|--------|-------------|-------|
| Skybrush | Custom binary protocol | Proprietary, tight integration |
| Verge Aero | USB + custom sync | Pre-flight only, no live sync |
| DJI FlightHub | Cloud API | Requires DJI ecosystem |
| GitOps (k8s) | Git + reconciliation loop | Closest analog to our approach |
| ArduPilot Mission Planner | MAVLink parameter download | Per-parameter, not codebase |

Our approach most closely resembles **GitOps** patterns used in Kubernetes fleet management, where git is the single source of truth and agents pull changes.

## Design Decisions

### GCS = Write, Drones = Read-Only
- Prevents drones from accidentally pushing config changes
- GCS is the single point of truth for all configuration
- Drones only pull; if they have local changes, they stash/discard

### SSH for Real Drones, HTTPS for SITL
- Real drones need SSH keys for authenticated pull (private repos)
- SITL containers use HTTPS (public repo, no key management in containers)
- `update_repo_https.sh` archived to `tools/deprecated/` — not used in production

### Structured Exit Status
- Both sync scripts output `GIT_SYNC_RESULT={...}` JSON line
- Enables machine parsing for status tracking without log scraping
- Forward-compatible: additional fields can be added without breaking parsers

### 30-Second Timeout on Git Operations
- Prevents config save from hanging indefinitely on network issues
- Uses SIGALRM for reliable timeout (no thread-based workarounds)
- Each phase (fetch, pull, push) has independent timeout

### Unified `/git-status` Endpoint
- Single endpoint returns both drone statuses and GCS status
- Eliminates separate polling for `/get-gcs-git-status`
- WebSocket sends same transformed structure as REST
- Deprecated endpoints kept for backward compatibility

## Future TODO

- **API-based config push**: Direct config push to drones without requiring git pull (for latency-sensitive changes)
- **Webhook-triggered sync**: GitHub webhook notifies GCS, which auto-triggers drone sync
- **Differential sync**: Only push changed files instead of full git pull
- **Sync health dashboard**: Historical sync success rates, latency graphs
