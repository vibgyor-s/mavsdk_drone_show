#!/bin/bash

#########################################
# Final Production-Ready Drone Services Launcher
#
# Project: Drone Show GCS Server
# Version: Production Final
#
# CRITICAL FIXES APPLIED:
# - Flask WSGI module-level app object created
# - Absolute path resolution for any execution directory
# - Clean bash commands (NO Unicode/emojis)
# - Robust virtual environment handling
# - Production-grade error handling
#
# Usage: ./linux_dashboard_start.sh [OPTIONS]
#########################################

# =============================================================================
# IMPORTANT: MAVLink Routing (External)
# =============================================================================
# This application expects MAVLink routing to be handled EXTERNALLY.
#
# For Raspberry Pi (Real Hardware):
#   1. Install mavlink-anywhere: git clone https://github.com/alireza787b/mavlink-anywhere
#   2. Run: cd mavlink-anywhere && sudo ./install_mavlink_router.sh
#   3. Configure: sudo ./configure_mavlink_router.sh
#      - Input: /dev/ttyS0:57600 (your serial port and baudrate)
#      - Outputs: 127.0.0.1:14540, 127.0.0.1:12550, 127.0.0.1:14569, GCS_IP:14550
#   4. Enable: sudo systemctl enable mavlink-router
#   5. Start: sudo systemctl start mavlink-router
#
# For SITL: Routing is handled automatically by startup_sitl.sh
#
# See docs/guides/mavlink-routing-setup.md for detailed instructions.
# =============================================================================

set -euo pipefail  # Strict error handling

# ===========================================
# CONFIGURATION
# ===========================================
DEFAULT_MODE="development"
PROD_WSGI_WORKERS=4
PROD_WSGI_BIND="0.0.0.0:5000"
PROD_GUNICORN_TIMEOUT=120
PROD_LOG_LEVEL="info"
DEV_REACT_PORT=3030
DEV_GCS_PORT=5000  # GCS Server port for development
SESSION_NAME="DroneServices"

# ===========================================
# PATH RESOLUTION (ABSOLUTE PATHS ONLY)
# ===========================================
SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
SCRIPT_DIR="$(dirname "$SCRIPT_PATH")"

# The script is in PROJECT_ROOT/app/, so PARENT_DIR is PROJECT_ROOT
PARENT_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_ROOT="$PARENT_DIR"

# All paths are relative to PROJECT_ROOT (the repository root)
REACT_APP_DIR="$PROJECT_ROOT/app/dashboard/drone-dashboard"
GCS_SERVER_DIR="$PROJECT_ROOT/gcs-server"
VENV_PATH="$PROJECT_ROOT/venv"

# Final path validation
if [[ ! -d "$GCS_SERVER_DIR" ]]; then
    echo "ERROR: GCS server directory not found at $GCS_SERVER_DIR"
    echo "Script location: $SCRIPT_DIR"
    echo "Parent directory: $PARENT_DIR"
    exit 1
fi

ENV_FILE_PATH="$REACT_APP_DIR/.env"
BUILD_DIR="$REACT_APP_DIR/build"
REAL_MODE_FILE="$GCS_SERVER_DIR/real.mode"
UPDATE_SCRIPT_PATH="$PROJECT_ROOT/tools/update_repo_ssh.sh"

# ===========================================
# VARIABLES
# ===========================================
DEPLOYMENT_MODE="$DEFAULT_MODE"
FORCE_REBUILD=false
CHECK_ONLY=false
RUN_GCS_SERVER=true
RUN_GUI_APP=true
USE_TMUX=true
COMBINED_VIEW=true
USE_SITL=false
USE_REAL=false
OVERWRITE_IP=""
SKIP_DEPENDENCY_CHECK=false
# Repository Configuration: Environment Variable Support (MDS v3.1+)
# This script now supports custom branches via environment variables
# Default behavior unchanged for normal users
BRANCH_NAME="${MDS_BRANCH:-main-candidate}"

# Backend Selection: FastAPI (recommended) or Flask (legacy)
# Options: fastapi, flask
# Can be overridden via GCS_BACKEND environment variable
GCS_BACKEND="${GCS_BACKEND:-fastapi}"

# ===========================================
# SYSTEM CONFIGURATION (MDS GCS Init Integration)
# ===========================================
GCS_SYSTEM_CONFIG="/etc/mds/gcs.env"

load_gcs_system_config() {
    if [[ -f "$GCS_SYSTEM_CONFIG" ]]; then
        # shellcheck source=/dev/null
        source "$GCS_SYSTEM_CONFIG"

        # Apply config values (respect CLI overrides)
        [[ -z "${VENV_PATH_OVERRIDE:-}" ]] && [[ -n "${VENV_PATH:-}" ]] && VENV_PATH="$VENV_PATH"
        [[ -z "${BRANCH_OVERRIDE:-}" ]] && [[ -n "${MDS_BRANCH:-}" ]] && BRANCH_NAME="$MDS_BRANCH"
        return 0
    fi
    return 1
}

