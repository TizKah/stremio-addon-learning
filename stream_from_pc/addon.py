from flask import Flask, jsonify, send_file, request, make_response, Response
from flask_cors import CORS
import subprocess

app = Flask(__name__)
CORS(app)

import socket


def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

# http://127.0.0.1:8080/manifest.json

@app.route("/manifest.json")
def manifest():
    return send_file("manifest.json")


@app.route("/catalog/movie/pc_stream.json")
def catalog():
    return send_file("catalog/movie/pc_stream.json")


@app.route("/meta/movie/<id>.json")
def meta(id):
    if id != "stream_pc":
        return no_cache(make_response(jsonify({}), 404))
    data = {
      "meta": {
        "id": "stream_pc",
        "type": "movie",
        "name": "Watch PC",
        "poster": "https://images.metahub.space/poster/medium/tt0032138/img",
        "background": "https://images.metahub.space/background/medium/tt0032138/img",
        "description": "Stream your PC screen directly!"
      }
    }
    return make_response(jsonify(data))

@app.route("/stream/movie/<id>.json")
def stream(id):
    if id != "stream_pc":
        return no_cache(make_response(jsonify({}), 404))
    # local_ip = get_local_ip()
    local_ip = "192.168.100.58"
    data = {
      "streams": [
        {
          "title": "Web Stream",
          "url": f"http://{local_ip}:8080/live",
          "notWebReady": True
        }
      ]
    }
    return make_response(jsonify(data))


def generate():
    audio_device_name = "CABLE Output (VB-Audio Virtual Cable)"
    # test ffmpeg -f gdigrab -framerate 30 -i desktop -vcodec libx264 -preset veryfast -tune zerolatency -f mpegts udp://192.168.100.58:8080
    cmd = [
        'ffmpeg',
        '-loglevel', 'info',

        # --- Entradas ---
        '-f', 'gdigrab',
        '-framerate', '40',
        '-i', 'desktop',

        # Entrada de audio
        '-f', 'dshow',
        '-i', f'audio={audio_device_name}',

        # --- Procesamiento y Codificación ---
        '-pix_fmt', 'yuv420p',
        '-c:v', 'libx264',
        '-preset', 'veryfast',

        '-ar', '44100',
        '-ac', '2',
        '-c:a', 'aac',
        '-b:a', '128k',

        # Sincronización de audio y video
        '-async', '1',

        # --- Salida ---
        '-f', 'mpegts',
        'pipe:1'
    ]
    
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

    try:
        while True:
            chunk = process.stdout.read(1024)
            if not chunk:
                break
            yield chunk
    finally:
        if process.poll() is None:
            process.terminate()
        process.wait()

@app.route('/live')
def live_stream():
    return Response(generate(), mimetype='video/mp2t')

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
