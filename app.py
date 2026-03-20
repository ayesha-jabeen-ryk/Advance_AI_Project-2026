import re
from urllib.parse import unquote

import pandas as pd
import streamlit as st

from src.dbpedia_client import run_sparql_query
from src.llm_client import generate_sparql_with_llm
from src.query_builder import build_query

st.set_page_config(
    page_title="DBpedia Question Answering System",
    page_icon="🌐",
    layout="wide",
)


def inject_custom_css() -> None:
    st.markdown(
        """
        <style>
        :root {
            --bg: #f4f8fb;
            --card: #ffffff;
            --card-border: #d8e5f1;
            --text: #18324a;
            --muted: #5f7388;
            --primary: #1f6aa5;
            --primary-dark: #173b6c;
            --accent: #2fb4c6;
            --success-bg: #eef8f2;
        }

        .stApp {
            background: linear-gradient(180deg, #eef5fb 0%, #f7fbff 45%, #f4f8fb 100%);
            color: var(--text);
        }

        [data-testid="stHeader"] {
            background: rgba(0, 0, 0, 0);
        }

        [data-testid="stSidebar"] {
            background: #edf4fa;
        }

        .block-container {
            padding-top: 2rem;
            padding-bottom: 2.5rem;
            max-width: 1200px;
        }

        .hero-card {
            background: linear-gradient(135deg, #173b6c 0%, #1f6aa5 55%, #2fb4c6 100%);
            border-radius: 24px;
            padding: 2rem 2.2rem;
            margin-bottom: 1.25rem;
            box-shadow: 0 14px 35px rgba(23, 59, 108, 0.18);
            color: white;
        }

        .hero-title {
            font-size: 2.5rem;
            font-weight: 800;
            line-height: 1.15;
            margin: 0 0 0.55rem 0;
            color: white;
        }

        .hero-subtitle {
            font-size: 1.05rem;
            margin: 0;
            color: rgba(255, 255, 255, 0.9);
        }

        .section-card {
            background: var(--card);
            border: 1px solid var(--card-border);
            border-radius: 20px;
            padding: 1.25rem 1.4rem;
            margin-bottom: 1rem;
            box-shadow: 0 10px 25px rgba(21, 52, 85, 0.06);
        }

        .section-title {
            font-size: 1.55rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
            color: var(--primary-dark);
        }

        .section-text {
            color: var(--text);
            line-height: 1.7;
        }

        .example-list {
            margin-top: 0.8rem;
            color: var(--text);
            line-height: 1.8;
        }

        .subtle-label {
            display: inline-block;
            padding: 0.32rem 0.7rem;
            background: #eaf3fb;
            color: var(--primary-dark);
            border: 1px solid #cfe0ef;
            border-radius: 999px;
            font-size: 0.88rem;
            font-weight: 600;
            margin-bottom: 0.85rem;
        }

        .stTextInput > div > div input {
            background: #f9fcff;
            color: var(--text);
            border-radius: 14px;
            border: 1px solid #c9dceb;
            min-height: 48px;
        }

        .stTextInput > label,
        .stMarkdown,
        .stCaption,
        .stSubheader,
        .stText,
        label,
        p,
        li {
            color: var(--text) !important;
        }

        .stButton > button,
        .stDownloadButton > button {
            border: none;
            border-radius: 12px;
            font-weight: 700;
            min-height: 44px;
            box-shadow: 0 8px 16px rgba(31, 106, 165, 0.15);
        }

        .stButton > button {
            background: linear-gradient(135deg, #1f6aa5 0%, #2fb4c6 100%);
            color: white;
        }

        .stButton > button:hover,
        .stDownloadButton > button:hover {
            filter: brightness(1.03);
            transform: translateY(-1px);
        }

        div[data-testid="stMetric"] {
            background: white;
            border: 1px solid var(--card-border);
            border-radius: 16px;
            padding: 0.7rem 0.9rem;
            box-shadow: 0 8px 20px rgba(21, 52, 85, 0.05);
        }

        [data-testid="metric-container"] {
            background: white;
            border: 1px solid var(--card-border);
            border-radius: 16px;
            padding: 0.8rem 1rem;
            box-shadow: 0 8px 20px rgba(21, 52, 85, 0.05);
        }

        div[data-baseweb="tab-list"] {
            gap: 0.5rem;
        }

        div[data-baseweb="tab"] {
            background: #edf4fa;
            border: 1px solid #d6e4f1;
            border-radius: 12px;
            padding: 0.55rem 1rem;
        }

        div[data-baseweb="tab"][aria-selected="true"] {
            background: #173b6c;
            color: white !important;
            border-color: #173b6c;
        }

        .result-card {
            background: white;
            border: 1px solid var(--card-border);
            border-radius: 18px;
            padding: 1rem 1.15rem;
            margin-bottom: 0.9rem;
            box-shadow: 0 10px 24px rgba(21, 52, 85, 0.06);
        }

        .result-answer {
            background: var(--success-bg);
            border: 1px solid #cfe8d8;
            color: #1f5f35;
            border-radius: 14px;
            padding: 0.9rem 1rem;
            font-weight: 700;
            font-size: 1.05rem;
        }

        .footer-note {
            text-align: center;
            color: var(--muted);
            font-size: 0.9rem;
            margin-top: 1.2rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data(show_spinner=False, ttl=3600)
def cached_run_query(query: str):
    return run_sparql_query(query)


def extract_bindings(result: dict) -> list[dict]:
    return result.get("results", {}).get("bindings", [])


def clean_uri_label(value: str) -> str:
    if not value:
        return ""
    if value.startswith("http://dbpedia.org/resource/"):
        return unquote(value.split("/")[-1].replace("_", " "))
    return value


def bindings_to_dataframe(bindings: list[dict]) -> pd.DataFrame:
    rows = []
    for row in bindings:
        clean_row = {}
        for key, value in row.items():
            raw_value = value.get("value", "")
            clean_row[key] = clean_uri_label(raw_value)
        rows.append(clean_row)
    return pd.DataFrame(rows)


def get_first_entity_uri(bindings: list[dict]) -> str | None:
    for row in bindings:
        for _, value in row.items():
            raw_value = value.get("value", "")
            if raw_value.startswith("http://dbpedia.org/resource/"):
                return raw_value
    return None


def sanitize_generated_query(query: str) -> str:
    if not query:
        return ""

    cleaned = query.strip()

    fenced_match = re.search(r"```(?:sparql)?\s*(.*?)```", cleaned, flags=re.IGNORECASE | re.DOTALL)
    if fenced_match:
        cleaned = fenced_match.group(1).strip()

    keyword_match = re.search(r"(PREFIX\s+\w+:.*|SELECT\s+.*|ASK\s+.*)", cleaned, flags=re.IGNORECASE | re.DOTALL)
    if keyword_match:
        cleaned = keyword_match.group(1).strip()

    return cleaned


@st.cache_data(show_spinner=False, ttl=3600)
def get_entity_details(entity_uri: str) -> dict:
    detail_query = f"""
    PREFIX dbo: <http://dbpedia.org/ontology/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX foaf: <http://xmlns.com/foaf/0.1/>

    SELECT
      (SAMPLE(?label_en) AS ?label)
      (SAMPLE(?abstract_en) AS ?abstract)
      (SAMPLE(?thumbnail_uri) AS ?thumbnail)
    WHERE {{
      OPTIONAL {{
        <{entity_uri}> rdfs:label ?label_en .
        FILTER(LANG(?label_en) = 'en')
      }}
      OPTIONAL {{
        <{entity_uri}> dbo:abstract ?abstract_en .
        FILTER(LANG(?abstract_en) = 'en')
      }}
      OPTIONAL {{
        <{entity_uri}> dbo:thumbnail ?thumbnail_uri .
      }}
      OPTIONAL {{
        <{entity_uri}> foaf:depiction ?thumbnail_uri .
      }}
    }}
    """

    try:
        result = cached_run_query(detail_query)
        bindings = extract_bindings(result)

        if not bindings:
            return {
                "label": clean_uri_label(entity_uri),
                "abstract": "",
                "thumbnail": "",
                "uri": entity_uri,
            }

        row = bindings[0]

        return {
            "label": row.get("label", {}).get("value", clean_uri_label(entity_uri)),
            "abstract": row.get("abstract", {}).get("value", ""),
            "thumbnail": row.get("thumbnail", {}).get("value", ""),
            "uri": entity_uri,
        }
    except Exception:
        return {
            "label": clean_uri_label(entity_uri),
            "abstract": "",
            "thumbnail": "",
            "uri": entity_uri,
        }


def detect_question_category(question: str) -> str:
    q = question.lower().strip()

    if "when" in q or "born" in q or "founded" in q or "end" in q or "after" in q or "before" in q:
        return "Date / Time Question"
    if "greater than" in q or "less than" in q or "more than" in q:
        return "Filter Question"
    if " and " in q:
        return "Compound / Multiple Triple Question"
    if q.startswith("which") or q.startswith("list") or q.startswith("name all"):
        return "List / Collection Question"
    return "Simple Fact Question"


def clear_state():
    st.session_state["question_input"] = ""
    st.session_state["last_result"] = None
    st.session_state["last_query"] = ""
    st.session_state["last_error"] = ""
    st.session_state["last_question"] = ""
    st.session_state["query_source"] = ""


DEFAULT_SESSION_STATE = {
    "question_input": "",
    "last_result": None,
    "last_query": "",
    "last_error": "",
    "last_question": "",
    "query_source": "",
}

for key, value in DEFAULT_SESSION_STATE.items():
    if key not in st.session_state:
        st.session_state[key] = value


inject_custom_css()

# -------------------------
# Header 
# -------------------------
st.markdown(
    """
    <div class="hero-card">
        <div class="subtle-label">Advanced Machine Learning Final Project</div>
        <div class="hero-title">🌐 DBpedia Question Answering System</div>
        <p class="hero-subtitle">
            Ask natural language questions about people, places, films, dates, and more.
            The system builds SPARQL queries, retrieves answers from DBpedia, and uses an LLM fallback for unsupported questions.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# -------------------------
# Intro Section
# -------------------------
st.markdown("<div class='section-card'>", unsafe_allow_html=True)
st.markdown("<div class='section-title'>Ask a Question</div>", unsafe_allow_html=True)
st.markdown(
    """
    <div class='section-text'>
        Enter a question in natural language. The system first tries rule-based SPARQL generation.
        If the question is not supported by the rule-based layer, it uses the SAIA-backed LLM fallback.
    </div>
    <div class='example-list'>
        <b>Example questions:</b><br>
        • What is the capital of Germany?<br>
        • Who is the spouse of Barack Obama?<br>
        • When was Barack Obama born?<br>
        • Which cities are in Germany?<br>
        • Cities in Germany with population greater than 1000000<br>
        • Films directed by Christopher Nolan and starring Leonardo DiCaprio
    </div>
    """,
    unsafe_allow_html=True,
)
st.markdown("</div>", unsafe_allow_html=True)

# -------------------------
# Input Section
# -------------------------
st.markdown("<div class='section-card'>", unsafe_allow_html=True)
st.markdown("<div class='section-title'>Question Input</div>", unsafe_allow_html=True)

question = st.text_input(
    "Enter your question:",
    key="question_input",
    placeholder="Example: What is the capital of France?",
)

btn_col1, btn_col2, btn_col3 = st.columns([1.2, 1.2, 7])

with btn_col1:
    get_answer_clicked = st.button("Get Answer", width="stretch", key="get_answer_btn")

with btn_col2:
    st.button("Reset", width="stretch", key="reset_btn", on_click=clear_state)

st.markdown("</div>", unsafe_allow_html=True)

if get_answer_clicked:
    st.session_state["last_question"] = question
    st.session_state["last_error"] = ""
    st.session_state["last_result"] = None
    st.session_state["last_query"] = ""
    st.session_state["query_source"] = ""

    if not question.strip():
        st.session_state["last_error"] = "Please enter a question."
    else:
        query = build_query(question)

        if query:
            st.session_state["query_source"] = "Rule-based"
        else:
            try:
                query = sanitize_generated_query(generate_sparql_with_llm(question))
                st.session_state["query_source"] = "LLM fallback"
            except Exception as exc:
                st.session_state["last_error"] = f"LLM fallback failed: {exc}"
                query = ""

        st.session_state["last_query"] = query

        if not query or query.strip().upper() == "UNSUPPORTED":
            if not st.session_state["last_error"]:
                st.session_state["last_error"] = "This question type is not supported yet."
        else:
            try:
                result = cached_run_query(query)
                st.session_state["last_result"] = result
            except Exception as exc:
                st.session_state["last_result"] = None
                st.session_state["last_error"] = f"Error while querying DBpedia: {exc}"

# -------------------------
# Output Section
# -------------------------
if st.session_state["last_error"]:
    st.error(st.session_state["last_error"])

if st.session_state["last_result"] is not None:
    result = st.session_state["last_result"]
    bindings = extract_bindings(result)
    df = bindings_to_dataframe(bindings) if bindings else pd.DataFrame()
    saved_question = st.session_state.get("last_question", "")

    st.markdown("<div class='section-title' style='margin-top:0.3rem;'>Results Overview</div>", unsafe_allow_html=True)

    overview_col1, overview_col2, overview_col3, overview_col4 = st.columns(4)

    with overview_col1:
        st.metric("Question Type", detect_question_category(saved_question))

    with overview_col2:
        st.metric("Rows Returned", len(bindings))

    with overview_col3:
        st.metric("Query Source", st.session_state.get("query_source", "Unknown"))

    with overview_col4:
        st.metric("Status", "Success")

    tab1, tab2, tab3 = st.tabs(["Answer", "SPARQL Query", "Details"])

    with tab1:
        st.markdown("<div class='result-card'>", unsafe_allow_html=True)
        st.subheader("Answer")

        if df.empty:
            st.warning("No answer found.")
        else:
            if len(df) == 1 and len(df.columns) == 1:
                answer_value = str(df.iloc[0, 0])
                st.markdown(f"<div class='result-answer'>{answer_value}</div>", unsafe_allow_html=True)
            elif len(df) == 1:
                st.dataframe(df, width="stretch", hide_index=True)
            else:
                st.info("Multiple results found. Displaying them in a table.")
                st.dataframe(df, width="stretch", hide_index=True)

            csv_data = df.to_csv(index=False).encode("utf-8")
            st.download_button(
                "Download results as CSV",
                data=csv_data,
                file_name="dbpedia_results.csv",
                mime="text/csv",
            )
        st.markdown("</div>", unsafe_allow_html=True)

    with tab2:
        st.markdown("<div class='result-card'>", unsafe_allow_html=True)
        st.subheader("Generated SPARQL Query")
        st.caption(f"Source: {st.session_state.get('query_source', 'Unknown')}")
        st.code(st.session_state["last_query"], language="sparql")
        st.markdown("</div>", unsafe_allow_html=True)

    with tab3:
        st.markdown("<div class='result-card'>", unsafe_allow_html=True)
        st.subheader("Entity Details")

        entity_uri = get_first_entity_uri(bindings)

        if not entity_uri:
            st.info("No DBpedia entity URI found in the current result to show extra details.")
        else:
            details = get_entity_details(entity_uri)

            left_col, right_col = st.columns([1, 2])

            with left_col:
                if details.get("thumbnail"):
                    st.image(details["thumbnail"], width="stretch")
                else:
                    st.info("No image available.")

            with right_col:
                st.markdown(f"### {details.get('label', 'Entity')}")
                st.write(f"**DBpedia URI:** {details.get('uri', '')}")

                wikipedia_link = details.get("uri", "").replace(
                    "http://dbpedia.org/resource/",
                    "https://en.wikipedia.org/wiki/",
                )
                st.markdown(f"**Wikipedia:** [Open article]({wikipedia_link})")

                show_summary = st.toggle("Show concise summary", key="show_summary_toggle")

                if show_summary:
                    abstract_text = details.get("abstract", "").strip()

                    if abstract_text:
                        short_summary = abstract_text[:600]
                        if len(abstract_text) > 600:
                            short_summary += "..."
                        st.success(short_summary)
                    else:
                        st.warning("No summary available for this entity in DBpedia.")
        st.markdown("</div>", unsafe_allow_html=True)

st.markdown(
    "<div class='footer-note'>Designed for your DBpedia QA final project submission by Ayesha Jabeen.</div>",
    unsafe_allow_html=True,
)