# ===========================================
# LOGGING FUNCTIONS
# ===========================================
log_info() { echo "[INFO] $1"; }
log_warn() { echo "[WARN] $1"; }
log_error() { echo "[ERROR] $1" >&2; }
log_success() { echo "[SUCCESS] $1"; }
log_header() { echo -e "\n=== $1 ==="; }

# ===========================================
# STATUS AND DIAGNOSTIC FUNCTIONS
# ===========================================
get_current_drone_mode() {
    if [[ -f "$REAL_MODE_FILE" ]]; then
        echo "REAL (Hardware)"
    else
        echo "SITL (Simulation)"
    fi
}

show_current_status() {
    cat << EOF

===============================================
  DRONE SERVICES - CURRENT STATUS
===============================================
Drone Mode:       $(get_current_drone_mode)
Real Mode File:   $([[ -f "$REAL_MODE_FILE" ]] && echo "EXISTS" || echo "NOT PRESENT")
Backend:          $GCS_BACKEND
Virtual Env:      $([[ -d "$VENV_PATH" ]] && echo "OK ($VENV_PATH)" || echo "MISSING")
React Build:      $([[ -d "$BUILD_DIR" ]] && echo "EXISTS" || echo "NOT BUILT")
.env File:        $([[ -f "$ENV_FILE_PATH" ]] && echo "EXISTS" || echo "MISSING")

PATHS:
  GCS Server:     $GCS_SERVER_DIR
  React App:      $REACT_APP_DIR
  Build Dir:      $BUILD_DIR

PORTS:
  GCS Server:     $DEV_GCS_PORT
  React App:      $DEV_REACT_PORT

To change mode:
  SITL mode:      $0 --sitl
  Real mode:      $0 --real
===============================================
EOF
}

check_python_dependencies() {
    if [[ "$SKIP_DEPENDENCY_CHECK" == "true" ]]; then
        log_info "Skipping Python dependency check (--skip-deps)"
        return 0
    fi

    local requirements_file="$PARENT_DIR/requirements.txt"
    local venv_marker="$VENV_PATH/.deps_installed"

    if [[ ! -f "$requirements_file" ]]; then
        log_warn "requirements.txt not found, skipping dependency check"
        return 0
    fi

    # Check if requirements changed since last install
    if [[ -f "$venv_marker" ]]; then
        if [[ "$requirements_file" -nt "$venv_marker" ]]; then
            log_info "requirements.txt changed, updating dependencies..."
            pip install -r "$requirements_file" --quiet
            touch "$venv_marker"
            log_success "Python dependencies updated"
        else
            log_info "Python dependencies are up-to-date"
        fi
    else
        log_info "Installing Python dependencies..."
        pip install -r "$requirements_file" --quiet
        touch "$venv_marker"
        log_success "Python dependencies installed"
    fi
}

run_health_check() {
    log_header "HEALTH CHECK"
    local all_ok=true

    # Check GCS Server
    if [[ "$RUN_GCS_SERVER" == "true" ]]; then
        log_info "Checking GCS Server on port $DEV_GCS_PORT..."
        sleep 2  # Give server time to start
        for i in {1..5}; do
            if curl -s "http://localhost:$DEV_GCS_PORT/health" > /dev/null 2>&1; then
                log_success "GCS Server is responding"
                break
            elif curl -s "http://localhost:$DEV_GCS_PORT/" > /dev/null 2>&1; then
                log_success "GCS Server is responding (no /health endpoint)"
                break
            fi
            if [[ $i -eq 5 ]]; then
                log_warn "GCS Server not responding yet (may still be starting)"
                all_ok=false
            fi
            sleep 1
        done
    fi

    # Check React App
    if [[ "$RUN_GUI_APP" == "true" ]]; then
        log_info "Checking React App on port $DEV_REACT_PORT..."
        for i in {1..5}; do
            if curl -s "http://localhost:$DEV_REACT_PORT/" > /dev/null 2>&1; then
                log_success "React App is responding"
                break
            fi
            if [[ $i -eq 5 ]]; then
                log_warn "React App not responding yet (may still be starting)"
                all_ok=false
            fi
            sleep 1
        done
    fi

    if [[ "$all_ok" == "true" ]]; then
        log_success "All services healthy!"
    else
        log_warn "Some services may still be starting - check tmux session"
    fi
}

