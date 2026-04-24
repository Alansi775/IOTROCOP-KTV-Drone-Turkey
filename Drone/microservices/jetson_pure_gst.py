#!/usr/bin/env python3
from flask import Flask, Response
import subprocess

app = Flask(__name__)

@app.route('/video_feed')
def video_feed():
    def generate():
        # gstreamer مباشرة - ينتج MJPEG stream
        cmd = [
            'gst-launch-1.0', '-q',
            'nvarguscamerasrc', '!',
            'video/x-raw(memory:NVMM),width=640,height=480,framerate=30/1', '!',
            'nvvidconv', '!',
            'video/x-raw,format=I420', '!',
            'jpegenc', '!',
            'multifilesink', 'location=/tmp/frame_%05d.jpg', 'max-files=1'
        ]
        
        # أو نستخدم stdout
        cmd = [
            'gst-launch-1.0', '-q',
            'nvarguscamerasrc', '!',
            'video/x-raw(memory:NVMM),width=640,height=480,framerate=30/1', '!',
            'nvvidconv', '!',
            'jpegenc', 'quality=60', '!',
            'multipartmux', 'boundary=frame', '!',
            'fdsink', 'fd=1'
        ]
        
        print("✅ Starting gstreamer...")
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0)
        
        try:
            while True:
                chunk = process.stdout.read(4096)
                if not chunk:
                    break
                yield chunk
        finally:
            process.terminate()
            print("✅ Stopped")
    
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    print("🚀 Pure Gstreamer: http://0.0.0.0:5003/video_feed")
    app.run(host='0.0.0.0', port=5000, threaded=True)
