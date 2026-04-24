#!/bin/bash

# 1. Python Köprüsünü başlat (Arka planda)
echo "Python Bridge başlatılıyor..."
cd /home/iot/microservices
python3 rpi_bridge.py &

# 2. Drone Monitor Network servisini başlat (Arka planda)
echo "Drone Monitor Network başlatılıyor..."
python3 drone_monitor_network.py &

# 3. Python servislerinin tamamen ayağa kalkması için bekle
sleep 5

# 4. Flutter Arayüzünü başlat
echo "Flutter Dashboard başlatılıyor..."
cd /home/iot/video_streaming_panel
sudo flutter-pi build/flutter_assets
