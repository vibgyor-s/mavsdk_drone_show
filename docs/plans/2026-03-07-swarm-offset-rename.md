# Swarm Offset Field Rename Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Rename swarm offset fields from `offset_n/offset_e/offset_alt/body_coord` to `offset_x/offset_y/offset_z/frame` for clarity and extensibility.

**Architecture:** The `frame` field becomes a string enum (`"ned"` or `"body"`) replacing the boolean `body_coord`. The three offset fields become generic `offset_x/offset_y/offset_z` — their meaning depends on the frame (ned: North/East/Up; body: Forward/Right/Up). This is a clean break with no backward compatibility. All 28 files touching these fields are updated atomically.

**Tech Stack:** Python/Pydantic (backend), React/JS (frontend), JSON (data), jq (shell), pytest (tests)

---

## Semantic Mapping

```
OLD                    NEW              NED meaning      Body meaning
─────────────────────  ───────────────  ───────────────  ──────────────
body_coord: bool       frame: str       "ned"            "body"
offset_n: float        offset_x: float  North (m)        Forward (m)
offset_e: float        offset_y: float  East (m)         Right (m)
offset_alt: float      offset_z: float  Up (m)           Up (m)
```

`offset_z` is always positive-up regardless of frame (operator-intuitive, not PX4 NED-down).

---

### Task 1: Update Pydantic Schema

**Files:**
- Modify: `gcs-server/schemas.py:90-106`

**Changes:**
```python
class SwarmAssignment(BaseModel):
    model_config = ConfigDict(extra='allow')

    hw_id: int = Field(..., ge=1, description="Hardware ID")
    follow: int = Field(0, ge=0, description="Leader hw_id to follow (0 = independent)")
    offset_x: float = Field(0.0, description="Offset axis 1: North (ned) or Forward (body), meters")
    offset_y: float = Field(0.0, description="Offset axis 2: East (ned) or Right (body), meters")
    offset_z: float = Field(0.0, description="Offset axis 3: Up (positive = higher), meters")
    frame: str = Field("ned", pattern=r'^(ned|body)$', description="Coordinate frame: 'ned' (North-East-Up) or 'body' (Forward-Right-Up)")
```

**Verify:** `python3 -m py_compile gcs-server/schemas.py`

---

### Task 2: Update Schema Validation Tests

**Files:**
- Modify: `tests/test_schema_validation.py:89-112`

**Changes:** Update all `SwarmAssignment` and `SwarmConfig` test instantiations:
- `offset_n=` → `offset_x=`
- `offset_e=` → `offset_y=`
- `offset_alt=` → `offset_z=`
- `body_coord=True` → `frame="body"`
- `body_coord=False` → `frame="ned"`
- Add test: `SwarmAssignment(hw_id=1, frame="invalid")` raises `ValidationError`
- Add test: `SwarmAssignment(hw_id=1)` has `frame="ned"` by default

**Verify:** `python3 -m pytest tests/test_schema_validation.py -v`

---

### Task 3: Update Test Fixtures

**Files:**
- Modify: `tests/fixtures/drone_configs.py:81-107, 291-304, 371-395`
- Modify: `tests/fixtures/mission_samples.py:312-339`

**Changes in drone_configs.py:**
- Dataclass fields (lines 81-86):
  - `follow: int = 0` (unchanged)
  - `offset_x: float = 0.0` (was offset_n)
  - `offset_y: float = 0.0` (was offset_e)
  - `offset_z: float = 0.0` (was offset_alt)
  - `frame: str = "ned"` (was body_coord: bool = False)
- `to_swarm_row()` (lines 99-108): return dict with new field names
- `drones_to_swarm_csv()` (lines 371-379): update CSV header and row generation
- Generator functions (lines 291-304): use new field names in assignments

**Changes in mission_samples.py:**
- All swarm config dicts (lines 312-339): rename keys

**Verify:** `python3 -m pytest tests/ -v --tb=short`

---

### Task 4: Update conftest.py Fixture Imports

**Files:**
- Modify: `tests/conftest.py` (if any fixture references changed names)

**Verify:** `python3 -m pytest tests/ --collect-only`

---

### Task 5: Update GCS Config Load/Save

