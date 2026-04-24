from flask import Flask, Response
import cv2
import time

app = Flask(__name__)
camera_lock = False

def generate_frames():
    global camera_lock
    
    if camera_lock:
        print("⚠️ Camera already in use")
        return
    
    camera_lock = True
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("❌ Camera failed to open!")
        camera_lock = False
        return
    
    print("✅ Camera opened!")
    
    # Lower resolution for faster streaming
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, 15)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    
    frame_count = 0
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print(f"❌ Frame {frame_count} failed")
                time.sleep(0.1)
                continue
            
            frame_count += 1
            
            # Encode JPEG with lower quality for speed
            ret, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 60])
            if not ret:
                continue
            
            if frame_count % 30 == 0:
                print(f"📹 Sent {frame_count} frames")
            
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')
    
    finally:
        cap.release()
        camera_lock = False
        print("✅ Camera released")

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    print("🚀 Camera Stream v2: http://0.0.0.0:5000/video_feed")
    app.run(host='0.0.0.0', port=5000, threaded=True, debug=False)
