#!/bin/bash
# =============================================================================
# MDS GCS Initialization Library: Repository Setup
# =============================================================================
# Version: 4.2.1
# Description: Clone/update repository with SSH key management for WRITE access
# Author: MDS Team
# =============================================================================

# Prevent double-sourcing
[[ -n "${_MDS_GCS_REPO_LOADED:-}" ]] && return 0
_MDS_GCS_REPO_LOADED=1

# =============================================================================
# CONSTANTS
# =============================================================================

readonly GCS_SSH_KEY_PATH="${HOME}/.ssh/mds_gcs_deploy_key"
readonly GCS_SSH_KEY_PUB="${GCS_SSH_KEY_PATH}.pub"

# =============================================================================
# REPOSITORY SELECTION
# =============================================================================

# Prompt user to select repository (default or custom fork)
prompt_repository_selection() {
    # Skip if non-interactive or already have a custom repo URL
    if [[ "${NON_INTERACTIVE:-false}" == "true" ]]; then
        log_info "Using default repository (non-interactive mode)"
        log_info "Repository: alireza787b/mavsdk_drone_show"
        log_info "Branch: ${BRANCH:-main-candidate}"
        return 0
    fi

    # If REPO_URL is already set (via CLI or env), use it
    if [[ -n "${REPO_URL:-}" ]]; then
        log_info "Using provided repository: ${REPO_URL}"
        log_info "Branch: ${BRANCH:-main-candidate}"
        return 0
    fi

    echo ""
    echo -e "${CYAN}+------------------------------------------------------------------------------+${NC}"
    echo -e "${CYAN}|${NC}  ${WHITE}Repository Selection${NC}"
    echo -e "${CYAN}+------------------------------------------------------------------------------+${NC}"
    echo ""
    echo -e "  Default: ${GREEN}github.com/alireza787b/mavsdk_drone_show${NC}"
    echo -e "  Branch:  ${CYAN}${BRANCH:-main-candidate}${NC}"
    echo ""

    if confirm "Use default repository?" "y"; then
        log_info "Using: alireza787b/mavsdk_drone_show (${BRANCH:-main-candidate})"
    else
        echo ""
        echo -e "  ${WHITE}Enter your fork details:${NC}"
        local github_user
        read -p "  GitHub username: " github_user </dev/tty

        if [[ -n "$github_user" ]]; then
            REPO_URL="https://github.com/${github_user}/mavsdk_drone_show.git"
            export REPO_URL
            echo ""
            log_info "Repository: ${REPO_URL}"
            log_info "Branch: ${BRANCH:-main-candidate}"
        else
            log_warn "No username provided, using default repository"
        fi
    fi
    echo ""
}

# =============================================================================
# SSH KEY MANAGEMENT
# =============================================================================

# Generate SSH deploy key
generate_ssh_key() {
    log_step "Generating SSH deploy key..."

    if is_dry_run; then
        echo -e "  ${DIM}[DRY-RUN] Would generate SSH key at: ${GCS_SSH_KEY_PATH}${NC}"
        return 0
    fi

    # Create .ssh directory if needed
    mkdir -p "${HOME}/.ssh"
    chmod 700 "${HOME}/.ssh"

    # Check if key already exists
    if [[ -f "$GCS_SSH_KEY_PATH" ]]; then
        log_info "SSH key already exists: ${GCS_SSH_KEY_PATH}"
        return 0
    fi

    # Generate new key
    local hostname
    hostname=$(hostname)
    local email="mds-gcs@${hostname}"

    if ssh-keygen -t ed25519 -f "$GCS_SSH_KEY_PATH" -N "" -C "$email" 2>/dev/null; then
        chmod 600 "$GCS_SSH_KEY_PATH"
        chmod 644 "$GCS_SSH_KEY_PUB"
        log_success "SSH deploy key generated"
        return 0
    else
        log_error "Failed to generate SSH key"
        return 1
    fi
}

# Display SSH key and instructions
display_ssh_key_instructions() {
    echo ""
    echo -e "${CYAN}+------------------------------------------------------------------------------+${NC}"
    echo -e "${CYAN}|${NC}  ${WHITE}SSH DEPLOY KEY SETUP REQUIRED${NC}"
    echo -e "${CYAN}+------------------------------------------------------------------------------+${NC}"
    echo ""
    echo -e "  ${YELLOW}IMPORTANT: You need to add this deploy key to your GitHub repository.${NC}"
    echo ""
    echo -e "  ${WHITE}Your deploy key (copy this entire key):${NC}"
    echo -e "  ${DIM}───────────────────────────────────────────────────────────────────────────${NC}"
    echo ""
    cat "$GCS_SSH_KEY_PUB"
    echo ""
    echo -e "  ${DIM}───────────────────────────────────────────────────────────────────────────${NC}"
    echo ""
    echo -e "  ${WHITE}Steps to add the deploy key:${NC}"
    echo ""
    echo -e "  1. Go to your repository on GitHub"
    echo -e "  2. Click ${CYAN}Settings${NC} → ${CYAN}Deploy keys${NC} → ${CYAN}Add deploy key${NC}"
    echo -e "  3. Title: ${GREEN}MDS GCS - $(hostname)${NC}"
    echo -e "  4. Paste the key above"
    echo -e "  ${YELLOW}5. CHECK 'Allow write access' (REQUIRED for git sync features)${NC}"
    echo -e "  6. Click ${CYAN}Add key${NC}"
    echo ""
    echo -e "${CYAN}+------------------------------------------------------------------------------+${NC}"

    # Wait for user to read the instructions
    wait_for_keypress "Press any key after copying the key..."
}

