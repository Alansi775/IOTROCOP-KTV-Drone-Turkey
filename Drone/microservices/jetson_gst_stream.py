#!/usr/bin/env python3
from flask import Flask, Response
import cv2

app = Flask(__name__)

def get_camera():
    pipeline = (
        'nvarguscamerasrc ! '
        'video/x-raw(memory:NVMM), width=1920, height=1080, format=NV12, framerate=30/1 ! '
        'nvvidconv ! '
        'video/x-raw, width=640, height=480, format=BGRx ! '
        'videoconvert ! '
        'video/x-raw, format=BGR ! '
        'appsink drop=1'
    )
    return cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)

@app.route('/video_feed')
def video_feed():
    def generate():
        camera = get_camera()
        print("✅ Camera opened")
        
        frame_count = 0
        while True:
            ret, frame = camera.read()
            if not ret:
                print("❌ Frame failed")
                break
            
            ret, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
            if not ret:
                continue
            
            frame_count += 1
            if frame_count % 30 == 0:
                print(f"📹 Frames: {frame_count}")
            
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')
        
        camera.release()
    
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    print("🚀 Gstreamer Flask Stream: http://0.0.0.0:5000/video_feed")
    app.run(host='0.0.0.0', port=5001, threaded=True)
