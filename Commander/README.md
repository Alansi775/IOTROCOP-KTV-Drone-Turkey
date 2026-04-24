# Commander Module - Raspberry Pi 4

Ground control station with Flutter UI for drone monitoring and control.

## Components

### video_streaming_panel
Flutter application featuring:
- Real-time MJPEG video display
- GPS tracking with interactive map
- Joystick telemetry visualization
- Connection status monitoring

### microservices
- `rpi_bridge.py` - Video proxy server (port 8080)
- `manual_joystick.py` - Keyboard control interface

## System Service

The Flutter app runs as a systemd service:

```bash
sudo systemctl status drone_app
sudo systemctl restart drone_app
```

## Manual Testing

```bash
cd ~/microservices
python3 manual_joystick.py

# Controls:
# SPACE - ARM/DISARM
# W/S   - Throttle UP/DOWN
# A/D   - Roll LEFT/RIGHT
# Q/E   - Pitch FORWARD/BACK
```

## Network Configuration

- IP: 192.168.100.1
- Video Proxy: Port 8080
- GPS Listener: Port 5658
- Telemetry Listener: Port 5657