run_configuration_check() {
    log_header "CONFIGURATION CHECK"
    local all_ok=true

    # Check virtual environment
    if [[ -d "$VENV_PATH" ]]; then
        log_success "Virtual environment: OK"
    else
        log_error "Virtual environment: MISSING at $VENV_PATH"
        all_ok=false
    fi

    # Check GCS server directory
    if [[ -d "$GCS_SERVER_DIR" ]]; then
        log_success "GCS Server directory: OK"
    else
        log_error "GCS Server directory: MISSING at $GCS_SERVER_DIR"
        all_ok=false
    fi

    # Check React app
    if [[ -f "$REACT_APP_DIR/package.json" ]]; then
        log_success "React app: OK"
    else
        log_error "React app: MISSING package.json"
        all_ok=false
    fi

    # Check .env file
    if [[ -f "$ENV_FILE_PATH" ]]; then
        log_success ".env file: OK"
        local server_url=$(grep "^REACT_APP_SERVER_URL=" "$ENV_FILE_PATH" 2>/dev/null | head -1 || echo "")
        if [[ -n "$server_url" ]]; then
            log_info "  Server URL: $server_url (explicit override)"
        else
            log_info "  Server URL: Auto-detected from browser"
        fi
    else
        log_warn ".env file: MISSING (will be created on first run)"
        log_info "  Server URL: Will auto-detect from browser"
    fi

    # Check current drone mode
    log_info "Current drone mode: $(get_current_drone_mode)"

    # Check tmux
    if command -v tmux &> /dev/null; then
        log_success "tmux: INSTALLED"
    else
        log_warn "tmux: NOT INSTALLED (will be installed on first run)"
    fi

    # Check Python dependencies
    if [[ -d "$VENV_PATH" ]]; then
        source "$VENV_PATH/bin/activate" 2>/dev/null
        if python -c "import fastapi" 2>/dev/null; then
            log_success "FastAPI: INSTALLED"
        else
            log_warn "FastAPI: NOT INSTALLED (will be installed on first run)"
        fi
    fi

    log_header "CHECK COMPLETE"
    if [[ "$all_ok" == "true" ]]; then
        log_success "All checks passed! Ready to start."
        echo ""
        echo "Quick start commands:"
        echo "  SITL mode:  $0 --sitl"
        echo "  Real mode:  $0 --real"
        echo "  Production: $0 --prod --real"
    else
        log_error "Some checks failed. Please fix the issues above."
        exit 1
    fi
}

# ===========================================
# BACKEND VALIDATION
# ===========================================
validate_backend() {
    # Check if FastAPI is available when fastapi backend is selected
    if [[ "$GCS_BACKEND" == "fastapi" ]]; then
        if ! python -c "import fastapi" 2>/dev/null; then
            log_warn "FastAPI not installed but GCS_BACKEND=fastapi"
            log_warn "Falling back to Flask backend"
            GCS_BACKEND="flask"
            export GCS_BACKEND
        fi
    fi

    # Show prominent backend info
    if [[ "$GCS_BACKEND" == "flask" ]]; then
        log_warn "Using LEGACY Flask backend (FastAPI recommended)"
        echo ""
        echo "  To use FastAPI (recommended):"
        echo "    pip install fastapi uvicorn"
        echo "    export GCS_BACKEND=fastapi"
        echo ""
    else
        log_success "Using FastAPI backend (recommended)"
    fi
}

# ===========================================
# GCS INITIALIZATION CHECK
# ===========================================
check_gcs_initialized() {
    if [[ ! -f "/etc/mds/gcs.env" ]] && [[ ! -d "$VENV_PATH" ]]; then
        log_warn "GCS may not be fully initialized"
        echo ""
        echo "If this is a fresh installation, run:"
        echo "  sudo ./tools/mds_gcs_init.sh"
        echo ""
        if [[ "${SKIP_INIT_CHECK:-false}" != "true" ]]; then
            read -p "Continue anyway? [y/N]: " confirm
            [[ "${confirm,,}" != "y" ]] && exit 1
        fi
    fi
}

