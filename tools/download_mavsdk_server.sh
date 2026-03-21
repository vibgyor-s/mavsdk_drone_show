#!/bin/bash
# =============================================================================
# MAVSDK Server Binary Downloader
# =============================================================================
# Version: 2.0.0
# Description: Downloads MAVSDK server binary with auto-version detection
# Author: MDS Team
#
# Features:
#   - Auto-detect latest MAVSDK version from GitHub API
#   - Support for specific version via --version flag
#   - Environment variable support (MDS_MAVSDK_VERSION)
#   - Architecture auto-detection (ARM64, x86_64)
#   - SITL mode flag for development
#
# Usage:
#   ./download_mavsdk_server.sh [OPTIONS]
#
# Options:
#   --sitl              Download x86_64 binary for SITL/development
#   --version VERSION   Download specific version (e.g., v3.5.0)
#   --latest            Force fetch latest version from GitHub API
#   --help              Show this help message
#
# Environment Variables:
#   MDS_MAVSDK_VERSION  Override MAVSDK version to download
#   MDS_MAVSDK_URL      Override download URL entirely
# =============================================================================

set -euo pipefail

# =============================================================================
# CONFIGURATION
# =============================================================================

# Default/fallback version if API fails
FALLBACK_VERSION="v3.5.0"

# GitHub API URL for latest release
GITHUB_API_URL="https://api.github.com/repos/mavlink/MAVSDK/releases/latest"

# Download URL templates
URL_TEMPLATE_ARM64="https://github.com/mavlink/MAVSDK/releases/download/{VERSION}/mavsdk_server_linux-arm64-musl"
URL_TEMPLATE_ARMHF="https://github.com/mavlink/MAVSDK/releases/download/{VERSION}/mavsdk_server_linux-armv7-musl"
URL_TEMPLATE_X86_64="https://github.com/mavlink/MAVSDK/releases/download/{VERSION}/mavsdk_server_musl_x86_64"

# Output configuration
FILENAME="mavsdk_server"

# Determine install directory
if [[ -n "${SUDO_USER:-}" ]]; then
    INSTALL_DIR="$(eval echo ~"$SUDO_USER")/mavsdk_drone_show"
else
    INSTALL_DIR="${HOME}/mavsdk_drone_show"
fi

# Override from environment
INSTALL_DIR="${MDS_INSTALL_DIR:-$INSTALL_DIR}"

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

print_info() {
    echo "[INFO] $*"
}

print_error() {
    echo "[ERROR] $*" >&2
}

print_success() {
    echo "[SUCCESS] $*"
}

show_help() {
    cat << 'EOF'
MAVSDK Server Binary Downloader v2.0.0

USAGE:
    ./download_mavsdk_server.sh [OPTIONS]

OPTIONS:
    --sitl              Download x86_64 binary for SITL/development
    --version VERSION   Download specific version (e.g., v3.5.0)
    --latest            Force fetch latest version from GitHub API
    --help              Show this help message

ENVIRONMENT VARIABLES:
    MDS_MAVSDK_VERSION  Override MAVSDK version to download
    MDS_MAVSDK_URL      Override download URL entirely

EXAMPLES:
    # Auto-detect architecture and use latest version
    ./download_mavsdk_server.sh --latest

    # Download specific version
    ./download_mavsdk_server.sh --version v3.5.0

    # Download for SITL development
    ./download_mavsdk_server.sh --sitl

    # Use environment variable
    MDS_MAVSDK_VERSION=v3.4.0 ./download_mavsdk_server.sh
EOF
}

# =============================================================================
# VERSION DETECTION
# =============================================================================

# Fetch latest version from GitHub API
fetch_latest_version() {
    local version

    print_info "Fetching latest MAVSDK version from GitHub..."

    version=$(curl -s --max-time 10 "$GITHUB_API_URL" 2>/dev/null | \
        grep '"tag_name"' | head -1 | \
        sed -E 's/.*"tag_name"[[:space:]]*:[[:space:]]*"([^"]+)".*/\1/')

    if [[ -n "$version" && "$version" != "null" ]]; then
        print_info "Latest version: $version"
        echo "$version"
        return 0
    fi

    print_error "Failed to fetch latest version, using fallback: $FALLBACK_VERSION"
    echo "$FALLBACK_VERSION"
    return 0
}

