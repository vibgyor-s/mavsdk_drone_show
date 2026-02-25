#!/bin/bash
# =============================================================================
# MDS GCS Initialization Library: Python Installation
# =============================================================================
# Version: 1.0.0
# Description: Install Python 3.11+ from deadsnakes PPA
# Author: MDS Team
# =============================================================================

# Prevent double-sourcing
[[ -n "${_MDS_GCS_PYTHON_LOADED:-}" ]] && return 0
_MDS_GCS_PYTHON_LOADED=1

# =============================================================================
# CONSTANTS
# =============================================================================

# Note: GCS_PYTHON_MIN_VERSION is defined in gcs_common.sh

# Get required packages for a specific Python version
get_python_packages() {
    local version="$1"  # e.g., "3.11" or "3.12"
    echo "python${version}" "python${version}-venv" "python${version}-dev"
}

# =============================================================================
# PYTHON CHECKS
# =============================================================================

# Get Python major.minor version (e.g., "3.12")
get_python_major_minor() {
    local python_cmd="$1"
    "$python_cmd" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null
}

# Check if Python version meets minimum requirement
check_python_version_ok() {
    local version="$1"
    local min_version="$GCS_PYTHON_MIN_VERSION"

    # Compare versions (3.11 -> 311, 3.12 -> 312)
    local version_num="${version//./}"
    local min_num="${min_version//./}"

    [[ "$version_num" -ge "$min_num" ]]
}

# Check if Python 3.11+ is available
check_python_available() {
    # Check default python3 first
    if command_exists python3; then
        local version
        version=$(get_python_major_minor "python3")
        if [[ -n "$version" ]] && check_python_version_ok "$version"; then
            log_debug "Found python3: $version"
            return 0
        fi
    fi

    # Check for specific versions (3.12, 3.11)
    for ver in "3.12" "3.11"; do
        if command_exists "python$ver"; then
            log_debug "Found python$ver"
            return 0
        fi
    done

    return 1
}

# Get the best available Python 3.11+ command
get_python_command() {
    # Check default python3 first
    if command_exists python3; then
        local version
        version=$(get_python_major_minor "python3")
        if [[ -n "$version" ]] && check_python_version_ok "$version"; then
            echo "python3"
            return
        fi
    fi

    # Check for specific versions (3.12, 3.11)
    for ver in "3.12" "3.11"; do
        if command_exists "python$ver"; then
            echo "python$ver"
            return
        fi
    done
}

# =============================================================================
# DEADSNAKES PPA
# =============================================================================

# Add deadsnakes PPA for Python
add_deadsnakes_ppa() {
    log_step "Adding deadsnakes PPA for Python..."

    if is_dry_run; then
        echo -e "  ${DIM}[DRY-RUN] Would add deadsnakes PPA${NC}"
        return 0
    fi

    # Check if already added
    if [[ -f /etc/apt/sources.list.d/deadsnakes-ubuntu-ppa-*.list ]] || \
       grep -rq "deadsnakes" /etc/apt/sources.list.d/ 2>/dev/null; then
        log_info "deadsnakes PPA already configured"
        return 0
    fi

    # Add PPA
    start_progress "Adding deadsnakes PPA" "may take 30-60s"
    add-apt-repository -y ppa:deadsnakes/ppa >/dev/null 2>&1
    local rc=$?
    stop_progress

    if [[ $rc -eq 0 ]]; then
        log_success "deadsnakes PPA added"
        start_progress "Updating package lists" "refreshing after PPA add"
        apt-get update -qq >/dev/null 2>&1
        stop_progress
        return 0
    else
        log_error "Failed to add deadsnakes PPA"
        return 1
    fi
}

# =============================================================================
# PYTHON INSTALLATION
# =============================================================================

