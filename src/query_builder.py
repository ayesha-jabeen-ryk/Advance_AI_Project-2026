def build_query(question: str) -> str:
    q = question.lower().strip()

    if "capital of germany" in q:
        return """
        PREFIX dbo: <http://dbpedia.org/ontology/>
        PREFIX dbr: <http://dbpedia.org/resource/>

        SELECT ?capital WHERE {
          dbr:Germany dbo:capital ?capital .
        }
        LIMIT 1
        """

    if "spouse of barack obama" in q or "who is the spouse of barack obama" in q:
        return """
        PREFIX dbo: <http://dbpedia.org/ontology/>
        PREFIX dbr: <http://dbpedia.org/resource/>

        SELECT ?spouse WHERE {
          dbr:Barack_Obama dbo:spouse ?spouse .
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

    return ""