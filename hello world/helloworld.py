from flask import Flask, jsonify, send_file, request
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)

# Ruta para servir el manifest desde archivo
@app.route("/manifest.json")
def manifest():
    return send_file("manifest.json")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7000)
