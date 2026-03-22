#!/bin/bash

set -euo pipefail

DEFAULT_REPO_URL="https://github.com/alireza787b/mavsdk_drone_show.git"
DEFAULT_BRANCH="main-candidate"
BASE_DIR="${MDS_BASE_DIR:-/root/mavsdk_drone_show}"
PX4_DIR="${MDS_PX4_DIR:-/root/PX4-Autopilot}"
REPO_URL="${1:-${MDS_REPO_URL:-$DEFAULT_REPO_URL}}"
BRANCH="${2:-${MDS_BRANCH:-$DEFAULT_BRANCH}}"
VENV_DIR="$BASE_DIR/venv"
VENV_REQUIREMENTS_MARKER="$VENV_DIR/.mds_requirements_state"
MAVSDK_BINARY_PATH="$BASE_DIR/mavsdk_server"
MAVSDK_DOWNLOAD_SCRIPT="$BASE_DIR/tools/download_mavsdk_server.sh"

log() {
    printf '%s\n' "$*"
}

fail() {
    printf 'Error: %s\n' "$*" >&2
    exit 1
}

require_cmd() {
    command -v "$1" >/dev/null 2>&1 || fail "Missing required command: $1"
}

retry_cmd() {
    local attempts="$1"
    shift
    local delay=2
    local try=1

    while true; do
        if "$@"; then
            return 0
        fi

        if [ "$try" -ge "$attempts" ]; then
            return 1
        fi

        sleep "$delay"
        try=$((try + 1))
        delay=$((delay * 2))
    done
}

github_https_fallback_url() {
    local repo_url="$1"
    if [[ "$repo_url" =~ ^git@github\.com:(.+)$ ]]; then
        echo "https://github.com/${BASH_REMATCH[1]}"
        return 0
    fi
    return 1
}

requirements_state_value() {
    local requirements_file="$BASE_DIR/requirements.txt"
    local requirements_hash
    local python_version
    requirements_hash=$(sha256sum "$requirements_file" | awk '{print $1}')
    python_version=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")')
    printf "%s|python=%s\n" "$requirements_hash" "$python_version"
}

fresh_clone_mds_repo() {
    local fallback_repo_url=""
    local clone_parent
    local clone_dir
    local preserve_dir
    preserve_dir=$(mktemp -d)

    if fallback_repo_url=$(github_https_fallback_url "$REPO_URL"); then
        :
    else
        fallback_repo_url=""
    fi

    if [ -x "$BASE_DIR/mavsdk_server" ]; then
        cp "$BASE_DIR/mavsdk_server" "$preserve_dir/mavsdk_server"
    fi

    clone_parent=$(mktemp -d)
    clone_dir="$clone_parent/repo"

    log "Cloning ${REPO_URL}@${BRANCH} as a shallow working tree..."
    if ! retry_cmd 3 git clone --depth 1 --branch "$BRANCH" "$REPO_URL" "$clone_dir"; then
        if [ -n "$fallback_repo_url" ] && [ "$fallback_repo_url" != "$REPO_URL" ]; then
            log "Primary clone failed. Retrying with HTTPS fallback: $fallback_repo_url"
            retry_cmd 3 git clone --depth 1 --branch "$BRANCH" "$fallback_repo_url" "$clone_dir"
        else
            fail "Unable to clone ${REPO_URL}@${BRANCH}"
        fi
    fi

    rm -rf "$BASE_DIR"
    mv "$clone_dir" "$BASE_DIR"
    rm -rf "$clone_parent"

    if [ -f "$preserve_dir/mavsdk_server" ] && [ ! -f "$BASE_DIR/mavsdk_server" ]; then
        mv "$preserve_dir/mavsdk_server" "$BASE_DIR/mavsdk_server"
        chmod +x "$BASE_DIR/mavsdk_server"
    fi

    rm -rf "$preserve_dir"
}

ensure_mavsdk_server() {
    if [ -x "$MAVSDK_BINARY_PATH" ]; then
        return 0
    fi

    [ -f "$MAVSDK_DOWNLOAD_SCRIPT" ] || fail "Missing MAVSDK download helper: $MAVSDK_DOWNLOAD_SCRIPT"
    require_cmd curl
    log "Provisioning mavsdk_server into $BASE_DIR..."
    MDS_INSTALL_DIR="$BASE_DIR" bash "$MAVSDK_DOWNLOAD_SCRIPT" >/tmp/mds_mavsdk_download.log 2>&1 || {
        tail -n 40 /tmp/mds_mavsdk_download.log >&2 || true
        fail "Failed to download mavsdk_server"
    }
    rm -f /tmp/mds_mavsdk_download.log
    [ -x "$MAVSDK_BINARY_PATH" ] || fail "mavsdk_server is still missing after download"
}

