#!/bin/bash
# =============================================================================
# MDS GCS Initialization Library: Node.js Environment
# =============================================================================
# Version: 1.0.0
# Description: Install npm dependencies for React dashboard
# Author: MDS Team
# =============================================================================

# Prevent double-sourcing
[[ -n "${_MDS_GCS_NODEJS_ENV_LOADED:-}" ]] && return 0
_MDS_GCS_NODEJS_ENV_LOADED=1

# =============================================================================
# CONSTANTS
# =============================================================================

readonly GCS_DASHBOARD_SUBDIR="app/dashboard/drone-dashboard"

# =============================================================================
# DASHBOARD PATH
# =============================================================================

# Get the dashboard directory path
get_dashboard_path() {
    local install_dir="${GCS_INSTALL_DIR:-$(pwd)}"
    echo "${install_dir}/${GCS_DASHBOARD_SUBDIR}"
}

# Check if dashboard directory exists
check_dashboard_exists() {
    local dashboard_path
    dashboard_path=$(get_dashboard_path)
    [[ -d "$dashboard_path" ]] && [[ -f "${dashboard_path}/package.json" ]]
}

# Check if node_modules exists
check_node_modules_exists() {
    local dashboard_path
    dashboard_path=$(get_dashboard_path)
    [[ -d "${dashboard_path}/node_modules" ]]
}

# =============================================================================
# NPM OPERATIONS
# =============================================================================

# Install npm dependencies
install_npm_dependencies() {
    local dashboard_path
    dashboard_path=$(get_dashboard_path)

    log_step "Installing npm dependencies..."
    log_info "Dashboard path: $dashboard_path"

    if is_dry_run; then
        echo -e "  ${DIM}[DRY-RUN] Would run: npm ci in $dashboard_path${NC}"
        return 0
    fi

    # Change to dashboard directory
    cd "$dashboard_path" || {
        log_error "Could not change to dashboard directory"
        return 1
    }

    # Try npm ci first (clean install), fall back to npm install
    log_info "Running npm ci (clean install)..."

    # Capture output to properly detect exit code (pipelines hide exit codes)
    local output
    local exit_code

    if output=$(npm ci 2>&1); then
        # Show progress from captured output
        echo "$output" | grep -q "added" && log_debug "$(echo "$output" | grep "added" | tail -1)"
        log_success "npm dependencies installed"
        return 0
    else
        exit_code=$?
        log_warn "npm ci failed (exit code: $exit_code), trying npm install..."

        if output=$(npm install 2>&1); then
            echo "$output" | grep -q "added" && log_debug "$(echo "$output" | grep "added" | tail -1)"
            log_success "npm dependencies installed (via npm install)"
            return 0
        else
            log_error "Failed to install npm dependencies"
            log_debug "npm install output: $output"
            return 1
        fi
    fi
}

# Verify node_modules
verify_node_modules() {
    local dashboard_path
    dashboard_path=$(get_dashboard_path)

    log_step "Verifying node_modules..."

    if is_dry_run; then
        echo -e "  ${DIM}[DRY-RUN] Would verify node_modules${NC}"
        return 0
    fi

    if check_node_modules_exists; then
        # Count packages
        local pkg_count
        pkg_count=$(find "${dashboard_path}/node_modules" -maxdepth 1 -type d | wc -l)
        log_success "node_modules verified ($pkg_count packages)"
        return 0
    else
        log_error "node_modules not found after installation"
        return 1
    fi
}

# Optional: Build production bundle
build_dashboard() {
    local dashboard_path
    dashboard_path=$(get_dashboard_path)

    log_step "Building production bundle (optional)..."

    if is_dry_run; then
        echo -e "  ${DIM}[DRY-RUN] Would run: npm run build${NC}"
        return 0
    fi

    # Check if build script exists
    if ! grep -q "\"build\"" "${dashboard_path}/package.json" 2>/dev/null; then
        log_info "No build script found, skipping"
        return 0
    fi

    cd "$dashboard_path" || return 1

    # Ask for confirmation in interactive mode
    if [[ "${NON_INTERACTIVE:-false}" != "true" ]]; then
        if ! confirm "Build production bundle now? (can be done later)" "n"; then
            log_info "Skipping production build"
            return 0
        fi
    fi

    log_info "Building... (this may take a while)"

    # Capture output to properly detect exit code
    local output
    if output=$(npm run build 2>&1); then
        log_success "Production bundle built"
        gcs_state_set_value "dashboard_built" "true"
        return 0
    else
        log_warn "Build failed (dashboard can still run in development mode)"
        log_debug "Build output: $output"
        return 0
    fi
}

# =============================================================================
# MAIN PHASE RUNNER
# =============================================================================

run_nodejs_env_phase() {
    print_phase_header "7" "Node.js Environment" "9"

    # Check skip flag
    if [[ "${SKIP_NODEJS_ENV:-false}" == "true" ]]; then
        log_info "Skipping Node.js environment setup (--skip-nodejs-env)"
        return 0
    fi

    local install_dir="${GCS_INSTALL_DIR:-$(pwd)}"

    print_section "Dashboard Check"

    # Verify dashboard directory exists
    if ! check_dashboard_exists; then
        log_error "Dashboard not found at: $(get_dashboard_path)"
        log_error "Please ensure repository is cloned first"
        return 1
    fi

    log_success "Dashboard directory found"

    # Check if node_modules already exists
    if check_node_modules_exists; then
        log_info "node_modules already exists"

        if [[ "${NON_INTERACTIVE:-false}" != "true" ]]; then
            if ! confirm "Reinstall npm dependencies?" "n"; then
                log_info "Keeping existing node_modules"
                verify_node_modules
                echo ""
                log_success "Node.js environment phase completed"
                return 0
            fi
        else
            # In non-interactive mode, skip if already installed
            verify_node_modules
            echo ""
            log_success "Node.js environment phase completed"
            return 0
        fi
    fi

    print_section "NPM Installation"
    install_npm_dependencies || return 1
    verify_node_modules || return 1

    print_section "Production Build"
    build_dashboard  # Optional, failure is OK

    # Store dashboard path in state
    gcs_state_set_value "dashboard_path" "$(get_dashboard_path)"

    echo ""
    log_success "Node.js environment phase completed"
    return 0
}
