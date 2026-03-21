# Advanced SITL Configuration Guide

## Overview

This guide is for advanced users who want to use their own forked repository or custom Docker images with MDS SITL.

> **⚠️ Prerequisites Required:**
> - Good understanding of Git, Docker, and Linux
> - Experience with environment variables and bash commands
> - Ability to maintain forked repositories
> - `p7zip-full` for working with the distributed `.7z` image archives
> - `pv` if you want progress output while exporting large Docker images

> **⚠️ Important Warning:**
> Using custom repositories disconnects you from automatic MDS updates. You'll need to manually sync your fork with upstream changes.

---

## Method 1: Using Environment Variables (Easiest)

### Step 1: Set Your Configuration

Copy and paste these commands, replacing with your repository details. For public GitHub repos, prefer HTTPS unless the container or build environment has working SSH keys.

```bash
# Set your custom repository configuration
export MDS_REPO_URL="https://github.com/YOURORG/YOURREPO.git"
export MDS_BRANCH="your-branch-name"
export MDS_DOCKER_IMAGE="your-custom-image:latest"

# Save to file for future use (optional)
cat > ~/.mds_config << EOF
export MDS_REPO_URL="https://github.com/YOURORG/YOURREPO.git"
export MDS_BRANCH="your-branch-name"
export MDS_DOCKER_IMAGE="your-custom-image:latest"
EOF
```

### Optional: Override Docker SITL Runtime Defaults

`create_dockers.sh` forwards all host `MDS_*` variables into each container, so you can tune the active headless PX4 Gazebo Harmonic launcher without editing the image.

```bash
# Example runtime overrides for startup_sitl.sh
export MDS_PX4_GZ_TARGET="gz_x500"
export MDS_QT_QPA_PLATFORM="offscreen"
export MDS_GZ_PARTITION_PREFIX="px4_sim"
export MDS_SITL_PARAM_OVERRIDES="COM_RC_IN_MODE=4,NAV_RCL_ACT=0,NAV_DLL_ACT=0,COM_DL_LOSS_T=0,CBRK_SUPPLY_CHK=894281,SDLOG_MODE=-1"

# Optional debugging / routing controls
export MDS_SITL_TRACE=0
export MDS_SITL_LOG_TAIL_LINES=40
export MDS_PX4_GCS_PORT=14550
```

Notes:
- `startup_sitl.sh` always runs headless PX4 Gazebo Harmonic in Docker SITL.
- If `MDS_GZ_PARTITION` is unset, startup derives a unique Gazebo partition per drone from `MDS_GZ_PARTITION_PREFIX` and `hw_id`.
- SITL parameter overrides are passed to PX4 via `PX4_PARAM_*` environment variables at launch time, after the airframe defaults load.
- Set `MDS_SITL_PARAM_OVERRIDES=none` if you intentionally want no SITL PX4 parameter overrides.
- `CBRK_SUPPLY_CHK=894281` is the PX4 circuit-breaker value for bypassing the supply check in SITL.
- `startup_sitl.sh` also verifies that `mavsdk_server` exists in the repo root and will provision it automatically if a custom image is missing the binary.
- If you want to pin the MAVSDK server version or URL, export `MDS_MAVSDK_VERSION` or `MDS_MAVSDK_URL` before launching `create_dockers.sh`.
- Running `HEADLESS=1 make px4_sitl gz_x500` manually inside the container is useful for raw PX4 debugging, but it bypasses `startup_sitl.sh`, so it will not apply the MDS `PX4_PARAM_*` overrides or `mavsdk_server` provisioning checks.

### Step 2: Build Custom Docker Image (If Needed)

```bash
# If you need a custom Docker image with your repository:
cd /path/to/mavsdk_drone_show
bash tools/build_custom_image.sh
```

`tools/build_custom_image.sh` now ensures `/root/mavsdk_drone_show/mavsdk_server` exists before committing the image. It also honors `MDS_MAVSDK_VERSION` and `MDS_MAVSDK_URL` if you need to pin or override the binary source. If you build images manually by copying only git-tracked files into a container, you must preserve or re-download `mavsdk_server` or takeoff/mission scripts will fail at runtime. For public GitHub repos, both the runtime launcher and image builder retry over HTTPS automatically if an SSH GitHub URL fails inside the container.

### Step 3: Deploy Your Drones

```bash
# Load your configuration (if saved to file)
source ~/.mds_config

# Deploy drones with your custom configuration
bash multiple_sitl/create_dockers.sh 5

# Start dashboard (development mode by default)
bash app/linux_dashboard_start.sh --sitl

# Production-style launch if needed
# bash app/linux_dashboard_start.sh --prod --sitl
```

---

## Method 2: Using HTTPS Repository (No SSH Keys)

If you don't want to set up SSH keys:

```bash
# Use HTTPS URL instead
export MDS_REPO_URL="https://github.com/YOURORG/YOURREPO.git"
export MDS_BRANCH="your-branch-name"

# Deploy
bash multiple_sitl/create_dockers.sh 5
```

---

## Method 3: Command Line Arguments

Some scripts support direct arguments:

```bash
# Dashboard with custom branch
bash app/linux_dashboard_start.sh --sitl -b your-branch-name

# Build custom image with arguments
bash tools/build_custom_image.sh "https://github.com/YOURORG/YOURREPO.git" "your-branch"
```

---

## Common Examples

### Example 1: Company Fork

```bash
export MDS_REPO_URL="https://github.com/mycompany/mds-fork.git"
export MDS_BRANCH="production"
export MDS_DOCKER_IMAGE="mycompany-drone:v1.0"

bash tools/build_custom_image.sh
bash multiple_sitl/create_dockers.sh 10
```

### Example 2: Development Branch

