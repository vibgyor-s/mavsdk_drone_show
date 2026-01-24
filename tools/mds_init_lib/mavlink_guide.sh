#!/bin/bash
# =============================================================================
# MDS Initialization Library: mavlink-anywhere Guidance
# =============================================================================
# Version: 4.0.0
# Description: Display instructions for manual mavlink-anywhere setup
# Author: MDS Team
# =============================================================================

# Prevent double-sourcing
[[ -n "${_MDS_MAVLINK_GUIDE_LOADED:-}" ]] && return 0
_MDS_MAVLINK_GUIDE_LOADED=1

# =============================================================================
# MAVLINK-ANYWHERE GUIDANCE
# =============================================================================

# TODO: Automate mavlink-anywhere installation in future release
# This phase currently provides guidance only. Future versions will support:
#   --install-mavlink-anywhere    Automatic installation and configuration
#   --mavlink-uart /dev/ttyS0     Specify UART device
#   --mavlink-baud 57600          Specify baud rate

# Check if mavlink-router is already installed
check_mavlink_router_installed() {
    if command_exists mavlink-routerd; then
        return 0
    fi

    if systemctl list-unit-files | grep -q "mavlink-router.service"; then
        return 0
    fi

    return 1
}

# Check if mavlink-router service is running
check_mavlink_router_running() {
    service_is_active "mavlink-router"
}

# Display mavlink-anywhere setup instructions
display_mavlink_instructions() {
    local gcs_ip="${1:-\${GCS_IP\}}"

    echo ""
    echo -e "${CYAN}┌────────────────────────────────────────────────────────────────────────────┐${NC}"
    echo -e "${CYAN}│${NC}  ${WHITE}mavlink-anywhere Installation Steps${NC}                                       ${CYAN}│${NC}"
    echo -e "${CYAN}├────────────────────────────────────────────────────────────────────────────┤${NC}"
    echo -e "${CYAN}│${NC}                                                                            ${CYAN}│${NC}"
    echo -e "${CYAN}│${NC}  ${BOLD}1. Clone the repository:${NC}                                                 ${CYAN}│${NC}"
    echo -e "${CYAN}│${NC}     ${GREEN}git clone https://github.com/alireza787b/mavlink-anywhere.git${NC}         ${CYAN}│${NC}"
    echo -e "${CYAN}│${NC}                                                                            ${CYAN}│${NC}"
    echo -e "${CYAN}│${NC}  ${BOLD}2. Install mavlink-router:${NC}                                               ${CYAN}│${NC}"
    echo -e "${CYAN}│${NC}     ${GREEN}cd mavlink-anywhere${NC}                                                    ${CYAN}│${NC}"
    echo -e "${CYAN}│${NC}     ${GREEN}sudo ./install_mavlink_router.sh${NC}                                       ${CYAN}│${NC}"
    echo -e "${CYAN}│${NC}                                                                            ${CYAN}│${NC}"
    echo -e "${CYAN}│${NC}  ${BOLD}3. Configure mavlink-router:${NC}                                             ${CYAN}│${NC}"
    echo -e "${CYAN}│${NC}     ${GREEN}sudo ./configure_mavlink_router.sh${NC}                                     ${CYAN}│${NC}"
    echo -e "${CYAN}│${NC}                                                                            ${CYAN}│${NC}"
    echo -e "${CYAN}│${NC}     ${DIM}When prompted, enter:${NC}                                                  ${CYAN}│${NC}"
    echo -e "${CYAN}│${NC}     ${DIM}- UART Device: /dev/ttyS0 (or /dev/ttyAMA0 for older Pi)${NC}               ${CYAN}│${NC}"
    echo -e "${CYAN}│${NC}     ${DIM}- Baud Rate: 57600${NC}                                                     ${CYAN}│${NC}"
    echo -e "${CYAN}│${NC}     ${DIM}- UDP Endpoints:${NC}                                                       ${CYAN}│${NC}"
    echo -e "${CYAN}│${NC}       ${DIM}• 127.0.0.1:14540  (MAVSDK)${NC}                                          ${CYAN}│${NC}"
    echo -e "${CYAN}│${NC}       ${DIM}• 127.0.0.1:14569  (mavlink2rest)${NC}                                    ${CYAN}│${NC}"
    echo -e "${CYAN}│${NC}       ${DIM}• 127.0.0.1:12550  (Local telemetry)${NC}                                 ${CYAN}│${NC}"
    echo -e "${CYAN}│${NC}       ${DIM}• ${gcs_ip}:24550  (GCS over VPN)${NC}                                     ${CYAN}│${NC}"
    echo -e "${CYAN}│${NC}                                                                            ${CYAN}│${NC}"
    echo -e "${CYAN}│${NC}  ${BOLD}4. Enable the service:${NC}                                                   ${CYAN}│${NC}"
    echo -e "${CYAN}│${NC}     ${GREEN}sudo systemctl enable mavlink-router${NC}                                   ${CYAN}│${NC}"
    echo -e "${CYAN}│${NC}     ${GREEN}sudo systemctl start mavlink-router${NC}                                    ${CYAN}│${NC}"
    echo -e "${CYAN}│${NC}                                                                            ${CYAN}│${NC}"
    echo -e "${CYAN}│${NC}  ${BOLD}5. Verify installation:${NC}                                                  ${CYAN}│${NC}"
    echo -e "${CYAN}│${NC}     ${GREEN}sudo systemctl status mavlink-router${NC}                                   ${CYAN}│${NC}"
    echo -e "${CYAN}│${NC}                                                                            ${CYAN}│${NC}"
    echo -e "${CYAN}└────────────────────────────────────────────────────────────────────────────┘${NC}"
    echo ""
}

