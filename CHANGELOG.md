# Changelog

All notable changes to MAVSDK Drone Show (MDS) project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project uses simple two-part versioning: `X.Y` (Major.Minor).

---

## [Unreleased]

### Added
- **Unified Logging System (`mds_logging`)**: Shared logging contract for all components
  - JSONL format for machine-parseable log files with ISO 8601 UTC timestamps
  - Session-based retention with configurable limits (count + size)
  - Colored console output with component-tagged messages
  - Component self-registration registry for auto-discovery
  - In-memory pub/sub watcher for SSE streaming
  - Shared CLI flags: `--verbose`, `--debug`, `--quiet`, `--log-json`, `--log-dir`
  - Environment variable config with `MDS_LOG_*` prefix and deprecation shims
- **Frontend Log Viewer (Phase 3)**:
  - Log Viewer page at `/logs` with Operations and Developer modes
  - Operations mode: WARNING+ filter, health bar, live event feed, clean UI
  - Developer mode: all log levels, component tree, search, session selector, export
  - Explicit `GCS` vs `Drone #N` scope switch for live streams and historical sessions
  - Human-readable session labels with explicit UTC note, clickable error/warning drill-down, and time-window focus controls
  - Active filter chips, one-click `Clear All Filters`, and explanatory empty states to reduce operator confusion
  - MUI DataGrid virtual scroll for 100K+ log rows
  - Real-time SSE streaming via `useLogStream` hook with 200ms batching and 5000-line ring buffer
  - Historical session browsing with filtering and client-side pagination
  - Export sessions as JSONL or ZIP, including proxied drone sessions
  - ErrorBoundary catches React render errors and reports to `POST /api/logs/frontend`
  - New "System" sidebar section with Log Viewer entry
  - `@mui/x-data-grid` dependency for virtual scroll
- **Log Aggregation & Streaming (Phase 2)**:
  - Drone-side log API: `GET /api/logs/sessions`, `GET /api/logs/sessions/{id}`, `GET /api/logs/stream` (SSE)
  - GCS log API router with 10 endpoints at `/api/logs/*`
  - Real-time SSE streaming with level/component/source/drone_id filtering
  - GCS-to-drone log proxy (sessions, session content, SSE stream forwarding)
  - Session export as JSONL or ZIP via `POST /api/logs/export`
  - Frontend error reporting via `POST /api/logs/frontend`
  - Component registry endpoint at `GET /api/logs/sources`
  - Optional background pull of WARNING+ logs from drones (`MDS_LOG_BACKGROUND_PULL`)
  - Runtime config toggle at `POST /api/logs/config`
  - `read_session_lines()` helper for filtered session content retrieval
  - `httpx` async HTTP client dependency for drone proxy
- **SITL Image Release Tooling**:
  - `tools/sitl_image_prepare.sh` to rebuild a clean runtime filesystem inside a temporary container
  - `tools/release_sitl_image.sh` to flatten and retag official SITL releases without carrying old `docker commit` history
  - `tools/run_with_log_policy.py` for bounded runtime file logs in SITL containers

### Changed
- All GCS server components migrated from `gcs_logging`/`logging_config` to `mds_logging`
- All drone-side components migrated from `configure_logging()`/inline setup to `mds_logging`
- CLI flags unified: `--debug` replaced with `--verbose`/`--debug`/`--quiet`
- `multiple_sitl/startup_sitl.sh` now keeps runtime repo sync via `git fetch/reset`, only reinstalls Python requirements when `requirements.txt` changes, and bounds container-side file logs by default
- `tools/build_custom_image.sh` now produces flattened custom images instead of layering more state through `docker commit`
- SITL image preparation/build docs now pin PX4 plus baked `mavsdk_server` inside the image, pass `MDS_MAVSDK_VERSION` / `MDS_MAVSDK_URL` through the image-build path, and use updated MAVSDK release asset naming for current releases

