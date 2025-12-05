from flask import Flask, render_template, jsonify, request
from SPARQLWrapper import SPARQLWrapper, JSON
from datetime import datetime
import os
import re

app = Flask(__name__)

SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"

SPARQL_QUERY = """
SELECT ?artist ?artistLabel ?birthDate ?birthPlaceLabel (COUNT(?award) AS ?awardsCount) 
WHERE {
  ?artist wdt:P31 wd:Q5.
  ?artist wdt:P106 wd:Q177220.
  ?artist wdt:P27 wd:Q212. 

  OPTIONAL { ?artist wdt:P569 ?birthDate. } # Дата народження
  OPTIONAL { ?artist wdt:P19 ?birthPlace.  # Місце народження
             ?birthPlace rdfs:label ?birthPlaceLabel. # Мітка місця народження
             FILTER(LANG(?birthPlaceLabel)="uk") # Фільтр за українською мовою
           }
  OPTIONAL { ?artist wdt:P166 ?award. } # Нагороди

  SERVICE wikibase:label { bd:serviceParam wikibase:language "uk,en". } # Отримання міток українською або англійською
}
GROUP BY ?artist ?artistLabel ?birthDate ?birthPlaceLabel # Групування за артистом, міткою, датою народження та місцем народження
ORDER BY DESC(?awardsCount) # Сортування за кількістю нагороджень
LIMIT 1000
"""
 # Функція для дебаунсу введення користувача
class WikidataService:
    def __init__(self, endpoint_url):
        self.sparql = SPARQLWrapper(endpoint_url)
        self.sparql.setReturnFormat(JSON)
    
    def execute_query(self, query):
        self.sparql.setQuery(query)
        try:
            results = self.sparql.query().convert()
            return results
        except Exception as e:
            raise Exception(f"Помилка виконання запиту: {str(e)}")
# Функція для дебаунсу введення користувача
class ArtistDataParser:
    @staticmethod
    def parse_results(results):
        artists = []
        for binding in results["results"]["bindings"]:
            raw_id = binding.get("artist", {}).get("value", "")
            q_id = raw_id.split("/")[-1]
            
            name = binding.get("artistLabel", {}).get("value", "Невідомо")
            
            if name == q_id:
                continue

            artist = {
                "id": raw_id,
                "name": name,
                "birth_date": binding.get("birthDate", {}).get("value"),
                "birth_place": binding.get("birthPlaceLabel", {}).get("value"),
                "awards_count": int(binding.get("awardsCount", {}).get("value", 0))
            }
            artists.append(artist)
        return artists
    # Функція для форматування дати народження
    @staticmethod
    def format_birth_date(date_string):
        if not date_string:
            return None
        try:
            date = datetime.fromisoformat(date_string.replace('Z', '+00:00'))
            months = [
                'січня', 'лютого', 'березня', 'квітня', 'травня', 'червня',
                'липня', 'серпня', 'вересня', 'жовтня', 'листопада', 'грудня'
            ]
            return f"{date.day} {months[date.month - 1]} {date.year}"
        except:
            return date_string
#   Клас для обчислення статистики
class StatisticsCalculator:
    @staticmethod
    def calculate_stats(artists):
        total = len(artists)
        total_awards = sum(a["awards_count"] for a in artists)
        avg_awards = round(total_awards / total, 1) if total > 0 else 0
        
        return {
            "total_artists": total,
            "total_awards": total_awards,
            "avg_awards": avg_awards
        }
# Ініціалізація сервісів
wikidata_service = WikidataService(SPARQL_ENDPOINT)
parser = ArtistDataParser()
# Ініціалізація Flask додатку
@app.route('/')
def index():
    return render_template('index.html')
#   Маршрут для отримання даних про виконавців
@app.route('/api/artists', methods=['GET'])
def get_artists():
    try:
        results = wikidata_service.execute_query(SPARQL_QUERY) 
        artists = parser.parse_results(results)
        for artist in artists:
            artist["birth_date_formatted"] = parser.format_birth_date(artist["birth_date"]) 
        stats = StatisticsCalculator.calculate_stats(artists) 
        return jsonify({"success": True, "data": artists, "stats": stats}) 
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
# Маршрут для пошуку та фільтрації виконавців
@app.route('/api/artists/search', methods=['GET'])
def search_artists():
    try:
        # Отримання всіх параметрів
        search_query = request.args.get('q', '').lower()
        sort_by = request.args.get('sort', 'awards')
        filter_by = request.args.get('filter', 'all')
        
        # Отримання параметрів для кастомного діапазону
        min_awards = int(request.args.get('min', 0))
        # Якщо max не вказано або порожнє, ставимо дуже велике число
        max_val_str = request.args.get('max', '')
        max_awards = int(max_val_str) if max_val_str else 999999
        
        results = wikidata_service.execute_query(SPARQL_QUERY)
        artists = parser.parse_results(results)
        
        for artist in artists:
            artist["birth_date_formatted"] = parser.format_birth_date(artist["birth_date"])
        
        # 1. Пошук по імені
        if search_query:
            artists = [a for a in artists if search_query in a["name"].lower()]
        
        # 2. Фільтрація
        if filter_by == "with_awards":
            artists = [a for a in artists if a["awards_count"] > 0]
        elif filter_by == "no_awards":
            artists = [a for a in artists if a["awards_count"] == 0]
        elif filter_by == "custom":
            # Нова логіка діапазону
            artists = [
                a for a in artists 
                if min_awards <= a["awards_count"] <= max_awards
            ]
        
        # 3. Сортування
        if sort_by == "name":
            artists.sort(key=lambda x: x["name"].lower())
        elif sort_by == "birth_date":
            artists.sort(key=lambda x: x["birth_date"] or "", reverse=True)
        else:  # awards
            artists.sort(key=lambda x: x["awards_count"], reverse=True)
        # 4. Форматування дати народження
        stats = StatisticsCalculator.calculate_stats(artists) 
        
        return jsonify({
            "success": True,
            "data": artists,
            "stats": stats
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)