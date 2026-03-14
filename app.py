import streamlit as st
import pandas as pd
from urllib.parse import unquote

from src.query_builder import build_query
from src.dbpedia_client import run_sparql_query

st.set_page_config(
    page_title="DBpedia Question Answering System",
    page_icon="🌐",
    layout="wide",
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


if "question_input" not in st.session_state:
    st.session_state["question_input"] = ""

if "last_result" not in st.session_state:
    st.session_state["last_result"] = None

if "last_query" not in st.session_state:
    st.session_state["last_query"] = ""

if "last_error" not in st.session_state:
    st.session_state["last_error"] = ""

if "last_question" not in st.session_state:
    st.session_state["last_question"] = ""


# -------------------------
# Header
# -------------------------
icon_col, title_col = st.columns([1, 14])

with icon_col:
    st.markdown("## 🌐")

with title_col:
    st.title("DBpedia Question Answering System")
    st.caption(
        "Ask natural language questions about people, places, films, dates, and more using the DBpedia Knowledge Graph."
    )

st.markdown("---")

# -------------------------
# Intro Section
# -------------------------
with st.container(border=True):
    st.subheader("Ask a Question")
    st.write(
        "Enter a question in natural language. The system generates a SPARQL query, retrieves results from DBpedia, and displays the answer in a user-friendly format."
    )

    st.markdown("**Example questions:**")
    st.markdown(
        """
- What is the capital of Germany?
- What is the capital of France?
- Who is the spouse of Barack Obama?
- When was Barack Obama born?
- Which cities are in Germany?
- Cities in Germany with population greater than 1000000
- Films directed by Christopher Nolan and starring Leonardo DiCaprio
"""
    )

# -------------------------
# Input Section
# -------------------------
st.markdown("### Question Input")

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

if get_answer_clicked:
    st.session_state["last_question"] = question

    if not question.strip():
        st.session_state["last_error"] = "Please enter a question."
        st.session_state["last_result"] = None
        st.session_state["last_query"] = ""
    else:
        query = build_query(question)
        st.session_state["last_query"] = query

        if not query:
            st.session_state["last_error"] = "This question type is not supported yet."
            st.session_state["last_result"] = None
        else:
            try:
                result = cached_run_query(query)
                st.session_state["last_result"] = result
                st.session_state["last_error"] = ""
            except Exception as exc:
                st.session_state["last_result"] = None
                st.session_state["last_error"] = f"Error while querying DBpedia: {exc}"

# -------------------------
# Output Section
# -------------------------
if st.session_state["last_error"]:
    st.error(st.session_state["last_error"])

if st.session_state["last_result"]:
    result = st.session_state["last_result"]
    bindings = extract_bindings(result)
    df = bindings_to_dataframe(bindings) if bindings else pd.DataFrame()
    saved_question = st.session_state.get("last_question", "")

    st.markdown("---")
    st.markdown("## Results Overview")

    overview_col1, overview_col2, overview_col3 = st.columns(3)

    with overview_col1:
        st.metric("Question Type", detect_question_category(saved_question))

    with overview_col2:
        st.metric("Rows Returned", len(bindings))

    with overview_col3:
        st.metric("Status", "Success")

    tab1, tab2, tab3 = st.tabs(["Answer", "SPARQL Query", "Details"])

    # -------------------------
    # Tab 1: Answer
    # -------------------------
    with tab1:
        st.subheader("Answer")

        if df.empty:
            st.warning("No answer found.")
        else:
            if len(df) == 1 and len(df.columns) == 1:
                answer_value = str(df.iloc[0, 0])
                st.success(answer_value)
            elif len(df) == 1:
                st.dataframe(df, width="stretch", hide_index=True)
            else:
                st.info("Multiple results found. Displaying them in a table.")
                st.dataframe(df, width="stretch", hide_index=True)

    # -------------------------
    # Tab 2: SPARQL Query
    # -------------------------
    with tab2:
        st.subheader("Generated SPARQL Query")
        st.code(st.session_state["last_query"], language="sparql")

    # -------------------------
    # Tab 3: Details
    # -------------------------
    with tab3:
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