### Removed
- `gcs-server/logging_config.py` (857 lines, DroneSwarmLogger)
- `gcs-server/gcs_logging.py` (PYTHONPATH workaround wrapper)
- `src/logging_config.py` (drone-side logging config)
- `configure_logging()` function from `drone_show_src/utils.py`
- `setup_logging()` function from `functions/file_management.py`
- All `logging.basicConfig()` calls across the codebase

---

## [5.0] - 2026-02-24

### Added
- **QuickScout SAR/Reconnaissance Module**: Multi-drone cooperative area survey
  - New mission mode: `QUICKSCOUT = 5` with boustrophedon coverage planning
  - Boustrophedon (lawn-mower) coverage path planner with Shapely polygon operations
  - ENU coordinate conversion via pymap3d for accurate local planning
  - Automatic sector partitioning and GPS-proximity drone assignment
  - PX4 Mission Mode executor (`quickscout_mission.py`) with MAVSDK mission upload
  - Mission lifecycle management: plan, launch, pause, resume, abort
  - Point of Interest (POI) management with CRUD operations
  - Terrain-following altitude adjustment
  - Camera trigger actions at configurable intervals
- **SAR API Endpoints**: FastAPI APIRouter at `/api/sar`
  - Coverage planning, mission control, drone progress, POI, and elevation endpoints
  - Thread-safe singleton managers for mission state and POI storage
- **QuickScout Dashboard Page**: Full Plan/Monitor UI
  - Mapbox GL polygon drawing for search area definition
  - Coverage path preview with per-drone color coding
  - Real-time drone progress monitoring with status cards
  - Interactive POI marker system
  - Survey configuration panel with advanced options
- **SAR Test Suite**: Schema validation, coverage planner algorithm, and API endpoint tests
- **New Dependencies**: `shapely>=2.0.0` and `pymap3d` (GCS server only), `@mapbox/mapbox-gl-draw` (frontend)
- **Documentation**: `docs/quickscout.md` with architecture, API reference, and configuration guide

---

## [4.5] - 2026-02-24

### Added
- **Automated mavlink-router Integration**: Dashboard binary auto-download, systemd service setup via `mavlink_setup.sh`

### Changed
- **Config/Swarm migrated from CSV to JSON** (`v4.5.0-config-json`):
  - `config.csv` → `config.json`, `swarm.csv` → `swarm.json` (same for SITL variants)
  - JSON envelope format: `{"version": 1, "drones": [...]}` / `{"version": 1, "assignments": [...]}`
  - Native types: `mavlink_port`/`baudrate` as int, `follow` as int
  - Pydantic schemas with `extra='allow'` for user-defined custom fields (e.g. `color`, `notes`)
  - Shell scripts use `jq` for config parsing (dependency checked at runtime)
  - Dashboard: JSON import/export (primary), CSV import as fallback
  - Resource templates updated (10 files)
  - One-time migration tool: `tools/migrate_csv_to_json.py`
  - Guide: `docs/guides/config-json-format.md`
- **Swarm offset fields renamed** for clarity and extensibility:
  - `offset_n/offset_e/offset_alt` → `offset_x/offset_y/offset_z`
  - `body_coord` (bool) → `frame` (enum: `"ned"` | `"body"`)
  - Meaning of x/y/z depends on frame (ned: North/East/Up; body: Forward/Right/Up)
  - `offset_z` is always positive-up regardless of frame

---

## [4.4] - 2026-01-30

### Changed
- Version bump for enterprise services and configuration improvements

---

## [4.3] - 2026-01-28

### Added
- **Enhanced Repository Management**: Interactive fork vs default repository selection
  - Clear read-only warning for default repo users
  - SSH access detection for collaborators
  - Fork configuration verification (matches RPi init behavior)
- **NetBird VPN Integration**: VPN networking guidance in installation summary
  - New guide: `docs/guides/netbird-setup.md`
  - Network architecture diagrams
  - Step-by-step setup instructions
