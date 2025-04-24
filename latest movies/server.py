import requests
from flask import Flask, jsonify, send_file, request
from flask_cors import CORS
from dotenv import load_dotenv
from datetime import datetime, timedelta 
import os
import json
import concurrent.futures 

load_dotenv()

app = Flask(__name__)
CORS(app)

TMDB_API_KEY = os.getenv("TMDB_API_KEY")


CACHE_FILE = "movie_data.json"
CACHE_DURATION_HOURS = 24 
ITEMS_PER_PAGE = 20
PAGES_TO_FETCH_INCREMENTALLY  = 5
MAX_WORKERS_API = 10 

@app.route("/manifest.json")
def manifest():
    return send_file("manifest.json")

def get_movie_external_ids(tmdb_id):
    url = f"https://api.themoviedb.org/3/movie/{tmdb_id}/external_ids"
    params = {"api_key": TMDB_API_KEY}
    try:
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status() 
        data = response.json()
        
        return tmdb_id, data.get("imdb_id")
    
    except requests.exceptions.RequestException as e:
        print(f"Error al obtener external_ids para TMDB ID {tmdb_id}: {e}")
        return tmdb_id, None 

@app.route("/catalog/movie/popular_movies.json")
def catalog_default():
    return catalog(0)


@app.route("/catalog/movie/popular_movies/skip=<int:skip>.json")
def catalog(skip):
    now = datetime.now()
    prev_cache = cache_manage(skip, now)
    if prev_cache and prev_cache["usefull_cache"]:
        return prev_cache["cache"]
    
    print("Fetcheando datos nuevos de TMDB Discover API...")
    all_tmdb_movies_results = get_movies(prev_cache, now)
    imdb_id_mapping = get_imdb_ids(all_tmdb_movies_results)
    movies_for_stremio = parse_movies_for_stremio(all_tmdb_movies_results ,imdb_id_mapping)
    save_cache(movies_for_stremio, now)

    return paginate_movies(movies_for_stremio, skip)

def parse_movies_for_stremio(all_tmdb_movies_results, imdb_id_mapping):
    movies_for_stremio = []
    for movie_data in all_tmdb_movies_results:
        tmdb_id = movie_data.get("id")
        imdb_id = imdb_id_mapping.get(tmdb_id)
        if not imdb_id:
            continue

        movies_for_stremio.append({
            "id": str(imdb_id), 
            "type": "movie",
            "name": movie_data.get("title"),
            "poster": f"https://image.tmdb.org/t/p/w500{movie_data.get('poster_path')}" if movie_data.get('poster_path') else None,
            "background": f"https://image.tmdb.org/t/p/w780{movie_data.get('backdrop_path')}" if movie_data.get('backdrop_path') else None,
            "description": movie_data.get("overview", ""),
            "year": int(movie_data.get("release_date", "0000")[:4]) if movie_data.get("release_date") and len(movie_data.get("release_date")) >= 4 else None,
        })
    return movies_for_stremio

def get_imdb_ids(all_tmdb_movies_results):
    tmdb_ids_to_fetch_imdb = [movie.get("id") for movie in all_tmdb_movies_results if movie.get("id")]
    imdb_id_mapping = {} 

    print(f"Obteniendo IMDB IDs concurrentemente para {len(tmdb_ids_to_fetch_imdb)} películas...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS_API) as executor:
        future_to_tmdb_id = {executor.submit(get_movie_external_ids, tmdb_id): tmdb_id for tmdb_id in tmdb_ids_to_fetch_imdb}
        for future in concurrent.futures.as_completed(future_to_tmdb_id):
            original_tmdb_id = future_to_tmdb_id[future]
            try:
                tmdb_id, imdb_id = future.result()
                
                if imdb_id and isinstance(imdb_id, str) and imdb_id.startswith("tt"):
                     imdb_id_mapping[tmdb_id] = imdb_id
                else:
                     pass 

            except Exception as exc:
                print(f'La obtención de external_ids para {original_tmdb_id} generó una excepción: {exc}')
    return imdb_id_mapping
    
def paginate_movies(movies_list, skip):
    """Pagina una lista de películas."""
    start_index = skip
    end_index = start_index + ITEMS_PER_PAGE
    paginated_movies = movies_list[start_index:end_index]

    print(f"Paginando: skip={skip}, mostrando de {start_index} a {end_index}. Total en lista: {len(movies_list)}")

    return jsonify({"metas": paginated_movies})

def cache_manage(skip, now):
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as file:
                data = json.load(file)
                last_updated_str = data.get("last_updated")
                cached_movies = data.get("movies", [])
                count = data.get("count")
                
            if last_updated_str and skip < len(cached_movies):
                last_updated = datetime.fromisoformat(last_updated_str)
                
                if now - last_updated < timedelta(hours=CACHE_DURATION_HOURS):
                    print(f"Usando caché. Última actualización: {last_updated_str}. Películas cacheadas: {len(cached_movies)}")
                    return {"cache": paginate_movies(cached_movies, skip), "count": count, "usefull_cache": True}
                else:
                    print(f"Caché expirada. Última actualización: {last_updated_str}")
            return {"cache": None, "count": count, "usefull_cache": False}

        except (IOError, json.JSONDecodeError) as e:
            print(f"Error leyendo o decodificando el archivo de caché {CACHE_FILE}: {e}")            
    else:
        print(f"Archivo de caché {CACHE_FILE} no encontrado.")
    return None

def get_movies(prev_cache, now):
    all_tmdb_movies_results = []
    if prev_cache:
        start_page = prev_cache["count"] // ITEMS_PER_PAGE
    else:
        start_page = 0
        
    for page in range(start_page + 1, start_page + PAGES_TO_FETCH_INCREMENTALLY + 1):
        url = "https://api.themoviedb.org/3/discover/movie"
        params = {
            "api_key": TMDB_API_KEY,
            "sort_by": "popularity.desc",
            "language": "en-US", 
            "primary_release_date.lte": now.strftime('%Y-%m-%d'), 
            "page": page 
        }
        try:
            
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            page_data = response.json()
            
            all_tmdb_movies_results.extend(page_data.get("results", []))
            
            if not page_data.get("results"):
                 print(f"Discover API página {page} sin resultados, parando la paginación.")
                 break
            else:
                print(f"Discover API página {page} con éxito.")
        except requests.exceptions.RequestException as e:
            print(f"Error al fetchear TMDB Discover API página {page}: {e}")
            
            if page == 1:
                 print("La primera página falló, devolviendo lista vacía.")
                 return jsonify({"metas": []})
            break 
    return all_tmdb_movies_results

def save_cache(movies_for_stremio, now):
    if movies_for_stremio:
        try:
            with open(CACHE_FILE, "w") as file:
                json.dump({
                    "movies": movies_for_stremio,
                    "last_updated": now.isoformat(), 
                    "count": len(movies_for_stremio) 
                }, file, indent=4) 
            print(f"Caché actualizada con {len(movies_for_stremio)} películas con IMDB IDs.")
        except IOError as e:
            print(f"Error al guardar el archivo de caché {CACHE_FILE}: {e}")
    
if __name__ == "__main__":
    print("Iniciando addon de películas populares...")
    app.run(host="0.0.0.0", port=7000, debug=True) 