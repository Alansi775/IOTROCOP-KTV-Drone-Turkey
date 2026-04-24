#!/usr/bin/env python3
"""
Joystick UDP Receiver
192.168.100.2 IP'li cihazda çalışır
UDP port 5005'ten joystick verilerini alır ve konsola yazdırır
"""

import socket
import json
import time
from datetime import datetime
import sys

# ============================================================================
#  KONFIGÜRASYON
# ============================================================================
UDP_IP = "0.0.0.0"  # Tüm interfaceler
UDP_PORT = 5005

# ============================================================================
#  GÖRSEL ARAYÜZ
# ============================================================================
class ReceiverUI:
    def __init__(self):
        self.packet_count = 0
        self.error_count = 0
        self.start_time = None
        self.last_sender_ip = None
    
    def format_uptime(self, seconds):
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    
    def get_position_indicator(self, x_norm, y_norm):
        """8 yön + merkez"""
        x_offset = x_norm - 2000
        y_offset = y_norm - 2000
        threshold = 200
        
        if abs(x_offset) < threshold and abs(y_offset) < threshold:
            return "🎯 MERKEZ", "●"
        
        if abs(y_offset) < threshold:
            if x_offset > 0:
                return "➡️  SAĞ", "→"
            else:
                return "⬅️  SOL", "←"
        
        if abs(x_offset) < threshold:
            if y_offset > 0:
                return "⬇️  GERİ", "↓"
            else:
                return "⬆️  İLERİ", "↑"
        
        if x_offset > 0 and y_offset < 0:
            return "↗️  SAĞ-İLERİ", "↗"
        elif x_offset < 0 and y_offset < 0:
            return "↖️  SOL-İLERİ", "↖"
        elif x_offset > 0 and y_offset > 0:
            return "↘️  SAĞ-GERİ", "↘"
        else:
            return "↙️  SOL-GERİ", "↙"
    
    def get_intensity(self, x_norm, y_norm):
        """Merkezden uzaklık %"""
        x_offset = x_norm - 2000
        y_offset = y_norm - 2000
        distance = (x_offset**2 + y_offset**2)**0.5
        max_distance = 2000 * (2**0.5)
        intensity = (distance / max_distance) * 100
        return min(100, intensity)
    
    def print_header(self):
        """Başlangıç header'ı"""
        print("=" * 110)
        print("📥  JOYSTICK UDP RECEIVER - 192.168.100.2")
        print("=" * 110)
        print(f"🌐 Listening on: {UDP_IP}:{UDP_PORT}")
        print(f"💡 Joystick verilerini bekliyor... (Ctrl+C ile durdurun)")
        print("=" * 110)
        print()
        print("Format: [Zaman] YÖN | Güç% | X:değer Y:değer | RAW X:adc Y:adc | Paket# | Kaynak IP")
        print("-" * 110)
    
    def print_packet(self, data, sender_ip):
        """Alınan paketi yazdır"""
        try:
            x_raw = data.get('x_raw', 0)
            y_raw = data.get('y_raw', 0)
            x_norm = data.get('x_normalized', 0)
            y_norm = data.get('y_normalized', 0)
            timestamp = data.get('timestamp', time.time())
            
            direction_text, direction_arrow = self.get_position_indicator(x_norm, y_norm)
            intensity = self.get_intensity(x_norm, y_norm)
            
            # Timestamp
            dt = datetime.fromtimestamp(timestamp)
            time_str = dt.strftime('%H:%M:%S.%f')[:-3]
            
            # Paket numarası artır
            self.packet_count += 1
            
            # Yazdır
            print(f"✅ [{time_str}] {direction_arrow} {direction_text:<15s} | Güç:{intensity:5.1f}% | X:{x_norm:4d} Y:{y_norm:4d} | RAW X:{x_raw:4d} Y:{y_raw:4d} | Paket#{self.packet_count} | {sender_ip}")
            
        except Exception as e:
            print(f"❌ Parse hatası: {e}")
            self.error_count += 1
    
    def print_stats(self):
        """Periyodik istatistikler"""
        if self.packet_count % 50 == 0 and self.packet_count > 0:
            uptime = time.time() - self.start_time if self.start_time else 0
            success_rate = (self.packet_count / (self.packet_count + self.error_count) * 100) if (self.packet_count + self.error_count) > 0 else 0
            print(f"\n📊 İstatistik: Alınan:{self.packet_count} | Hata:{self.error_count} | Başarı:{success_rate:.1f}% | Uptime:{self.format_uptime(uptime)}\n")
    
    def print_new_sender(self, sender_ip):
        """Yeni gönderici tespit edildiğinde"""
        if sender_ip != self.last_sender_ip:
            print(f"\n🆕 Yeni gönderici algılandı: {sender_ip}\n")
            self.last_sender_ip = sender_ip

# ============================================================================
#  UDP RECEIVER
# ============================================================================
class UDPReceiver:
    def __init__(self, listen_ip, listen_port):
        self.listen_ip = listen_ip
        self.listen_port = listen_port
        self.sock = None
        
    def start(self):
        """UDP socket'i başlat"""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.bind((self.listen_ip, self.listen_port))
            self.sock.settimeout(1.0)  # 1 saniye timeout
            return True
        except Exception as e:
            print(f"❌ Socket başlatma hatası: {e}")
            return False
    
    def receive(self):
        """Veri al (blocking değil, timeout var)"""
        try:
            data, addr = self.sock.recvfrom(1024)  # Buffer: 1KB
            sender_ip = addr[0]
            
            # JSON parse
            json_data = json.loads(data.decode('utf-8'))
            
            return json_data, sender_ip
            
        except socket.timeout:
            return None, None
        except json.JSONDecodeError as e:
            print(f"❌ JSON decode hatası: {e}")
            return None, None
        except Exception as e:
            return None, None
    
    def close(self):
        """Socket'i kapat"""
        try:
            if self.sock:
                self.sock.close()
        except:
            pass

# ============================================================================
#  ANA PROGRAM
# ============================================================================
def main():
    print("=" * 110)
    print("📥  JOYSTICK UDP RECEIVER - BAŞLATILIYOR")
    print("=" * 110)
    print(f"\n🌐 UDP Server: {UDP_IP}:{UDP_PORT}")
    print("🔄 Socket başlatılıyor...\n")
    
    time.sleep(1)
    
    ui = ReceiverUI()
    receiver = UDPReceiver(UDP_IP, UDP_PORT)
    
    if not receiver.start():
        print("❌ HATA: UDP socket başlatılamadı!")
        sys.exit(1)
    
    print("✅ Socket başarıyla başlatıldı")
    time.sleep(1)
    
    ui.print_header()
    ui.start_time = time.time()
    
    try:
        while True:
            # Veri al
            data, sender_ip = receiver.receive()
            
            if data and sender_ip:
                # Yeni gönderici kontrolü
                ui.print_new_sender(sender_ip)
                
                # Paketi yazdır
                ui.print_packet(data, sender_ip)
                
                # İstatistik
                ui.print_stats()
    
    except KeyboardInterrupt:
        print("\n\n🛑 Durduruldu (Ctrl+C)")
        print(f"📊 Toplam Alınan Paket: {ui.packet_count}")
        print(f"❌ Toplam Hata: {ui.error_count}")
        
        if ui.start_time:
            uptime = time.time() - ui.start_time
            print(f"⏱  Çalışma Süresi: {ui.format_uptime(uptime)}")
    
    except Exception as e:
        print(f"\n\n❌ Beklenmeyen hata: {e}")
    
    finally:
        receiver.close()
        print("✅ Çıkış")

if __name__ == '__main__':
    main()