- **CLI Improvements**: New `--fork` option for `install_gcs.sh`
  - Quick fork setup: `curl ... | sudo bash -s -- --fork username`
  - Better error messages and guidance

### Changed
- **Repository Selection Flow**: Separated "what repo" from "how to access"
  - Step 1: Choose official repo or your own fork
  - Step 2: Choose HTTPS or SSH access
  - SSH recommended for production (enables git sync)
- **Path Resolution**: Fixed PYTHONPATH for GCS server module imports
  - Works correctly from any execution directory
  - Explicitly sets PROJECT_ROOT in PYTHONPATH
- **Documentation**: Updated gcs-setup.md with repository options and VPN networking

### Fixed
- **Module Import Issues**: GCS server can now find functions module from any path
- **Version Consistency**: All files updated to 4.3.0

---

## [4.2] - 2026-01-28

### Added
- **Unified MDS Branding**: Consistent ASCII art banner across all initialization scripts
  - New shared banner file: `tools/mds_banner.sh`
  - `print_mds_banner()` function for consistent display
  - `get_git_info()` function for git branch/commit retrieval
- **Version/Git Info at Startup**: All scripts now display version, branch, and commit at startup
  - GCS bootstrap shows version and branch during installation
  - GCS init displays version, branch, commit, and timestamp
  - RPi init displays version, branch, commit, and timestamp
  - Dashboard startup shows version and git info

### Changed
- **Banner Unification**: All scripts now use the same MDS ASCII art
  - `tools/install_gcs.sh`: Replaced box-drawing banner with unified banner
  - `tools/mds_gcs_init.sh`: Uses shared banner with git info
  - `tools/mds_gcs_init_lib/gcs_common.sh`: Sources shared banner
  - `tools/mds_init.sh`: Uses shared banner with git info
  - `tools/mds_init_lib/common.sh`: Sources shared banner
  - `app/linux_dashboard_start.sh`: Replaced wide ASCII with unified banner
- **Version Synchronization**: All version numbers updated to 4.2.0
  - `GCS_VERSION` in gcs_common.sh
  - `MDS_VERSION` in common.sh
  - `MDS_BANNER_VERSION` in mds_banner.sh
  - Documentation updated (README.md, docs/README.md, gcs-setup.md)

---

## [4.1] - 2026-01-24

### Added
- **GCS Initialization System**: Enterprise-grade VPS/Ubuntu GCS setup
  - One-line installation: `curl ... | sudo bash`
  - Comprehensive `mds_gcs_init.sh` with 9 phases
  - Library modules for prereqs, Python, Node.js, firewall, etc.
- **Documentation Updates**: GCS setup guide and documentation links

---

## [4.0] - 2026-01-20

### Added
- **Enterprise Raspberry Pi Initialization**: Production-ready `mds_init.sh`
  - Modular library architecture in `mds_init_lib/`
  - 13 installation phases with state tracking
  - Resume capability for interrupted installations
  - SSH key management for git sync
- **Production Dashboard Startup**: Enhanced `linux_dashboard_start.sh`
  - FastAPI/Flask backend selection
  - Development and production modes
  - tmux session management

---

## [3.8] - 2025-11-07

### Added
- Automated version bump (minor)

### Changed
- See commit history for detailed changes

---


## [3.7] - 2025-11-07

### Added
- **Comprehensive Project Cleanup**: Removed 14 unnecessary files and directories from root
  - Removed backup files: `config.csv.backup`, `config_sitl.csv.backup`
  - Removed old code backups: `drone_show_bak.py`, `smart_swarm_old.py`
  - Removed test/experimental scripts: `offboard_multiple_from_csv.py`, `test_config_*.py`
  - Removed empty npm artifacts: `drone-dashboard@1.0.0`, `react-scripts`
  - Removed misplaced `package-lock.json` from root (React is in `app/dashboard/drone-dashboard/`)
