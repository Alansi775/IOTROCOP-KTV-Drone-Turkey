# Dosya Adı: jetson_yayinci.py
import cv2
import threading
from flask import Flask, Response

app = Flask(__name__)

# --- Gstreamer Pipeline (IMX219 Kamera İçin Standart Ayar) ---
def gstreamer_pipeline(
    sensor_id=0,
    capture_width=1280,
    capture_height=720,
    display_width=640,   # Çözünürlüğü düşürerek hızı artırıyoruz
    display_height=360,
    framerate=30,
    flip_method=0,
):
    return (
        "nvarguscamerasrc sensor-id=%d ! "
        "video/x-raw(memory:NVMM), width=(int)%d, height=(int)%d, format=(string)NV12, framerate=(fraction)%d/1 ! "
        "nvvidconv flip-method=%d ! "
        "video/x-raw, width=(int)%d, height=(int)%d, format=(string)BGRx ! "
        "videoconvert ! "
        "video/x-raw, format=(string)BGR ! appsink"
        % (
            sensor_id,
            capture_width,
            capture_height,
            framerate,
            flip_method,
            display_width,
            display_height,
        )
    )

print("--- KAMERA BAŞLATILIYOR ---")
# Kamerayı GStreamer ile aç
video_capture = cv2.VideoCapture(gstreamer_pipeline(flip_method=0), cv2.CAP_GSTREAMER)

# Kamera açıldı mı kontrol et
if not video_capture.isOpened():
    print("\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
    print("HATA: Kamera AÇILAMADI! Kabloyu kontrol et veya servisi resetle.")
    print("Komut: sudo systemctl restart nvargus-daemon")
    print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n")
    exit()
else:
    print("BAŞARILI: Kamera donanımı algılandı, yayın başlıyor...")

def frame_uretici():
    """Kameradan görüntü okuyup Web'e basan döngü"""
    while True:
        success, frame = video_capture.read()
        if not success:
            print("HATA: Görüntü karesi okunamadı!")
            break
        
        # JPEG Sıkıştırma (Kalite %50 - Hız/Kalite dengesi)
        ret, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 50])
        frame_bytes = buffer.tobytes()
        
        # MJPEG formatında parça parça gönder
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@app.route('/video_feed')
def video_feed():
    return Response(frame_uretici(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    # '0.0.0.0' diyerek tüm bağlantılara izin veriyoruz
    print(f"Yayın Başladı! Link: http://192.168.100.2:5000/video_feed")
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)