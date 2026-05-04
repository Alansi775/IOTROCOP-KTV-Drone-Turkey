import requests
from flask import Flask, Response

app = Flask(__name__)

# Jetson IP
JETSON_URL = "http://192.168.100.2:5000/video_feed"

def proxy_stream():
    try:
        # stream=True çok önemli
        with requests.get(JETSON_URL, stream=True, timeout=3) as r:
            # Chunk boyutunu 8192 (8KB) yaptık. Veri daha bloklar halinde akar, CPU rahatlar.
            for chunk in r.iter_content(chunk_size=8192):
                yield chunk
    except Exception as e:
        print(f"Hata: {e}")

@app.route('/video_feed')
def video_feed():
    return Response(proxy_stream(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    print("Köprü (Bridge) Modu Aktif: Port 8080")
    app.run(host='0.0.0.0', port=8080, debug=False, threaded=True)
