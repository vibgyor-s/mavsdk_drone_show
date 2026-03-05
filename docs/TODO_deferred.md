# Deferred TODOs — Drone Identity & Configuration

Items intentionally deferred from the hw_id/pos_id cleanup (2026-03-05).
Each has a corresponding `TODO(deferred)` comment in the code at the referenced location.

---

## TODO 1: Decouple hw_id from MAV_SYS_ID (for >254 drones)

**Priority:** Medium (needed when fleet > 254)
**Status:** Deferred — current fleet uses 1-254 range

**Problem:** `hw_id` is currently set equal to `MAV_SYS_ID` (PX4 parameter). MAVLink system IDs are `uint8` (1-254). If hw_id exceeds 254, it silently truncates on the wire, causing collisions.

**Solution:** Add `mav_sys_id` column to config.csv. `hw_id` becomes a pure software identity (any positive integer). `mav_sys_id` is the MAVLink address (1-254), independently assigned. Consider Skybrush's `SHOW_GROUP` parameter approach for >250 drones.

**Files to modify:**
- `actions.py` — `init_sysid()` function (currently sets `MAV_SYS_ID = HW_ID`)
- `multiple_sitl/startup_sitl.sh` — `MAV_SYS_ID` env variable
- `multiple_sitl/set_sys_id.py` — PX4 rcS modification
- `gcs-server/config.py` — `CONFIG_COLUMNS` add `mav_sys_id`
- `src/drone_config/config_loader.py` — load mav_sys_id from CSV
- `tools/mds_init_lib/common.sh` — `validate_drone_id()` upper bound (currently 999)
- Frontend config editor — add mav_sys_id field

**Reference:** Skybrush Sidekick 1.8.0+ `SHOW_GROUP` extension

---

## TODO 2: Auto-update swarm follow chains on role swap

**Priority:** Medium
**Status:** Deferred — needs UX design for swarm mode interaction

**Problem:** `swarm.csv` `follow` column references `hw_id`. If drone hw_id=2 fails and spare hw_id=10 takes pos_id=2, followers still reference `follow=2` (the dead drone). Operators must manually edit swarm.csv.

**Solution:** When operator changes a drone's pos_id in config.csv (via UI), detect if swarm.csv follow chains reference the old hw_id and offer to auto-update. Options:
- (a) Change `follow` column to reference pos_id instead of hw_id
- (b) Keep hw_id reference but add UI warning + auto-update on role swap
- (c) Option (b) is recommended — minimal data model change, smart UI

**Files to modify:**
- `gcs-server/config.py` — add swarm chain validation in `validate_and_process_config()`
- `gcs-server/app_fastapi.py` — endpoint to update swarm follow chains
- Frontend `SwarmDesign.js` — warning when follow target is offline/replaced
- Frontend `SaveReviewDialog.js` — warn about broken follow chains

---

## TODO 3: Move from CSV to JSON/YAML configuration

**Priority:** Low
**Status:** Deferred — major migration

**Problem:** CSV is fragile (column order dependent, no nesting, no comments, no schema validation, no versioning). Complex config (nested parameters, arrays) cannot be represented.

**Solution:** Migrate to JSON or YAML with schema validation (JSON Schema or Pydantic). Maintain backward-compatible CSV import for migration. Consider TOML for human-editable configs.

**Files to modify:** All config loading/saving code, frontend CSV import/export, documentation.

---

## TODO 4: Central config service (pull-based)

**Priority:** Low
**Status:** Deferred — needs offline fallback design

**Problem:** Each drone reads config.csv from its local filesystem. Config changes require git push + git pull on every drone. Slow for large fleets.

**Solution:** Drones pull config from GCS API on boot. GCS serves as config authority. Drones cache last-known config for offline fallback. Config changes propagate instantly on next heartbeat cycle.

**Files to modify:**
- `src/drone_config/config_loader.py` — add API-based config fetching
- `gcs-server/app_fastapi.py` — add `/drone-config/{hw_id}` endpoint
- `src/heartbeat_sender.py` — include config version hash in heartbeat

---

## TODO 5: Validate config on drone boot

**Priority:** Medium
**Status:** Deferred — needs inter-drone awareness at boot time

**Problem:** A drone boots and reads its config without checking for duplicate pos_ids. Two drones with the same pos_id will both arm and fly identical trajectories, causing mid-air collision.

**Solution:** On startup, after loading config, query GCS for all active drones' pos_ids. If collision detected, refuse to arm and show clear error. Alternative: GCS validates and blocks command submission if duplicates exist (partially implemented in `validate_and_process_config()`).

**Files to modify:**
- `src/drone_config/__init__.py` — add boot-time validation
- `coordinator.py` — fail-safe check before entering ready state
- `gcs-server/app_fastapi.py` — add `/validate-drone/{hw_id}` endpoint