# ===========================================
# UTILITY FUNCTIONS
# ===========================================
display_usage() {
    cat << EOF
Production-Ready Drone Services Launcher

USAGE: $0 [OPTIONS]

MODE OPTIONS:
  --prod, --production  : Production mode (optimized builds, WSGI server)
  --dev, --development  : Development mode (hot reload, debug server)

BUILD OPTIONS:
  --rebuild             : Force rebuild all components (React + dependencies)
  --force-rebuild       : Same as --rebuild (alias)
  --skip-deps           : Skip Python dependency check (faster startup)

DRONE MODE OPTIONS:
  --sitl                : Switch to simulation mode (SITL)
  --real                : Switch to real drone/hardware mode
  (If neither specified, current mode is preserved)

SERVICE OPTIONS:
  -g                    : Do NOT run GCS Server (default: enabled)
  -u                    : Do NOT run GUI React App (default: enabled)
  -n                    : Do NOT use tmux (default: uses tmux)
  -s                    : Run components in separate windows (default: combined)

DIAGNOSTICS:
  --check               : Check configuration and dependencies without starting
  --status              : Show current mode (SITL/Real) and configuration

NETWORK OPTIONS:
  --overwrite-ip <IP>   : Override server IP in environment

REPOSITORY OPTIONS:
  -b <branch>           : Specify git branch (default: from MDS_BRANCH env var)

HELP:
  -h, --help            : Display this help message

EXAMPLES:
  Quick start (SITL):    $0 --sitl
  Quick start (Real):    $0 --real
  Production deploy:     $0 --prod --real
  Dev with rebuild:      $0 --dev --sitl --rebuild
  Check config only:     $0 --check
  Show current status:   $0 --status
EOF
}

parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --prod|--production) DEPLOYMENT_MODE="production"; shift ;;
            --dev|--development) DEPLOYMENT_MODE="development"; shift ;;
            --rebuild|--force-rebuild) FORCE_REBUILD=true; shift ;;
            --skip-deps) SKIP_DEPENDENCY_CHECK=true; shift ;;
            --check) CHECK_ONLY=true; shift ;;
            --status) show_current_status; exit 0 ;;
            --sitl)
                if [[ "$USE_REAL" == "true" ]]; then
                    log_error "Cannot use --sitl and --real simultaneously."
                    exit 1
                fi
                USE_SITL=true; shift ;;
            --real)
                if [[ "$USE_SITL" == "true" ]]; then
                    log_error "Cannot use --sitl and --real simultaneously."
                    exit 1
                fi
                USE_REAL=true; shift ;;
            --overwrite-ip)
                if [[ -n "${2:-}" ]]; then
                    OVERWRITE_IP="$2"; shift 2
                else
                    log_error "--overwrite-ip requires an argument."; exit 1
                fi ;;
            -b)
                if [[ -n "${2:-}" ]]; then
                    BRANCH_NAME="$2"; shift 2
                else
                    log_error "-b requires a branch name."; exit 1
                fi ;;
            -g) RUN_GCS_SERVER=false; shift ;;
            -u) RUN_GUI_APP=false; shift ;;
            -n) USE_TMUX=false; shift ;;
            -s) COMBINED_VIEW=false; shift ;;
            -h|--help) display_usage; exit 0 ;;
            *) log_error "Unknown option: $1"; display_usage; exit 1 ;;
        esac
    done
}

check_command_installed() {
    local cmd="$1"
    local pkg="$2"
    if ! command -v "$cmd" &> /dev/null; then
        log_warn "$cmd not found. Installing $pkg..."
        sudo apt-get update && sudo apt-get install -y "$pkg"
        if [[ $? -ne 0 ]]; then
            log_error "Failed to install $pkg. Please install manually."
            exit 1
        fi
        log_success "$pkg installed successfully."
    else
        log_info "$cmd is available."
    fi
}

check_and_kill_port() {
    local port="$1"
    check_command_installed "lsof" "lsof"
    local pids=$(lsof -t -i :"$port" 2>/dev/null || true)
    if [[ -n "$pids" ]]; then
        log_warn "Port $port is in use. Killing processes: $pids"
        echo "$pids" | xargs -r kill -9
        log_success "Port $port freed."
    else
        log_info "Port $port is available."
    fi
}

load_virtualenv() {
    if [[ -d "$VENV_PATH" ]]; then
        source "$VENV_PATH/bin/activate"
        log_success "Virtual environment activated: $VENV_PATH"
    else
        log_error "Virtual environment not found: $VENV_PATH"
        log_error "Please create virtual environment first."
        exit 1
    fi
}

handle_real_mode_file() {
    if [[ "$USE_REAL" == "true" ]]; then
        log_info "Switching to Real Mode..."
        touch "$REAL_MODE_FILE"
        log_success "Real mode file created."
    elif [[ "$USE_SITL" == "true" ]]; then
        log_info "Switching to Simulation Mode..."
        if [[ -f "$REAL_MODE_FILE" ]]; then
            rm "$REAL_MODE_FILE"
            log_success "Real mode file removed."
        else
            log_info "Already in Simulation Mode."
        fi
    else
        log_info "No mode switch requested. Current mode preserved."
    fi
}

update_repository() {
    if [[ -n "$BRANCH_NAME" && -f "$UPDATE_SCRIPT_PATH" ]]; then
        log_info "Updating repository to branch: $BRANCH_NAME"
        bash "$UPDATE_SCRIPT_PATH" -b "$BRANCH_NAME"
        if [[ $? -eq 0 ]]; then
            log_success "Repository updated successfully."
        else
            log_error "Repository update failed."
            exit 1
        fi
    else
        log_info "Repository update skipped."
    fi
}