# Configure SSH for GitHub
configure_ssh_github() {
    log_step "Configuring SSH for GitHub..."

    if is_dry_run; then
        echo -e "  ${DIM}[DRY-RUN] Would configure SSH for GitHub${NC}"
        return 0
    fi

    local ssh_config="${HOME}/.ssh/config"

    # Check if already configured
    if [[ -f "$ssh_config" ]] && grep -q "mds_gcs_deploy_key" "$ssh_config" 2>/dev/null; then
        log_info "SSH config already set up for MDS GCS"
        return 0
    fi

    # Add GitHub config
    cat >> "$ssh_config" << EOF

# MDS GCS Deploy Key
Host github.com
    HostName github.com
    User git
    IdentityFile ${GCS_SSH_KEY_PATH}
    IdentitiesOnly yes
EOF

    chmod 600 "$ssh_config"
    log_success "SSH config updated"
    return 0
}

# Test SSH connection to GitHub
test_ssh_connection() {
    log_step "Testing SSH connection to GitHub..."

    if is_dry_run; then
        echo -e "  ${DIM}[DRY-RUN] Would test SSH connection to GitHub${NC}"
        return 0
    fi

    # Add GitHub to known hosts if not present
    if ! grep -q "github.com" "${HOME}/.ssh/known_hosts" 2>/dev/null; then
        ssh-keyscan -t ed25519 github.com >> "${HOME}/.ssh/known_hosts" 2>/dev/null
    fi

    # Test connection
    local result
    result=$(ssh -T -o BatchMode=yes -o ConnectTimeout=10 git@github.com 2>&1) || true

    if echo "$result" | grep -qi "successfully authenticated"; then
        log_success "SSH connection to GitHub verified"
        gcs_state_set_value "ssh_key_configured" "true"
        return 0
    else
        log_warn "SSH key not yet authorized on GitHub"
        return 1
    fi
}

# Wait for user to configure SSH key
wait_for_ssh_key() {
    if [[ "${NON_INTERACTIVE:-false}" == "true" ]]; then
        log_warn "SSH key not authorized in non-interactive mode"
        log_info "Falling back to HTTPS (read-only access, no git sync features)"
        USE_HTTPS="true"
        export USE_HTTPS
        return 0
    fi

    display_ssh_key_instructions

    while true; do
        echo ""
        if confirm "Have you added the deploy key to GitHub with write access?" "n"; then
            if test_ssh_connection; then
                return 0
            else
                log_warn "SSH authentication failed. Please verify the key was added correctly."
                echo ""
            fi
        else
            echo ""
            if confirm "Do you want to use HTTPS instead (no git sync features)?" "n"; then
                USE_HTTPS="true"
                export USE_HTTPS
                log_info "Switching to HTTPS mode"
                return 0
            fi
        fi
    done
}

# =============================================================================
# REPOSITORY OPERATIONS
# =============================================================================

# Get the repository URL to use
get_repo_url() {
    if [[ "${USE_HTTPS:-false}" == "true" ]]; then
        if [[ -n "${REPO_URL:-}" ]]; then
            # Convert SSH URL to HTTPS if needed
            echo "$REPO_URL" | sed 's|git@github.com:|https://github.com/|'
        else
            echo "$GCS_DEFAULT_REPO"
        fi
    else
        if [[ -n "${REPO_URL:-}" ]]; then
            # Convert HTTPS URL to SSH if needed
            echo "$REPO_URL" | sed 's|https://github.com/|git@github.com:|'
        else
            echo "$GCS_DEFAULT_REPO_SSH"
        fi
    fi
}

