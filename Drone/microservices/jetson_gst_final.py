#!/usr/bin/env python3
from flask import Flask, Response
import cv2
import time

app = Flask(__name__)

@app.route('/video_feed')
def video_feed():
    def generate():
        # Pipeline أبسط
        pipeline = (
            'nvarguscamerasrc ! '
            'video/x-raw(memory:NVMM), width=640, height=480, format=NV12, framerate=30/1 ! '
            'nvvidconv ! '
            'video/x-raw, format=BGRx ! '
            'videoconvert ! '
            'appsink'
        )
        
        camera = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
        
        if not camera.isOpened():
            print("❌ Pipeline failed")
            return
        
        print("✅ Pipeline opened")
        
        # Warm up
        for _ in range(5):
            camera.grab()
            time.sleep(0.1)
        
        frame_count = 0
        
        while True:
            ret, frame = camera.read()
            
            if not ret:
                print("❌ Read failed")
                time.sleep(0.1)
                continue
            
            # Encode
            ret, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 60])
            
            if not ret:
                print("❌ Encode failed")
                continue
            
            frame_count += 1
            if frame_count % 30 == 0:
                print(f"📹 {frame_count} frames")
            
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')
            
            time.sleep(0.03)
    
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    print("🚀 Final Stream: http://0.0.0.0:5002/video_feed")
    app.run(host='0.0.0.0', port=5002, threaded=True)
