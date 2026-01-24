#!/bin/bash
# =============================================================================
# MDS GCS Bootstrap Installer
# =============================================================================
# Version: 1.0.0
# Description: Bootstrap installer for remote GCS setup
#              Downloads and runs mds_gcs_init.sh
# Author: MDS Team
# License: MIT
# =============================================================================
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/alireza787b/mavsdk_drone_show/main-candidate/tools/install_gcs.sh | sudo bash
#
#   Or with options:
#   curl -fsSL ... | sudo bash -s -- --branch develop --https
#
# =============================================================================

set -euo pipefail

# =============================================================================
# CONFIGURATION
# =============================================================================

REPO_URL="${MDS_REPO_URL:-https://github.com/alireza787b/mavsdk_drone_show.git}"
BRANCH="${MDS_BRANCH:-main-candidate}"
INSTALL_DIR="${MDS_INSTALL_DIR:-/opt/mavsdk_drone_show}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# =============================================================================
# FUNCTIONS
# =============================================================================

log_info() {
    echo -e "${CYAN}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_banner() {
    echo ""
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC}                   ${GREEN}MDS GCS Bootstrap Installer${NC}                    ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}                      Ground Control Station                       ${CYAN}║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

install_git() {
    if command -v git &>/dev/null; then
        log_success "git is already installed"
        return 0
    fi

    log_info "Installing git..."
    apt-get update -qq
    apt-get install -y -qq git
    log_success "git installed"
}

clone_repository() {
    log_info "Cloning repository..."
    log_info "  URL: $REPO_URL"
    log_info "  Branch: $BRANCH"
    log_info "  Directory: $INSTALL_DIR"

    if [[ -d "$INSTALL_DIR/.git" ]]; then
        log_info "Repository already exists, updating..."
        cd "$INSTALL_DIR"
        git fetch origin "$BRANCH"
        git checkout "$BRANCH"
        git pull origin "$BRANCH"
    else
        mkdir -p "$(dirname "$INSTALL_DIR")"
        git clone -b "$BRANCH" "$REPO_URL" "$INSTALL_DIR"
    fi

    log_success "Repository ready"
}

run_init_script() {
    local init_script="${INSTALL_DIR}/tools/mds_gcs_init.sh"

    if [[ ! -f "$init_script" ]]; then
        log_error "Init script not found: $init_script"
        exit 1
    fi

    chmod +x "$init_script"

    log_info "Running GCS initialization script..."
    echo ""

    # Pass through any extra arguments
    exec "$init_script" "$@"
}

show_help() {
    cat << 'EOF'
MDS GCS Bootstrap Installer

USAGE:
    curl -fsSL <url> | sudo bash
    curl -fsSL <url> | sudo bash -s -- [OPTIONS]

OPTIONS:
    --branch BRANCH     Git branch to use (default: main-candidate)
    --install-dir PATH  Installation directory (default: /opt/mavsdk_drone_show)
    -h, --help          Show this help message

    All other options are passed to mds_gcs_init.sh

ENVIRONMENT VARIABLES:
    MDS_REPO_URL        Git repository URL
    MDS_BRANCH          Git branch
    MDS_INSTALL_DIR     Installation directory

EXAMPLES:
    # Default installation
    curl -fsSL https://raw.githubusercontent.com/.../install_gcs.sh | sudo bash

    # Custom branch
    curl -fsSL ... | sudo bash -s -- --branch develop

    # Non-interactive
    curl -fsSL ... | sudo bash -s -- -y

EOF
}

# =============================================================================
# MAIN
# =============================================================================

main() {
    # Parse bootstrap-specific arguments
    local passthrough_args=()

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --branch)
                BRANCH="$2"
                shift 2
                ;;
            --install-dir)
                INSTALL_DIR="$2"
                passthrough_args+=("--install-dir" "$2")
                shift 2
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            *)
                passthrough_args+=("$1")
                shift
                ;;
        esac
    done

    print_banner

    log_info "Starting GCS bootstrap installation..."
    echo ""

    check_root
    install_git
    clone_repository
    run_init_script "${passthrough_args[@]}"
}

main "$@"
