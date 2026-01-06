# MAVLink Routing Setup Guide

## Overview

mavsdk_drone_show requires **external MAVLink routing** via mavlink-anywhere or a custom router setup. The application no longer manages MAVLink routing internally - this provides better flexibility and allows multiple applications to share the MAVLink data stream.

## Architecture

```
                        Flight Controller (Pixhawk/PX4)
                              │
           ┌──────────────────┴──────────────────┐
           │         mavlink-routerd             │
           │   (mavlink-anywhere or manual)      │
           └──────────────────┬──────────────────┘
                              │
     ┌────────────────────────┼────────────────────────┐
     │                        │                        │
     ▼                        ▼                        ▼
┌─────────────┐      ┌─────────────────┐      ┌─────────────┐
│   MAVSDK    │      │  mavlink2rest   │      │     GCS     │
│ :14540/UDP  │      │   :14569/UDP    │      │ :14550/UDP  │
│ coordinator │      │    REST API     │      │     QGC     │
└─────────────┘      └─────────────────┘      └─────────────┘
     │
     ▼
┌─────────────────────┐
│LocalMavlinkController│
│    :12550/UDP       │
│  (pymavlink telem)  │
└─────────────────────┘
```

## Port Reference

| Port  | Service               | Direction | Description                          |
|-------|-----------------------|-----------|--------------------------------------|
| 14540 | MAVSDK                | Local     | coordinator.py SDK connection        |
| 12550 | LocalMavlinkController| Local     | pymavlink telemetry monitoring       |
| 14569 | mavlink2rest          | Local     | REST API bridge for web interfaces   |
| 14550 | GCS                   | Network   | QGroundControl or other GCS          |

## Setup Options

### Option A: SITL/Docker Mode (Automatic)

For SITL containers, MAVLink routing is handled automatically by `startup_sitl.sh` which calls `tools/run_mavlink_router.sh`. No manual setup is required.

The script reads `GCS_IP` from `Params.GCS_IP` to route MAVLink to your ground control station.

### Option B: Real Hardware (Raspberry Pi) - Manual Setup

For real hardware deployment, you need to set up mavlink-anywhere as a systemd service.

#### Prerequisites

- Raspberry Pi with serial UART enabled
- Serial console DISABLED (required for MAVLink on /dev/ttyS0)
- Flight controller connected via serial cable

#### Step 1: Enable UART and Disable Serial Console

```bash
sudo raspi-config
# Interface Options → Serial Port →
#   "Login shell over serial?" → NO
#   "Enable serial hardware?" → YES
# Reboot after making changes
```

#### Step 2: Install mavlink-anywhere

```bash
cd ~
git clone https://github.com/alireza787b/mavlink-anywhere.git
cd mavlink-anywhere
chmod +x install_mavlink_router.sh
sudo ./install_mavlink_router.sh
```

**Note**: This builds mavlink-router from source. Takes approximately 10 minutes on Raspberry Pi.

#### Step 3: Configure Routing Endpoints

```bash
sudo ./configure_mavlink_router.sh
```

When prompted, enter:
- **UART device**: `/dev/ttyS0` (Pi Zero/3/4) or `/dev/ttyAMA0` (older Pi)
- **Baud rate**: `57600` (must match Pixhawk TELEM port setting)
- **UDP endpoints**: `127.0.0.1:14540 127.0.0.1:14569 127.0.0.1:12550 YOUR_GCS_IP:14550`

**Example for GCS at 192.168.1.100**:
```
UDP endpoints: 127.0.0.1:14540 127.0.0.1:14569 127.0.0.1:12550 192.168.1.100:14550
```

**Important**: Include all four endpoints:
- `127.0.0.1:14540` - MAVSDK (coordinator.py)
- `127.0.0.1:14569` - mavlink2rest
- `127.0.0.1:12550` - LocalMavlinkController (pymavlink telemetry)
- `GCS_IP:14550` - Ground Control Station

#### Step 4: Enable and Start Service

```bash
sudo systemctl daemon-reload
sudo systemctl enable mavlink-router
sudo systemctl start mavlink-router
```

#### Step 5: Verify Service is Running

```bash
sudo systemctl status mavlink-router
# Should show "active (running)"

# Check logs for MAVLink activity
sudo journalctl -u mavlink-router -f
```

## Manual Configuration (Alternative)

If you prefer manual configuration, create `/etc/mavlink-router/main.conf`:

```ini
[General]
TcpServerPort=5760
ReportStats=false

[UartEndpoint uart]
Device=/dev/ttyS0
Baud=57600

[UdpEndpoint mavsdk]
Mode=normal
Address=127.0.0.1
Port=14540

[UdpEndpoint local_mavlink]
Mode=normal
Address=127.0.0.1
Port=12550

[UdpEndpoint mavlink2rest]
Mode=normal
Address=127.0.0.1
Port=14569

[UdpEndpoint gcs]
Mode=normal
Address=192.168.1.100
Port=14550
```

Replace `192.168.1.100` with your actual GCS IP address.

## Troubleshooting

### No MAVLink Data

1. **Check serial cable connection** - Ensure TX/RX are crossed correctly
2. **Verify baud rate** - Must match Pixhawk TELEM port (usually 57600)
3. **Check UART permissions** - `ls -l /dev/ttyS0` should show `crw-rw----`

### Permission Denied on Serial Port

Add user to dialout group:
```bash
sudo usermod -a -G dialout $USER
# Log out and back in for changes to take effect
```

### Service Won't Start

Check configuration syntax:
```bash
cat /etc/mavlink-router/main.conf
mavlink-routerd --conf /etc/mavlink-router/main.conf
```

### Port Already in Use

Check for conflicting processes:
```bash
sudo netstat -tulpn | grep -E "14540|14550|14569|12550"
```

### coordinator.py Can't Connect to MAVSDK

1. Verify mavlink-router is running: `systemctl status mavlink-router`
2. Check port 14540 is receiving data: `sudo tcpdump -i lo udp port 14540`
3. Ensure `Params.mavsdk_port` matches the router config (default: 14540)

## Migration Notes

Prior to this change, mavsdk_drone_show used an internal `MavlinkManager` class that spawned `mavlink-routerd` as a subprocess. This was removed because:

1. **Conflict potential** - Multiple apps fighting for serial port access
2. **No sharing** - Only one consumer per endpoint
3. **Tight coupling** - Application responsible for system-level routing

With external routing:
1. **Multiple consumers** - QGC, mavlink2rest, custom tools can all receive data
2. **System-level config** - Persists across app restarts
3. **Separation of concerns** - Routing is infrastructure, not app logic

## See Also

- [mavlink-anywhere GitHub](https://github.com/alireza787b/mavlink-anywhere)
- [mavlink-router Documentation](https://github.com/mavlink-router/mavlink-router)
- [SITL Comprehensive Guide](./sitl-comprehensive.md)
