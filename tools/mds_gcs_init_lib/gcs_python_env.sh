#!/bin/bash
# =============================================================================
# MDS GCS Initialization Library: Python Environment
# =============================================================================
# Version: 1.0.0
# Description: Create venv and install Python requirements
# Author: MDS Team
# =============================================================================

# Prevent double-sourcing
[[ -n "${_MDS_GCS_PYTHON_ENV_LOADED:-}" ]] && return 0
_MDS_GCS_PYTHON_ENV_LOADED=1

# =============================================================================
# VENV MANAGEMENT
# =============================================================================

# Get the venv path
get_venv_path() {
    local install_dir="${GCS_INSTALL_DIR:-$(pwd)}"
    echo "${install_dir}/venv"
}

# Check if venv exists and is valid
check_venv_exists() {
    local venv_path
    venv_path=$(get_venv_path)

    [[ -d "$venv_path" ]] && [[ -f "${venv_path}/bin/activate" ]] && [[ -f "${venv_path}/bin/python" ]]
}

# Create Python virtual environment
create_venv() {
    local venv_path
    venv_path=$(get_venv_path)
    local python_cmd
    python_cmd=$(gcs_state_get_value "python_command" "python3.11")

    log_step "Creating Python virtual environment..."
    log_info "Python: $python_cmd"
    log_info "Venv path: $venv_path"

    if is_dry_run; then
        echo -e "  ${DIM}[DRY-RUN] Would create venv at: $venv_path${NC}"
        return 0
    fi

    # Remove existing venv if corrupted
    if [[ -d "$venv_path" ]] && ! check_venv_exists; then
        log_warn "Removing corrupted venv..."
        rm -rf "$venv_path"
    fi

    # Create venv
    if ! check_venv_exists; then
        if "$python_cmd" -m venv "$venv_path" 2>/dev/null; then
            log_success "Virtual environment created"
        else
            log_error "Failed to create virtual environment"
            return 1
        fi
    else
        log_info "Virtual environment already exists"
    fi

    return 0
}

# Upgrade pip in venv
upgrade_pip() {
    local venv_path
    venv_path=$(get_venv_path)
    local pip_cmd="${venv_path}/bin/pip"

    log_step "Upgrading pip..."

    if is_dry_run; then
        echo -e "  ${DIM}[DRY-RUN] Would upgrade pip${NC}"
        return 0
    fi

    if "$pip_cmd" install --upgrade pip 2>/dev/null; then
        local pip_version
        pip_version=$("$pip_cmd" --version 2>/dev/null | grep -oP '\d+\.\d+\.\d+' | head -1)
        log_success "pip upgraded to $pip_version"
        return 0
    else
        log_warn "Failed to upgrade pip (continuing anyway)"
        return 0
    fi
}

# =============================================================================
# REQUIREMENTS INSTALLATION
# =============================================================================

# Install requirements from requirements.txt
# Note: requirements.txt uses platform markers to skip RPi packages on x86
install_requirements() {
    local install_dir="${GCS_INSTALL_DIR:-$(pwd)}"
    local venv_path
    venv_path=$(get_venv_path)
    local pip_cmd="${venv_path}/bin/pip"
    local requirements_file="${install_dir}/requirements.txt"

    log_step "Installing Python requirements..."

    if is_dry_run; then
        echo -e "  ${DIM}[DRY-RUN] Would install from: $requirements_file${NC}"
        return 0
    fi

    # Check if requirements file exists
    if [[ ! -f "$requirements_file" ]]; then
        log_error "Requirements file not found at: $requirements_file"
        return 1
    fi

    # Count packages
    local pkg_count
    pkg_count=$(grep -c "^[^#]" "$requirements_file" 2>/dev/null || echo "0")
    log_info "Installing $pkg_count packages from $(basename "$requirements_file")..."
    log_info "This may take a few minutes..."

    # Install requirements with visible output for errors
    if "$pip_cmd" install -r "$requirements_file"; then
        log_success "Python requirements installed"
        return 0
    else
        echo ""
        log_error "Failed to install some requirements"
        echo ""
        echo -e "  ${YELLOW}Troubleshooting:${NC}"
        echo -e "  1. Check internet connection"
        echo -e "  2. Ensure build tools: ${CYAN}sudo apt install build-essential${NC}"
        echo -e "  3. Try manually: ${CYAN}source ${venv_path}/bin/activate && pip install -r $(basename "$requirements_file")${NC}"
        echo -e "  4. Check for specific package errors above"
        echo ""
        return 1
    fi
}

# Verify critical packages are installed
verify_packages() {
    local venv_path
    venv_path=$(get_venv_path)
    local python_cmd="${venv_path}/bin/python"

    log_step "Verifying critical packages..."

    if is_dry_run; then
        echo -e "  ${DIM}[DRY-RUN] Would verify packages${NC}"
        return 0
    fi

    local all_ok=true

    for pkg in "${GCS_PYTHON_PACKAGES[@]}"; do
        if "$python_cmd" -c "import $pkg" 2>/dev/null; then
            log_debug "Package verified: $pkg"
        else
            log_warn "Package not available: $pkg"
            all_ok=false
        fi
    done

    if [[ "$all_ok" == "true" ]]; then
        log_success "All critical packages verified"
        return 0
    else
        log_warn "Some packages may be missing (this might be OK)"
        return 0
    fi
}

# =============================================================================
# MAIN PHASE RUNNER
# =============================================================================

run_python_env_phase() {
    print_phase_header "6" "Python Environment" "9"

    # Check skip flag
    if [[ "${SKIP_PYTHON_ENV:-false}" == "true" ]]; then
        log_info "Skipping Python environment setup (--skip-python-env)"
        return 0
    fi

    local install_dir="${GCS_INSTALL_DIR:-$(pwd)}"

    # Verify we're in the right directory
    if [[ ! -f "${install_dir}/requirements.txt" ]]; then
        log_error "requirements.txt not found in: $install_dir"
        log_error "Please ensure repository is cloned first"
        return 1
    fi

    print_section "Virtual Environment"
    create_venv || return 1
    upgrade_pip || return 1

    print_section "Package Installation"
    install_requirements || return 1
    verify_packages || return 1

    # Store venv path in state
    local venv_path
    venv_path=$(get_venv_path)
    gcs_state_set_value "venv_path" "$venv_path"

    echo ""
    log_success "Python environment phase completed"
    return 0
}
