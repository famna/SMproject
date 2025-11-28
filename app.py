from flask import Flask, render_template, jsonify, request
from SPARQLWrapper import SPARQLWrapper, JSON
from datetime import datetime
import os
import re

app = Flask(__name__)

# Конфігурація SPARQL endpoint
SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"

# SPARQL запит для отримання даних про українських виконавців
# Зміни: додано fallback мову "en" у SERVICE wikibase:label
SPARQL_QUERY = """
SELECT ?artist ?artistLabel ?birthDate ?birthPlaceLabel (COUNT(?award) AS ?awardsCount)
WHERE {
  ?artist wdt:P31 wd:Q5.                         # людина
  ?artist wdt:P106 wd:Q177220.                   # музичний виконавець
  ?artist wdt:P27 wd:Q212.                       # громадянство Україна (Q212)

  OPTIONAL { ?artist wdt:P569 ?birthDate. }
  OPTIONAL { ?artist wdt:P19 ?birthPlace. 
             ?birthPlace rdfs:label ?birthPlaceLabel.
             FILTER(LANG(?birthPlaceLabel)="uk")
           }
  OPTIONAL { ?artist wdt:P166 ?award. }          # нагороди

  SERVICE wikibase:label { bd:serviceParam wikibase:language "uk,en". }
}
GROUP BY ?artist ?artistLabel ?birthDate ?birthPlaceLabel
ORDER BY DESC(?awardsCount)
LIMIT 200
"""


class WikidataService:
    """Сервіс для роботи з Wikidata"""
    
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


class ArtistDataParser:
    """Парсер даних про виконавців"""
    
    @staticmethod
    def parse_results(results):
        artists = []
        
        for binding in results["results"]["bindings"]:
            raw_id = binding.get("artist", {}).get("value", "")
            q_id = raw_id.split("/")[-1] # Отримуємо сам код, наприклад Q4277799
            
            name = binding.get("artistLabel", {}).get("value", "Невідомо")
            
            # ФІЛЬТРАЦІЯ: Якщо ім'я співпадає з Q-кодом, пропускаємо цього виконавця
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


class StatisticsCalculator:
    """Калькулятор статистики"""
    
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


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/artists', methods=['GET'])
def get_artists():
    try:
        results = wikidata_service.execute_query(SPARQL_QUERY)
        artists = parser.parse_results(results)
        
        for artist in artists:
            artist["birth_date_formatted"] = parser.format_birth_date(artist["birth_date"])
        
        stats = StatisticsCalculator.calculate_stats(artists)
        
        return jsonify({
            "success": True,
            "data": artists,
            "stats": stats
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/artists/search', methods=['GET'])
def search_artists():
    try:
        search_query = request.args.get('q', '').lower()
        sort_by = request.args.get('sort', 'awards')
        
        results = wikidata_service.execute_query(SPARQL_QUERY)
        artists = parser.parse_results(results)
        
        for artist in artists:
            artist["birth_date_formatted"] = parser.format_birth_date(artist["birth_date"])
        
        # Пошук
        if search_query:
            artists = [a for a in artists if search_query in a["name"].lower()]
        
        # Сортування
        if sort_by == "name":
            # ВИПРАВЛЕННЯ: Сортування з приведенням до нижнього регістру для коректного алфавіту
            artists.sort(key=lambda x: x["name"].lower())
        elif sort_by == "birth_date":
            artists.sort(key=lambda x: x["birth_date"] or "", reverse=True)
        else:  # awards
            artists.sort(key=lambda x: x["awards_count"], reverse=True)
        
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