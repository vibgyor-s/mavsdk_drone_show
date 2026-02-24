# MAVSDK Drone Show (MDS)

**All-in-One Drone Show & Smart Swarm Framework for PX4**

[![Version](https://img.shields.io/badge/version-5.0-blue.svg)](CHANGELOG.md)
[![License](https://img.shields.io/badge/license-PolyForm%20Dual-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue.svg)](docs/guides/python-compatibility.md)

MDS is a unified platform for PX4-based drone performances and intelligent swarm missions. Whether you want to run pre-planned, decentralized drone shows using SkyBrush outputs or orchestrate live, collaborative swarms with leader–follower clustering, MDS has you covered.

---

## Table of Contents

- [Overview](#overview)
- [Demo Videos](#demo-videos)
- [Key Features](#key-features)
- [Getting Started](#getting-started)
  - [Python Requirements](#python-requirements)
  - [Quick Start (SITL Demo)](#quick-start-sitl-demo)
  - [Advanced Configuration](#advanced-configuration)
  - [Real Hardware Deployment](#real-hardware-deployment)
- [Documentation](#documentation)
- [Version & Changelog](#version--changelog)
- [Commercial Support](#-commercial-support--custom-implementation)
- [Contact & Contributions](#contact--contributions)
- [Disclaimer](#disclaimer)
- [Additional Resources](#additional-resources)
- [License](#license)

---

## Overview

MDS 3 combines three core components into a single, cohesive package:

### 1. Drone Side
- Runs on any Linux-based autopilot platform (Raspberry Pi, NVIDIA Jetson, or similar)
- Handles MAVSDK integration, local trajectory execution, and failsafe monitoring
- Dynamic formation logic and autonomous operation

### 2. Cloud Side (Optional Backend)
- Hosts formation-planning engine, mission dispatcher, and WebSocket/MAVLink router
- Provides global setpoint management, three-way startup handshake, and health-check services
- Deploy on cloud VM (Ubuntu 22.04/23.04) or on-premises server

### 3. Frontend (React Dashboard)
- Full-featured React GUI for real-time monitoring and control
- Upload offline "ShowMode" trajectories (CSV/JSON from SkyBrush)
- Visualize live positions, assign leaders/followers, and trigger mission modes
- **3D Trajectory Planning** with interactive waypoints and terrain elevation
- Supports both Drone-Show mode and Smart-Swarm mode

**In short, MDS 3 is one package for:**
- **Offline Drone Shows**: Pre-planned, synchronized formations from SkyBrush CSV
- **Smart Swarm Missions**: Decentralized leader–follower missions with robust failsafe handling

---

## Demo Videos

### MDS 3 Complete Feature Showcase
**3D Drone Swarms in Action | Mission Planning + Autonomous Clustered Formation**

[![MDS 3 Complete Feature Showcase](https://img.youtube.com/vi/mta2ARQKWRQ/maxresdefault.jpg)](https://www.youtube.com/watch?v=mta2ARQKWRQ)

### 100-Drone SITL Test (Version 2)
**Large-Scale Cloud Simulation**

[![100-Drone SITL Test](https://img.youtube.com/vi/VsNs3kFKEvU/maxresdefault.jpg)](https://www.youtube.com/watch?v=VsNs3kFKEvU)

### Smart Swarm Mode Demo
**Live Leader-Follower Clustering**

[![Smart Swarm Mode Demo](https://img.youtube.com/vi/qRXE3LTd40c/maxresdefault.jpg)](https://youtu.be/qRXE3LTd40c)

---

## Key Features

### All-in-One Architecture
- Shared Docker image and codebase for offline shows and live swarm missions
- Single command-line interface and unified React dashboard
- Streamlined deployment workflow

### Offline Drone-Show Mode
- Converts SkyBrush CSV/JSON into MAVSDK-compatible "ShowMode" files
- Global setpoint propagation for perfect synchronization (10–100+ drones)
- Preflight sanity checks (battery, GPS lock, ESC health)

### Smart Swarm Mode (Live, Decentralized)
- Clustered leader–follower architecture with Kalman-filter state estimation
- Automatic leader failure detection and re-election
- Dynamic formation reshaping and per-drone role changes
- In-flight failsafe monitors for communication, altimeter, ESC health

### Stable Startup Handshake
- Three-way acknowledgement chain (Drone ⇄ PX4 ⇄ MAVSDK ⇄ GCS)
- "OK-to-Start" broadcast prevents premature launches
- Guaranteed readiness before takeoff

### Robustness & Performance
- Race-condition fixes under high CPU load
- Emergency-land command reliability during mode transitions
- Network buffer tuning for large-scale simulations (100+ drones)

### Professional React Dashboard
- Live monitoring: position, battery, mode, failsafe status per drone
- Mission upload interface for offline trajectories or real-time swarm commands
- **3D Trajectory Planning**: Interactive waypoint creation with real terrain elevation
  - Professional trajectory management with speed optimization
  - Requires Mapbox access token for full functionality
- Formation editor (drag-and-drop) - coming soon
- REST API endpoints via MAVLink2REST

### Automated Docker Environment
- Prebuilt image includes: PX4 1.16, MAVSDK, MAVLink Router, MAVLink2REST, Gazebo
- Auto hardware-ID detection
- Dynamic container creation scripts

### Mission Configuration Tools
- SkyBrush CSV → MDS converter script
- JSON-based mission/formation files with validators
- Parameter tuning utilities for leader election, Kalman filters, failsafe timeouts

---

## Getting Started

### Python Requirements

**MDS requires Python 3.11, 3.12, or 3.13.** The latest Raspberry Pi OS includes Python 3.13 and is fully supported.

📖 See [Python Compatibility Guide](docs/guides/python-compatibility.md) for details and troubleshooting.

### Quick Start (SITL Demo)

The fastest way to try MDS is with our SITL (Software-In-The-Loop) demo:

📖 **[SITL Demo Guide](docs/guides/sitl-comprehensive.md)** - Complete step-by-step setup

This guide covers:
- Docker image pull/load commands
- Environment setup (`setup_environment.sh`, `create_dockers.sh`)
- Network, MAVLink Router, Netbird VPN configuration
- React dashboard startup (`linux_dashboard_start.sh --sitl`)
- Uploading offline trajectories or launching live swarm missions
- 3D Trajectory Planning setup (add Mapbox access token to `.env`)

**Quick Start Option:**
📖 **[Deployment Quick Reference](docs/guides/deployment-quick-reference.md)** - Essential commands only

### Advanced Configuration

For custom repositories, production SITL deployments, or advanced scenarios:

📖 **[Advanced SITL Guide](docs/guides/advanced-sitl.md)** - Custom configuration and environment variables

> ⚠️ **Advanced configuration requires good understanding of Git, Docker, and Linux**

### Real Hardware Deployment

**⚠️ IMPORTANT:** Deploying MDS on real drones requires:
- Deep understanding of flight control systems and safety protocols
- Aviation regulations compliance
- Extensive testing in controlled environments
- Professional drone operation knowledge and certifications
- Additional hardware setup, networking, and safety configurations

**For real hardware deployment assistance, see the [Contact](#contact--contributions) section.**

### GCS Server Setup (VPS/Ubuntu)

For setting up a Ground Control Station on a VPS or Ubuntu server:

**One-Line Installation:**
```bash
curl -fsSL https://raw.githubusercontent.com/alireza787b/mavsdk_drone_show/main-candidate/tools/install_gcs.sh | sudo bash
```

**Manual Installation:**
```bash
git clone https://github.com/alireza787b/mavsdk_drone_show.git
cd mavsdk_drone_show
sudo ./tools/mds_gcs_init.sh
```

See [GCS Setup Guide](docs/guides/gcs-setup.md) for detailed instructions, CLI options, and troubleshooting.

### Hardware Setup (Raspberry Pi)

For Raspberry Pi deployment, use the enterprise-grade initialization script:

**One-Line Installation (Fresh Raspbian):**
```bash
curl -fsSL https://raw.githubusercontent.com/alireza787b/mavsdk_drone_show/main-candidate/tools/install_rpi.sh | sudo bash
```

**With Drone ID (Non-Interactive):**
```bash
curl -fsSL https://raw.githubusercontent.com/alireza787b/mavsdk_drone_show/main-candidate/tools/install_rpi.sh | sudo bash -s -- -d 1 -y
```

**Using Your Own Fork:**
```bash
curl -fsSL ... | sudo bash -s -- --fork yourusername -d 1 -y
```

**Manual Installation (Already Cloned):**
```bash
cd ~/mavsdk_drone_show
sudo ./tools/mds_init.sh -d <DRONE_ID> -y
```

📖 **Hardware Setup Guides:**
- **[MDS Init Setup Guide](docs/guides/mds-init-setup.md)** - Complete Raspberry Pi initialization
- **[CLI Reference](docs/guides/mds-init-cli-reference.md)** - All command-line options
- **[Headless Automation](docs/guides/headless-automation.md)** - Fleet provisioning and CI/CD
- **[Troubleshooting](docs/guides/mds-init-troubleshooting.md)** - Common issues and solutions

---

## Documentation

### 📚 Documentation Index

All project documentation is organized in the `docs/` folder:

📖 **[Documentation Index](docs/README.md)** - Complete guide to all available documentation

### Quick Links

| Category | Description | Link |
|----------|-------------|------|
| **Quick Start** | Fast SITL demo setup | [docs/guides/sitl-comprehensive.md](docs/guides/sitl-comprehensive.md) |
| **Guides** | Comprehensive setup and configuration | [docs/guides/](docs/guides/) |
| **Features** | Detailed feature documentation | [docs/features/](docs/features/) |
| **Hardware** | Hardware-specific guides | [docs/hardware/](docs/hardware/) |
| **API** | API documentation | [docs/api/](docs/api/) |
| **Versioning** | Version management workflow | [docs/VERSIONING.md](docs/VERSIONING.md) |

### Key Guides

- **[SITL Comprehensive Guide](docs/guides/sitl-comprehensive.md)** - Full SITL setup and usage
- **[Advanced SITL Configuration](docs/guides/advanced-sitl.md)** - Custom deployments
- **[CSV Migration Guide](docs/guides/csv-migration.md)** - Configuration format migration
- **[Python Compatibility](docs/guides/python-compatibility.md)** - Python version requirements
- **[Swarm Trajectory Feature](docs/features/swarm-trajectory.md)** - Smart swarm capabilities
- **[Origin System](docs/features/origin-system.md)** - Coordinate system implementation
- **[Control Modes and Coordinates](docs/control-modes-and-coordinates.md)** - Comprehensive control modes, coordinate systems, and Phase 2 reference

---

## Version & Changelog

**Current Version: 5.0** (February 2026)

Major updates in this version:
- **QuickScout SAR Module**: Cooperative multi-drone search & rescue survey mode with boustrophedon coverage planning, PX4 Mission Mode execution, and real-time progress monitoring
- **Automated mavlink-router Integration**: Dashboard binary auto-download, systemd service setup
- **RPi Bootstrap Installer**: One-line curl installation for fresh Raspbian
- **Flask Removed**: Backend is now FastAPI only

📖 **[Full Changelog](CHANGELOG.md)** - Complete version history from v0.1 to current

📖 **[Versioning Guide](docs/VERSIONING.md)** - How we manage versions and releases

---

## 🏢 Licensing & Commercial Use

**MDS uses dual licensing to support everyone - from students to enterprises.**

### Free Licenses

✅ **PolyForm Noncommercial** - For education, research, non-profits
- Students, teachers, researchers
- Non-profit organizations
- Personal hobbyist projects
- Unlimited drones for non-commercial use

✅ **PolyForm Small Business** - For small commercial operations
- **FREE if ALL apply:**
  - < 100 employees/contractors
  - < $1M USD annual revenue
  - **< 10 drones per operation**
- Perfect for startups and small businesses

📄 **[See LICENSE for full details →](LICENSE)**

### Commercial License (Large Operations)

📄 **Required if ANY apply:**
- 100+ employees, OR
- $1M+ revenue, OR
- **10+ drones in operation**

**[Commercial licensing information →](LICENSE-COMMERCIAL.md)**

### Professional Services

Whether you need a license or implementation support:

- 💼 **Commercial Licensing** - Flexible terms for large-scale use
- ✈️ **Custom Development** - Specialized features
- 🚁 **Hardware Implementation** - Real drone deployment
- 🏢 **Enterprise Integration** - Custom APIs and systems
- 📊 **Performance Optimization** - Large swarm operations
- 🔧 **Training & Support** - Professional assistance

**Contact:** [p30planets@gmail.com](mailto:p30planets@gmail.com)

---

## Contact & Contributions

We welcome contributions, bug reports, feature suggestions, and commercial inquiries:

- **Email:** [p30planets@gmail.com](mailto:p30planets@gmail.com)
- **LinkedIn:** [Alireza Ghaderi](https://www.linkedin.com/in/alireza787b/)
- **GitHub Issues:** [Report bugs or request features](https://github.com/alireza787b/mavsdk_drone_show/issues)

### Contributing

We welcome code, documentation improvements, Docker recipes, and new swarm algorithms:

1. Fork the repository
2. Create a feature branch from `main-candidate`
3. Make your changes with clear commit messages
4. Submit a pull request with detailed description

See our [Contributing Guide](CONTRIBUTING.md) for more details.

---

## Disclaimer

**⚠️ SAFETY WARNING**

Using offboard mode or live swarm control on real drones carries significant risk. Before attempting any real-world flights:

- Ensure you have the necessary expertise and certifications
- Understand all safety implications and failure modes
- Implement robust failsafe procedures
- Prioritize regulatory compliance and flight safety
- Conduct extensive testing in controlled environments
- Follow all local aviation regulations and laws

**The maintainers assume no liability for damage, injury, or legal consequences resulting from use of this software.**

**📄 [Read full legal disclaimer →](DISCLAIMER.md)**

### Ethical Use Statement

This software is developed for peaceful, educational, and research purposes. While we cannot enforce all uses, we strongly encourage ethical applications that:

- Prioritize safety and regulatory compliance
- Advance education and knowledge
- Respect human rights and dignity
- Consider the societal impact of drone technology

**By using this software, you accept full responsibility for your actions and their consequences.**

---

## Additional Resources

### Official Documentation
- **GitHub Repository:** [https://github.com/alireza787b/mavsdk_drone_show](https://github.com/alireza787b/mavsdk_drone_show)
- **SITL Demo Guide:** [docs/guides/sitl-comprehensive.md](docs/guides/sitl-comprehensive.md)
- **Documentation Index:** [docs/README.md](docs/README.md)

### YouTube Tutorials
- [Project History & Tutorials Playlist](https://www.youtube.com/playlist?list=PLVZvZdBQdm_7ViwRhUFrmLFpFkP3VSakk)
- [IoT-Based Telemetry & Video Drone Concepts](https://www.youtube.com/playlist?list=PLVZvZdBQdm_7E_wxfXWKyZoaK7yucl6w4)

### Related Technologies
- **MAVSDK Documentation:** [https://mavsdk.mavlink.io/](https://mavsdk.mavlink.io/)
- **PX4 Autopilot:** [https://px4.io/](https://px4.io/)
- **Netbird VPN:** [https://docs.netbird.io/](https://docs.netbird.io/)
- **MAVLink2REST:** [https://github.com/mavlink/mavlink2rest](https://github.com/mavlink/mavlink2rest)
- **SkyBrush Drone Show Tool:** [https://skybrush.io/](https://skybrush.io/)

---

## License

© 2025 Alireza Ghaderi

### Dual Licensing

This software is available under multiple licenses to support different users:

**📄 [LICENSE](LICENSE)** - Main license file with decision guide

**Free Licenses:**
- **[PolyForm Noncommercial](LICENSE-NONCOMMERCIAL.md)** - Education, research, non-profits
- **[PolyForm Small Business](LICENSE-SMALL-BUSINESS.md)** - Small commercial (< 10 drones, < 100 employees, < $1M revenue)

**Commercial License:**
- **[Commercial Licensing](LICENSE-COMMERCIAL.md)** - Large operations (10+ drones, 100+ employees, or $1M+ revenue)

### Key Terms

**Attribution Required:** All uses must credit the original project

**Free Small Commercial:** Operations with < 10 drones, < 100 employees, and < $1M revenue can use for FREE

**Large Commercial:** Contact p30planets@gmail.com for licensing

### Legal

**📄 [Full License Details →](LICENSE)**
**📄 [Legal Disclaimer →](DISCLAIMER.md)**
**📄 [Ethical Use Statement →](ETHICAL-USE.md)**

---

**⭐ If you find this project useful, please consider giving it a star on GitHub!**