# Clone or update repository
clone_or_update_repo() {
    local repo_url
    repo_url=$(get_repo_url)
    local branch="${BRANCH:-$GCS_DEFAULT_BRANCH}"
    local install_dir="${GCS_INSTALL_DIR:-$(pwd)}"

    log_step "Repository: $repo_url"
    log_step "Branch: $branch"
    log_step "Install directory: $install_dir"

    if is_dry_run; then
        echo -e "  ${DIM}[DRY-RUN] Would clone/update repository${NC}"
        return 0
    fi

    # Check if already in a git repo with the right remote
    if [[ -d "${install_dir}/.git" ]]; then
        log_info "Repository already exists, updating..."

        cd "$install_dir" || return 1

        # Fetch and checkout branch
        git fetch origin "$branch" 2>/dev/null || {
            log_warn "Could not fetch from remote"
        }

        # Check current branch
        local current_branch
        current_branch=$(git branch --show-current 2>/dev/null)

        if [[ "$current_branch" != "$branch" ]]; then
            log_info "Switching from $current_branch to $branch"
            git checkout "$branch" 2>/dev/null || git checkout -b "$branch" "origin/$branch" 2>/dev/null || {
                log_error "Failed to checkout branch: $branch"
                return 1
            }
        fi

        # Pull latest changes
        git pull origin "$branch" 2>/dev/null || {
            log_warn "Could not pull latest changes (may have local modifications)"
        }

        local commit
        commit=$(git rev-parse --short HEAD 2>/dev/null)
        log_success "Repository updated (commit: $commit)"
        gcs_state_set_value "repo_commit" "$commit"

    else
        log_info "Cloning repository..."

        # Ensure parent directory exists
        local parent_dir
        parent_dir=$(dirname "$install_dir")
        mkdir -p "$parent_dir"

        if git clone -b "$branch" "$repo_url" "$install_dir" 2>/dev/null; then
            cd "$install_dir" || return 1
            local commit
            commit=$(git rev-parse --short HEAD 2>/dev/null)
            log_success "Repository cloned (commit: $commit)"
            gcs_state_set_value "repo_commit" "$commit"
        else
            log_error "Failed to clone repository"
            return 1
        fi
    fi

    # Store repo info in state
    gcs_state_set_value "repo_url" "$repo_url"
    gcs_state_set_value "repo_branch" "$branch"
    gcs_state_set_value "install_dir" "$install_dir"

    return 0
}

# =============================================================================
# MAIN PHASE RUNNER
# =============================================================================

run_repository_phase() {
    print_phase_header "4" "Repository Setup" "9"

    # Check skip flag
    if [[ "${SKIP_REPO:-false}" == "true" ]]; then
        log_info "Skipping repository setup (--skip-repo)"
        return 0
    fi

    local install_dir="${GCS_INSTALL_DIR:-$(pwd)}"

    # Check if we're already in a valid repo (bootstrapped by install_gcs.sh)
    if [[ -d "${install_dir}/.git" ]]; then
        print_section "Repository Configuration"

        # Show current repo info
        local current_remote current_branch current_commit
        current_remote=$(cd "$install_dir" && git remote get-url origin 2>/dev/null || echo "unknown")
        current_branch=$(cd "$install_dir" && git branch --show-current 2>/dev/null || echo "unknown")
        current_commit=$(cd "$install_dir" && git rev-parse --short HEAD 2>/dev/null || echo "unknown")

        echo ""
        echo -e "  ${WHITE}Current Repository:${NC}"
        echo -e "    Remote: ${GREEN}${current_remote}${NC}"
        echo -e "    Branch: ${CYAN}${current_branch}${NC}"
        echo -e "    Commit: ${DIM}${current_commit}${NC}"
        echo ""

        # Ask about access mode if not already set via CLI
        if [[ "${USE_HTTPS:-}" != "true" ]] && [[ "${NON_INTERACTIVE:-false}" != "true" ]]; then
            echo -e "${CYAN}+------------------------------------------------------------------------------+${NC}"
            echo -e "${CYAN}|${NC}  ${WHITE}Git Access Mode${NC}"
            echo -e "${CYAN}+------------------------------------------------------------------------------+${NC}"
            echo ""
            echo -e "  ${WHITE}1)${NC} ${GREEN}HTTPS (Recommended for most users)${NC}"
            echo -e "     - Simple setup, no SSH keys needed"
            echo -e "     - Read-only access (manual git push if needed)"
            echo ""
            echo -e "  ${WHITE}2)${NC} SSH with deploy key"
            echo -e "     - Enables automatic git sync features"
            echo -e "     - Requires adding deploy key to GitHub"
            echo ""
            echo -e "${CYAN}+------------------------------------------------------------------------------+${NC}"
            echo ""

            local access_choice
            read -p "  Select access mode [1]: " access_choice </dev/tty
            access_choice=${access_choice:-1}

            if [[ "$access_choice" == "1" ]]; then
                USE_HTTPS="true"
                export USE_HTTPS
                log_info "Using HTTPS mode (simple setup)"
            else
                log_info "Setting up SSH deploy key..."
            fi
            echo ""
        fi

        # If using HTTPS mode, we're done with repo phase
        if [[ "${USE_HTTPS:-false}" == "true" ]]; then
            log_info "Repository configured with HTTPS access"
            clone_or_update_repo || return 1
            echo ""
            log_success "Repository phase completed"
            return 0
        fi
    else
        # No existing repo - prompt for repository selection
        print_section "Repository Selection"
        prompt_repository_selection
    fi

    # SSH key setup for write access (only if not using HTTPS)
    if [[ "${USE_HTTPS:-false}" != "true" ]]; then
        print_section "SSH Deploy Key Setup"
        log_info "Setting up SSH key for git sync features..."
        echo ""

        generate_ssh_key || return 1
        configure_ssh_github || return 1

        if ! test_ssh_connection; then
            wait_for_ssh_key || return 1
        fi
    fi

    print_section "Repository Clone/Update"
    clone_or_update_repo || return 1

    echo ""
    log_success "Repository phase completed"
    return 0
}