```bash
export MDS_REPO_URL="https://github.com/myusername/mds-dev.git"
export MDS_BRANCH="feature-branch"

bash multiple_sitl/create_dockers.sh 3
```

### Example 3: Different Environments

```bash
# Development
export MDS_REPO_URL="https://github.com/company/mds.git"
export MDS_BRANCH="develop"
bash multiple_sitl/create_dockers.sh 2

# Production
export MDS_REPO_URL="https://github.com/company/mds.git"
export MDS_BRANCH="production"
bash multiple_sitl/create_dockers.sh 20
```

---

## Getting Help

### Check Script Options

Most scripts have help:

```bash
bash tools/build_custom_image.sh --help
bash multiple_sitl/create_dockers.sh --help
bash app/linux_dashboard_start.sh --help
```

### Verify Your Configuration

```bash
# Check what will be used
echo "Repository: $MDS_REPO_URL"
echo "Branch: $MDS_BRANCH"
echo "Docker Image: $MDS_DOCKER_IMAGE"

# Test repository access
git ls-remote "$MDS_REPO_URL"
```

### Check Container Status

```bash
# See running containers
docker ps

# Check container repository
docker exec drone-1 bash -c "cd /root/mavsdk_drone_show && git remote -v"
```

---

## Troubleshooting

### Problem: SSH Authentication Failed

**Solution:** Use HTTPS instead, or let public GitHub SSH URLs auto-fallback inside the container:
```bash
export MDS_REPO_URL="https://github.com/YOURORG/YOURREPO.git"
```

### Problem: Docker Image Not Found

**Solution:** Build the image first:
```bash
bash tools/build_custom_image.sh
```

### Problem: Containers Using Wrong Repository

**Solution:** Check environment variables are set:
```bash
echo $MDS_REPO_URL
echo $MDS_BRANCH
```

---

## Docker Container Development Workflow

**⚠️ IMPORTANT:** This section is ONLY for creating custom Docker images. For actual SITL drone operations, always use `bash multiple_sitl/create_dockers.sh` which handles hwid generation and proper drone setup.

For advanced users who want to develop inside containers and maintain custom images:

### Step 1: Create Development Container

```bash
# Create a template container directly (avoid create_dockers.sh to prevent hwid generation)
sudo docker run -it --name my-drone-dev drone-template:latest /bin/bash
```

### Step 2: Make Your Changes Inside Container

```bash
# Inside container - make your changes:
cd /root/mavsdk_drone_show

# Update to your repository if needed
git remote set-url origin https://github.com/YOURORG/YOURREPO.git
git pull origin your-branch

# Edit files, test changes, debug issues
# Install new packages, modify configuration
# Make any customizations you need
```

### Step 3: Commit Your Changes

```bash
# Exit the container first
exit

# Commit container to new image version
docker commit -m "Updated custom drone image" my-drone-dev drone-template:v4.0

# Tag as latest (optional)
docker tag drone-template:v4.0 drone-template:latest
```

### Step 4: Export Container (Optional)

```bash
# Install optional helper tools if needed
sudo apt install -y p7zip-full pv

cd ~

# Export to tar file for backup/distribution
docker save drone-template:v4.0 | pv > drone-template-v4.tar

# Optional: compress the tar afterwards for storage or sharing
7z a drone-template-v4.7z drone-template-v4.tar
```

### Step 5: Use Your Custom Image for Real SITL Operations

```bash
# Set your custom image for future SITL deployments
export MDS_DOCKER_IMAGE="drone-template:v4.0"

# NOW use create_dockers.sh for actual SITL drone operations
# (This will properly generate hwid and configure each drone)
bash multiple_sitl/create_dockers.sh 5
```

### Regular Maintenance Workflow

```bash
# Start your development container again (for image updates only)
sudo docker run -it --name my-drone-dev-v2 drone-template:latest /bin/bash

# Make updates inside container
cd /root/mavsdk_drone_show
git pull

# Exit and commit new version
exit
docker commit -m "Updated to latest version" my-drone-dev-v2 drone-template:v4.1
docker tag drone-template:v4.1 drone-template:latest

# Clean up old containers
docker rm my-drone-dev my-drone-dev-v2
```

> **💡 Pro Tip:** This workflow is for customizing Docker images only. For actual SITL drone operations, always use `bash multiple_sitl/create_dockers.sh` which handles proper drone setup, hwid generation, and network configuration.

---

## Commercial Support & Custom Implementation

### For Companies and Real-World Deployments

The basic SITL demo is designed for evaluation and learning. For production deployments, custom features, or hardware implementation, professional support is available:

**Services Available:**
- ✈️ **Custom SITL Features** - Specialized simulation scenarios and advanced functionality
- 🚁 **Hardware Implementation** - Real drone deployment with safety protocols
- 🏢 **Enterprise Integration** - Custom APIs, cloud integration, fleet management
- 📊 **Performance Optimization** - Large-scale swarm optimization and mission planning
- 🔧 **Training & Support** - Team training and ongoing technical support
- 🎯 **Custom Mission Types** - Specialized applications beyond standard formations

**Contact for Professional Implementation:**
- **Email:** [p30planets@gmail.com](mailto:p30planets@gmail.com)
- **LinkedIn:** [Alireza Ghaderi](https://www.linkedin.com/in/alireza787b/)

> **🏢 Note for Companies:** Real-world drone deployments require aviation compliance, safety protocols, and specialized expertise. Contact us for professional consultation and implementation contracts.

---

## Support

For help with advanced configuration:
- **Email:** [p30planets@gmail.com](mailto:p30planets@gmail.com)
- **LinkedIn:** [Alireza Ghaderi](https://www.linkedin.com/in/alireza787b/)

---

*Back to: [Main SITL Guide](sitl-comprehensive.md)*