- **.gitignore Enhancements**: Added patterns to prevent future clutter
  - Backup files: `*.backup`, `*.bak`, `*_bak.py`, `*_old.py`
  - Binary executables: `mavsdk_server*`
  - Empty npm artifacts: `react-scripts`, `drone-dashboard@*`
  - Test scripts in root: `/test_config*.py`, `/offboard_multiple*.py`
- **PolyForm Dual Licensing**: Professional open-source licensing framework
  - PolyForm Noncommercial 1.0.0 for education, research, non-profits
  - PolyForm Small Business 1.0.0 for small commercial operations (< 10 drones, < $1M revenue, < 100 employees)
  - Custom commercial licensing for large operations
  - Comprehensive legal protection: LICENSE, DISCLAIMER.md, NOTICE, ETHICAL-USE.md

### Fixed
- **Critical UX Issue - Modal Dialog Centering**: Confirmation dialogs now properly center in viewport
  - Implemented React Portal for modal rendering (CommandSender.js)
  - Modal now renders to `document.body` instead of inline in container
  - Users no longer need to scroll to find confirmation dialogs - major UX improvement
- **React Console Warnings Resolved**:
  - Removed 6 debug `console.log()` statements from `missionConfigUtilities.js`
  - Fixed "assign before export" warning in `version.js` by refactoring export pattern
  - Updated `tools/version_sync.py` to generate ESLint-compliant JavaScript exports
  - Kept appropriate `console.error()` statements for error handling

### Changed
- **JavaScript Export Pattern**: Modernized version.js and auto-generation script
  - Declare constants first, then export (ESLint best practice)
  - Updated `tools/version_sync.py` template to generate compliant code
- **Legal Documentation Structure**: Confirmed LICENSE files correctly placed in root per industry standards
  - LICENSE, NOTICE, DISCLAIMER.md remain in root (GitHub/Apache/Google best practice)
  - Dual licensing structure clearly documented for easy discovery

---

## [3.6] - 2025-11-06

### Added
- **Documentation Restructure**: Comprehensive reorganization of all project documentation
  - Created organized folder structure: `docs/quickstart/`, `docs/guides/`, `docs/features/`, `docs/hardware/`, `docs/api/`
  - Created `docs/archives/` for historical documentation and implementation summaries
  - New documentation index at `docs/README.md` for easy navigation
- **Versioning System**: Unified version management across entire project
  - Single source of truth: `VERSION` file in project root
  - Automated version synchronization script: `tools/version_sync.py`
  - Dynamic version display in dashboard with git commit hash
  - Versioning workflow guide at `docs/VERSIONING.md`
- **CHANGELOG.md**: Separate, structured changelog following Keep a Changelog format
- **GCS Configuration Enhancements**:
  - Dashboard .env file auto-update feature for GCS IP changes
  - Checkbox option to update `REACT_APP_SERVER_URL` when changing GCS IP
  - User warnings about rebuild requirements and server location
- **UI/UX Production Improvements**:
  - Origin coordinate display with responsive multi-line layout
  - GPS coordinates truncated to 6 decimal places (0.11m accuracy)
  - Modal dialogs now center on viewport instead of container
  - Comprehensive toast notifications for save operations with git status
  - Save button renamed to "Save & Commit to Git" for clarity

### Changed
- **README.md**: Cleaned and streamlined for professional presentation
  - Added table of contents
  - Removed embedded version history (moved to CHANGELOG.md)
  - Better separation of quick start vs comprehensive guides
  - Improved navigation and structure
- **Documentation Organization**:
  - Moved implementation summaries to `docs/archives/implementation-summaries/`
  - Moved legacy docs (v2.0, HTML, PDF) to `docs/archives/`
  - Renamed and relocated current docs to new folder structure
  - Dashboard README customized for MDS (was generic Create React App template)
- **Dark Mode Fixes**:
  - Fixed unreadable metric boxes in ManageDroneShow page
  - Replaced MUI inline styles with CSS variables for theme compatibility
  - Added 80+ lines of dark mode compatible CSS
