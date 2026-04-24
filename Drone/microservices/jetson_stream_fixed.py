#!/usr/bin/env python3
from flask import Flask, Response
import cv2
import time

app = Flask(__name__)

@app.route('/video_feed')
def video_feed():
    def generate():
        camera = cv2.VideoCapture(0)
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        
        # Warm up
        for _ in range(3):
            camera.grab()
        
        print("✅ Streaming started")
        frame_count = 0
        
        try:
            while True:
                ret = camera.grab()
                if not ret:
                    print("❌ grab failed")
                    time.sleep(0.1)
                    continue
                
                ret, frame = camera.retrieve()
                if not ret:
                    print("❌ retrieve failed")
                    time.sleep(0.1)
                    continue
                
                ret, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 60])
                if not ret:
                    print("❌ encode failed")
                    continue
                
                frame_count += 1
                if frame_count % 30 == 0:
                    print(f"📹 Frames: {frame_count}")
                
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')
                
                time.sleep(0.033)  # ~30fps
                
        finally:
            camera.release()
            print("✅ Camera released")
    
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    print("🚀 Fixed Stream: http://0.0.0.0:5000/video_feed")
    app.run(host='0.0.0.0', port=5000, threaded=True)
