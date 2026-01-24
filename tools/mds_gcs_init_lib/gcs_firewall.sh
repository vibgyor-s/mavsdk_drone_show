#!/bin/bash
# =============================================================================
# MDS GCS Initialization Library: Firewall Configuration
# =============================================================================
# Version: 1.0.0
# Description: Configure UFW with GCS-specific ports
# Author: MDS Team
# =============================================================================

# Prevent double-sourcing
[[ -n "${_MDS_GCS_FIREWALL_LOADED:-}" ]] && return 0
_MDS_GCS_FIREWALL_LOADED=1

# =============================================================================
# FIREWALL CHECKS
# =============================================================================

# Check if UFW is installed
check_ufw_installed() {
    command_exists ufw
}

# Check if UFW is active
check_ufw_active() {
    ufw status 2>/dev/null | grep -qi "status: active"
}

# =============================================================================
# UFW CONFIGURATION
# =============================================================================

# Enable UFW
enable_ufw() {
    log_step "Enabling UFW firewall..."

    if is_dry_run; then
        echo -e "  ${DIM}[DRY-RUN] Would enable UFW${NC}"
        return 0
    fi

    # Set default policies
    ufw default deny incoming 2>/dev/null
    ufw default allow outgoing 2>/dev/null

    # Enable UFW (non-interactive)
    if echo "y" | ufw enable 2>/dev/null; then
        log_success "UFW enabled"
        return 0
    else
        log_error "Failed to enable UFW"
        return 1
    fi
}

# Open a single port
open_port() {
    local port_proto="$1"
    local description="$2"
    local port="${port_proto%/*}"
    local proto="${port_proto#*/}"

    log_debug "Opening port: $port/$proto ($description)"

    if is_dry_run; then
        echo -e "  ${DIM}[DRY-RUN] Would open: $port/$proto - $description${NC}"
        return 0
    fi

    if ufw allow "$port/$proto" comment "$description" 2>/dev/null; then
        return 0
    else
        # Try without comment (older UFW versions)
        ufw allow "$port/$proto" 2>/dev/null
    fi
}

# Open all GCS ports
open_gcs_ports() {
    log_step "Opening GCS ports..."

    local count=0
    local total=${#GCS_PORTS[@]}

    for port_proto in "${!GCS_PORTS[@]}"; do
        local description="${GCS_PORTS[$port_proto]}"
        ((count++))

        if is_dry_run; then
            echo -e "  ${DIM}[DRY-RUN] [$count/$total] $port_proto - $description${NC}"
        else
            open_port "$port_proto" "$description"
            echo -e "  ${CHECK} [$count/$total] ${port_proto} - ${description}"
        fi
    done

    return 0
}

# Display firewall rules summary
show_firewall_summary() {
    log_step "Current firewall rules:"
    echo ""

    if is_dry_run; then
        echo -e "  ${DIM}[DRY-RUN] Would show UFW status${NC}"
        return 0
    fi

    # Show UFW status in a formatted way
    ufw status numbered 2>/dev/null | while IFS= read -r line; do
        echo "  $line"
    done

    echo ""
}

# =============================================================================
# MAIN PHASE RUNNER
# =============================================================================

run_firewall_phase() {
    print_phase_header "5" "Firewall Configuration" "9"

    # Check skip flag
    if [[ "${SKIP_FIREWALL:-false}" == "true" ]]; then
        log_info "Skipping firewall configuration (--skip-firewall)"
        return 0
    fi

    print_section "UFW Check"

    # Check if UFW is installed
    if ! check_ufw_installed; then
        log_error "UFW is not installed. Installing..."
        if is_dry_run; then
            echo -e "  ${DIM}[DRY-RUN] Would install UFW${NC}"
        else
            apt-get install -y -qq ufw 2>/dev/null || {
                log_error "Failed to install UFW"
                return 1
            }
        fi
    fi

    log_success "UFW is installed"

    print_section "Port Configuration"

    # Display port list
    echo ""
    echo -e "  ${WHITE}GCS Required Ports:${NC}"
    echo -e "  ${DIM}───────────────────────────────────────────────────────────────${NC}"
    printf "  ${WHITE}%-12s %-10s %s${NC}\n" "PORT" "PROTO" "DESCRIPTION"
    echo -e "  ${DIM}───────────────────────────────────────────────────────────────${NC}"

    for port_proto in "${!GCS_PORTS[@]}"; do
        local port="${port_proto%/*}"
        local proto="${port_proto#*/}"
        local desc="${GCS_PORTS[$port_proto]}"
        printf "  %-12s %-10s %s\n" "$port" "$proto" "$desc"
    done

    echo -e "  ${DIM}───────────────────────────────────────────────────────────────${NC}"
    echo ""

    # Ask for confirmation in interactive mode
    if [[ "${NON_INTERACTIVE:-false}" != "true" ]]; then
        if ! confirm "Configure firewall with these ports?" "y"; then
            log_info "Skipping firewall configuration"
            return 0
        fi
    fi

    print_section "Applying Rules"

    # Enable UFW if not active
    if ! check_ufw_active; then
        enable_ufw || return 1
    else
        log_info "UFW already active"
    fi

    # Open all GCS ports
    open_gcs_ports || return 1

    # Reload UFW
    if ! is_dry_run; then
        ufw reload 2>/dev/null
    fi

    print_section "Summary"
    show_firewall_summary

    echo ""
    log_success "Firewall phase completed"
    return 0
}
