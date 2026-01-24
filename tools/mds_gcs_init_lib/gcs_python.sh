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

readonly GCS_PYTHON_TARGET="python3.11"
readonly GCS_PYTHON_APT_PACKAGES=("python3.11" "python3.11-venv" "python3.11-dev" "python3.11-distutils")

# =============================================================================
# PYTHON CHECKS
# =============================================================================

# Check if Python 3.11+ is available
check_python_available() {
    # Check for python3.11 specifically
    if command_exists python3.11; then
        local version
        version=$(get_python_version "python3.11")
        log_debug "Found python3.11: $version"
        return 0
    fi

    # Check if default python3 is >= 3.11
    if command_exists python3; then
        local version
        version=$(get_python_version "python3")
        if [[ -n "$version" ]]; then
            local major_minor="${version%.*}"
            major_minor="${major_minor//./}"
            if [[ "$major_minor" -ge 311 ]]; then
                log_debug "Found python3 >= 3.11: $version"
                return 0
            fi
        fi
    fi

    return 1
}

# Get the best available Python 3.11+ command
get_python_command() {
    if command_exists python3.11; then
        echo "python3.11"
    elif command_exists python3; then
        local version
        version=$(get_python_version "python3")
        if [[ -n "$version" ]]; then
            local major_minor="${version%.*}"
            major_minor="${major_minor//./}"
            if [[ "$major_minor" -ge 311 ]]; then
                echo "python3"
            fi
        fi
    fi
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
    if add-apt-repository -y ppa:deadsnakes/ppa 2>/dev/null; then
        log_success "deadsnakes PPA added"
        apt-get update -qq 2>/dev/null
        return 0
    else
        log_error "Failed to add deadsnakes PPA"
        return 1
    fi
}

# =============================================================================
# PYTHON INSTALLATION
# =============================================================================

# Install Python 3.11
install_python() {
    log_step "Installing Python 3.11..."

    if is_dry_run; then
        echo -e "  ${DIM}[DRY-RUN] Would install: ${GCS_PYTHON_APT_PACKAGES[*]}${NC}"
        return 0
    fi

    local packages_to_install=()
    for pkg in "${GCS_PYTHON_APT_PACKAGES[@]}"; do
        if ! dpkg -l "$pkg" 2>/dev/null | grep -q "^ii"; then
            packages_to_install+=("$pkg")
        fi
    done

    if [[ ${#packages_to_install[@]} -eq 0 ]]; then
        log_success "Python 3.11 packages already installed"
        return 0
    fi

    log_info "Installing: ${packages_to_install[*]}"

    if DEBIAN_FRONTEND=noninteractive apt-get install -y -qq "${packages_to_install[@]}" 2>/dev/null; then
        log_success "Python 3.11 installed"
        return 0
    else
        log_error "Failed to install Python 3.11"
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

    # Check if Python 3.11+ already available
    if check_python_available; then
        local python_cmd
        python_cmd=$(get_python_command)
        local version
        version=$(get_python_version "$python_cmd")
        log_success "Python 3.11+ already installed: $version"
        gcs_state_set_value "python_version" "$version"
        gcs_state_set_value "python_command" "$python_cmd"
        return 0
    fi

    print_section "PPA Setup"

    # Determine OS - only use deadsnakes for Ubuntu
    local os_info
    os_info=$(get_os_info)
    local os_id="${os_info%%:*}"

    if [[ "$os_id" == "ubuntu" ]]; then
        add_deadsnakes_ppa || return 1
    else
        log_warn "Not Ubuntu - attempting direct Python 3.11 installation"
    fi

    print_section "Installation"
    install_python || return 1
    verify_python || return 1

    echo ""
    log_success "Python phase completed"
    return 0
}