ensure_python_env() {
    log "Preparing Python virtual environment..."
    python3 -m venv "$VENV_DIR"
    source "$VENV_DIR/bin/activate"

    PIP_NO_CACHE_DIR=1 python3 -m pip install --upgrade pip >/tmp/mds_pip_install.log 2>&1
    PIP_NO_CACHE_DIR=1 python3 -m pip install -r "$BASE_DIR/requirements.txt" >>/tmp/mds_pip_install.log 2>&1 || {
        tail -n 40 /tmp/mds_pip_install.log >&2 || true
        fail "Failed to install Python requirements"
    }
    printf "%s\n" "$(requirements_state_value)" > "$VENV_REQUIREMENTS_MARKER"
    rm -f /tmp/mds_pip_install.log
}

stabilize_mavlink2rest_binary() {
    local current_bin
    current_bin=$(command -v mavlink2rest || true)
    [ -n "$current_bin" ] || fail "mavlink2rest is not installed in the base image"

    if [ "$current_bin" != "/usr/local/bin/mavlink2rest" ]; then
        install -m 0755 "$current_bin" /usr/local/bin/mavlink2rest
    fi
}

prepare_px4_git_snapshot() {
    log "Preparing compact PX4 git metadata for runtime make checks..."

    rm -rf "$PX4_DIR/.git"
    git -C "$PX4_DIR" init -q
    git -C "$PX4_DIR" config user.name "MDS SITL Image"
    git -C "$PX4_DIR" config user.email "mds-sitl-image@example.invalid"
    git -C "$PX4_DIR" add -A
    git -C "$PX4_DIR" commit -q -m "PX4 runtime snapshot"
}

cleanup_runtime_baggage() {
    log "Removing cached and development-only baggage..."

    rm -rf "$BASE_DIR/logs"
    mkdir -p "$BASE_DIR/logs"
    find "$BASE_DIR" -maxdepth 1 -name '*.hwID' -delete
    rm -rf "$BASE_DIR/app/dashboard/drone-dashboard/node_modules"
    rm -rf "$BASE_DIR/app/dashboard/drone-dashboard/build"
    rm -rf "$BASE_DIR/.pytest_cache"

    if [ -d "$PX4_DIR/build" ]; then
        find "$PX4_DIR/build" -mindepth 1 -maxdepth 1 ! -name px4_sitl_default -exec rm -rf {} +
    fi

    rm -rf "$PX4_DIR/docs"
    rm -rf "$PX4_DIR/.github"

    rm -rf /root/.cargo
    rm -rf /root/.rustup
    rm -rf /root/.cache/pip
    rm -rf /root/.npm
    rm -rf /tmp/*
    rm -rf /var/tmp/*
    rm -rf /var/lib/apt/lists/*

    if [ -f /root/.profile ]; then
        sed -i '\#\.cargo/env#d' /root/.profile
    fi

    if [ -f /root/.bashrc ]; then
        sed -i '\#\.cargo/env#d' /root/.bashrc
    fi
}

write_build_metadata() {
    local commit_hash
    commit_hash=$(git -C "$BASE_DIR" rev-parse --short HEAD)

    cat > "$BASE_DIR/.mds_sitl_image_build.env" <<EOF
MDS_IMAGE_REPO_URL=${REPO_URL}
MDS_IMAGE_BRANCH=${BRANCH}
MDS_IMAGE_COMMIT=${commit_hash}
MDS_IMAGE_PREPARED_AT_UTC=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
EOF
}

main() {
    require_cmd git
    require_cmd python3
    require_cmd sha256sum

    fresh_clone_mds_repo
    ensure_mavsdk_server
    ensure_python_env
    stabilize_mavlink2rest_binary
    cleanup_runtime_baggage
    prepare_px4_git_snapshot
    write_build_metadata

    log "Prepared image workspace:"
    log "  Base dir : $BASE_DIR"
    log "  PX4 dir  : $PX4_DIR"
    log "  Repo     : ${REPO_URL}@${BRANCH}"
    log "  Commit   : $(git -C "$BASE_DIR" rev-parse --short HEAD)"
}

main "$@"
