import re
def normalize_question(question: str) -> str:
    q = question.lower().strip()
    q = q.replace("?", "").replace(".", "").replace(",", "")
    return " ".join(q.split())


def build_query(question: str) -> str:
    q = normalize_question(question)

    # -------------------------
    # Simple fact questions
    # -------------------------
    if "capital of germany" in q:
        return """
        PREFIX dbo: <http://dbpedia.org/ontology/>
        PREFIX dbr: <http://dbpedia.org/resource/>

        SELECT ?capital WHERE {
          dbr:Germany dbo:capital ?capital .
        }
        LIMIT 1
        """

    if "capital of france" in q:
        return """
        PREFIX dbo: <http://dbpedia.org/ontology/>
        PREFIX dbr: <http://dbpedia.org/resource/>

        SELECT ?capital WHERE {
          dbr:France dbo:capital ?capital .
        }
        LIMIT 1
        """

    if "spouse of" in q or "who is the spouse of" in q:
      import re
      match = re.search(r"spouse of (.+)", q)
      if match:
        person = match.group(1).strip()

        return f"""
        PREFIX dbo: <http://dbpedia.org/ontology/>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

        SELECT ?spouse WHERE {{
          ?person rdfs:label "{person.title()}"@en .
          ?person dbo:spouse ?spouse .
        }}
        LIMIT 1
        """
    if "spouse of barack obama" in q:
        return """
        PREFIX dbo: <http://dbpedia.org/ontology/>
        PREFIX dbr: <http://dbpedia.org/resource/>

        SELECT ?spouse WHERE {
          dbr:Barack_Obama dbo:spouse ?spouse .
        }
        LIMIT 1
        """

    if "where was albert einstein born" in q or "birth place of albert einstein" in q:
        return """
        PREFIX dbo: <http://dbpedia.org/ontology/>
        PREFIX dbr: <http://dbpedia.org/resource/>

        SELECT ?birthPlace WHERE {
          dbr:Albert_Einstein dbo:birthPlace ?birthPlace .
        }
        LIMIT 1
        """

    # -------------------------
    # Date / time questions
    # -------------------------
    # -----------------------------

    if "when was" in q and "born" in q:
      import re
      match = re.search(r"when was (.+?) born", q)
      if match:
        person = match.group(1).strip()

        return f"""
        PREFIX dbo: <http://dbpedia.org/ontology/>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

        SELECT ?birthDate WHERE {{
          ?person rdfs:label "{person.title()}"@en .
          ?person dbo:birthDate ?birthDate .
        }}
        LIMIT 1
        """
    
    if "when was google founded" in q:
        return """
        PREFIX dbo: <http://dbpedia.org/ontology/>
        PREFIX dbr: <http://dbpedia.org/resource/>

        SELECT ?foundingDate WHERE {
          dbr:Google dbo:foundingDate ?foundingDate .
        }
        LIMIT 1
        """

    if "when did world war ii start" in q or "when did world war 2 start" in q:
        return """
        PREFIX dbo: <http://dbpedia.org/ontology/>
        PREFIX dbr: <http://dbpedia.org/resource/>

        SELECT ?date WHERE {
        dbr:World_War_II dbo:date ?date .
        }
        LIMIT 1
        """

    # -------------------------
    # List / collection questions
    # -------------------------
    # -----------------------------
