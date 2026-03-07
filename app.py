import streamlit as st
from src.query_builder import build_query
from src.dbpedia_client import run_sparql_query
from src.answer_formatter import format_answer

st.set_page_config(page_title="DBpedia QA System", layout="centered")

st.title("DBpedia Question Answering System")
st.write("Ask a question and get an answer from the DBpedia Knowledge Graph.")

question = st.text_input("Enter your question:")

if st.button("Get Answer"):
    if not question.strip():
        st.warning("Please enter a question.")
    else:
        query = build_query(question)

        if not query:
            st.error("This question type is not supported yet.")
        else:
            st.subheader("Generated SPARQL Query")
            st.code(query, language="sparql")

            try:
                result = run_sparql_query(query)
                answer = format_answer(result)

                st.subheader("Answer")
                st.success(answer)
            except Exception as exc:
                st.exception(exc)