# GCS Server Setup Guide

**Complete guide for setting up the MDS Ground Control Station on Ubuntu/VPS**

---

## Table of Contents

- [Quick Start](#quick-start)
- [Manual Setup](#manual-setup)
- [CLI Reference](#cli-reference)
- [Configuration Files](#configuration-files)
- [Firewall Ports](#firewall-ports)
- [Verification](#verification)
- [Troubleshooting](#troubleshooting)
- [Running the Dashboard](#running-the-dashboard)

---

## Quick Start

### One-Line Installation (Recommended)

The fastest way to set up a GCS server on a fresh Ubuntu VPS:

```bash
curl -fsSL https://raw.githubusercontent.com/alireza787b/mavsdk_drone_show/main-candidate/tools/install_gcs.sh | sudo bash
```

This script will:
- Detect your system and validate prerequisites
- Install all required dependencies (Python, Node.js, etc.)
- Clone the repository
- Set up the virtual environment
- Install npm dependencies
- Configure firewall rules
- Create system configuration files

---

## Manual Setup

### Prerequisites

- **Operating System:** Ubuntu 20.04, 22.04, or 24.04 (recommended: 22.04)
- **Architecture:** x86_64 or arm64/aarch64
- **Disk Space:** Minimum 5GB free
- **Network:** Internet access for package downloads
- **Privileges:** Root or sudo access

### Step-by-Step Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/alireza787b/mavsdk_drone_show.git
   cd mavsdk_drone_show
   ```

2. **Run the GCS initialization script:**
   ```bash
   sudo ./tools/mds_gcs_init.sh
   ```

3. **Follow the interactive prompts to:**
   - Configure SSH deploy key (for git sync features) or use HTTPS
   - Set up Python virtual environment
   - Install npm dependencies
   - Configure firewall rules
   - Set up Mapbox token (optional, for map features)

---

## CLI Reference

### Mode Selection

| Option | Description |
|--------|-------------|
| `--configure` | Full setup mode (default) |
| `--run` | Start services only (skip setup) |

### Common Options

| Option | Description |
|--------|-------------|
| `-y, --yes` | Non-interactive mode (accept defaults) |
| `--dry-run` | Preview changes without executing |
| `--resume` | Continue interrupted setup from last checkpoint |
| `--https` | Use HTTPS for repository (no SSH key needed) |
| `--force` | Force reinstallation, overwrite existing setup |
| `-v, --verbose` | Show detailed output |
| `--debug` | Show debug-level logging |

### Skip Options

| Option | Description |
|--------|-------------|
| `--skip-prereqs` | Skip prerequisite checks |
| `--skip-python` | Skip Python installation |
| `--skip-nodejs` | Skip Node.js installation |
| `--skip-repo` | Skip repository clone/update |
| `--skip-firewall` | Skip firewall configuration |
| `--skip-python-env` | Skip virtual environment setup |
| `--skip-nodejs-env` | Skip npm dependencies |
| `--skip-env-config` | Skip .env configuration |

### Examples

```bash
# Full interactive setup
sudo ./tools/mds_gcs_init.sh

# Non-interactive setup with HTTPS
sudo ./tools/mds_gcs_init.sh -y --https

# Dry run to preview changes
sudo ./tools/mds_gcs_init.sh --dry-run

# Resume interrupted installation
sudo ./tools/mds_gcs_init.sh --resume

# Skip firewall changes (if using external firewall)
sudo ./tools/mds_gcs_init.sh --skip-firewall
```

---

## Configuration Files

### System Configuration

| File | Purpose |
|------|---------|
| `/etc/mds/gcs.env` | System-wide GCS configuration |
| `/var/lib/mds/gcs_init_state.json` | Installation state (for resume) |
| `/var/log/mds/mds_gcs_init.log` | Installation logs |

### Application Configuration

| File | Purpose |
|------|---------|
| `app/dashboard/drone-dashboard/.env` | Dashboard settings (Mapbox, ports) |
| `requirements.txt` | Python dependencies |
| `app/dashboard/drone-dashboard/package.json` | Node.js dependencies |

### Example `/etc/mds/gcs.env`

```bash
# MDS GCS Configuration
GCS_PORT=5000
GCS_BACKEND=uvicorn

# Repository Settings
MDS_REPO_URL=git@github.com:alireza787b/mavsdk_drone_show.git
MDS_BRANCH=main-candidate
MDS_INSTALL_DIR=/opt/mavsdk_drone_show

# Dashboard Settings
DASHBOARD_PORT=3030

# Virtual Environment
VENV_PATH=/opt/mavsdk_drone_show/venv
```

---

## Firewall Ports

The following ports are configured by the initialization script:

| Port | Protocol | Purpose |
|------|----------|---------|
| 22 | TCP | SSH access |
| 5000 | TCP | GCS API Server (FastAPI/Flask) |
| 3030 | TCP | React Dashboard |
| 14550 | UDP | GCS MAVLink (from drones) |
| 24550 | UDP | Additional MAVLink (multi-GCS) |
| 34550 | UDP | Additional MAVLink (multi-GCS) |
| 14540 | UDP | MAVSDK SDK (for SITL) |
| 12550 | UDP | Local MAVLink telemetry |
| 14569 | UDP | mavlink2rest API |

### Manual Firewall Configuration

If you skipped firewall setup or need to configure manually:

```bash
# Using UFW
sudo ufw allow 22/tcp
sudo ufw allow 5000/tcp
sudo ufw allow 3030/tcp
sudo ufw allow 14550/udp
sudo ufw allow 14540/udp
sudo ufw allow 14569/udp
sudo ufw enable
```

---

## Verification

### Check Installation Status

```bash
# View state file
cat /var/lib/mds/gcs_init_state.json | jq .

# Check log file
tail -50 /var/log/mds/mds_gcs_init.log

# Verify Python environment
source /opt/mavsdk_drone_show/venv/bin/activate
python -c "import fastapi; print('FastAPI OK')"
python -c "import mavsdk; print('MAVSDK OK')"

# Verify Node.js environment
ls /opt/mavsdk_drone_show/app/dashboard/drone-dashboard/node_modules | head -5
```

### Run Diagnostic Check

```bash
cd /opt/mavsdk_drone_show/app
./linux_dashboard_start.sh --check
```

---

## Troubleshooting

### SSH Key Issues

**Problem:** SSH authentication fails when cloning repository.

**Solutions:**
1. **Use HTTPS instead:**
   ```bash
   sudo ./tools/mds_gcs_init.sh --https
   ```

2. **Verify deploy key is added to GitHub:**
   - Go to repository Settings > Deploy keys
   - Ensure the key from `~/.ssh/mds_gcs_deploy_key.pub` is added
   - Check "Allow write access" is enabled

3. **Test SSH connection:**
   ```bash
   ssh -T git@github.com
   ```

### Port Conflicts

**Problem:** Port already in use error.

**Solution:**
```bash
# Find process using port
sudo lsof -i :5000
# or
sudo netstat -tlnp | grep 5000

# Kill the process
sudo kill -9 <PID>
```

### Python Environment Issues

**Problem:** Virtual environment creation fails.

**Solutions:**
1. **Install Python venv module:**
   ```bash
   sudo apt-get install python3.11-venv
   ```

2. **Remove corrupted venv and retry:**
   ```bash
   rm -rf /opt/mavsdk_drone_show/venv
   sudo ./tools/mds_gcs_init.sh --resume
   ```

### npm Install Failures

**Problem:** npm ci or npm install fails.

**Solutions:**
1. **Clear npm cache:**
   ```bash
   npm cache clean --force
   ```

2. **Remove node_modules and retry:**
   ```bash
   rm -rf /opt/mavsdk_drone_show/app/dashboard/drone-dashboard/node_modules
   cd /opt/mavsdk_drone_show/app/dashboard/drone-dashboard
   npm install
   ```

### Resume Interrupted Installation

If installation was interrupted:
```bash
sudo ./tools/mds_gcs_init.sh --resume
```

This will continue from the last completed phase.

---

## Running the Dashboard

After successful installation, start the dashboard:

### Development Mode (Recommended for testing)

```bash
cd /opt/mavsdk_drone_show/app
./linux_dashboard_start.sh --dev --sitl
```

### Production Mode

```bash
cd /opt/mavsdk_drone_show/app
./linux_dashboard_start.sh --prod --real
```

### Quick Status Check

```bash
./linux_dashboard_start.sh --status
```

### Access Points

After starting:
- **React Dashboard:** http://YOUR_SERVER_IP:3030
- **GCS API Server:** http://YOUR_SERVER_IP:5000
- **API Health Check:** http://YOUR_SERVER_IP:5000/health

---

## Next Steps

1. **Configure Mapbox Token** (optional): Edit `.env` file to add your Mapbox access token for map features
2. **Set up MAVLink Routing**: See [MAVLink Routing Setup](mavlink-routing-setup.md)
3. **Configure Drones**: See [MDS Init Setup](mds-init-setup.md) for Raspberry Pi drones
4. **Review SITL Guide**: See [SITL Comprehensive Guide](sitl-comprehensive.md) for simulation testing

---

**Last Updated:** January 2026 (Version 4.2.0)
