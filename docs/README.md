# MAVSDK Drone Show Documentation

**Complete documentation index for MDS 4.3**

Welcome to the MAVSDK Drone Show documentation! This index will help you find the right guide for your needs.

---

## 📋 Table of Contents

- [Getting Started](#-getting-started)
- [Setup Guides](#-setup-guides)
- [Features](#-features)
- [Configuration](#-configuration)
- [Hardware](#-hardware)
- [API & Integration](#-api--integration)
- [Version Management](#-version-management)
- [Archived Documentation](#-archived-documentation)

---

## 🚀 Getting Started

### New to MDS?

Start here to get your first drone show simulation running:

1. **[SITL Comprehensive Guide](guides/sitl-comprehensive.md)** - Recommended for first-time users
   - Complete step-by-step SITL setup
   - Network configuration, Docker setup, dashboard startup

2. **[Deployment Quick Reference](guides/deployment-quick-reference.md)** - Essential commands only

### Choose Your Path

| I want to... | Start with... |
|--------------|---------------|
| Try MDS quickly (SITL) | [SITL Comprehensive Guide](guides/sitl-comprehensive.md) |
| Set up GCS server | [GCS Setup Guide](guides/gcs-setup.md) |
| Deploy on Raspberry Pi | [MDS Init Setup](guides/mds-init-setup.md) |
| Customize deployment | [Advanced SITL Guide](guides/advanced-sitl.md) |
| Understand features | [Features Section](#-features) |

---

## 📖 Setup Guides

### SITL (Simulation)

| Guide | Description | Audience |
|-------|-------------|----------|
| **[SITL Comprehensive](guides/sitl-comprehensive.md)** | Complete SITL setup from scratch | Beginners |
| **[Advanced SITL](guides/advanced-sitl.md)** | Custom configuration, environment variables, production deployments | Advanced users |
| **[Deployment Quick Reference](guides/deployment-quick-reference.md)** | Quick command reference for deployment | All users |

### Configuration

| Guide | Description |
|-------|-------------|
| **[CSV Migration Guide](guides/csv-migration.md)** | Migrating from 10-column to 8-column CSV format |
| **[Python Compatibility](guides/python-compatibility.md)** | Python version requirements (3.11-3.13) |

---

## ✨ Features

Detailed documentation for MDS features:

| Feature | Description |
|---------|-------------|
| **[Swarm Trajectory](features/swarm-trajectory.md)** | Smart swarm mode, leader-follower clustering, Kalman filters |
| **[Origin System](features/origin-system.md)** | Coordinate system implementation and global positioning |
| **[Control Modes and Coordinates](control-modes-and-coordinates.md)** | Comprehensive guide to control modes, coordinate systems, Phase 2 auto-correction, and time synchronization |

---

## ⚙️ Configuration

### Configuration Files

- **config.csv** - Main drone configuration file (8-column format)
  - Hardware ID, Serial port, Baudrate, Drone ID, etc.
  - See [CSV Migration Guide](guides/csv-migration.md) for details

### Environment Variables

MDS supports environment variable overrides for advanced configuration:

| Variable | Purpose | Default |
|----------|---------|---------|
| `MDS_REPO_URL` | Custom git repository URL | Official repo |
| `MDS_BRANCH` | Custom git branch | `main-candidate` |
| `MDS_DOCKER_IMAGE` | Custom Docker image | Official image |

See [Advanced SITL Guide](guides/advanced-sitl.md) for usage examples.

---

## 🔧 Hardware

### Supported Platforms

- Raspberry Pi (4 & 5)
- NVIDIA Jetson series
- Any Linux-based companion computer

### Hardware Setup Guides (Raspberry Pi)

| Guide | Description |
|-------|-------------|
| **[MDS Init Setup](guides/mds-init-setup.md)** | Complete step-by-step Raspberry Pi initialization |
| **[CLI Reference](guides/mds-init-cli-reference.md)** | All CLI arguments, environment variables, examples |
| **[Headless Automation](guides/headless-automation.md)** | Fleet provisioning, CI/CD, batch deployment |
| **[Troubleshooting](guides/mds-init-troubleshooting.md)** | Common issues, recovery procedures, FAQ |
| **[Service Architecture](guides/raspberry-pi-services.md)** | Systemd services, boot order, configuration |

### Hardware-Specific Configuration

| Platform | Serial Port | Baudrate | Guide Status |
|----------|-------------|----------|--------------|
| Raspberry Pi 4 | `/dev/ttyS0` | 57600 / 921600 | [MDS Init Setup](guides/mds-init-setup.md) |
| Raspberry Pi 5 | `/dev/ttyAMA0` | 57600 / 921600 | [MDS Init Setup](guides/mds-init-setup.md) |
| Jetson (Orin/Xavier) | `/dev/ttyTHS1` | 57600 / 921600 | *(Documentation TBD)* |

**Note:** Real hardware deployment requires professional expertise. See [Contact](../README.md#contact--contributions) for assistance.

---

## 🖥️ GCS Server Setup

### Ground Control Station

| Guide | Description |
|-------|-------------|
| **[GCS Setup Guide](guides/gcs-setup.md)** | Complete GCS server installation and configuration |
| **[NetBird VPN Setup](guides/netbird-setup.md)** | Secure networking between GCS and drones |

Quick start for VPS/Ubuntu:
```bash
curl -fsSL https://raw.githubusercontent.com/alireza787b/mavsdk_drone_show/main-candidate/tools/install_gcs.sh | sudo bash
```

Manual setup:
```bash
sudo ./tools/mds_gcs_init.sh
```

---

## 🔌 API & Integration

### Available APIs

- **FastAPI Backend** (recommended) - High-performance REST API
  - Health check: `/health`
  - See [GCS Setup Guide](guides/gcs-setup.md) for configuration
- **Flask Backend** (legacy) - REST API for configuration and control
  - Endpoint documentation: *(TBD)*
- **MAVLink2REST** - REST API for MAVLink messages
  - [Official Documentation](https://github.com/mavlink/mavlink2rest)
- **WebSocket** - Real-time telemetry streaming
  - Protocol documentation: *(TBD)*

### Integration Examples

*(Coming soon - integration examples with external tools and platforms)*

---

## 📦 Version Management

Understanding how MDS manages versions:

**[Versioning Guide](VERSIONING.md)** - Complete versioning workflow

Topics covered:
- Version numbering scheme (X.Y)
- How to bump versions
- Release process (main-candidate → main → GitHub release)
- Automated version synchronization
- Manual override capabilities

**Current Version:** 4.2

**Changelog:** See [CHANGELOG.md](../CHANGELOG.md) for complete version history.

---

## 📁 Archived Documentation

Historical documentation and implementation summaries are preserved for reference:

### Implementation Summaries

Detailed reports of major implementations and bug fixes (chronologically organized):

- [2025-09-04: Flight Mode Fix](archives/implementation-summaries/2025-09-04_flight-mode-fix.md)
- [2025-09-06: Mission State Rename](archives/implementation-summaries/2025-09-06_mission-state-rename.md)
- [2025-09-20: Robustness Summary](archives/implementation-summaries/2025-09-20_robustness-summary.md)
- [2025-09-20: Container Fixes](archives/implementation-summaries/2025-09-20_container-fixes.md)
- [2025-11-04: Processing Validation](archives/implementation-summaries/2025-11-04_processing-validation.md)
- [2025-11-05: Bug Fix Report](archives/implementation-summaries/2025-11-05_bug-fix-report.md)
- [2025-11-05: Implementation Summary](archives/implementation-summaries/2025-11-05_implementation-summary.md)
- [2025-11-06: Cleanup Summary](archives/implementation-summaries/2025-11-06_cleanup-summary.md)

### Deprecated Documentation

Older versions retained for historical reference:

- [DEPRECATED: Version 2.0 SITL Guide](archives/deprecated/DEPRECATED_v2.0_doc_sitl_demo.md)

### Legacy Documentation

Original documentation from early versions:

- Version 0.1 Documentation (PDF)
- Version 0.7 Documentation (HTML)
- Version 0.8 Server Documentation (HTML)

Located in: `archives/legacy-versions/`

---

## 🎯 Quick Navigation

### By User Type

**Beginners:**
1. Start with [SITL Comprehensive Guide](guides/sitl-comprehensive.md)
2. Review [Python Compatibility](guides/python-compatibility.md)
3. Explore [Features Documentation](#-features)

**Experienced Users:**
1. Check [Advanced SITL Guide](guides/advanced-sitl.md)
2. Review [Swarm Trajectory Features](features/swarm-trajectory.md)
3. Consult [API Documentation](#-api--integration)

**Developers/Contributors:**
1. Read [Versioning Guide](VERSIONING.md)
2. Review [Configuration Guides](#-configuration)
3. Check [Archived Implementation Summaries](#implementation-summaries)

---

## 🔍 Can't Find What You're Looking For?

- **Search the repository:** Use GitHub's search function
- **Check the main README:** [../README.md](../README.md)
- **Browse the codebase:** Inline documentation in source files
- **Ask for help:** See [Contact & Contributions](../README.md#contact--contributions)

---

## 📝 Contributing to Documentation

Documentation improvements are always welcome! If you:
- Found an error or outdated information
- Want to add a new guide
- Have suggestions for better organization

Please submit a pull request or open an issue on GitHub.

---

**Last Updated:** January 2026 (Version 4.2)

© 2025 Alireza Ghaderi | Licensed under CC BY-SA 4.0
