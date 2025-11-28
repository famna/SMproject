from SPARQLWrapper import SPARQLWrapper, JSON

sparql = SPARQLWrapper("https://query.wikidata.org/sparql")
sparql.setReturnFormat(JSON)

query = """
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

sparql.setQuery(query)
results = sparql.query().convert()

artists = []

for r in results["results"]["bindings"]:
    name = r["artistLabel"]["value"]
    birth = r.get("birthDate", {}).get("value", "—")
    place = r.get("birthPlaceLabel", {}).get("value", "—")
    awards = int(r["awardsCount"]["value"])

    artists.append({
        "name": name,
        "birth": birth,
        "place": place,
        "awards": awards
    })

# Сортування за кількістю нагород
artists = sorted(artists, key=lambda x: x["awards"], reverse=True)

# Вивід у консоль
for a in artists:
    print(f"Ім'я: {a['name']}")
    print(f"Народився(лась): {a['birth']}")
    print(f"Місце народження: {a['place']}")
    print(f"Кількість нагород: {a['awards']}")
    print("----------------------------------------")
