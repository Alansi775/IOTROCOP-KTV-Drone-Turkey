# Drone Module - NVIDIA Jetson Xavier NX

Onboard computer system for autonomous drone control.

## Components

### droneCommands
- `full_control.py` - Main flight controller interface
- `gps_bridge.py` - GPS data UDP bridge
- MAVSDK integration for Pixhawk communication

### microservices
- `jetson_pure_gst.py` - GStreamer camera pipeline
- Video encoding and streaming services

## Services

All services are configured for automatic startup:

- **mavsdk-server** - Flight controller communication (port 50051)
- **drone-control** - Offboard flight control (UDP 5656)
- **gps-bridge** - GPS data streaming (UDP 5658)
- **camera-stream** - Video streaming (HTTP 5000)

## Configuration

Serial Port: `/dev/ttyACM0` (Pixhawk Orange Cube)
Baud Rate: 921600
Network: 192.168.100.2 (Fiber Optic)

## Testing

```bash
# Check all services
sudo systemctl status mavsdk-server
sudo systemctl status drone-control
sudo systemctl status gps-bridge
sudo systemctl status camera-stream

# Send test GPS
python3 /tmp/test_gps_istanbul.py
```
