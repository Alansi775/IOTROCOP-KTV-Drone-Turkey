import cv2
import threading
import time
from flask import Flask, Response

app = Flask(__name__)

# --- AYARLAR ---
FRAME_WIDTH = 640   # Hız için ideal (daha düşük: 480x270 deneyebilirsin)
FRAME_HEIGHT = 360
JPEG_QUALITY = 40   # 50'den 40'a çektim, hız artar görüntü çok bozulmaz

# Global değişkenler (Thread güvenliği için)
output_frame = None
lock = threading.Lock()

def gstreamer_pipeline():
    """Donanım hızlandırmalı GStreamer hattı"""
    return (
        "nvarguscamerasrc ! "
        "video/x-raw(memory:NVMM), width=1280, height=720, format=(string)NV12, framerate=30/1 ! "
        "nvvidconv flip-method=0 ! "
        "video/x-raw, width=(int)%d, height=(int)%d, format=(string)BGRx ! "
        "videoconvert ! "
        "video/x-raw, format=(string)BGR ! appsink drop=1"
        % (FRAME_WIDTH, FRAME_HEIGHT)
    )

def camera_thread():
    """
    Bu fonksiyon arka planda sürekli çalışır ve en son kareyi yakalar.
    Eski kareleri umursamaz, sürekli 'şu an'ı kovalar.
    """
    global output_frame
    
    print("Kamera başlatılıyor...")
    cap = cv2.VideoCapture(gstreamer_pipeline(), cv2.CAP_GSTREAMER)
    
    # Tampon boyutunu 1 yaparak gecikmeyi önlüyoruz
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    if not cap.isOpened():
        print("Kamera hatası! 'sudo systemctl restart nvargus-daemon' dene.")
        return

    while True:
        success, frame = cap.read()
        if success:
            # Sadece sıkıştırma işlemini burada yapmıyoruz, 
            # ham görüntüyü alıp kilitli kasaya koyuyoruz.
            with lock:
                output_frame = frame.copy()
        else:
            print("Frame okunamadı!")
            time.sleep(0.1)

def generate():
    """Web istemcisine (RPi'ye) MJPEG akışı sağlar"""
    global output_frame
    
    while True:
        with lock:
            if output_frame is None:
                continue
            
            # Görüntüyü al ve JPEG'e sıkıştır
            # Kodlama işlemini burada yapıyoruz
            (flag, encodedImage) = cv2.imencode(".jpg", output_frame, [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY])
            
            if not flag:
                continue

        # Byte dizisine çevir ve gönder
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + bytearray(encodedImage) + b'\r\n')
        
        # Çok minik bir uyku CPU'yu rahatlatır (opsiyonel)
        # time.sleep(0.01) 

@app.route('/video_feed')
def video_feed():
    return Response(generate(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    # Kamera okuyucu thread'i başlat
    t = threading.Thread(target=camera_thread, daemon=True)
    t.start()
    
    print(f"🚀 Jetson Yayını Başladı: http://192.168.100.2:5000/video_feed")
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