handle_env_file() {
    log_info "Checking .env configuration..."

    local env_example="$REACT_APP_DIR/.env.example"

    if [[ -f "$ENV_FILE_PATH" ]]; then
        log_success ".env file found."
        # Handle explicit IP override (for advanced use cases)
        if [[ -n "$OVERWRITE_IP" ]]; then
            log_info "Overwriting server IP to: $OVERWRITE_IP"
            cp "$ENV_FILE_PATH" "$ENV_FILE_PATH.bak"
            # Add or update SERVER_URL line
            if grep -q "^REACT_APP_SERVER_URL=" "$ENV_FILE_PATH"; then
                sed -i "s|^REACT_APP_SERVER_URL=.*|REACT_APP_SERVER_URL=http://$OVERWRITE_IP|" "$ENV_FILE_PATH"
            else
                echo "REACT_APP_SERVER_URL=http://$OVERWRITE_IP" >> "$ENV_FILE_PATH"
            fi
            log_success "Server IP updated and backup created."
        fi
    else
        log_warn ".env file not found. Creating from template..."
        mkdir -p "$(dirname "$ENV_FILE_PATH")"

        if [[ -f "$env_example" ]]; then
            # Copy from .env.example (SERVER_URL is commented out for auto-detection)
            cp "$env_example" "$ENV_FILE_PATH"
            log_success ".env created from template"
            log_info "Server URL: Auto-detected from browser (no configuration needed)"
        else
            # Fallback: create minimal .env with essential settings
            cat > "$ENV_FILE_PATH" << EOF
# Auto-generated .env file
# Server URL is auto-detected from browser location (no configuration needed)
# Uncomment only if you need to override (e.g., different host):
# REACT_APP_SERVER_URL=http://192.168.1.100

REACT_APP_GCS_PORT=5000
REACT_APP_DRONE_PORT=7070
PORT=3030
GENERATE_SOURCEMAP=false
SKIP_PREFLIGHT_CHECK=true
EOF
            log_success ".env file created with auto-detection enabled"
        fi

        # Apply explicit override if provided
        if [[ -n "$OVERWRITE_IP" ]]; then
            log_info "Applying server IP override: $OVERWRITE_IP"
            # Add SERVER_URL for override
            if grep -q "^# REACT_APP_SERVER_URL=" "$ENV_FILE_PATH"; then
                sed -i "s|^# REACT_APP_SERVER_URL=.*|REACT_APP_SERVER_URL=http://$OVERWRITE_IP|" "$ENV_FILE_PATH"
            else
                echo "REACT_APP_SERVER_URL=http://$OVERWRITE_IP" >> "$ENV_FILE_PATH"
            fi
            log_success "Server IP override applied: $OVERWRITE_IP"
        fi
    fi
}

check_build_needed() {
    if [[ "$FORCE_REBUILD" == "true" ]]; then
        log_info "Force rebuild requested."
        return 0
    fi
    
    if [[ ! -d "$BUILD_DIR" ]]; then
        log_info "No build directory found. Build needed."
        return 0
    fi
    
    local package_json="$REACT_APP_DIR/package.json"
    if [[ "$package_json" -nt "$BUILD_DIR" ]]; then
        log_info "Package.json updated. Build needed."
        return 0
    fi
    
    local src_dir="$REACT_APP_DIR/src"
    if [[ -d "$src_dir" ]]; then
        local newest_src=$(find "$src_dir" -type f -newer "$BUILD_DIR" 2>/dev/null | head -1)
        if [[ -n "$newest_src" ]]; then
            log_info "Source files updated. Build needed."
            return 0
        fi
    fi
    
    log_info "Build is up-to-date. Skipping rebuild."
    return 1
}

build_react_app() {
    log_info "Building React application for production..."
    
    cd "$REACT_APP_DIR" || {
        log_error "Failed to navigate to React app directory: $REACT_APP_DIR"
        exit 1
    }
    
    if [[ ! -d "node_modules" || "$REACT_APP_DIR/package.json" -nt "node_modules" ]]; then
        log_info "Installing Node.js dependencies..."
        npm ci --only=production
        if [[ $? -ne 0 ]]; then
            log_error "Failed to install dependencies."
            exit 1
        fi
    fi
    
    log_info "Building optimized production bundle..."
    npm run build
    if [[ $? -ne 0 ]]; then
        log_error "Build failed."
        exit 1
    fi
    
    log_success "React build completed successfully."
}

