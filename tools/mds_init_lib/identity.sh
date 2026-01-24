#!/bin/bash
# =============================================================================
# MDS Initialization Library: Hardware Identity
# =============================================================================
# Version: 4.0.0
# Description: Hardware ID file creation, hostname configuration, real.mode marker
# Author: MDS Team
# =============================================================================

# Prevent double-sourcing
[[ -n "${_MDS_IDENTITY_LOADED:-}" ]] && return 0
_MDS_IDENTITY_LOADED=1

# =============================================================================
# HARDWARE ID FUNCTIONS
# =============================================================================

# Remove existing hwID files
cleanup_old_hwid_files() {
    log_step "Cleaning up old hwID files..."

    if is_dry_run; then
        echo -e "  ${DIM}[DRY-RUN] Would remove old .hwID files${NC}"
        return 0
    fi

    local count=0
    for hwid_file in "${MDS_INSTALL_DIR}"/*.hwID; do
        if [[ -f "$hwid_file" ]]; then
            rm -f "$hwid_file"
            ((count++))
        fi
    done

    if [[ $count -gt 0 ]]; then
        log_info "Removed $count old hwID file(s)"
    fi

    return 0
}

# Create hardware ID file
create_hwid_file() {
    local drone_id="$1"

    log_step "Creating hardware ID file..."

    if ! validate_drone_id "$drone_id"; then
        log_error "Invalid drone ID: $drone_id (must be 1-999)"
        return 1
    fi

    if is_dry_run; then
        echo -e "  ${DIM}[DRY-RUN] Would create: ${MDS_INSTALL_DIR}/${drone_id}.hwID${NC}"
        return 0
    fi

    # Remove old hwID files first
    cleanup_old_hwid_files

    # Create new hwID file
    local hwid_file="${MDS_INSTALL_DIR}/${drone_id}.hwID"
    touch "$hwid_file"
    chown "${MDS_USER}:${MDS_USER}" "$hwid_file"
    chmod 644 "$hwid_file"

    log_success "Hardware ID file created: ${drone_id}.hwID"
    state_set_value "hw_id" "$drone_id"
    return 0
}

# Create real.mode marker file
create_realmode_file() {
    log_step "Creating real.mode marker..."

    local realmode_file="${MDS_INSTALL_DIR}/real.mode"

    if is_dry_run; then
        echo -e "  ${DIM}[DRY-RUN] Would create: ${realmode_file}${NC}"
        return 0
    fi

    if [[ -f "$realmode_file" ]]; then
        log_info "real.mode file already exists"
        return 0
    fi

    touch "$realmode_file"
    chown "${MDS_USER}:${MDS_USER}" "$realmode_file"
    chmod 644 "$realmode_file"

    log_success "real.mode marker created"
    return 0
}

# Get current hardware ID from existing file
get_current_hwid() {
    for hwid_file in "${MDS_INSTALL_DIR}"/*.hwID; do
        if [[ -f "$hwid_file" ]]; then
            basename "$hwid_file" .hwID
            return 0
        fi
    done
    echo ""
}

# =============================================================================
# HOSTNAME CONFIGURATION
# =============================================================================

# Configure hostname
configure_hostname() {
    local drone_id="$1"
    local new_hostname="drone${drone_id}"

    log_step "Configuring hostname..."

    local current_hostname
    current_hostname=$(hostname)

    if [[ "$current_hostname" == "$new_hostname" ]]; then
        log_info "Hostname already set to: $new_hostname"
        return 0
    fi

    if is_dry_run; then
        echo -e "  ${DIM}[DRY-RUN] Would set hostname: ${current_hostname} -> ${new_hostname}${NC}"
        return 0
    fi

    log_info "Changing hostname: $current_hostname -> $new_hostname"

    # Update /etc/hostname
    echo "$new_hostname" > /etc/hostname

    # Update /etc/hosts
    update_hosts_file "$current_hostname" "$new_hostname"

    # Apply hostname change
    hostnamectl set-hostname "$new_hostname" 2>/dev/null || hostname "$new_hostname"

    log_success "Hostname configured: $new_hostname"
    state_set_value "hostname" "$new_hostname"
    return 0
}

# Update /etc/hosts file
update_hosts_file() {
    local old_hostname="$1"
    local new_hostname="$2"

    log_step "Updating /etc/hosts..."

    if is_dry_run; then
        echo -e "  ${DIM}[DRY-RUN] Would update /etc/hosts${NC}"
        return 0
    fi

    # Backup hosts file
    backup_file "/etc/hosts"

    # Remove old hostname entries if they exist
    sed -i "s/\b${old_hostname}\b/${new_hostname}/g" /etc/hosts 2>/dev/null || true

    # Ensure localhost entries exist
    if ! grep -q "127.0.0.1.*localhost" /etc/hosts; then
        echo "127.0.0.1 localhost" >> /etc/hosts
    fi

    if ! grep -q "127.0.1.1.*${new_hostname}" /etc/hosts; then
        # Add or update 127.0.1.1 entry
        if grep -q "^127.0.1.1" /etc/hosts; then
            sed -i "s/^127.0.1.1.*/127.0.1.1\t${new_hostname}/" /etc/hosts
        else
            echo -e "127.0.1.1\t${new_hostname}" >> /etc/hosts
        fi
    fi

    log_success "/etc/hosts updated"
    return 0
}

