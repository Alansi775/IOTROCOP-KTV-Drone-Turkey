from flask import Flask, Response
import cv2
import time
import threading

app = Flask(__name__)

# Global camera object
camera = None
camera_lock = threading.Lock()

def init_camera():
    global camera
    with camera_lock:
        if camera is not None:
            return True
        
        print("🔧 Initializing camera...")
        camera = cv2.VideoCapture(0)
        
        if not camera.isOpened():
            print("❌ Camera failed to open!")
            camera = None
            return False
        
        # Set properties
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        # Warm up - read and discard first frames
        print("⏳ Warming up camera...")
        for i in range(10):
            ret, _ = camera.read()
            if ret:
                print(f"  Frame {i+1}/10 OK")
            time.sleep(0.1)
        
        print("✅ Camera ready!")
        return True

def generate_frames():
    if not init_camera():
        return
    
    frame_count = 0
    
    while True:
        with camera_lock:
            ret, frame = camera.read()
        
        if not ret:
            print("⚠️ Failed to read frame")
            time.sleep(0.1)
            continue
        
        # Encode
        ret, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
        if not ret:
            continue
        
        frame_count += 1
        if frame_count % 30 == 0:
            print(f"📹 Frames sent: {frame_count}")
        
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    print("🚀 Camera Stream v3: http://0.0.0.0:5000/video_feed\n")
    app.run(host='0.0.0.0', port=5000, threaded=True)