**Files:**
- Modify: `gcs-server/config.py:26-28`

**Changes:**
- `SWARM_REQUIRED_FIELDS = {'hw_id'}` — no change needed (offset fields have defaults)

**Verify:** `python3 -m py_compile gcs-server/config.py`

---

### Task 6: Update smart_swarm.py

**Files:**
- Modify: `smart_swarm.py` (~15 locations)

**Changes — read_swarm() function (~line 305-312):**
```python
SWARM_CONFIG[hw_id] = {
    'hw_id': hw_id,
    'follow': int(entry["follow"]),
    'offset_x': float(entry["offset_x"]),
    'offset_y': float(entry["offset_y"]),
    'offset_z': float(entry["offset_z"]),
    'frame': str(entry.get("frame", "ned")),
}
```

**Changes — periodic update (~line 549-554):**
```python
SWARM_CONFIG[hw_str] = {
    'follow':   int(entry.get('follow', 0)),
    'offset_x': offset_x_val,
    'offset_y': offset_y_val,
    'offset_z': offset_z_val,
    'frame':    str(entry.get('frame', 'ned')),
}
```

**Changes — parse_float calls (~line 545-547):**
- `entry.get('offset_n', ...)` → `entry.get('offset_x', ...)`
- `entry.get('offset_e', ...)` → `entry.get('offset_y', ...)`
- `entry.get('offset_alt', ...)` → `entry.get('offset_z', ...)`

**Changes — offset comparison/update (~line 562-568, 629-634):**
- All dict key references: `'offset_n'` → `'offset_x'`, `'offset_e'` → `'offset_y'`, `'offset_alt'` → `'offset_z'`
- `'body_coord'` → `'frame'`
- body_coord comparisons: `new_body_coord != BODY_COORD` → `new_frame != FRAME`

**Changes — global variables and OFFSETS dict:**
- Rename global `BODY_COORD` → `FRAME` (string, not bool)
- OFFSETS keys: `'n'` → `'x'`, `'e'` → `'y'`, `'alt'` → `'z'`

**Changes — control loop offset application (~line 938-951):**
```python
if FRAME == "body":
    offset_x_ned, offset_y_ned = transform_body_to_nea(OFFSETS['x'], OFFSETS['y'], leader_yaw)
else:
    offset_x_ned, offset_y_ned = OFFSETS['x'], OFFSETS['y']

desired_n = leader_n + offset_x_ned
desired_e = leader_e + offset_y_ned
desired_d = -1 * (leader_d + OFFSETS['z'])
```

**Changes — initial state setup (~line 1145-1149):**
```python
FRAME = swarm_config['frame']
IS_LEADER = swarm_config['follow'] == 0
OFFSETS['x'] = swarm_config['offset_x']
OFFSETS['y'] = swarm_config['offset_y']
OFFSETS['z'] = swarm_config['offset_z']
```

**Verify:** `python3 -m py_compile smart_swarm.py`

---

### Task 7: Update smart_swarm_src/utils.py

**Files:**
- Modify: `smart_swarm_src/utils.py:10-27`

**Changes:** Function signature and docstring only — the function takes positional args (offset_forward, offset_right), not named dict keys. Just update docstring/comments to reference offset_x/offset_y instead of offset_n/offset_e.

**Verify:** `python3 -m py_compile smart_swarm_src/utils.py`

---

### Task 8: Update functions/ Python files

**Files:**
- Modify: `functions/swarm_global_calculator.py:45-73`
- Modify: `functions/swarm_analyzer.py:57-60`
- Modify: `functions/swarm_trajectory_processor.py:301-304`
- Modify: `functions/swarm_session_manager.py:49-52`

**Changes — swarm_global_calculator.py:**
- All `offset_config['offset_n']` → `offset_config['offset_x']`
- All `offset_config['offset_e']` → `offset_config['offset_y']`
- All `offset_config['offset_alt']` → `offset_config['offset_z']`
- `offset_config['body_coord']` → `offset_config['frame'] == "body"`
- Update docstring

**Changes — swarm_analyzer.py:**
- DataFrame column names: `'offset_n'` → `'offset_x'`, `'offset_e'` → `'offset_y'`, `'offset_alt'` → `'offset_z'`, `'body_coord'` → `'frame'`