# =============================================================================
# ENVIRONMENT CONFIGURATION
# =============================================================================

# Setup local.env file
setup_local_env() {
    local drone_id="$1"
    local gcs_ip="${2:-}"
    local repo_url="${3:-}"
    local branch="${4:-}"

    log_step "Setting up local environment configuration..."

    if is_dry_run; then
        echo -e "  ${DIM}[DRY-RUN] Would create: ${MDS_LOCAL_ENV}${NC}"
        return 0
    fi

    # Ensure config directory exists
    mkdir -p "${MDS_CONFIG_DIR}"
    chmod 755 "${MDS_CONFIG_DIR}"

    # Generate local.env content
    local content
    content=$(cat << EOF
# MDS Local Configuration
# Generated by mds_init.sh v${MDS_VERSION} on $(date '+%Y-%m-%d %H:%M:%S')
# This file is loaded by params.py to override default settings
# Do not commit this file to git - it contains drone-specific configuration

# Hardware ID (required)
MDS_HW_ID=${drone_id}

EOF
)

    # Add optional overrides
    if [[ -n "$gcs_ip" ]]; then
        content+="# Ground Control Station IP override
MDS_GCS_IP=${gcs_ip}
"
    fi

    if [[ -n "$repo_url" ]]; then
        content+="# Repository URL override (for custom forks)
MDS_REPO_URL=${repo_url}
"
    fi

    if [[ -n "$branch" ]]; then
        content+="# Branch override
MDS_BRANCH=${branch}
"
    fi

    # Add common optional settings as comments
    content+="
# Optional settings (uncomment to override):
# MDS_LOG_LEVEL=DEBUG
# MDS_LOG_MAX_SIZE_MB=100
# MDS_BACKUP_COUNT=20
# MDS_SIM_MODE=false
# MDS_MAVLINK_PORT=14540
"

    # Write the file
    echo "$content" > "${MDS_LOCAL_ENV}"
    chmod 644 "${MDS_LOCAL_ENV}"

    log_success "Local environment configured: ${MDS_LOCAL_ENV}"
    return 0
}

# Read value from local.env
get_local_env_value() {
    local key="$1"
    local default="${2:-}"

    if [[ -f "${MDS_LOCAL_ENV}" ]]; then
        local value
        value=$(grep "^${key}=" "${MDS_LOCAL_ENV}" 2>/dev/null | cut -d= -f2- | tr -d '"'"'" || echo "")
        [[ -n "$value" ]] && echo "$value" || echo "$default"
    else
        echo "$default"
    fi
}

# Update a value in local.env
update_local_env_value() {
    local key="$1"
    local value="$2"

    if [[ ! -f "${MDS_LOCAL_ENV}" ]]; then
        echo "${key}=${value}" > "${MDS_LOCAL_ENV}"
        return 0
    fi

    if grep -q "^${key}=" "${MDS_LOCAL_ENV}"; then
        sed -i "s|^${key}=.*|${key}=${value}|" "${MDS_LOCAL_ENV}"
    else
        echo "${key}=${value}" >> "${MDS_LOCAL_ENV}"
    fi
}

# =============================================================================
# MAIN IDENTITY RUNNER
# =============================================================================

run_identity_phase() {
    local drone_id="${DRONE_ID:-}"

    print_phase_header "4" "Hardware Identity"

    # Check for existing hardware ID
    local existing_id
    existing_id=$(get_current_hwid)

    if [[ -z "$drone_id" ]]; then
        if [[ -n "$existing_id" ]]; then
            log_info "Found existing hardware ID: $existing_id"

            if [[ "${NON_INTERACTIVE:-false}" != "true" ]]; then
                if confirm "Keep existing hardware ID ($existing_id)?" "y"; then
                    drone_id="$existing_id"
                else
                    prompt_input "Enter new drone ID (1-999)" "1" drone_id
                fi
            else
                drone_id="$existing_id"
            fi
        else
            if [[ "${NON_INTERACTIVE:-false}" == "true" ]]; then
                log_error "Drone ID is required in non-interactive mode (use -d or --drone-id)"
                return 1
            fi

            prompt_input "Enter drone ID (1-999)" "1" drone_id
        fi
    fi

    # Validate drone ID
    if ! validate_drone_id "$drone_id"; then
        log_error "Invalid drone ID: $drone_id (must be 1-999)"
        return 1
    fi

    # Store in global for other phases
    DRONE_ID="$drone_id"
    export DRONE_ID

    # Update state
    state_set_drone_id "$drone_id"

    print_section "Hardware Identity Setup"

    # Create hwID file
    create_hwid_file "$drone_id" || return 1

    # Create real.mode marker
    create_realmode_file || return 1

    # Configure hostname
    configure_hostname "$drone_id" || return 1

    print_section "Environment Configuration"

    # Setup local.env
    setup_local_env "$drone_id" "${GCS_IP:-}" "${REPO_URL:-}" "${BRANCH:-}" || return 1

    echo ""
    log_success "Hardware identity configured for Drone $drone_id"
    return 0
}
