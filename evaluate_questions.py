from pathlib import Path
from src.query_builder import build_query
from src.dbpedia_client import run_sparql_query


QUESTIONS = [
    "What is the capital of Germany?",
    "What is the capital of France?",
    "Who is the spouse of Barack Obama?",
    "Where was Albert Einstein born?",
    "When was Barack Obama born?",
    "When was Google founded?",
    "When did World War II start?",
    "Which cities are in Germany?",
    "Which films were directed by Christopher Nolan?",
    "Which universities are in Berlin?",
    "Which rivers are in France?",
    "Which cities in Germany have population greater than 1000000?",
    "Which people were born after 1950?",
    "Which rivers in France are longer than 500000?",
    "Which films were directed by Christopher Nolan and starred Leonardo DiCaprio?",
    "Which universities in Berlin have more than 20000 students?",
    "Which scientists were born in Germany and died in the United States?",
    "Which people were born in Germany and received the Nobel Prize?",
    "Which films starring Leonardo DiCaprio were released in 2010?",
    "Which films directed by Christopher Nolan were released after 2010?",
    "Who married Michelle Obama in 1992?",
]


def extract_bindings(result: dict) -> list[dict]:
    return result.get("results", {}).get("bindings", [])


def main():
    working = []
    non_working = []
    report_lines = []

    for question in QUESTIONS:
        print(f"\nTesting: {question}")
        query = build_query(question)

        if not query.strip():
            print("  -> No query generated")
            non_working.append(question)
            report_lines.append(f"{question} | NO_QUERY | 0")
            continue

        try:
            result = run_sparql_query(query)
            bindings = extract_bindings(result)
            row_count = len(bindings)

            if row_count > 0:
                print(f"  -> Working ({row_count} rows)")
                working.append(question)
                report_lines.append(f"{question} | WORKING | {row_count}")
            else:
                print("  -> Query ran but returned 0 rows")
                non_working.append(question)
                report_lines.append(f"{question} | ZERO_ROWS | 0")

        except Exception as exc:
            print(f"  -> Error: {exc}")
            non_working.append(question)
            report_lines.append(f"{question} | ERROR | 0")

    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)

    (data_dir / "working_questions.txt").write_text(
        "\n".join(working), encoding="utf-8"
    )
    (data_dir / "non_working_questions.txt").write_text(
        "\n".join(non_working), encoding="utf-8"
    )
    (data_dir / "evaluation_report.txt").write_text(
        "\n".join(report_lines), encoding="utf-8"
    )

    print("\nFinished.")
    print(f"Working: {len(working)}")
    print(f"Non-working: {len(non_working)}")
    print("Files updated in data/ folder.")


if __name__ == "__main__":
    main()