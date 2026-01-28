#!/bin/bash
# =============================================================================
# MDS GCS Initialization Library: Node.js Installation
# =============================================================================
# Version: 4.2.1
# Description: Install Node.js 20.x LTS from NodeSource
# Author: MDS Team
# =============================================================================

# Prevent double-sourcing
[[ -n "${_MDS_GCS_NODEJS_LOADED:-}" ]] && return 0
_MDS_GCS_NODEJS_LOADED=1

# =============================================================================
# CONSTANTS
# =============================================================================

readonly NODESOURCE_URL="https://deb.nodesource.com/setup_20.x"

# =============================================================================
# NODE.JS CHECKS
# =============================================================================

# Check if Node.js is available and meets minimum version
check_nodejs_available() {
    if ! command_exists node; then
        return 1
    fi

    local version
    version=$(get_node_version)
    if [[ -z "$version" ]]; then
        return 1
    fi

    # Extract major version
    local major="${version%%.*}"
    if [[ "$major" -ge "$GCS_NODE_MIN_VERSION" ]]; then
        log_debug "Found Node.js $version (major: $major)"
        return 0
    fi

    return 1
}

# Check if npm is available
check_npm_available() {
    command_exists npm
}

# =============================================================================
# NODESOURCE SETUP
# =============================================================================

# Add NodeSource repository
add_nodesource_repo() {
    log_step "Adding NodeSource repository for Node.js ${GCS_NODE_TARGET_VERSION}.x..."

    if is_dry_run; then
        echo -e "  ${DIM}[DRY-RUN] Would add NodeSource repository${NC}"
        return 0
    fi

    # Check if already added
    if [[ -f /etc/apt/sources.list.d/nodesource.list ]] || \
       grep -rq "nodesource" /etc/apt/sources.list.d/ 2>/dev/null; then
        log_info "NodeSource repository already configured"
        return 0
    fi

    # Download and run NodeSource setup script
    log_info "Downloading NodeSource setup script..."
    if curl -fsSL "$NODESOURCE_URL" | bash - 2>/dev/null; then
        log_success "NodeSource repository added"
        return 0
    else
        log_error "Failed to add NodeSource repository"
        return 1
    fi
}

# =============================================================================
# NODE.JS INSTALLATION
# =============================================================================

# Install Node.js
install_nodejs() {
    log_step "Installing Node.js..."

    if is_dry_run; then
        echo -e "  ${DIM}[DRY-RUN] Would install: nodejs${NC}"
        return 0
    fi

    if dpkg -l nodejs 2>/dev/null | grep -q "^ii"; then
        log_info "Node.js package already installed"
        return 0
    fi

    if DEBIAN_FRONTEND=noninteractive apt-get install -y -qq nodejs 2>/dev/null; then
        log_success "Node.js installed"
        return 0
    else
        log_error "Failed to install Node.js"
        return 1
    fi
}

# Verify Node.js installation
verify_nodejs() {
    log_step "Verifying Node.js installation..."

    if is_dry_run; then
        echo -e "  ${DIM}[DRY-RUN] Would verify Node.js installation${NC}"
        return 0
    fi

    if ! command_exists node; then
        log_error "Node.js not found after installation"
        return 1
    fi

    local node_version
    node_version=$(get_node_version)
    if [[ -z "$node_version" ]]; then
        log_error "Could not determine Node.js version"
        return 1
    fi

    log_success "Node.js verified: v${node_version}"
    gcs_state_set_value "node_version" "$node_version"

    # Check npm
    if ! check_npm_available; then
        log_error "npm not found"
        return 1
    fi

    local npm_version
    npm_version=$(get_npm_version)
    log_success "npm verified: v${npm_version}"
    gcs_state_set_value "npm_version" "$npm_version"

    return 0
}

# =============================================================================
# MAIN PHASE RUNNER
# =============================================================================

run_nodejs_phase() {
    print_phase_header "3" "Node.js Installation" "9"

    # Check skip flag
    if [[ "${SKIP_NODEJS:-false}" == "true" ]]; then
        log_info "Skipping Node.js installation (--skip-nodejs)"
        return 0
    fi

    print_section "Node.js Check"

    # Check if Node.js already available and sufficient
    if check_nodejs_available && check_npm_available; then
        local node_version
        node_version=$(get_node_version)
        local npm_version
        npm_version=$(get_npm_version)
        log_success "Node.js already installed: v${node_version}"
        log_success "npm already installed: v${npm_version}"
        gcs_state_set_value "node_version" "$node_version"
        gcs_state_set_value "npm_version" "$npm_version"
        return 0
    fi

    print_section "Repository Setup"
    add_nodesource_repo || return 1

    print_section "Installation"
    install_nodejs || return 1
    verify_nodejs || return 1

    echo ""
    log_success "Node.js phase completed"
    return 0
}
