import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

SAIA_API_KEY = os.getenv("SAIA_API_KEY")
SAIA_BASE_URL = os.getenv("SAIA_BASE_URL", "https://chat-ai.academiccloud.de/v1")
SAIA_MODEL = os.getenv("SAIA_MODEL", "meta-llama-3.1-8b-instruct")


def generate_sparql_with_llm(question: str) -> str:
    if not SAIA_API_KEY:
        raise ValueError("SAIA_API_KEY is missing in the .env file.")

    client = OpenAI(
        api_key=SAIA_API_KEY,
        base_url=SAIA_BASE_URL,
    )

    system_prompt = """
You are a DBpedia SPARQL generator.

Your task:
- Convert the user's natural language question into a valid SPARQL query for DBpedia.
- Return ONLY the SPARQL query.
- Use DBpedia prefixes such as dbo:, dbr:, rdf:, rdfs:, xsd: when needed.
- Prefer simple, correct DBpedia ontology properties.
- Do not include markdown, explanations, or code fences.
- If the question is too vague or cannot be mapped, return exactly: UNSUPPORTED
"""

    user_prompt = f"Question: {question}"

    response = client.chat.completions.create(
        model=SAIA_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0,
    )

    content = response.choices[0].message.content.strip()
    return content