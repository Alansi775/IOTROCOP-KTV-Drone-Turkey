#!/bin/bash

# 1. Video Bridge
echo "Starting Video Bridge..."
cd /home/iot/microservices
python3 rpi_bridge.py &

# 2. STM32 Forwarder
echo "Starting STM32 Forwarder..."
python3 stm32_forwarder.py &

# 3. Wait
sleep 5

# 4. Flutter UI
echo "Starting Flutter Dashboard..."
cd /home/iot/video_streaming_panel
sudo flutter-pi build/flutter_assets