verify_react_setup() {
    log_info "Verifying React setup..."

    if [[ ! -f "$REACT_APP_DIR/package.json" ]]; then
        log_error "package.json not found at: $REACT_APP_DIR"
        exit 1
    fi

    # Verify node_modules exists (MDS GCS Init integration)
    if [[ ! -d "$REACT_APP_DIR/node_modules" ]]; then
        log_warn "Node modules not installed at $REACT_APP_DIR"
        log_info "Installing npm dependencies..."
        (cd "$REACT_APP_DIR" && npm ci) || {
            log_warn "npm ci failed, trying npm install..."
            (cd "$REACT_APP_DIR" && npm install) || {
                log_error "Failed to install npm dependencies"
                log_info "Run: cd $REACT_APP_DIR && npm install"
                exit 1
            }
        }
        log_success "npm dependencies installed"
    fi

    log_success "React setup verified."
}

install_production_dependencies() {
    log_info "Installing production dependencies..."
    
    if ! python -c "import gunicorn" 2>/dev/null; then
        log_info "Installing gunicorn for production WSGI server..."
        pip install gunicorn
        if [[ $? -ne 0 ]]; then
            log_error "Failed to install gunicorn."
            exit 1
        fi
        log_success "Gunicorn installed successfully."
    else
        log_info "Gunicorn is already installed."
    fi
}

setup_production_environment() {
    if [[ "$DEPLOYMENT_MODE" == "production" ]]; then
        log_info "Configuring production environment..."
        # Environment configuration
        export GCS_ENV=production
        export GCS_PORT="$DEV_GCS_PORT"
        export GCS_BACKEND="$GCS_BACKEND"

        # Node/React environment
        export NODE_ENV=production
        export REACT_APP_ENV=production
        install_production_dependencies
        log_success "Production environment configured (Backend: $GCS_BACKEND)"
    else
        log_info "Configuring development environment..."
        # Environment configuration
        export GCS_ENV=development
        export GCS_PORT="$DEV_GCS_PORT"
        export GCS_BACKEND="$GCS_BACKEND"

        # Node/React environment
        export NODE_ENV=development
        export REACT_APP_ENV=development
        log_success "Development environment configured (Backend: $GCS_BACKEND)"
    fi
}

get_gcs_server_command() {
    # Set PYTHONPATH to include project root for module imports (functions, src, etc.)
    local python_path="PYTHONPATH='$PROJECT_ROOT:$PROJECT_ROOT/src:\$PYTHONPATH'"

    # Support both FastAPI and Flask backends
    if [[ "$GCS_BACKEND" == "fastapi" ]]; then
        if [[ "$DEPLOYMENT_MODE" == "production" ]]; then
            # FastAPI production: Gunicorn with Uvicorn workers
            echo "cd '$GCS_SERVER_DIR' && $python_path gunicorn -w $PROD_WSGI_WORKERS -k uvicorn.workers.UvicornWorker -b $PROD_WSGI_BIND --timeout $PROD_GUNICORN_TIMEOUT --log-level $PROD_LOG_LEVEL app_fastapi:app"
        else
            # FastAPI development: Uvicorn with auto-reload
            echo "cd '$GCS_SERVER_DIR' && $python_path uvicorn app_fastapi:app --host 0.0.0.0 --port $DEV_GCS_PORT --reload"
        fi
    else
        # Flask backend (legacy)
        if [[ "$DEPLOYMENT_MODE" == "production" ]]; then
            echo "cd '$GCS_SERVER_DIR' && $python_path gunicorn -w $PROD_WSGI_WORKERS -b $PROD_WSGI_BIND --timeout $PROD_GUNICORN_TIMEOUT --log-level $PROD_LOG_LEVEL app:app"
        else
            echo "cd '$GCS_SERVER_DIR' && $python_path python app.py"
        fi
    fi
}


get_react_command() {
    if [[ "$DEPLOYMENT_MODE" == "production" ]]; then
        if check_build_needed; then
            build_react_app
        fi
        echo "cd '$BUILD_DIR' && python3 -m http.server $DEV_REACT_PORT"
    else
        verify_react_setup
        echo "cd '$REACT_APP_DIR' && npm start"
    fi
}

