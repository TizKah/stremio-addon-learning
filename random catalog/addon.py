from flask import Flask, jsonify, send_file, request
from flask_cors import CORS
import os
import random
import json

app = Flask(__name__)
CORS(app)

MOVIES_JSON = "movie_data.json"

# Test with curl http://127.0.0.1:7000/manifest.json
@app.route("/manifest.json")
def manifest():
    return send_file("manifest.json")

def fomart_json_random_pick(random_movie):
    movie_info = { 
        "background": "https://img.freepik.com/free-vector/vector-damask-seamless-pattern-background-classical-luxury-old-fashioned-damask-ornament-royal-victorian-seamless-texture-wallpapers-textile-wrapping-exquisite-floral-baroque-template_1217-738.jpg?t=st=1745615123~exp=1745618723~hmac=77fb7bf6965cec5bba8f8a0ab0446972dc5022ad3e6c4a71d84294d749b035e1&w=740",
        "description": "Just a random movie :)",
        "id": random_movie.get("id"),
        "name": "Random movie",
        "poster": "https://img.freepik.com/free-vector/white-question-mark-sketch-style-dark-background_78370-4761.jpg?t=st=1745615086~exp=1745618686~hmac=2c015fd9ba71a67b36f309fb27a67c6f8f148d4196c51b4c7ce555c2b87a4afb&w=740",
        "type": "movie",
        "genres": ["Action", "Drama"],
        "year": random_movie.get("year")
    }
    
    return jsonify({"metas": [movie_info]})

# Test with curl http://127.0.0.1:7000/catalog/movie/random_movie.json
@app.route("/catalog/movie/random_movie.json")
def movieCatalog():
    if os.path.exists(MOVIES_JSON):
        with open(MOVIES_JSON, "r") as movies_file:
            movies_data = json.load(movies_file)
            movies = movies_data.get("movies", [])
            count = movies_data.get("count")
            random_movie = movies[random.randint(0, count)]
    
    return fomart_json_random_pick(random_movie)
            
            
        

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7000, debug=True)
