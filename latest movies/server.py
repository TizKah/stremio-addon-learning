import requests
from flask import Flask, jsonify, send_file, request
from flask_cors import CORS
from dotenv import load_dotenv
from datetime import datetime
import os

load_dotenv()

app = Flask(__name__)
CORS(app)

TMDB_API_KEY = os.getenv("TMDB_API_KEY")

@app.route("/manifest.json")
def manifest():
    return send_file("manifest.json")

def tmdb_id_to_imdb_id(tmdb_id):
    url = f"https://api.themoviedb.org/3/movie/{tmdb_id}"
    params = {"api_key": TMDB_API_KEY}
    response = requests.get(url, params=params)
    if response.status_code != 200:
        return None
    return response.json().get("imdb_id")

@app.route("/catalog/movie/latest-by-country.json")
def catalog_default():
    return catalog(0)

@app.route("/catalog/movie/latest-by-country/skip=<int:skip>.json")
def catalog(skip):
    page = skip // 20 + 1 

    today = datetime.today().strftime('%Y-%m-%d')
    url = "https://api.themoviedb.org/3/discover/movie"
    params = {
        "api_key": TMDB_API_KEY,
        "sort_by": "popularity.desc",  
        "language": "en-US",
        "primary_release_date.lte": today,  
        "page": page 
    }

    response = requests.get(url, params=params)
    if response.status_code != 200:
        return jsonify({"metas": []})

    metas = []
    for movie in response.json().get("results", []):
        imdb_id = tmdb_id_to_imdb_id(movie.get("id"))
        if not imdb_id:
            continue

        metas.append({
            "id": imdb_id,
            "type": "movie",
            "name": movie.get("title"),
            "poster": f"https://image.tmdb.org/t/p/w500{movie.get('poster_path')}" if movie.get("poster_path") else None,
            "background": f"https://image.tmdb.org/t/p/w780{movie.get('backdrop_path')}" if movie.get("backdrop_path") else None,
            "description": movie.get("overview", ""),
            "year": int(movie.get("release_date", "2000")[:4]) if movie.get("release_date") else 2000
        })

    return jsonify({"metas": metas})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7000)