start_services_in_tmux() {
    local session="$SESSION_NAME"
    
    # Kill existing session
    if tmux has-session -t "$session" 2>/dev/null; then
        log_warn "Killing existing tmux session: $session"
        tmux kill-session -t "$session"
        sleep 1
    fi
    
    log_info "Creating tmux session: $session (mode: $DEPLOYMENT_MODE)"
    tmux new-session -d -s "$session"
    tmux set-option -g mouse on
    
    local gcs_cmd=""
    local react_cmd=""
    
    if [[ "$RUN_GCS_SERVER" == "true" ]]; then
        gcs_cmd=$(get_gcs_server_command)
    fi
    
    if [[ "$RUN_GUI_APP" == "true" ]]; then
        react_cmd=$(get_react_command)
    fi
    
    if [[ "$COMBINED_VIEW" == "true" ]]; then
        tmux rename-window -t "$session:0" "Services"
        local pane_index=0
        
        if [[ "$RUN_GCS_SERVER" == "true" ]]; then
            tmux send-keys -t "$session:Services.$pane_index" "clear && echo 'Starting GCS server ($GCS_BACKEND) in $DEPLOYMENT_MODE mode...' && $gcs_cmd" C-m
            pane_index=$((pane_index + 1))
        fi
        
        if [[ "$RUN_GUI_APP" == "true" ]]; then
            if [[ $pane_index -gt 0 ]]; then
                tmux split-window -t "$session:Services" -h
            fi
            tmux send-keys -t "$session:Services.$pane_index" "clear && echo 'Starting React app in $DEPLOYMENT_MODE mode...' && $react_cmd" C-m
        fi
        
        if [[ $pane_index -gt 0 ]]; then
            tmux select-layout -t "$session:Services" tiled
        fi
    else
        # Separate windows
        local window_index=0
        
        if [[ "$RUN_GCS_SERVER" == "true" ]]; then
            tmux rename-window -t "$session:0" "GCS-Server"
            tmux send-keys -t "$session:GCS-Server" "clear && echo 'Starting GCS server ($GCS_BACKEND)...' && $gcs_cmd" C-m
            window_index=$((window_index + 1))
        fi
        
        if [[ "$RUN_GUI_APP" == "true" ]]; then
            if [[ $window_index -eq 0 ]]; then
                tmux rename-window -t "$session:0" "React-App"
            else
                tmux new-window -t "$session" -n "React-App"
            fi
            tmux send-keys -t "$session:React-App" "clear && echo 'Starting React app...' && $react_cmd" C-m
        fi
    fi
    
    show_tmux_instructions
    tmux attach-session -t "$session"
}

start_services_no_tmux() {
    log_info "Starting services without tmux in $DEPLOYMENT_MODE mode..."

    if [[ "$RUN_GCS_SERVER" == "true" ]]; then
        local gcs_cmd=$(get_gcs_server_command)
        gnome-terminal -- bash -c "echo 'Starting GCS server ($GCS_BACKEND) in $DEPLOYMENT_MODE mode...' && $gcs_cmd; exec bash"
    fi
    
    if [[ "$RUN_GUI_APP" == "true" ]]; then
        local react_cmd=$(get_react_command)
        gnome-terminal -- bash -c "echo 'Starting React app in $DEPLOYMENT_MODE mode...' && $react_cmd; exec bash"
    fi
}

show_tmux_instructions() {
    cat << EOF

===============================================
  tmux Session Guide (Mode: $DEPLOYMENT_MODE)
===============================================
Prefix key (Ctrl+B), then:
EOF

    if [[ "$COMBINED_VIEW" == "true" ]]; then
        echo "  - Switch panes: Arrow keys"
        echo "  - Resize panes: Hold Ctrl+B + Arrow key"
    else
        echo "  - Switch windows: Number keys (1, 2, etc.)"
    fi

    cat << EOF
  - Detach session: Ctrl+B, then D
  - Reattach: tmux attach -t $SESSION_NAME
  - Kill session: tmux kill-session -t $SESSION_NAME

MODE INFORMATION:
EOF

    if [[ "$DEPLOYMENT_MODE" == "production" ]]; then
        cat << EOF
  - React: Serving optimized build files
  - GCS Server: $GCS_BACKEND with gunicorn WSGI server
  - Working Dir: $GCS_SERVER_DIR
  - Logging: Production logging enabled
EOF
    else
        cat << EOF
  - React: Hot reload enabled on port $DEV_REACT_PORT
  - GCS Server: $GCS_BACKEND with auto-restart
  - Logging: Verbose debug logging enabled
EOF
    fi

    echo "==============================================="
    echo
}