**Changes — swarm_trajectory_processor.py:**
- Same DataFrame column renames

**Changes — swarm_session_manager.py:**
- Dict key renames

**Verify:** `python3 -m py_compile` on all four files

---

### Task 9: Update tools/migrate_csv_to_json.py

**Files:**
- Modify: `tools/migrate_csv_to_json.py:28-34`

**Changes:** Update the migration script to output new field names. The script reads old CSV (which had offset_n/offset_e/offset_alt/body_coord) and should output JSON with offset_x/offset_y/offset_z/frame.

```python
elif k == 'body_coord':
    a['frame'] = 'body' if (v.strip() and bool(int(v))) else 'ned'
elif k == 'offset_n':
    a['offset_x'] = float(v) if v.strip() else 0.0
elif k == 'offset_e':
    a['offset_y'] = float(v) if v.strip() else 0.0
elif k == 'offset_alt':
    a['offset_z'] = float(v) if v.strip() else 0.0
```

**Verify:** `python3 -m py_compile tools/migrate_csv_to_json.py`

---

### Task 10: Update All JSON Data Files

**Files (6 files):**
- Modify: `swarm.json`
- Modify: `swarm_sitl.json`
- Modify: `resources/swarm_12docker.json`
- Modify: `resources/swarm_16docker.json`
- Modify: `resources/swarm_40docker.json`
- Modify: `resources/swarm_sitl_100.json`

**Changes (all files, every assignment object):**
- `"offset_n":` → `"offset_x":`
- `"offset_e":` → `"offset_y":`
- `"offset_alt":` → `"offset_z":`
- `"body_coord": false` → `"frame": "ned"`
- `"body_coord": true` → `"frame": "body"`

Use sed or a script to batch-rename across all files.

**Verify:** `python3 -c "import json; [json.load(open(f)) for f in ['swarm.json','swarm_sitl.json']]"` — no parse errors

---

### Task 11: Update Frontend — DroneCard.js

**Files:**
- Modify: `app/dashboard/drone-dashboard/src/components/DroneCard.js`

**Changes:**
- State init (~line 20-24): `drone.offset_n` → `drone.offset_x`, etc.
- `isBodyCoord` state → `frame` state (string "ned" or "body")
- `body_coord === '1' || body_coord === 1 || body_coord === true` → `drone.frame === 'body'`
- Form submission (~line 53-56): output `offset_x/offset_y/offset_z/frame`
- UI labels (~line 46-47): dynamic based on `frame === 'body'`
- Coordinate type dropdown (~line 135-137):
  ```jsx
  <select value={frame} onChange={e => setFrame(e.target.value)}>
      <option value="ned">North-East-Up (NEU)</option>
      <option value="body">Body (Forward-Right-Up)</option>
  </select>
  ```
- Display text (~line 83): update offset references

**Verify:** `node --check` on the file (syntax only)

---

### Task 12: Update Frontend — SwarmDesign.js

**Files:**
- Modify: `app/dashboard/drone-dashboard/src/pages/SwarmDesign.js`

**Changes:**
- Default drone template (~line 83-86): `offset_x: 0.0, offset_y: 0.0, offset_z: 0.0, frame: "ned"`
- CSV import header validation (~line 163): update expected headers
- CSV row parsing (~line 170-171): map to new field names
- JSON import: field names come from JSON directly — no change needed if JSON files already updated

**Verify:** `node --check` on the file

---

### Task 13: Update Frontend — SwarmPlots.js

**Files:**
- Modify: `app/dashboard/drone-dashboard/src/components/SwarmPlots.js`

**Changes:**
- Offset parsing (~line 346-348): `drone.offset_n` → `drone.offset_x`, etc.
- body_coord check (~line 350): `drone.body_coord === '1' || ...` → `drone.frame === 'body'`
- Body-to-NED rotation (~line 357-361): variable names offset_n/offset_e → offset_x_ned/offset_y_ned (local calc vars)

**Verify:** `node --check`

---

### Task 14: Update Frontend — DroneGraph.js

**Files:**
- Modify: `app/dashboard/drone-dashboard/src/components/DroneGraph.js`