# Get version to download
get_target_version() {
    local force_latest="${1:-false}"
    local specified_version="${2:-}"

    # Priority 1: Direct URL override
    if [[ -n "${MDS_MAVSDK_URL:-}" ]]; then
        echo "custom"
        return 0
    fi

    # Priority 2: Command line --version
    if [[ -n "$specified_version" ]]; then
        echo "$specified_version"
        return 0
    fi

    # Priority 3: Environment variable
    if [[ -n "${MDS_MAVSDK_VERSION:-}" ]]; then
        echo "${MDS_MAVSDK_VERSION}"
        return 0
    fi

    # Priority 4: Fetch latest (if requested) or use fallback
    if [[ "$force_latest" == "true" ]]; then
        fetch_latest_version
    else
        echo "$FALLBACK_VERSION"
    fi
}

# =============================================================================
# ARCHITECTURE DETECTION
# =============================================================================

detect_architecture() {
    local arch
    arch=$(uname -m)

    case "$arch" in
        aarch64|arm64)
            echo "arm64"
            ;;
        armv7l|armhf)
            echo "armhf"
            ;;
        x86_64)
            echo "x86_64"
            ;;
        *)
            print_error "Unsupported architecture: $arch"
            return 1
            ;;
    esac
}

# Get URL template for architecture
get_url_template() {
    local arch="$1"

    case "$arch" in
        arm64)
            echo "$URL_TEMPLATE_ARM64"
            ;;
        armhf)
            echo "$URL_TEMPLATE_ARMHF"
            ;;
        x86_64)
            echo "$URL_TEMPLATE_X86_64"
            ;;
        *)
            print_error "No URL template for architecture: $arch"
            return 1
            ;;
    esac
}

# =============================================================================
# DOWNLOAD FUNCTION
# =============================================================================

download_mavsdk() {
    local version="$1"
    local arch="$2"
    local url

    # Direct URL override
    if [[ -n "${MDS_MAVSDK_URL:-}" ]]; then
        url="${MDS_MAVSDK_URL}"
        print_info "Using direct URL: $url"
    else
        # Construct URL from template
        local template
        template=$(get_url_template "$arch") || return 1
        url="${template//\{VERSION\}/$version}"
        print_info "Download URL: $url"
    fi

    # Create install directory
    mkdir -p "$INSTALL_DIR"

    local output_path="${INSTALL_DIR}/${FILENAME}"

    print_info "Downloading to: $output_path"

    # Download with progress
    if ! curl -L --progress-bar --fail --max-time 120 -o "$output_path" "$url"; then
        print_error "Failed to download MAVSDK binary"
        rm -f "$output_path"
        return 1
    fi

    # Make executable
    chmod +x "$output_path"

    # Verify binary without executing it. Some MAVSDK server builds do not
    # exit cleanly for `--version`, which can hang image builds or runtime
    # provisioning.
    if [[ -x "$output_path" ]]; then
        local binary_details
        local binary_size
        binary_details=$(file "$output_path" 2>/dev/null || echo "unknown binary type")
        binary_size=$(stat -c%s "$output_path" 2>/dev/null || echo "unknown")
        print_success "MAVSDK server downloaded successfully"
        print_info "Binary: $binary_details"
        print_info "Size (bytes): $binary_size"
        print_success "Location: $output_path"
        return 0
    fi

    print_error "Binary verification failed"
    return 1
}

# =============================================================================
# MAIN FUNCTION
# =============================================================================

main() {
    local sitl_mode="false"
    local force_latest="false"
    local specified_version=""

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --sitl)
                sitl_mode="true"
                shift
                ;;
            --version)
                specified_version="$2"
                shift 2
                ;;
            --latest)
                force_latest="true"
                shift
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done

    # Determine architecture
    local arch
    if [[ "$sitl_mode" == "true" ]]; then
        arch="x86_64"
        print_info "SITL mode: using x86_64 binary"
    else
        arch=$(detect_architecture) || exit 1
        print_info "Detected architecture: $arch"
    fi

    # Determine version
    local version
    version=$(get_target_version "$force_latest" "$specified_version")
    print_info "Target version: $version"

    # Download
    download_mavsdk "$version" "$arch" || exit 1

    print_success "MAVSDK server installation complete!"
}

# =============================================================================
# RUN MAIN
# =============================================================================

main "$@"