# Display UART selection guidance
display_uart_selection_guide() {
    echo ""
    echo -e "${CYAN}┌────────────────────────────────────────────────────────────────────────────┐${NC}"
    echo -e "${CYAN}│${NC}  ${WHITE}UART Device Selection Guide${NC}                                              ${CYAN}│${NC}"
    echo -e "${CYAN}├────────────────────────────────────────────────────────────────────────────┤${NC}"
    echo -e "${CYAN}│${NC}                                                                            ${CYAN}│${NC}"
    echo -e "${CYAN}│${NC}  ${BOLD}Raspberry Pi 4/5 (64-bit OS):${NC}                                            ${CYAN}│${NC}"
    echo -e "${CYAN}│${NC}    Primary UART:    ${GREEN}/dev/ttyAMA0${NC}   (GPIO 14/15, pins 8/10)                ${CYAN}│${NC}"
    echo -e "${CYAN}│${NC}    Mini UART:       ${GREEN}/dev/ttyS0${NC}     (GPIO 14/15, when Bluetooth enabled)  ${CYAN}│${NC}"
    echo -e "${CYAN}│${NC}                                                                            ${CYAN}│${NC}"
    echo -e "${CYAN}│${NC}  ${BOLD}Raspberry Pi 3 (32-bit OS):${NC}                                              ${CYAN}│${NC}"
    echo -e "${CYAN}│${NC}    Use:             ${GREEN}/dev/ttyS0${NC}                                            ${CYAN}│${NC}"
    echo -e "${CYAN}│${NC}                                                                            ${CYAN}│${NC}"
    echo -e "${CYAN}│${NC}  ${BOLD}Check available ports:${NC}                                                   ${CYAN}│${NC}"
    echo -e "${CYAN}│${NC}    ${DIM}ls -la /dev/tty*${NC}                                                        ${CYAN}│${NC}"
    echo -e "${CYAN}│${NC}    ${DIM}ls -la /dev/serial*${NC}                                                     ${CYAN}│${NC}"
    echo -e "${CYAN}│${NC}                                                                            ${CYAN}│${NC}"
    echo -e "${CYAN}│${NC}  ${BOLD}Enable UART in /boot/config.txt:${NC}                                         ${CYAN}│${NC}"
    echo -e "${CYAN}│${NC}    ${DIM}enable_uart=1${NC}                                                           ${CYAN}│${NC}"
    echo -e "${CYAN}│${NC}    ${DIM}dtoverlay=disable-bt${NC}  (Optional: frees /dev/ttyAMA0 from Bluetooth)     ${CYAN}│${NC}"
    echo -e "${CYAN}│${NC}                                                                            ${CYAN}│${NC}"
    echo -e "${CYAN}└────────────────────────────────────────────────────────────────────────────┘${NC}"
    echo ""
}