**Changes:**
- Edge data (~line 28): `body_coord: drone.body_coord` → `frame: drone.frame`
- CSS selectors (~line 111, 120): `edge[body_coord="1"]` → `edge[frame="body"]`, `edge[body_coord="0"]` → `edge[frame="ned"]`

**Verify:** `node --check`

---

### Task 15: Update Frontend — missionConfigUtilities.js

**Files:**
- Modify: `app/dashboard/drone-dashboard/src/utilities/missionConfigUtilities.js`

**Changes:** Check if CORE_FIELDS or OPTIONAL_FIELDS reference swarm fields — they don't (those are config fields only). But check for any swarm CSV export/import that references the old names.

**Verify:** grep for offset_n/body_coord — if none found, no changes needed.

---

### Task 16: Update Documentation

**Files:**
- Modify: `docs/guides/config-json-format.md:55-76`
- Modify: `docs/features/swarm-trajectory.md:65-72`
- Modify: `docs/apis/drone-api-server.md:281-292`

**Changes — config-json-format.md:**
- Update swarm.json field table and example
- Update field descriptions:
  - `offset_x` — Offset axis 1: North (ned) / Forward (body), meters
  - `offset_y` — Offset axis 2: East (ned) / Right (body), meters
  - `offset_z` — Offset axis 3: Up (positive = higher), meters
  - `frame` — Coordinate frame: `"ned"` or `"body"`
- Add interpretation table showing what x/y/z mean per frame

**Changes — swarm-trajectory.md:**
- Update field references and examples

**Changes — drone-api-server.md:**
- Update JSON response examples

**Verify:** No broken links, field names match schema

---

### Task 17: Update CHANGELOG

**Files:**
- Modify: `CHANGELOG.md`

**Changes:** Add entry under [4.5]:
```markdown
- **Swarm offset fields renamed** for clarity and extensibility:
  - `offset_n/offset_e/offset_alt` → `offset_x/offset_y/offset_z`
  - `body_coord` (bool) → `frame` (enum: `"ned"` | `"body"`)
  - Meaning of x/y/z depends on frame (ned: North/East/Up; body: Forward/Right/Up)
  - `offset_z` is always positive-up regardless of frame
```

---

### Task 18: Run Full Verification

1. `python3 -m py_compile` on all modified Python files
2. `python3 -m pytest tests/ -v` — 473 tests pass, 0 fail
3. `grep -rn "offset_n\|offset_e\|offset_alt\|body_coord" --include="*.py" --include="*.js" --include="*.json" /opt/mavsdk_drone_show/ | grep -v node_modules | grep -v __pycache__ | grep -v docs/plans | grep -v docs/archives | grep -v docs/research | grep -v plot_drone_paths` — **ZERO hits** (plot_drone_paths uses offset_n/offset_e as unrelated local variables for plot margins, excluded)
4. `node --check` on all modified JS files
5. All JSON data files valid

---

### Task 19: Commit, Push

```bash
git add -A
git commit -m "refactor: rename swarm offset fields for clarity

- offset_n/offset_e/offset_alt → offset_x/offset_y/offset_z
- body_coord (bool) → frame (enum: 'ned' | 'body')
- x/y/z meaning depends on frame:
  ned:  North / East / Up
  body: Forward / Right / Up
- offset_z always positive-up (operator-intuitive)
- 28 files updated across backend, frontend, data, tests, docs"
git push origin main-candidate
```

---

## File Change Summary

| Category | Files | Key Change |
|----------|-------|-----------|
| Schema | `gcs-server/schemas.py` | SwarmAssignment field defs |
| Backend | `smart_swarm.py` | ~15 locations, OFFSETS dict, FRAME global |
| Functions | 4 files in `functions/` | Dict key renames |
| Utils | `smart_swarm_src/utils.py` | Docstring only |
| Migration | `tools/migrate_csv_to_json.py` | Output new names |
| Frontend | 4 JS files | Props, state, labels, selectors |
| Data | 6 JSON files | All field names in every assignment |
| Tests | 3 test files | Assertions, fixtures, samples |
| Docs | 3 doc files + CHANGELOG | Examples, tables, descriptions |
| **Total** | **~24 files** | |