display_config_summary() {
    cat << EOF

===============================================
  Configuration Summary
===============================================
Deployment Mode: $(echo $DEPLOYMENT_MODE | tr '[:lower:]' '[:upper:]')
Branch: $BRANCH_NAME
GCS Server: $([[ "$RUN_GCS_SERVER" == "true" ]] && echo "ENABLED" || echo "DISABLED")
GUI React App: $([[ "$RUN_GUI_APP" == "true" ]] && echo "ENABLED" || echo "DISABLED")
Tmux: $([[ "$USE_TMUX" == "true" ]] && echo "ENABLED" || echo "DISABLED")
View: $([[ "$COMBINED_VIEW" == "true" ]] && echo "Combined Panes" || echo "Separate Windows")
Force Rebuild: $([[ "$FORCE_REBUILD" == "true" ]] && echo "YES" || echo "NO")
EOF

    if [[ "$DEPLOYMENT_MODE" == "production" ]]; then
        cat << EOF

PRODUCTION CONFIG:
  - WSGI Workers: $PROD_WSGI_WORKERS
  - Bind Address: $PROD_WSGI_BIND
  - Timeout: $PROD_GUNICORN_TIMEOUT seconds
  - Working Dir: $GCS_SERVER_DIR (FIXED)
  - Build Optimization: ENABLED
EOF
    else
        cat << EOF

DEVELOPMENT CONFIG:
  - React Port: $DEV_REACT_PORT
  - GCS Port: $DEV_GCS_PORT
  - Hot Reload: ENABLED
  - Debug Mode: ENABLED
EOF
    fi

    if [[ "$USE_REAL" == "true" ]]; then
        echo "Drone Mode: REAL (Hardware) [switching]"
    elif [[ "$USE_SITL" == "true" ]]; then
        echo "Drone Mode: SITL (Simulation) [switching]"
    else
        echo "Drone Mode: $(get_current_drone_mode) [current]"
    fi

    if [[ -n "$OVERWRITE_IP" ]]; then
        echo "Server IP Override: $OVERWRITE_IP"
    fi

    echo "==============================================="
    echo
}

#########################################
# MAIN EXECUTION
#########################################

# Banner - Use shared banner if available
display_startup_banner() {
    local banner_path="$PARENT_DIR/tools/mds_banner.sh"
    if [[ -f "$banner_path" ]]; then
        source "$banner_path"
        local git_info branch commit git_date
        git_info=$(get_git_info "$PARENT_DIR" 2>/dev/null || echo "unknown|unknown|unknown")
        IFS='|' read -r branch commit git_date <<< "$git_info"
        print_mds_banner "Dashboard Services" "4.3.0" "$branch" "$commit"
    else
        # Fallback banner
        echo ""
        echo ",--.   ,--.,------.   ,---.   "
        echo "|   \`.'   ||  .-.  \\ '   .-'  "
        echo "|  |'.'|  ||  |  \\  :\`.  \`-.  "
        echo "|  |   |  ||  '--'  /.-'    | "
        echo "\`--'   \`--'\`-------' \`-----'  "
        echo ""
        echo "MAVSDK Drone Show - Dashboard Services"
        echo "================================================"
        echo "Version:  4.3.0"
        echo "================================================"
        echo ""
    fi
}

display_startup_banner

# Parse arguments and initialize
parse_arguments "$@"

# Load GCS system configuration if available (MDS GCS Init integration)
if load_gcs_system_config; then
    log_info "Loaded system configuration from $GCS_SYSTEM_CONFIG"
fi

# Handle --check option (run checks only, don't start services)
if [[ "$CHECK_ONLY" == "true" ]]; then
    run_configuration_check
    exit 0
fi

log_info "Initializing Drone Services System..."
display_config_summary

# System checks
check_command_installed "tmux" "tmux"
check_command_installed "lsof" "lsof"

# GCS initialization check (MDS GCS Init integration)
check_gcs_initialized

# Execute setup sequence
handle_real_mode_file
update_repository
load_virtualenv
validate_backend  # Check FastAPI availability
check_python_dependencies  # Smart dependency check
handle_env_file
setup_production_environment

# Port management
log_info "Checking ports for $DEPLOYMENT_MODE mode..."
if [[ "$RUN_GCS_SERVER" == "true" ]]; then
    if [[ "$DEPLOYMENT_MODE" == "production" ]]; then
        prod_port=$(echo "$PROD_WSGI_BIND" | cut -d':' -f2)
        check_and_kill_port "$prod_port"
    else
        check_and_kill_port "$DEV_GCS_PORT"
    fi
fi

if [[ "$RUN_GUI_APP" == "true" ]]; then
    check_and_kill_port "$DEV_REACT_PORT"
fi

# Start services
if [[ "$USE_TMUX" == "true" ]]; then
    start_services_in_tmux
else
    start_services_no_tmux
fi

log_success "Drone Services System Started Successfully!"
log_info "Mode: $(echo $DEPLOYMENT_MODE | tr '[:lower:]' '[:upper:]') | Backend: $GCS_BACKEND | Drone: $(get_current_drone_mode)"

if [[ "$DEPLOYMENT_MODE" == "production" ]]; then
    log_info "Production optimizations active"
else
    log_info "Development mode with hot reloading active"
fi

echo ""
echo "Quick Commands:"
echo "  Check health:  curl http://localhost:$DEV_GCS_PORT/health"
echo "  View status:   $0 --status"
echo "  Stop services: tmux kill-session -t $SESSION_NAME"