# Display endpoint configuration reference
display_endpoint_reference() {
    echo ""
    echo -e "${CYAN}┌────────────────────────────────────────────────────────────────────────────┐${NC}"
    echo -e "${CYAN}│${NC}  ${WHITE}MAVLink Endpoint Configuration Reference${NC}                                ${CYAN}│${NC}"
    echo -e "${CYAN}├────────────────────────────────────────────────────────────────────────────┤${NC}"
    echo -e "${CYAN}│${NC}                                                                            ${CYAN}│${NC}"
    echo -e "${CYAN}│${NC}  ${BOLD}Port${NC}      ${BOLD}Protocol${NC}   ${BOLD}Service${NC}              ${BOLD}Direction${NC}                     ${CYAN}│${NC}"
    echo -e "${CYAN}│${NC}  ──────────────────────────────────────────────────────────────────────  ${CYAN}│${NC}"
    echo -e "${CYAN}│${NC}  14540     UDP        MAVSDK SDK           Local                         ${CYAN}│${NC}"
    echo -e "${CYAN}│${NC}  14550     UDP        GCS/QGroundControl   Bidirectional                 ${CYAN}│${NC}"
    echo -e "${CYAN}│${NC}  14569     UDP        mavlink2rest         Local                         ${CYAN}│${NC}"
    echo -e "${CYAN}│${NC}  12550     UDP        Local telemetry      Local                         ${CYAN}│${NC}"
    echo -e "${CYAN}│${NC}  24550     UDP        Remote GCS over VPN  Outbound                      ${CYAN}│${NC}"
    echo -e "${CYAN}│${NC}  34550     UDP        MAVLink aggregation  Local                         ${CYAN}│${NC}"
    echo -e "${CYAN}│${NC}                                                                            ${CYAN}│${NC}"
    echo -e "${CYAN}│${NC}  ${DIM}These endpoints should be configured in mavlink-router${NC}                  ${CYAN}│${NC}"
    echo -e "${CYAN}│${NC}  ${DIM}Configuration file: /etc/mavlink-router/main.conf${NC}                       ${CYAN}│${NC}"
    echo -e "${CYAN}│${NC}                                                                            ${CYAN}│${NC}"
    echo -e "${CYAN}└────────────────────────────────────────────────────────────────────────────┘${NC}"
    echo ""
}

# =============================================================================
# MAIN MAVLINK GUIDANCE RUNNER
# =============================================================================

run_mavlink_guidance_phase() {
    print_phase_header "2" "mavlink-anywhere Guidance"

    set_led_state "NETWORK_INIT"

    # Check if mavlink-router is already configured
    if check_mavlink_router_installed; then
        log_success "mavlink-router is already installed"

        if check_mavlink_router_running; then
            log_success "mavlink-router service is running"

            # Show configuration location
            if [[ -f /etc/mavlink-router/main.conf ]]; then
                echo ""
                log_info "Current configuration: /etc/mavlink-router/main.conf"
                echo ""
            fi

            if [[ "${NON_INTERACTIVE:-false}" != "true" ]]; then
                echo ""
                if ! confirm "mavlink-router appears configured. Skip guidance?" "y"; then
                    display_mavlink_instructions "${GCS_IP:-}"
                    display_endpoint_reference
                fi
            fi

            return 0
        else
            log_warn "mavlink-router installed but not running"
            log_info "Start with: sudo systemctl start mavlink-router"
        fi
    else
        log_warn "mavlink-router not detected"
    fi

    # Display full guidance
    echo ""
    echo -e "  ${YELLOW}mavlink-anywhere must be configured separately.${NC}"
    echo -e "  ${DIM}This provides MAVLink routing between flight controller and MDS services.${NC}"
    echo ""

    display_mavlink_instructions "${GCS_IP:-}"

    if [[ "${VERBOSE:-false}" == "true" ]]; then
        display_uart_selection_guide
        display_endpoint_reference
    fi

    # Interactive mode: wait for user acknowledgment
    if [[ "${NON_INTERACTIVE:-false}" != "true" ]]; then
        echo ""
        echo -e "  ${INFO} ${WHITE}Please set up mavlink-anywhere before continuing.${NC}"
        echo -e "  ${DIM}Press Enter to continue when ready, or Ctrl+C to exit and configure first.${NC}"
        echo ""

        if confirm "Have you configured mavlink-anywhere (or will configure later)?" "y"; then
            log_info "Continuing with initialization..."
        else
            echo ""
            log_info "Run this script again after configuring mavlink-anywhere."
            echo ""
            echo -e "  ${CYAN}Quick start command:${NC}"
            echo -e "  ${GREEN}git clone https://github.com/alireza787b/mavlink-anywhere.git && cd mavlink-anywhere && sudo ./install_mavlink_router.sh${NC}"
            echo ""
            return 1
        fi
    else
        log_info "Non-interactive mode: skipping mavlink-anywhere guidance acknowledgment"
    fi

    return 0
}
