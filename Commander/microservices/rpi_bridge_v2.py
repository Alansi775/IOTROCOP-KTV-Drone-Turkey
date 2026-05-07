import requests
from flask import Flask, Response

app = Flask(__name__)

JETSON_URL = "http://192.168.100.2:5000/video_feed"

def proxy_stream():
    """Stream frames from Nvidia camera"""
    try:
        print(f"🔗 Connecting to: {JETSON_URL}")
        
        with requests.get(JETSON_URL, stream=True, timeout=10) as r:
            print(f"✅ Connected! Status: {r.status_code}")
            
            # Stream chunks directly
            for chunk in r.iter_content(chunk_size=1024):
                if chunk:
                    yield chunk
                    
    except Exception as e:
        print(f"❌ Error: {e}")
        yield b''

@app.route('/video_feed')
def video_feed():
    return Response(
        proxy_stream(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )

if __name__ == '__main__':
    print("🚀 Video Bridge v2: Port 8080")
    app.run(host='0.0.0.0', port=8080, threaded=True)
