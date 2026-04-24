import socket
import time

# Hedefin (Raspberry Pi'nin) IP Adresi
TARGET_IP = "192.168.100.1"
UDP_PORT = 5005
MESSAGE = "Selam Yer Istasyonu, ben Drone!"

print(f"Hedef IP: {TARGET_IP} hedef portuna veri gönderiliyor...")

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP

sayac = 0
while True:
    sayac += 1
    gonderilecek_veri = f"{MESSAGE} - Paket No: {sayac}"
    
    sock.sendto(gonderilecek_veri.encode(), (TARGET_IP, UDP_PORT))
    print(f"Gonderildi: {gonderilecek_veri}")
    
    time.sleep(1) # Saniyede 1 mesaj at (Spam yapmasın)