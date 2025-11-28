from flask import Flask, render_template, jsonify, request
from SPARQLWrapper import SPARQLWrapper, JSON
from datetime import datetime
import os

app = Flask(__name__)

# Конфігурація SPARQL endpoint
SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"

# SPARQL запит для отримання даних про українських виконавців
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

  SERVICE wikibase:label { bd:serviceParam wikibase:language "uk". }
}
GROUP BY ?artist ?artistLabel ?birthDate ?birthPlaceLabel
ORDER BY DESC(?awardsCount)
LIMIT 200
"""


class WikidataService:
    """Сервіс для роботи з Wikidata"""
    
    def __init__(self, endpoint_url):
        """
        Ініціалізація сервісу
        
        Args:
            endpoint_url (str): URL SPARQL endpoint
        """
        self.sparql = SPARQLWrapper(endpoint_url)
        self.sparql.setReturnFormat(JSON)
    
    def execute_query(self, query):
        """
        Виконання SPARQL запиту
        
        Args:
            query (str): SPARQL запит
            
        Returns:
            dict: Результати запиту
        """
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
        """
        Парсинг результатів SPARQL запиту
        
        Args:
            results (dict): Результати запиту
            
        Returns:
            list: Список виконавців
        """
        artists = []
        
        for binding in results["results"]["bindings"]:
            artist = {
                "id": binding.get("artist", {}).get("value", ""),
                "name": binding.get("artistLabel", {}).get("value", "Невідомо"),
                "birth_date": binding.get("birthDate", {}).get("value"),
                "birth_place": binding.get("birthPlaceLabel", {}).get("value"),
                "awards_count": int(binding.get("awardsCount", {}).get("value", 0))
            }
            artists.append(artist)
        
        return artists
    
    @staticmethod
    def format_birth_date(date_string):
        """
        Форматування дати народження
        
        Args:
            date_string (str): Дата у форматі ISO
            
        Returns:
            str: Форматована дата
        """
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
        """
        Розрахунок статистики
        
        Args:
            artists (list): Список виконавців
            
        Returns:
            dict: Статистичні дані
        """
        total = len(artists)
        with_awards = len([a for a in artists if a["awards_count"] > 0])
        total_awards = sum(a["awards_count"] for a in artists)
        avg_awards = round(total_awards / with_awards, 1) if with_awards > 0 else 0
        
        return {
            "total": total,
            "with_awards": with_awards,
            "avg_awards": avg_awards
        }


# Ініціалізація сервісів
wikidata_service = WikidataService(SPARQL_ENDPOINT)
parser = ArtistDataParser()


@app.route('/')
def index():
    """Головна сторінка"""
    return render_template('index.html')


@app.route('/api/artists', methods=['GET'])
def get_artists():
    """
    API endpoint для отримання даних про виконавців
    
    Returns:
        JSON: Дані про виконавців та статистика
    """
    try:
        # Виконання запиту до Wikidata
        results = wikidata_service.execute_query(SPARQL_QUERY)
        
        # Парсинг результатів
        artists = parser.parse_results(results)
        
        # Форматування дат
        for artist in artists:
            artist["birth_date_formatted"] = parser.format_birth_date(artist["birth_date"])
        
        # Розрахунок статистики
        stats = StatisticsCalculator.calculate_stats(artists)
        
        return jsonify({
            "success": True,
            "data": artists,
            "stats": stats
        })
    
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/artists/search', methods=['GET'])
def search_artists():
    """
    API endpoint для пошуку виконавців
    
    Query params:
        q (str): Пошуковий запит
        sort (str): Тип сортування (awards, name, birth_date)
        filter (str): Фільтр (all, with_awards, no_awards)
    
    Returns:
        JSON: Відфільтровані дані
    """
    try:
        # Отримання параметрів
        search_query = request.args.get('q', '').lower()
        sort_by = request.args.get('sort', 'awards')
        filter_by = request.args.get('filter', 'all')
        
        # Виконання запиту
        results = wikidata_service.execute_query(SPARQL_QUERY)
        artists = parser.parse_results(results)
        
        # Форматування дат
        for artist in artists:
            artist["birth_date_formatted"] = parser.format_birth_date(artist["birth_date"])
        
        # Пошук
        if search_query:
            artists = [a for a in artists if search_query in a["name"].lower()]
        
        # Фільтрація
        if filter_by == "with_awards":
            artists = [a for a in artists if a["awards_count"] > 0]
        elif filter_by == "no_awards":
            artists = [a for a in artists if a["awards_count"] == 0]
        
        # Сортування
        if sort_by == "name":
            artists.sort(key=lambda x: x["name"])
        elif sort_by == "birth_date":
            artists.sort(key=lambda x: x["birth_date"] or "", reverse=True)
        else:  # awards
            artists.sort(key=lambda x: x["awards_count"], reverse=True)
        
        # Статистика
        stats = StatisticsCalculator.calculate_stats(artists)
        
        return jsonify({
            "success": True,
            "data": artists,
            "stats": stats
        })
    
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)