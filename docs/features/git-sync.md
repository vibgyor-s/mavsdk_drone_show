# Git Sync System

## Architecture Overview

The MDS git sync system uses git as the transport mechanism to keep code and configuration synchronized between the GCS (Ground Control Station) server and the drone fleet.

```
GCS Server (write/push via SSH)
    |
    v
GitHub Repository (central source of truth)
    |
    v
Drones (read/pull only)
  - Real drones: SSH (via update_repo_ssh.sh)
  - SITL containers: HTTPS (inline in startup_sitl.sh)
```

## Access Model

| Role | Protocol | Access | Script |
|------|----------|--------|--------|
| GCS Server | SSH | Read + Write (push) | `gcs-server/utils.py` `git_operations()` |
| Real Drones | SSH | Read only (pull) | `tools/update_repo_ssh.sh` |
| SITL Containers | HTTPS | Read only (pull) | `multiple_sitl/startup_sitl.sh` `update_repository()` |

## Sync Trigger Paths

| Trigger | When | What Happens |
|---------|------|-------------|
| Boot service | Drone startup | `update_repo_ssh.sh` runs via systemd service |
| UI "Sync Drones" button | Operator-initiated | `POST /sync-repos` sends `UPDATE_CODE` (Mission 103) to drones |
| UI "Save & Commit" button | Config/swarm save | `git_operations()` commits + pushes on GCS |
| UPDATE_CODE command | GCS command | Drone runs `actions.py --action=update_code` which calls `update_repo_ssh.sh` |

## Auto-Commit on Config Save

When `GIT_AUTO_PUSH` is enabled (default), saving configuration or swarm data via the dashboard automatically:

1. Stages all changes
2. Commits with a descriptive message (e.g., `config: update config.csv via dashboard (10 drones updated)`)
3. Rebases on top of remote changes
4. Pushes to origin

The commit result (hash or error) is returned to the frontend and displayed in a toast notification.

A 30-second timeout protects against network hangs during fetch/pull/push operations.

## Monitoring: Git Status Polling

1. GCS polls each drone's `/get-git-status` endpoint (via `git_status.py` background thread)
2. Results are aggregated and transformed into `DroneGitStatus` objects
3. Available via:
   - REST: `GET /git-status` (includes `gcs_status` field for GCS repo status)
   - WebSocket: `/ws/git-status` (same transformed structure, 5-second interval)
4. Frontend shows:
   - Per-drone sync status in `DroneGitStatus` component
   - GCS repo info in `GitInfo` component (uses unified `/git-status` endpoint)
   - Warning banner (`SyncWarningBanner`) on all pages when drones are out of sync

## Sync Warning Banner

An amber warning banner appears on all dashboard pages when any drones are out of sync with GCS:

```
[warning] X of Y drones out of sync with GCS  [Sync Now]  [x]
```

- Auto-dismisses when all drones sync
- Re-appears if new drones go out of sync
- Operator can manually dismiss (non-blocking)
- "Sync Now" button triggers `POST /sync-repos`

## Structured Sync Results

Both `update_repo_ssh.sh` and `startup_sitl.sh` output a machine-parseable result line:

```
GIT_SYNC_RESULT={"success":true,"branch":"main-candidate","commit":"abc1234","message":"feat: example commit","duration":5}
```

This is parsed by `actions.py` for logging and status tracking.

## Error States and Recovery

| Error | Cause | Recovery |
|-------|-------|----------|
| Push timeout | Network issue | GCS retries on next save; check connectivity |
| Push permission denied | Missing SSH key | Add deploy key with write access (see gcs-setup.md) |
| Push rejected (non-fast-forward) | Remote diverged | Pull and resolve conflicts |
| HTTPS remote detected | GCS using HTTPS | Switch to SSH remote for push access |
| Merge conflict on rebase | Concurrent edits | Auto-resolved: abort rebase, reset, retry |
| Fetch timeout on drone | Network issue | Graceful degradation: drone continues with cached code |

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/git-status` | GET | Aggregated drone git status + GCS status |
| `/sync-repos` | POST | Trigger UPDATE_CODE on drones |
| `/ws/git-status` | WebSocket | Real-time git status stream |
| `/get-gcs-git-status` | GET | (Deprecated) Use `/git-status` instead |
| `/get-drone-git-status/{id}` | GET | (Deprecated) Use `/git-status` instead |

## Files

### GCS Server
- `gcs-server/utils.py` - `git_operations()`: commit, rebase, push with timeout
- `gcs-server/git_status.py` - Background polling, `check_git_sync_status()`
- `gcs-server/app_fastapi.py` - REST/WebSocket endpoints, `/sync-repos` implementation
- `gcs-server/schemas.py` - Pydantic models for git status data
- `functions/git_manager.py` - `get_local_git_report()`, `get_remote_git_status()`

### Drone Side
- `src/drone_api_server.py` - `/get-git-status` endpoint
- `actions.py` - `update_code()` action handler
- `tools/update_repo_ssh.sh` - SSH-based git sync script (production)

### SITL
- `multiple_sitl/startup_sitl.sh` - `update_repository()` with retry/jitter

### Frontend
- `src/components/SyncWarningBanner.js` - Out-of-sync warning banner
- `src/components/ControlButtons.js` - "Sync Drones" button
- `src/components/GitInfo.js` - GCS git info display
- `src/components/DroneGitStatus.js` - Per-drone git status card
- `src/utilities/utilities.js` - URL helpers (`getSyncReposURL`, `getUnifiedGitStatusURL`)