# Install Python and venv packages for a specific version
install_python() {
    local target_version="${1:-3.11}"
    log_step "Installing Python $target_version packages..."

    # Get required packages for this version
    local packages
    packages=$(get_python_packages "$target_version")

    if is_dry_run; then
        echo -e "  ${DIM}[DRY-RUN] Would install: $packages${NC}"
        return 0
    fi

    local packages_to_install=()
    for pkg in $packages; do
        if ! dpkg -l "$pkg" 2>/dev/null | grep -q "^ii"; then
            packages_to_install+=("$pkg")
        fi
    done

    if [[ ${#packages_to_install[@]} -eq 0 ]]; then
        log_success "Python $target_version packages already installed"
        return 0
    fi

    log_info "Installing: ${packages_to_install[*]}"

    start_progress "Installing Python $target_version" "may take 1-2 min"
    DEBIAN_FRONTEND=noninteractive apt-get install -y "${packages_to_install[@]}" >/dev/null 2>&1
    local rc=$?
    stop_progress

    if [[ $rc -eq 0 ]]; then
        log_success "Python $target_version packages installed"
        return 0
    else
        log_error "Failed to install Python $target_version packages"
        return 1
    fi
}

# Ensure venv and dev packages are installed for the detected Python version
ensure_python_packages() {
    local python_cmd="$1"
    local version
    version=$(get_python_major_minor "$python_cmd")

    if [[ -z "$version" ]]; then
        log_error "Could not detect Python version"
        return 1
    fi

    log_step "Ensuring Python $version packages..."

    # Packages needed for venv and compiling C extensions
    local packages=("python${version}-venv" "python${version}-dev")
    local packages_to_install=()

    for pkg in "${packages[@]}"; do
        if ! dpkg -l "$pkg" 2>/dev/null | grep -q "^ii"; then
            packages_to_install+=("$pkg")
        fi
    done

    if [[ ${#packages_to_install[@]} -eq 0 ]]; then
        log_info "All Python $version packages already installed"
        return 0
    fi

    log_info "Installing: ${packages_to_install[*]}"

    start_progress "Installing Python $version packages"
    DEBIAN_FRONTEND=noninteractive apt-get install -y "${packages_to_install[@]}" >/dev/null 2>&1
    local rc=$?
    stop_progress

    if [[ $rc -eq 0 ]]; then
        log_success "Python $version packages installed"
        return 0
    else
        log_error "Failed to install Python packages"
        log_info "Try manually: sudo apt install ${packages_to_install[*]}"
        return 1
    fi
}

# Verify Python installation
verify_python() {
    log_step "Verifying Python installation..."

    if is_dry_run; then
        echo -e "  ${DIM}[DRY-RUN] Would verify Python installation${NC}"
        return 0
    fi

    local python_cmd
    python_cmd=$(get_python_command)

    if [[ -z "$python_cmd" ]]; then
        log_error "Python 3.11+ not found after installation"
        return 1
    fi

    local version
    version=$(get_python_version "$python_cmd")
    log_success "Python verified: $python_cmd ($version)"

    # Store in state
    gcs_state_set_value "python_version" "$version"
    gcs_state_set_value "python_command" "$python_cmd"

    return 0
}

# =============================================================================
# MAIN PHASE RUNNER
# =============================================================================

run_python_phase() {
    print_phase_header "2" "Python Installation" "9"

    # Check skip flag
    if [[ "${SKIP_PYTHON:-false}" == "true" ]]; then
        log_info "Skipping Python installation (--skip-python)"
        return 0
    fi

    print_section "Python Check"

    local python_cmd=""
    local python_version=""

    # Check if Python 3.11+ already available
    if check_python_available; then
        python_cmd=$(get_python_command)
        python_version=$(get_python_major_minor "$python_cmd")
        log_success "Python ${python_version} found: $python_cmd"

        # Ensure venv and dev packages are installed for this version
        ensure_python_packages "$python_cmd" || {
            log_warn "Could not install Python packages automatically"
            log_info "Please run: sudo apt install python${python_version}-venv python${python_version}-dev"
        }

        gcs_state_set_value "python_version" "$python_version"
        gcs_state_set_value "python_command" "$python_cmd"

        echo ""
        log_success "Python phase completed"
        return 0
    fi

    # Python not found - need to install
    print_section "PPA Setup"

    # Determine OS - only use deadsnakes for Ubuntu
    local os_info
    os_info=$(get_os_info)
    local os_id="${os_info%%:*}"

    if [[ "$os_id" == "ubuntu" ]]; then
        add_deadsnakes_ppa || return 1
    else
        log_warn "Not Ubuntu - attempting direct Python installation"
    fi

    print_section "Installation"
    install_python "3.11" || return 1
    verify_python || return 1

    echo ""
    log_success "Python phase completed"
    return 0
}