- **Version Display**: Dashboard sidebar now shows `v3.6 (git-hash)` dynamically

### Fixed
- GCS configuration dialog showing empty "Current IP" field (nested data structure issue)
- GCS IP not differentiating between SITL mode (172.18.0.1) and Real mode (100.96.32.75)
- Confirmation dialogs requiring scroll to see (viewport centering issue)
- No visual feedback during configuration save/commit operations
- Origin GPS coordinates overflowing container
- Dark mode color accessibility in VisualizationSection components

---

## [3.5] - 2025-09

### Added
- **Professional React Dashboard** with expert portal-based UI/UX using React Portal architecture
- **3D Trajectory Planning** with interactive waypoint creation, terrain elevation, and speed optimization
- **Enhanced Mobile Responsiveness** with touch-friendly interface and responsive design
- **Smart Swarm Trajectory Processing** with cluster leader management and dynamic formation reshaping
- **Expert Tab Navigation** with professional mission operations interface
- **Advanced UI/UX Improvements** with modal overlays, responsive design, and touch-friendly controls

### Changed
- Complete dashboard redesign with modern React patterns

### Fixed
- Multiple bug fixes and performance improvements for production deployment

---

## [3.0] - 2025-06

### Added
- **Smart Swarm Leader–Follower System**: Fully operational with leader failover, auto re-election, and seamless follower sync
- **Global Mode Setpoints**: Unified approach for both offline and live missions
- **Enhanced Failsafe Checks**: Comprehensive preflight health checks and in-flight monitoring
- **Stable Startup Sequence**: Three-way handshake mechanism ("OK-to-Start" broadcast)
- **Unified All-in-One System**: Single platform for both drone shows and live swarm operations

### Fixed
- Race condition issues under high CPU load (GUIDED → AUTO transitions)
- Emergency-land command reliability during mode transitions
- Network buffer tuning for large-scale simulations (100+ drones)

---

## [2.0] - 2024-11

### Added
- Enhanced React GUI with improved user experience
- Robust Flask backend architecture
- Comprehensive drone-show scripts
- Docker SITL environment for testing
- [100-Drone SITL Test Video](https://www.youtube.com/watch?v=VsNs3kFKEvU)

### Changed
- Major GUI overhaul
- Backend infrastructure improvements

---

## [1.5] - 2023-08

### Added
- Mission configuration tools
- SkyBrush CSV converter utility
- Expanded MAVLink2REST integration

---

## [1.0] - 2023-03

### Added
- **Stable Release Milestone**
- Flask web server implementation
- Professional API structure

### Removed
- UDP dependencies (replaced with more reliable protocols)

---

## [0.8] - 2022-09

### Added
- Major GUI enhancements
- Kalman-filter–based swarm behaviors
- Optimized cloud SITL performance

---

## [0.7] - 2022-04

### Added
- React GUI for real-time swarm monitoring
- Docker automation for PX4 SITL environments

---

## [0.6] - 2021-12

### Added
- Complex leader/follower swarm control capabilities
- Docker-based SITL environment

---

## [0.5] - 2021-07

### Added
- Basic leader/follower missions on real hardware
- Enhanced GCS data handling

---

## [0.4] - 2021-02

### Added
- `Coordinator.py` for advanced swarm coordination
- Improved telemetry and command systems

---

## [0.3] - 2020-10

### Added
- SkyBrush CSV processing integration
- Code optimizations for drone show performances

---

## [0.2] - 2020-06

### Added
- Multi-drone support with offset/delayed CSV trajectories

---

## [0.1] - 2020-03

### Added
- Initial release
- Single-drone CSV trajectory following
- Basic MAVSDK integration

---

## Release Types

- **Major Version (X.0)**: Significant architectural changes, breaking changes, or major new features
- **Minor Version (X.Y)**: New features, improvements, and non-breaking changes

---

© 2025 Alireza Ghaderi | Licensed under CC BY-NC-SA 4.0