# WHICH CITIES ARE IN X (GENERAL)
# -----------------------------
    import re
    if "cities" in q and "in" in q:
      match = re.search(r"(cities.*in|list cities in|which cities are in) (.+)", q)
      if match:
        country = match.group(2).strip()

        return f"""
        PREFIX dbo: <http://dbpedia.org/ontology/>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

        SELECT DISTINCT ?cityLabel WHERE {{
          ?city a dbo:City .
          ?city dbo:country ?country .
          ?country rdfs:label "{country.title()}"@en .

          ?city rdfs:label ?cityLabel .
          FILTER(LANG(?cityLabel) = 'en')
        }}
        LIMIT 20
        """

    if "which cities are in germany" in q or "list cities in germany" in q:
        return """
        PREFIX dbo: <http://dbpedia.org/ontology/>
        PREFIX dbr: <http://dbpedia.org/resource/>

        SELECT ?city WHERE {
          ?city a dbo:City .
          ?city dbo:country dbr:Germany .
        }
        LIMIT 20
        """

    if "which films were directed by christopher nolan" in q or "films directed by christopher nolan" in q:
        return """
        PREFIX dbo: <http://dbpedia.org/ontology/>
        PREFIX dbr: <http://dbpedia.org/resource/>

        SELECT ?film WHERE {
          ?film dbo:director dbr:Christopher_Nolan .
        }
        LIMIT 20
        """

    if "which universities are in berlin" in q or "universities in berlin" in q:
        return """
        PREFIX dbo: <http://dbpedia.org/ontology/>
        PREFIX dbr: <http://dbpedia.org/resource/>

        SELECT ?university WHERE {
          ?university a dbo:University .
          ?university dbo:city dbr:Berlin .
        }
        LIMIT 20
        """

    if "which rivers are in france" in q or "rivers in france" in q:
        return """
        PREFIX dbo: <http://dbpedia.org/ontology/>
        PREFIX dbr: <http://dbpedia.org/resource/>

        SELECT ?river WHERE {
          ?river a dbo:River .
          ?river dbo:country dbr:France .
        }
        LIMIT 20
        """

    # -------------------------
    # Filter questions
    # -------------------------
    if "cities in germany with population greater than 1000000" in q or \
       "which cities in germany have population greater than 1000000" in q:
        return """
        PREFIX dbo: <http://dbpedia.org/ontology/>
        PREFIX dbr: <http://dbpedia.org/resource/>

        SELECT ?city ?population WHERE {
          ?city a dbo:City .
          ?city dbo:country dbr:Germany .
          ?city dbo:populationTotal ?population .
          FILTER(?population > 1000000)
        }
        ORDER BY DESC(?population)
        LIMIT 20
        """

    if "which people were born after 1950" in q or "people born after 1950" in q:
        return """
        PREFIX dbo: <http://dbpedia.org/ontology/>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

        SELECT ?person ?birthDate WHERE {
          ?person dbo:birthDate ?birthDate .
          FILTER(?birthDate > "1950-12-31"^^xsd:date)
        }
        ORDER BY ?birthDate
        LIMIT 20
        """

    if "which rivers in france are longer than 500000" in q or \
       "rivers in france longer than 500000" in q:
        return """
        PREFIX dbo: <http://dbpedia.org/ontology/>
        PREFIX dbr: <http://dbpedia.org/resource/>

        SELECT ?river ?length WHERE {
          ?river a dbo:River .
          ?river dbo:country dbr:France .
          ?river dbo:length ?length .
          FILTER(?length > 500000)
        }
        ORDER BY DESC(?length)
        LIMIT 20
        """

    # -------------------------
    # Compound / multiple triple questions
    # -------------------------
    if "films directed by christopher nolan and starring leonardo dicaprio" in q or \
       "which films were directed by christopher nolan and starred leonardo dicaprio" in q:
        return """
        PREFIX dbo: <http://dbpedia.org/ontology/>
        PREFIX dbr: <http://dbpedia.org/resource/>

        SELECT ?film WHERE {
          ?film dbo:director dbr:Christopher_Nolan .
          ?film dbo:starring dbr:Leonardo_DiCaprio .
        }
        LIMIT 20
        """

    if "universities in berlin with more than 20000 students" in q or \
       "which universities in berlin have more than 20000 students" in q:
        return """
        PREFIX dbo: <http://dbpedia.org/ontology/>
        PREFIX dbr: <http://dbpedia.org/resource/>

        SELECT ?university ?students WHERE {
          ?university a dbo:University .
          ?university dbo:city dbr:Berlin .
          ?university dbo:numberOfStudents ?students .
          FILTER(?students > 20000)
        }
        ORDER BY DESC(?students)
        LIMIT 20
        """

    if "which scientists were born in germany and died in the united states" in q or \
       "scientists born in germany and died in the united states" in q:
        return """
        PREFIX dbo: <http://dbpedia.org/ontology/>
        PREFIX dbr: <http://dbpedia.org/resource/>

        SELECT ?scientist WHERE {
          ?scientist a dbo:Scientist .
          ?scientist dbo:birthPlace ?birthPlace .
          ?scientist dbo:deathPlace ?deathPlace .
          ?birthPlace dbo:country dbr:Germany .
          ?deathPlace dbo:country dbr:United_States .
        }
        LIMIT 20
        """

    if "which people were born in germany and received the nobel prize" in q or \
       "people born in germany and received the nobel prize" in q:
        return """
        PREFIX dbo: <http://dbpedia.org/ontology/>
        PREFIX dbr: <http://dbpedia.org/resource/>

        SELECT ?person ?award WHERE {
          ?person dbo:birthPlace ?birthPlace .
          ?birthPlace dbo:country dbr:Germany .
          ?person dbo:award ?award .
          FILTER(CONTAINS(LCASE(STR(?award)), "nobel"))
        }
        LIMIT 20
        """

    # -------------------------
    # Date + compound questions
    # -------------------------
    if "which films starring leonardo dicaprio were released in 2010" in q or \
       "films starring leonardo dicaprio released in 2010" in q:
        return """
        PREFIX dbo: <http://dbpedia.org/ontology/>
        PREFIX dbr: <http://dbpedia.org/resource/>

        SELECT ?film ?releaseDate WHERE {
          ?film dbo:starring dbr:Leonardo_DiCaprio .
          ?film dbo:releaseDate ?releaseDate .
          FILTER(YEAR(?releaseDate) = 2010)
        }
        LIMIT 20
        """

    if "which films directed by christopher nolan were released after 2010" in q or \
       "films directed by christopher nolan released after 2010" in q:
        return """
        PREFIX dbo: <http://dbpedia.org/ontology/>
        PREFIX dbr: <http://dbpedia.org/resource/>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

        SELECT ?film ?releaseDate WHERE {
          ?film dbo:director dbr:Christopher_Nolan .
          ?film dbo:releaseDate ?releaseDate .
          FILTER(?releaseDate > "2010-12-31"^^xsd:date)
        }
        ORDER BY ?releaseDate
        LIMIT 20
        """

    # -------------------------
    # Experimental ternary-like question
    # -------------------------
    if "who married michelle obama in 1992" in q:
        return """
        PREFIX dbo: <http://dbpedia.org/ontology/>
        PREFIX dbr: <http://dbpedia.org/resource/>

        SELECT ?person ?date WHERE {
          ?person dbo:spouse dbr:Michelle_Obama .
          ?person dbo:marriageDate ?date .
          FILTER(YEAR(?date) = 1992)
        }
        LIMIT 10
        """

    return ""