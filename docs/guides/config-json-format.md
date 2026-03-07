# Config JSON Format Reference

## Overview

MDS uses JSON files for fleet and swarm configuration. The format supports optional and custom fields via Pydantic `extra='allow'`.

## config.json / config_sitl.json

```json
{
  "version": 1,
  "drones": [
    {
      "hw_id": 1,
      "pos_id": 1,
      "ip": "192.168.1.10",
      "mavlink_port": 14551,
      "serial_port": "/dev/ttyS0",
      "baudrate": 57600,
      "color": "#FF6B00",
      "notes": "Replaced motor 2 on 2026-02-15"
    }
  ]
}
```

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `hw_id` | int (>=1) | Hardware ID -- unique physical drone identifier |
| `pos_id` | int (>=1) | Position ID -- maps to trajectory `Drone {pos_id}.csv` |
| `ip` | string | IP address (IPv4) |
| `mavlink_port` | int (>=1) | MAVLink UDP port |

### Optional Core Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `serial_port` | string | `""` | Serial port device (empty for SITL) |
| `baudrate` | int | `0` | Serial baudrate (0 for SITL) |
| `color` | string | `null` | Hex color for UI (`#RRGGBB`) |
| `notes` | string | `null` | Operator notes |

### Custom Fields

Any additional fields are preserved. Example: `"drone_type": "quad"`, `"label": "Alpha-1"`.

## swarm.json / swarm_sitl.json

```json
{
  "version": 1,
  "assignments": [
    {
      "hw_id": 1,
      "follow": 0,
      "offset_n": 0.0,
      "offset_e": 0.0,
      "offset_alt": 0.0,
      "body_coord": false
    }
  ]
}
```

### Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `hw_id` | int (>=1) | required | Hardware ID |
| `follow` | int (>=0) | `0` | Leader hw_id (0 = independent) |
| `offset_n` | float | `0.0` | North offset (meters) |
| `offset_e` | float | `0.0` | East offset (meters) |
| `offset_alt` | float | `0.0` | Altitude offset (meters) |
| `body_coord` | bool | `false` | Body-frame offsets (true) or NED-frame (false) |

## Mode Selection

| Mode | Config File | Swarm File |
|------|-------------|------------|
| Real | `config.json` | `swarm.json` |
| SITL | `config_sitl.json` | `swarm_sitl.json` |

Selected automatically by `src/params.py` based on the presence of `real.mode` file.

## Import/Export

The dashboard supports both JSON (primary) and CSV (legacy) import/export:
- **Export JSON**: Downloads `config.json` with version wrapper
- **Export CSV**: Downloads `config_export.csv` (core 6 fields only)
- **Import**: Accepts `.json` or `.csv`, auto-detects format

## Validation

Configuration is validated with Pydantic schemas (`gcs-server/schemas.py`):
- `hw_id` and `pos_id` must be >= 1 (1-based)
- `ip` must be valid IPv4
- Duplicate `hw_id` values are rejected
- Duplicate `pos_id` values trigger a collision warning
- Missing trajectory files for a `pos_id` trigger a warning

---

**Last Updated:** 2026-03-06
