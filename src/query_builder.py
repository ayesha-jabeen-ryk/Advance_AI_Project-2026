import re


PREFIXES = """
PREFIX dbo: <http://dbpedia.org/ontology/>
PREFIX dbp: <http://dbpedia.org/property/>
PREFIX dbr: <http://dbpedia.org/resource/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
""".strip()


def normalize_question(question: str) -> str:
    q = question.lower().strip()
    q = re.sub(r"[?.!,]", "", q)
    return " ".join(q.split())


def _clean_capture(text: str) -> str:
    text = re.sub(r"\s+", " ", text.strip(" \t\n\r?.!,"))
    text = re.sub(r"^the\s+", "", text, flags=re.IGNORECASE)
    return text.strip()


def _escape_literal(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"')


def _label_match(var: str, label_var: str, value: str) -> str:
    safe_value = _escape_literal(_clean_capture(value))
    return f"""
      {var} rdfs:label {label_var} .
      FILTER(LANG({label_var}) = "en")
      FILTER(LCASE(STR({label_var})) = LCASE("{safe_value}"))
    """


def _numeric(value: str) -> str:
    return value.replace(",", "").strip()


def _city_type_union(city_var: str = "?city") -> str:
    return f"""
      {{
        {city_var} a dbo:City .
      }}
      UNION
      {{
        {city_var} a dbo:Settlement .
      }}
      UNION
      {{
        {city_var} a dbo:PopulatedPlace .
      }}
    """


def _film_director_match(film_var: str = "?film", director_var: str = "?director") -> str:
    return f"""
      {{
        {film_var} dbo:director {director_var} .
      }}
      UNION
      {{
        {film_var} dbp:director {director_var} .
      }}
    """


def _film_starring_match(film_var: str = "?film", actor_var: str = "?actor") -> str:
    return f"""
      {{
        {film_var} dbo:starring {actor_var} .
      }}
      UNION
      {{
        {film_var} dbp:starring {actor_var} .
      }}
    """


def _film_release_match(film_var: str = "?film", release_var: str = "?releaseDate") -> str:
    return f"""
      {film_var} (dbo:releaseDate|dbp:released|dbp:releaseDate) {release_var} .
    """


def _start_date_match(event_var: str = "?event", date_var: str = "?startDate") -> str:
    return f"""
      {{
        {event_var} dbo:startDate {date_var} .
      }}
      UNION
      {{
        {event_var} dbp:startDate {date_var} .
      }}
      UNION
      {{
        {event_var} dbp:date {date_var} .
      }}
    """


def _country_link(subject_var: str, country_var: str) -> str:
    return f"""
      {{
        {subject_var} dbo:country {country_var} .
      }}
      UNION
      {{
        {subject_var} dbp:country {country_var} .
      }}
    """


def _city_link(subject_var: str, city_var: str) -> str:
    return f"""
      {{
        {subject_var} dbo:city {city_var} .
      }}
      UNION
      {{
        {subject_var} dbp:city {city_var} .
      }}
    """


def _birth_place_match(person_var: str = "?person", place_var: str = "?birthPlace") -> str:
    return f"""
      {{
        {person_var} dbo:birthPlace {place_var} .
      }}
      UNION
      {{
        {person_var} dbp:birthPlace {place_var} .
      }}
    """


def _death_place_match(person_var: str = "?person", place_var: str = "?deathPlace") -> str:
    return f"""
      {{
        {person_var} dbo:deathPlace {place_var} .
      }}
      UNION
      {{
        {person_var} dbp:deathPlace {place_var} .
      }}
    """


def _spouse_match(person_var: str = "?person", spouse_var: str = "?spouse") -> str:
    return f"""
      {{
        {person_var} dbo:spouse {spouse_var} .
      }}
      UNION
      {{
        {person_var} dbp:spouse {spouse_var} .
      }}
    """


def _award_match(person_var: str = "?person", award_var: str = "?award") -> str:
    return f"""
      {{
        {person_var} dbo:award {award_var} .
      }}
      UNION
      {{
        {person_var} dbp:awards {award_var} .
      }}
      UNION
      {{
        {person_var} dbp:award {award_var} .
      }}
    """


def build_query(question: str) -> str:
    q = normalize_question(question)
    clean_question = question.strip().rstrip("?.! ")

    # =========================================================
    # 1) Simple fact questions
    # =========================================================
    match = re.search(r"what is the capital of (.+)$", clean_question, flags=re.IGNORECASE)
    if match:
        country = _clean_capture(match.group(1))
        return f"""
        {PREFIXES}

        SELECT ?capital WHERE {{
          {_label_match('?country', '?countryLabel', country)}
          ?country dbo:capital ?capital .
        }}
        LIMIT 1
        """

    match = re.search(r"(?:who is\s+)?(?:the\s+)?spouse of (.+)$", clean_question, flags=re.IGNORECASE)
    if not match:
        match = re.search(r"who is (.+?)'?s spouse$", clean_question, flags=re.IGNORECASE)
    if match:
        person = _clean_capture(match.group(1))
        return f"""
        {PREFIXES}

        SELECT DISTINCT ?spouse WHERE {{
          {_label_match('?person', '?personLabel', person)}
          {_spouse_match('?person', '?spouse')}
        }}
        LIMIT 1
        """

    match = re.search(
        r"(?:where was|what is the birth place of|birth place of) (.+?)(?: born)?$",
        clean_question,
        flags=re.IGNORECASE,
    )
    if match:
        person = _clean_capture(match.group(1))
        return f"""
        {PREFIXES}

        SELECT DISTINCT ?birthPlace WHERE {{
          {_label_match('?person', '?personLabel', person)}
          {_birth_place_match('?person', '?birthPlace')}
        }}
        LIMIT 1
        """

    # =========================================================
    # 2) Date / time questions
    # =========================================================
    match = re.search(r"when was (.+?) born$", clean_question, flags=re.IGNORECASE)
    if match:
        person = _clean_capture(match.group(1))
        return f"""
        {PREFIXES}

        SELECT DISTINCT ?birthDate WHERE {{
          {_label_match('?person', '?personLabel', person)}
          ?person dbo:birthDate ?birthDate .
        }}
        LIMIT 1
        """

    match = re.search(r"when was (.+?) founded$", clean_question, flags=re.IGNORECASE)
    if match:
        organization = _clean_capture(match.group(1))
        return f"""
        {PREFIXES}

        SELECT DISTINCT ?foundingDate WHERE {{
          {_label_match('?org', '?orgLabel', organization)}
          {{
            ?org dbo:foundingDate ?foundingDate .
          }}
          UNION
          {{
            ?org dbp:founded ?foundingDate .
          }}
        }}
        LIMIT 1
        """

    match = re.search(r"when did (.+?) start$", clean_question, flags=re.IGNORECASE)
    if match:
        event = _clean_capture(match.group(1))
        return f"""
        {PREFIXES}

        SELECT DISTINCT ?startDate WHERE {{
          {_label_match('?event', '?eventLabel', event)}
          {_start_date_match('?event', '?startDate')}
        }}
        ORDER BY ?startDate
        LIMIT 1
        """

    # =========================================================
    # 3) Count / aggregate questions
    # =========================================================
    match = re.search(r"how many cities are in (.+)$", clean_question, flags=re.IGNORECASE)
    if match:
        country = _clean_capture(match.group(1))
        return f"""
        {PREFIXES}

        SELECT (COUNT(DISTINCT ?city) AS ?count) WHERE {{
          {_label_match('?country', '?countryLabel', country)}
          {_country_link('?city', '?country')}
          {_city_type_union('?city')}
        }}
        """

    match = re.search(r"how many films did (.+?) direct$", clean_question, flags=re.IGNORECASE)
    if match:
        director = _clean_capture(match.group(1))
        return f"""
        {PREFIXES}

        SELECT (COUNT(DISTINCT ?film) AS ?count) WHERE {{
          {_label_match('?director', '?directorLabel', director)}
          ?film a dbo:Film .
          {_film_director_match('?film', '?director')}
        }}
        """

    match = re.search(
        r"how many films starring (.+?) were released in (\d{4})$",
        clean_question,
        flags=re.IGNORECASE,
    )
    if match:
        actor = _clean_capture(match.group(1))
        year = match.group(2)
        return f"""
        {PREFIXES}

        SELECT (COUNT(DISTINCT ?film) AS ?count) WHERE {{
          {_label_match('?actor', '?actorLabel', actor)}
          ?film a dbo:Film .
          {_film_starring_match('?film', '?actor')}
          {_film_release_match('?film', '?releaseDate')}
          BIND(SUBSTR(STR(?releaseDate), 1, 4) AS ?releaseYearText)
          FILTER(REGEX(?releaseYearText, "^[0-9]{{4}}$"))
          BIND(xsd:integer(?releaseYearText) AS ?releaseYear)
          FILTER(?releaseYear = {year})
        }}
        """

    # =========================================================
    # 4) Complex film questions
    # Specific patterns first
    # =========================================================
    match = re.search(
        r"(?:which\s+)?films(?: were)? directed by (.+?) and (?:starring|starred) (.+?) released after (\d{4})$",
        clean_question,
        flags=re.IGNORECASE,
    )
    if match:
        director = _clean_capture(match.group(1))
        actor = _clean_capture(match.group(2))
        year = match.group(3)
        return f"""
        {PREFIXES}

        SELECT DISTINCT ?filmLabel ?releaseDate WHERE {{
          {_label_match('?director', '?directorLabel', director)}
          {_label_match('?actor', '?actorLabel', actor)}
          ?film a dbo:Film .
          {_film_director_match('?film', '?director')}
          {_film_starring_match('?film', '?actor')}
          {_film_release_match('?film', '?releaseDate')}
          ?film rdfs:label ?filmLabel .
          FILTER(LANG(?filmLabel) = "en")
          BIND(SUBSTR(STR(?releaseDate), 1, 4) AS ?releaseYearText)
          FILTER(REGEX(?releaseYearText, "^[0-9]{{4}}$"))
          BIND(xsd:integer(?releaseYearText) AS ?releaseYear)
          FILTER(?releaseYear > {year})
        }}
        ORDER BY DESC(?releaseDate)
        LIMIT 20
        """

    match = re.search(
        r"(?:which\s+)?films(?: were)? directed by (.+?) and (?:starring|starred) (.+)$",
        clean_question,
        flags=re.IGNORECASE,
    )
    if match and "released after" not in q:
        director = _clean_capture(match.group(1))
        actor = _clean_capture(match.group(2))
        return f"""
        {PREFIXES}

        SELECT DISTINCT ?filmLabel WHERE {{
          {_label_match('?director', '?directorLabel', director)}
          {_label_match('?actor', '?actorLabel', actor)}
          ?film a dbo:Film .
          {_film_director_match('?film', '?director')}
          {_film_starring_match('?film', '?actor')}
          ?film rdfs:label ?filmLabel .
          FILTER(LANG(?filmLabel) = "en")
        }}
        LIMIT 20
        """

    match = re.search(
        r"(?:which\s+)?films directed by (.+?) or starring (.+)$",
        clean_question,
        flags=re.IGNORECASE,
    )
    if match:
        director = _clean_capture(match.group(1))
        actor = _clean_capture(match.group(2))
        return f"""
        {PREFIXES}

        SELECT DISTINCT ?filmLabel WHERE {{
          {_label_match('?director', '?directorLabel', director)}
          {_label_match('?actor', '?actorLabel', actor)}
          ?film a dbo:Film .
          ?film rdfs:label ?filmLabel .
          FILTER(LANG(?filmLabel) = "en")
          {{
            {_film_director_match('?film', '?director')}
          }}
          UNION
          {{
            {_film_starring_match('?film', '?actor')}
          }}
        }}
        LIMIT 25
        """

    match = re.search(
        r"(?:which\s+)?films directed by (.+?) released between (\d{4}) and (\d{4})$",
        clean_question,
        flags=re.IGNORECASE,
    )
    if match:
        director = _clean_capture(match.group(1))
        year1 = match.group(2)
        year2 = match.group(3)
        return f"""
        {PREFIXES}

        SELECT DISTINCT ?filmLabel ?releaseDate WHERE {{
          {_label_match('?director', '?directorLabel', director)}
          ?film a dbo:Film .
          {_film_director_match('?film', '?director')}
          {_film_release_match('?film', '?releaseDate')}
          ?film rdfs:label ?filmLabel .
          FILTER(LANG(?filmLabel) = "en")
          BIND(SUBSTR(STR(?releaseDate), 1, 4) AS ?releaseYearText)
          FILTER(REGEX(?releaseYearText, "^[0-9]{{4}}$"))
          BIND(xsd:integer(?releaseYearText) AS ?releaseYear)
          FILTER(?releaseYear >= {year1} && ?releaseYear <= {year2})
        }}
        ORDER BY ?releaseDate
        LIMIT 20
        """

    match = re.search(
        r"(?:which\s+)?films starring (.+?) (?:were )?released in (\d{4})$",
        clean_question,
        flags=re.IGNORECASE,
    )
    if match:
        actor = _clean_capture(match.group(1))
        year = match.group(2)
        return f"""
        {PREFIXES}

        SELECT DISTINCT ?filmLabel ?releaseDate WHERE {{
          {_label_match('?actor', '?actorLabel', actor)}
          ?film a dbo:Film .
          {_film_starring_match('?film', '?actor')}
          {_film_release_match('?film', '?releaseDate')}
          ?film rdfs:label ?filmLabel .
          FILTER(LANG(?filmLabel) = "en")
          BIND(SUBSTR(STR(?releaseDate), 1, 4) AS ?releaseYearText)
          FILTER(REGEX(?releaseYearText, "^[0-9]{{4}}$"))
          BIND(xsd:integer(?releaseYearText) AS ?releaseYear)
          FILTER(?releaseYear = {year})
        }}
        ORDER BY ?releaseDate
        LIMIT 20
        """

    match = re.search(
        r"(?:which\s+)?films starring (.+?) (?:were )?released after (\d{4})$",
        clean_question,
        flags=re.IGNORECASE,
    )
    if match:
        actor = _clean_capture(match.group(1))
        year = match.group(2)
        return f"""
        {PREFIXES}

        SELECT DISTINCT ?filmLabel ?releaseDate WHERE {{
          {_label_match('?actor', '?actorLabel', actor)}
          ?film a dbo:Film .
          {_film_starring_match('?film', '?actor')}
          {_film_release_match('?film', '?releaseDate')}
          ?film rdfs:label ?filmLabel .
          FILTER(LANG(?filmLabel) = "en")
          BIND(SUBSTR(STR(?releaseDate), 1, 4) AS ?releaseYearText)
          FILTER(REGEX(?releaseYearText, "^[0-9]{{4}}$"))
          BIND(xsd:integer(?releaseYearText) AS ?releaseYear)
          FILTER(?releaseYear > {year})
        }}
        ORDER BY DESC(?releaseDate)
        LIMIT 20
        """

    match = re.search(
        r"(?:which\s+)?films directed by (.+?) (?:were )?released (after|before) (\d{4})$",
        clean_question,
        flags=re.IGNORECASE,
    )
    if match:
        director = _clean_capture(match.group(1))
        direction = match.group(2).lower()
        year = match.group(3)
        comparator = ">" if direction == "after" else "<"
        return f"""
        {PREFIXES}

        SELECT DISTINCT ?filmLabel ?releaseDate WHERE {{
          {_label_match('?director', '?directorLabel', director)}
          ?film a dbo:Film .
          {_film_director_match('?film', '?director')}
          {_film_release_match('?film', '?releaseDate')}
          ?film rdfs:label ?filmLabel .
          FILTER(LANG(?filmLabel) = "en")
          BIND(SUBSTR(STR(?releaseDate), 1, 4) AS ?releaseYearText)
          FILTER(REGEX(?releaseYearText, "^[0-9]{{4}}$"))
          BIND(xsd:integer(?releaseYearText) AS ?releaseYear)
          FILTER(?releaseYear {comparator} {year})
        }}
        ORDER BY ?releaseDate
        LIMIT 20
        """

    # =========================================================
    # 5) List / collection questions
    # =========================================================
    match = re.search(
        r"(?:which\s+)?films(?: were)? directed by (.+)$",
        clean_question,
        flags=re.IGNORECASE,
    )
    if match and all(token not in q for token in ["starring", "starred", "released", "after", "before", "between", "or"]):
        director = _clean_capture(match.group(1))
        return f"""
        {PREFIXES}

        SELECT DISTINCT ?filmLabel WHERE {{
          {_label_match('?director', '?directorLabel', director)}
          ?film a dbo:Film .
          {_film_director_match('?film', '?director')}
          ?film rdfs:label ?filmLabel .
          FILTER(LANG(?filmLabel) = "en")
        }}
        LIMIT 20
        """

    match = re.search(r"(?:which\s+|list\s+)?universities(?: are)? in (.+)$", clean_question, flags=re.IGNORECASE)
    if match and all(token not in q for token in ["students", "greater than", "more than", "have"]):
        city = _clean_capture(match.group(1))
        return f"""
        {PREFIXES}

        SELECT DISTINCT ?universityLabel WHERE {{
          {_label_match('?city', '?cityLabel', city)}
          ?university a dbo:University .
          {_city_link('?university', '?city')}
          ?university rdfs:label ?universityLabel .
          FILTER(LANG(?universityLabel) = "en")
        }}
        LIMIT 20
        """

    match = re.search(r"(?:which\s+|list\s+)?rivers(?: are)? in (.+)$", clean_question, flags=re.IGNORECASE)
    if match and all(token not in q for token in ["longer than", "between"]):
        country = _clean_capture(match.group(1))
        return f"""
        {PREFIXES}

        SELECT DISTINCT ?riverLabel WHERE {{
          {_label_match('?country', '?countryLabel', country)}
          ?river a dbo:River .
          {_country_link('?river', '?country')}
          ?river rdfs:label ?riverLabel .
          FILTER(LANG(?riverLabel) = "en")
        }}
        LIMIT 20
        """

    match = re.search(r"(?:which\s+)?cities(?: are)? in (.+)$", clean_question, flags=re.IGNORECASE)
    if match and all(token not in q for token in ["population", "top", "largest", "smallest", "or", "have"]):
        country = _clean_capture(match.group(1))
        return f"""
        {PREFIXES}

        SELECT DISTINCT ?cityLabel WHERE {{
          {_label_match('?country', '?countryLabel', country)}
          {_country_link('?city', '?country')}
          {_city_type_union('?city')}
          ?city rdfs:label ?cityLabel .
          FILTER(LANG(?cityLabel) = "en")
        }}
        LIMIT 20
        """

    # =========================================================
    # 6) DISTINCT questions
    # =========================================================
    match = re.search(
        r"which distinct actors starred in films directed by (.+)$",
        clean_question,
        flags=re.IGNORECASE,
    )
    if match:
        director = _clean_capture(match.group(1))
        return f"""
        {PREFIXES}

        SELECT DISTINCT ?actorLabel WHERE {{
          {_label_match('?director', '?directorLabel', director)}
          ?film a dbo:Film .
          {_film_director_match('?film', '?director')}
          {_film_starring_match('?film', '?actor')}
          ?actor rdfs:label ?actorLabel .
          FILTER(LANG(?actorLabel) = "en")
        }}
        LIMIT 30
        """

    match = re.search(r"which distinct films star (.+)$", clean_question, flags=re.IGNORECASE)
    if match:
        actor = _clean_capture(match.group(1))
        return f"""
        {PREFIXES}

        SELECT DISTINCT ?filmLabel WHERE {{
          {_label_match('?actor', '?actorLabel', actor)}
          ?film a dbo:Film .
          {_film_starring_match('?film', '?actor')}
          ?film rdfs:label ?filmLabel .
          FILTER(LANG(?filmLabel) = "en")
        }}
        LIMIT 30
        """

    # =========================================================
    # 7) FILTER questions
    # =========================================================
    match = re.search(
        r"(?:which\s+)?cities(?: are)? in (.+?) (?:with|have) population (greater than|more than|less than) ([\d,]+)$",
        clean_question,
        flags=re.IGNORECASE,
    )
    if match:
        country = _clean_capture(match.group(1))
        comparator = ">" if match.group(2).lower() in {"greater than", "more than"} else "<"
        population = _numeric(match.group(3))
        order = "DESC" if comparator == ">" else "ASC"
        return f"""
        {PREFIXES}

        SELECT ?cityLabel ?population WHERE {{
          {{
            SELECT ?city (MAX(?popValue) AS ?population) WHERE {{
              {_label_match('?country', '?countryLabel', country)}
              {_country_link('?city', '?country')}
              ?city dbo:populationTotal ?popValue .
              FILTER(?popValue {comparator} {population})
              {_city_type_union('?city')}
            }}
            GROUP BY ?city
            ORDER BY {order}(?population)
            LIMIT 20
          }}
          ?city rdfs:label ?cityLabel .
          FILTER(LANG(?cityLabel) = "en")
        }}
        ORDER BY {order}(?population)
        """

    match = re.search(
        r"cities in (.+?) with population between ([\d,]+) and ([\d,]+)$",
        clean_question,
        flags=re.IGNORECASE,
    )
    if match:
        country = _clean_capture(match.group(1))
        low = _numeric(match.group(2))
        high = _numeric(match.group(3))
        return f"""
        {PREFIXES}

        SELECT ?cityLabel ?population WHERE {{
          {{
            SELECT ?city (MAX(?popValue) AS ?population) WHERE {{
              {_label_match('?country', '?countryLabel', country)}
              {_country_link('?city', '?country')}
              ?city dbo:populationTotal ?popValue .
              FILTER(?popValue >= {low} && ?popValue <= {high})
              {_city_type_union('?city')}
            }}
            GROUP BY ?city
            ORDER BY DESC(?population)
            LIMIT 20
          }}
          ?city rdfs:label ?cityLabel .
          FILTER(LANG(?cityLabel) = "en")
        }}
        ORDER BY DESC(?population)
        """

    match = re.search(
        r"(?:which\s+)?rivers(?: are)? in (.+?) (?:are |that are )?longer than ([\d,]+)$",
        clean_question,
        flags=re.IGNORECASE,
    )
    if match:
        country = _clean_capture(match.group(1))
        length = _numeric(match.group(2))
        return f"""
        {PREFIXES}

        SELECT ?riverLabel ?length WHERE {{
          {_label_match('?country', '?countryLabel', country)}
          ?river a dbo:River .
          {_country_link('?river', '?country')}
          ?river dbo:length ?length .
          ?river rdfs:label ?riverLabel .
          FILTER(LANG(?riverLabel) = "en")
          FILTER(?length > {length})
        }}
        ORDER BY DESC(?length)
        LIMIT 20
        """

    match = re.search(
        r"(?:which\s+)?universities(?: are)? in (.+?) (?:with|have) (?:more than|greater than) ([\d,]+) students$",
        clean_question,
        flags=re.IGNORECASE,
    )
    if match:
        city = _clean_capture(match.group(1))
        students = _numeric(match.group(2))
        return f"""
        {PREFIXES}

        SELECT ?universityLabel ?students WHERE {{
          {_label_match('?city', '?cityLabel', city)}
          ?university a dbo:University .
          {_city_link('?university', '?city')}
          ?university dbo:numberOfStudents ?students .
          ?university rdfs:label ?universityLabel .
          FILTER(LANG(?universityLabel) = "en")
          FILTER(?students > {students})
        }}
        ORDER BY DESC(?students)
        LIMIT 20
        """

    match = re.search(r"(?:which\s+)?people were born after (\d{4})$", clean_question, flags=re.IGNORECASE)
    if match:
        year = match.group(1)
        return f"""
        {PREFIXES}

        SELECT ?person ?birthDate WHERE {{
          ?person a dbo:Person .
          ?person dbo:birthDate ?birthDate .
          FILTER(?birthDate > "{year}-12-31"^^xsd:date)
        }}
        ORDER BY ?birthDate
        LIMIT 20
        """

    match = re.search(
        r"(?:which\s+)?scientists(?: were)? born in (.+?) and died in (.+)$",
        clean_question,
        flags=re.IGNORECASE,
    )
    if match:
        birth_country = _clean_capture(match.group(1))
        death_country = _clean_capture(match.group(2))
        return f"""
        {PREFIXES}

        SELECT DISTINCT ?scientistLabel WHERE {{
          {_label_match('?birthCountry', '?birthCountryLabel', birth_country)}
          {_label_match('?deathCountry', '?deathCountryLabel', death_country)}
          ?scientist a dbo:Scientist .
          {_birth_place_match('?scientist', '?birthPlace')}
          {_death_place_match('?scientist', '?deathPlace')}
          {_country_link('?birthPlace', '?birthCountry')}
          {_country_link('?deathPlace', '?deathCountry')}
          ?scientist rdfs:label ?scientistLabel .
          FILTER(LANG(?scientistLabel) = "en")
        }}
        LIMIT 20
        """

    match = re.search(
        r"(?:which\s+)?people(?: were)? born in (.+?) and received the nobel prize$",
        clean_question,
        flags=re.IGNORECASE,
    )
    if match:
        country = _clean_capture(match.group(1))
        return f"""
        {PREFIXES}

        SELECT DISTINCT ?personLabel ?award WHERE {{
          {_label_match('?country', '?countryLabel', country)}
          {_birth_place_match('?person', '?birthPlace')}
          {_country_link('?birthPlace', '?country')}
          {_award_match('?person', '?award')}
          ?person rdfs:label ?personLabel .
          FILTER(LANG(?personLabel) = "en")
          FILTER(CONTAINS(LCASE(STR(?award)), "nobel"))
        }}
        LIMIT 20
        """

    # =========================================================
    # 8) ORDER BY / top-k questions
    # =========================================================
    match = re.search(r"top (\d+) cities in (.+?) by population$", clean_question, flags=re.IGNORECASE)
    if match:
        limit = match.group(1)
        country = _clean_capture(match.group(2))
        return f"""
        {PREFIXES}

        SELECT ?cityLabel ?population WHERE {{
          {{
            SELECT ?city (MAX(?popValue) AS ?population) WHERE {{
              {_label_match('?country', '?countryLabel', country)}
              {_country_link('?city', '?country')}
              ?city dbo:populationTotal ?popValue .
              {_city_type_union('?city')}
            }}
            GROUP BY ?city
            ORDER BY DESC(?population)
            LIMIT {limit}
          }}
          ?city rdfs:label ?cityLabel .
          FILTER(LANG(?cityLabel) = "en")
        }}
        ORDER BY DESC(?population)
        """

    match = re.search(r"largest cities in (.+)$", clean_question, flags=re.IGNORECASE)
    if match:
        country = _clean_capture(match.group(1))
        return f"""
        {PREFIXES}

        SELECT ?cityLabel ?population WHERE {{
          {{
            SELECT ?city (MAX(?popValue) AS ?population) WHERE {{
              {_label_match('?country', '?countryLabel', country)}
              {_country_link('?city', '?country')}
              ?city dbo:populationTotal ?popValue .
              {_city_type_union('?city')}
            }}
            GROUP BY ?city
            ORDER BY DESC(?population)
            LIMIT 10
          }}
          ?city rdfs:label ?cityLabel .
          FILTER(LANG(?cityLabel) = "en")
        }}
        ORDER BY DESC(?population)
        """

    # =========================================================
    # 9) OR questions with cities
    # =========================================================
    match = re.search(
        r"cities in (.+?) or (.+?) with population greater than ([\d,]+)$",
        clean_question,
        flags=re.IGNORECASE,
    )
    if match:
        country1 = _clean_capture(match.group(1))
        country2 = _clean_capture(match.group(2))
        population = _numeric(match.group(3))
        return f"""
        {PREFIXES}

        SELECT ?cityLabel ?population WHERE {{
          {{
            SELECT ?city (MAX(?popValue) AS ?population) WHERE {{
              {_label_match('?country1', '?country1Label', country1)}
              {_label_match('?country2', '?country2Label', country2)}
              ?city dbo:populationTotal ?popValue .
              ?city dbo:country ?country .
              FILTER(?country = ?country1 || ?country = ?country2)
              FILTER(?popValue > {population})
              {_city_type_union('?city')}
            }}
            GROUP BY ?city
            ORDER BY DESC(?population)
            LIMIT 25
          }}
          ?city rdfs:label ?cityLabel .
          FILTER(LANG(?cityLabel) = "en")
        }}
        ORDER BY DESC(?population)
        """

    # =========================================================
    # 10) Ternary-like / best-effort questions
    # =========================================================
    match = re.search(r"who married (.+?) in (\d{4})$", clean_question, flags=re.IGNORECASE)
    if match:
        spouse = _clean_capture(match.group(1))
        year = match.group(2)
        return f"""
        {PREFIXES}

        SELECT DISTINCT ?personLabel ?date WHERE {{
          {_label_match('?spouse', '?spouseLabel', spouse)}
          {_spouse_match('?person', '?spouse')}
          ?person rdfs:label ?personLabel .
          FILTER(LANG(?personLabel) = "en")

          OPTIONAL {{
            {{
              ?person dbo:marriageDate ?date .
            }}
            UNION
            {{
              ?person dbp:marriageDate ?date .
            }}
            UNION
            {{
              ?person dbp:married ?date .
            }}
          }}

          FILTER(!BOUND(?date) || REGEX(STR(?date), "{year}"))
        }}
        LIMIT 10
        """

    return ""