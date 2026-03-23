# Smart Swarm Guide

**Mission Type:** `2` (`SMART_SWARM`)  
**Primary UI Surface:** `Swarm Design` page  
**Runtime Model:** live leader-follower formation with saved follow chains and in-flight reassignment

## Overview

Smart Swarm is the live, cooperative formation mode in MDS. Each drone uses a saved `swarm.json` assignment:

- `hw_id` identifies the physical drone
- `follow` identifies the drone it should follow by **hardware ID**
- `offset_x`, `offset_y`, `offset_z` define the relative formation offset
- `frame` controls whether offsets are interpreted in `ned` or `body`

Unlike the time-synchronized **Swarm Trajectory** mode, Smart Swarm is designed for live clustered operations where operators may change leaders, offsets, frames, or relay roles while drones are airborne.

## Operator Model

Smart Swarm now has two clean command scopes:

### 1. Single-drone commands

Use the normal drone action controls when you want to affect only one aircraft.

Examples:
- send `RTL` to one drone
- send `LAND` to one drone
- send a new mission to one drone

These commands stay scoped to that drone. They do **not** automatically cancel Smart Swarm on other drones.

### 2. Swarm runtime commands

Use the `Smart Swarm Runtime` panel on the `Swarm Design` page when the intent is live Smart Swarm control:

- `Start Smart Swarm`
- `Stop Swarm (Hold)`
- `Land Swarm`
- `RTL Swarm`

The runtime panel supports:

- `Selected Drone`
- `Selected Cluster`

This keeps swarm intent explicit instead of overloading the generic command sender with swarm-only controls, and it preserves mixed-mission operations when only part of the fleet is flying Smart Swarm.

## Runtime Behavior

### Mission start

When Smart Swarm starts, each drone:

1. loads the local fleet config
2. refreshes the latest swarm assignment from GCS
3. decides whether it is a top leader or follower
4. starts follower tasks only if it is configured as a follower

This avoids stale local `swarm_sitl.json` assignments at startup.

### Dynamic reassignment

During flight, the runtime periodically refreshes assignments from GCS. Supported live changes include:

- changing the followed leader
- changing offsets
- switching between `ned` and `body`
- switching a drone between leader and follower roles

When a drone transitions back into follower mode, the runtime now explicitly re-establishes offboard control and restarts any missing follower tasks instead of assuming the previous follower runtime is still healthy.

### Leader-loss handling

Current default policy: `upstream_or_hold`

If a follower loses its direct leader:

- if the failed leader was itself following another leader, the follower adopts that upstream leader
- if no safe upstream leader exists, the drone self-promotes to an independent leader and enters `HOLD`

Leader-loss handling now treats both cases as degraded leader health:

- outright leader API fetch failures
- leader telemetry that still responds but stops advancing `update_time`

This is safer than the older global “next numeric hw_id” fallback because it stays within the active follow chain instead of jumping across unrelated drones.

Available policy values in [params.py](/opt/mavsdk_drone_show/src/params.py):

- `upstream_or_hold` - default, cluster-safe fallback
- `hold` - always self-promote and hold
- `next_hw_id` - legacy deterministic behavior, kept only for controlled compatibility

Cycle protection is enforced in two places:

- dashboard assignment validation before save
- GCS backend validation for `save-swarm-data` and `request-new-leader`

That prevents live leader changes from silently introducing a loop into the follow chain.

## Runtime Guarantees Added In This Audit

- follower control waits for both own-state and leader-state lock before sending formation setpoints
- follower re-entry restarts offboard mode cleanly after leader-to-follower transitions
- stale leader telemetry now participates in the same failover path as explicit request failures
- runtime controls default to `Selected Drone`; cluster scope is opt-in

## Files That Matter

### Runtime and failover

- [smart_swarm.py](/opt/mavsdk_drone_show/smart_swarm.py)
- [failover.py](/opt/mavsdk_drone_show/smart_swarm_src/failover.py)
- [params.py](/opt/mavsdk_drone_show/src/params.py)

### GCS persistence and live updates

- [app_fastapi.py](/opt/mavsdk_drone_show/gcs-server/app_fastapi.py)
  - `GET /get-swarm-data`
  - `POST /save-swarm-data`
  - `POST /request-new-leader`

### Frontend control surfaces

- [SwarmDesign.js](/opt/mavsdk_drone_show/app/dashboard/drone-dashboard/src/pages/SwarmDesign.js)
- [SwarmRuntimeControls.js](/opt/mavsdk_drone_show/app/dashboard/drone-dashboard/src/components/SwarmRuntimeControls.js)
- [swarmDesignUtils.js](/opt/mavsdk_drone_show/app/dashboard/drone-dashboard/src/utilities/swarmDesignUtils.js)
- [swarmRuntimeUtils.js](/opt/mavsdk_drone_show/app/dashboard/drone-dashboard/src/utilities/swarmRuntimeUtils.js)

## Operational Notes

- Smart Swarm follow links use `hw_id`, not `pos_id`.
- Slot swaps change the show slot, not the follow chain.
- Start Smart Swarm only after saving the intended assignments.
- Use swarm runtime controls when you want either a selected-drone override or an explicit cluster-level intent.
- Use single-drone controls when you want a scoped override.

## Recommended SITL Validation

For each Smart Swarm release, validate at minimum:

1. takeoff with 4-5 drones
2. start Smart Swarm on a cluster
3. change offsets and frame in flight
4. reassign one follower to a different leader
5. send a single-drone override to confirm other followers remain in Smart Swarm
6. run `Land Swarm` or `RTL Swarm`
7. verify all drones disarm cleanly

## Known Next-Step Opportunities

- richer operator-facing swarm stop/hold state reporting
- smarter cluster-level leader election policies
- transport optimization beyond HTTP polling if very large swarms require it
- UI playback and incident review tied to unified logging
