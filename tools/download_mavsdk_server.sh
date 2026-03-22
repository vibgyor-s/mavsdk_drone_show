#!/bin/bash
# =============================================================================
# MAVSDK Server Binary Downloader
# =============================================================================
# Version: 2.1.0
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
#   --version VERSION   Download specific version (e.g., v3.15.0)
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

# Default pinned version if API fails
FALLBACK_VERSION="v3.15.0"

# GitHub API URL for latest release
GITHUB_API_URL="https://api.github.com/repos/mavlink/MAVSDK/releases/latest"
GITHUB_TAG_API_TEMPLATE="https://api.github.com/repos/mavlink/MAVSDK/releases/tags/{VERSION}"

# Download URL templates
URL_TEMPLATE_ARM64="https://github.com/mavlink/MAVSDK/releases/download/{VERSION}/mavsdk_server_linux-arm64-musl"
URL_TEMPLATE_ARMHF="https://github.com/mavlink/MAVSDK/releases/download/{VERSION}/mavsdk_server_linux-armv7l-musl"
URL_TEMPLATE_ARMHF_LEGACY="https://github.com/mavlink/MAVSDK/releases/download/{VERSION}/mavsdk_server_linux-armv7-musl"
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
MAVSDK Server Binary Downloader v2.1.0

USAGE:
    ./download_mavsdk_server.sh [OPTIONS]

OPTIONS:
    --sitl              Download x86_64 binary for SITL/development
    --version VERSION   Download specific version (e.g., v3.15.0)
    --latest            Force fetch latest version from GitHub API
    --help              Show this help message

ENVIRONMENT VARIABLES:
    MDS_MAVSDK_VERSION  Override MAVSDK version to download
    MDS_MAVSDK_URL      Override download URL entirely

EXAMPLES:
    # Auto-detect architecture and use latest version
    ./download_mavsdk_server.sh --latest

    # Download specific version
    ./download_mavsdk_server.sh --version v3.15.0

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
    local response

    print_info "Fetching latest MAVSDK version from GitHub..."

    response=$(curl -fsSL --max-time 15 \
        -H "Accept: application/vnd.github+json" \
        -H "User-Agent: mds-mavsdk-downloader" \
        "$GITHUB_API_URL" 2>/dev/null || true)

    if [[ -n "$response" ]] && command -v python3 >/dev/null 2>&1; then
        version=$(printf '%s' "$response" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("tag_name", ""))' 2>/dev/null || true)
    fi

    if [[ -z "$version" ]]; then
        version=$(printf '%s' "$response" | grep '"tag_name"' | head -1 | \
            sed -E 's/.*"tag_name"[[:space:]]*:[[:space:]]*"([^"]+)".*/\1/' || true)
    fi

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
        normalize_version "$specified_version"
        return 0
    fi

    # Priority 3: Environment variable
    if [[ -n "${MDS_MAVSDK_VERSION:-}" ]]; then
        normalize_version "${MDS_MAVSDK_VERSION}"
        return 0
    fi

    # Priority 4: Fetch latest (if requested) or use fallback
    if [[ "$force_latest" == "true" ]]; then
        fetch_latest_version
    else
        echo "$FALLBACK_VERSION"
    fi
}

normalize_version() {
    local version="$1"

    if [[ -z "$version" || "$version" == "custom" ]]; then
        echo "$version"
        return 0
    fi

    if [[ "$version" =~ ^v ]]; then
        echo "$version"
    else
        echo "v${version}"
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

get_legacy_url_template() {
    local arch="$1"

    case "$arch" in
        armhf)
            echo "$URL_TEMPLATE_ARMHF_LEGACY"
            ;;
        *)
            return 1
            ;;
    esac
}

get_release_api_url() {
    local version="$1"

    if [[ "$version" == "latest" ]]; then
        echo "$GITHUB_API_URL"
    else
        echo "${GITHUB_TAG_API_TEMPLATE//\{VERSION\}/$version}"
    fi
}

get_asset_names() {
    local arch="$1"

    case "$arch" in
        arm64)
            printf '%s\n' "mavsdk_server_linux-arm64-musl"
            ;;
        armhf)
            printf '%s\n' \
                "mavsdk_server_linux-armv7l-musl" \
                "mavsdk_server_linux-armv7-musl"
            ;;
        x86_64)
            printf '%s\n' "mavsdk_server_musl_x86_64"
            ;;
        *)
            return 1
            ;;
    esac
}

resolve_asset_urls_from_api() {
    local version="$1"
    local arch="$2"
    local release_api_url
    local response

    command -v python3 >/dev/null 2>&1 || return 1

    release_api_url=$(get_release_api_url "$version")
    response=$(curl -fsSL --max-time 20 \
        -H "Accept: application/vnd.github+json" \
        -H "User-Agent: mds-mavsdk-downloader" \
        "$release_api_url" 2>/dev/null || true)

    [[ -n "$response" ]] || return 1

    mapfile -t asset_names < <(get_asset_names "$arch")
    [[ ${#asset_names[@]} -gt 0 ]] || return 1

    printf '%s' "$response" | python3 - "${asset_names[@]}" <<'PY'
import json
import sys

obj = json.load(sys.stdin)
targets = sys.argv[1:]
assets = {asset.get("name"): asset.get("browser_download_url", "") for asset in obj.get("assets", [])}

for target in targets:
    url = assets.get(target)
    if url:
        print(url)
PY
}

build_candidate_urls() {
    local version="$1"
    local arch="$2"
    local template
    local legacy_template
    local url

    if [[ -n "${MDS_MAVSDK_URL:-}" ]]; then
        printf '%s\n' "${MDS_MAVSDK_URL}"
        return 0
    fi

    resolve_asset_urls_from_api "$version" "$arch" || true

    template=$(get_url_template "$arch") || return 1
    printf '%s\n' "${template//\{VERSION\}/$version}"

    if legacy_template=$(get_legacy_url_template "$arch" 2>/dev/null); then
        printf '%s\n' "${legacy_template//\{VERSION\}/$version}"
    fi
}

# =============================================================================
# DOWNLOAD FUNCTION
# =============================================================================

download_mavsdk() {
    local version="$1"
    local arch="$2"
    local output_path="${INSTALL_DIR}/${FILENAME}"
    local tmp_path="${output_path}.tmp"
    local url
    local attempted=0

    mkdir -p "$INSTALL_DIR"
    print_info "Downloading to: $output_path"

    while IFS= read -r url; do
        [[ -n "$url" ]] || continue
        attempted=1
        print_info "Trying download URL: $url"
        rm -f "$tmp_path"

        if ! curl -L --progress-bar --fail --max-time 180 -o "$tmp_path" "$url"; then
            print_error "Download attempt failed: $url"
            rm -f "$tmp_path"
            continue
        fi

        mv "$tmp_path" "$output_path"
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

        rm -f "$output_path"
    done < <(build_candidate_urls "$version" "$arch")

    rm -f "$tmp_path" "$output_path"
    if [[ "$attempted" -eq 0 ]]; then
        print_error "No candidate MAVSDK download URLs could be resolved"
    else
        print_error "Failed to download MAVSDK binary"
    fi
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
