from pathlib import Path
import csv
import re
import time
from collections import Counter, defaultdict

from src.query_builder import build_query
from src.dbpedia_client import run_sparql_query
from src.llm_client import generate_sparql_with_llm


QUESTIONS = [
    "What is the capital of Germany?",
    "What is the capital of France?",
    "Who is the spouse of Barack Obama?",
    "Where was Albert Einstein born?",
    "When was Barack Obama born?",
    "Who is the spouse of David Beckham?",
    "Who is the spouse of Jay-Z?",
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
    "Top 10 cities in Germany by population",
    "Films directed by Christopher Nolan and starring Leonardo DiCaprio released after 2010",
    "Films directed by Christopher Nolan or starring Leonardo DiCaprio",
    "Films directed by Christopher Nolan released between 2000 and 2015",
    # Good fallback tests
    "Name the capital city of Spain.",
    "Show me actors in movies directed by Quentin Tarantino.",
    "List movies with Tom Hanks released after 2015.",
]


def extract_bindings(result: dict) -> list[dict]:
    return result.get("results", {}).get("bindings", [])


def categorize_question(question: str) -> str:
    q = question.lower().strip()

    if " or " in q:
        return "or_union"
    if q.startswith("how many"):
        return "aggregate_count"
    if any(word in q for word in ["top ", "largest ", "smallest "]):
        return "order_by_topk"
    if any(word in q for word in ["greater than", "less than", "between", "longer than", "more than"]):
        return "filter"
    if any(word in q for word in ["released after", "released before", "released in", "when", "born", "founded", "start"]):
        return "date_time"
    if "distinct" in q:
        return "distinct"
    if " and " in q:
        return "compound_join"
    if "married" in q:
        return "ternary_like"
    if q.startswith("which") or q.startswith("list") or q.startswith("show me") or q.startswith("name"):
        return "list"
    return "fact"


def resolve_build_query_output(output) -> tuple[str, str]:
    """
    Supports:
    1) "SPARQL QUERY"
    2) ("SPARQL QUERY", "rule_based")
    3) {"query": "...", "source": "..."}
    """
    if isinstance(output, str):
        return output, "rule_based"

    if isinstance(output, tuple):
        query = str(output[0]) if len(output) > 0 and output[0] else ""
        source = str(output[1]) if len(output) > 1 and output[1] else "rule_based"
        return query, source

    if isinstance(output, dict):
        query = str(output.get("query", "") or "")
        source = str(output.get("source", "rule_based") or "rule_based")
        return query, source

    return "", "unknown"


def sanitize_llm_query(query: str) -> str:
    if not query:
        return ""

    cleaned = query.strip()

    # remove fenced code blocks if present
    cleaned = re.sub(r"^```(?:sparql)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    # keep only from first PREFIX/SELECT/ASK onward
    match = re.search(r"(PREFIX|SELECT|ASK|CONSTRUCT|DESCRIBE)\b", cleaned, flags=re.IGNORECASE)
    if match:
        cleaned = cleaned[match.start():]

    return cleaned.strip()


def binding_to_preview(binding: dict) -> str:
    if not binding:
        return ""

    parts = []
    for key, value in binding.items():
        if isinstance(value, dict):
            parts.append(f"{key}={value.get('value', '')}")
        else:
            parts.append(f"{key}={value}")
    return " | ".join(parts)


def clean_one_line(text: str) -> str:
    if text is None:
        return ""
    return re.sub(r"\s+", " ", str(text)).strip()


def write_text_file(path: Path, lines: list[str]) -> None:
    path.write_text("\n".join(lines), encoding="utf-8")


def try_generate_query(question: str) -> tuple[str, str, str]:
    """
    Returns:
    query, query_source, build_note

    query_source values:
    - rule_based
    - llm_fallback
    - unsupported
    - fallback_error
    """
    raw_output = build_query(question)
    query, query_source = resolve_build_query_output(raw_output)

    if query.strip():
        return query.strip(), query_source, "rule-based query generated"

    try:
        llm_query = generate_sparql_with_llm(question)
        llm_query = sanitize_llm_query(llm_query)

        if not llm_query or llm_query.strip().upper() == "UNSUPPORTED":
            return "", "unsupported", "rule-based missed; fallback returned unsupported"

        return llm_query, "llm_fallback", "rule-based missed; fallback generated query"

    except Exception as exc:
        return "", "fallback_error", f"fallback failed: {clean_one_line(str(exc))}"


def main():
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)

    results = []
    working_questions = []
    non_working_questions = []
    fallback_questions = []
    rule_based_questions = []

    print("=" * 80)
    print("DBpedia QA Evaluation Started")
    print("=" * 80)

    for idx, question in enumerate(QUESTIONS, start=1):
        print(f"\n[{idx}/{len(QUESTIONS)}] Testing: {question}")

        category = categorize_question(question)

        build_start = time.perf_counter()
        query, query_source, build_note = try_generate_query(question)
        build_end = time.perf_counter()
        build_time_ms = round((build_end - build_start) * 1000, 2)

        if not query.strip():
            status = "UNSUPPORTED" if query_source == "unsupported" else "NO_QUERY"

            print(f"  -> {status} ({build_note})")

            results.append(
                {
                    "question": question,
                    "category": category,
                    "query_source": query_source,
                    "status": status,
                    "row_count": 0,
                    "build_time_ms": build_time_ms,
                    "query_time_ms": 0.0,
                    "total_time_ms": build_time_ms,
                    "sample_result": "",
                    "error_message": build_note,
                    "query": "",
                }
            )
            non_working_questions.append(question)
            continue

        try:
            query_start = time.perf_counter()
            result = run_sparql_query(query)
            query_end = time.perf_counter()

            bindings = extract_bindings(result)
            row_count = len(bindings)
            query_time_ms = round((query_end - query_start) * 1000, 2)
            total_time_ms = round(build_time_ms + query_time_ms, 2)
            sample_result = binding_to_preview(bindings[0]) if bindings else ""

            if row_count > 0:
                if query_source == "llm_fallback":
                    status = "WORKING_FALLBACK"
                    fallback_questions.append(question)
                else:
                    status = "WORKING_RULE"
                    rule_based_questions.append(question)

                working_questions.append(question)
                print(f"  -> {status} ({row_count} rows, {total_time_ms} ms)")
            else:
                status = "ZERO_ROWS"
                non_working_questions.append(question)
                print(f"  -> ZERO_ROWS ({query_source}, {total_time_ms} ms)")

            results.append(
                {
                    "question": question,
                    "category": category,
                    "query_source": query_source,
                    "status": status,
                    "row_count": row_count,
                    "build_time_ms": build_time_ms,
                    "query_time_ms": query_time_ms,
                    "total_time_ms": total_time_ms,
                    "sample_result": clean_one_line(sample_result),
                    "error_message": "",
                    "query": query.strip(),
                }
            )

        except Exception as exc:
            error_message = clean_one_line(str(exc))
            print(f"  -> ERROR ({query_source}): {error_message}")

            results.append(
                {
                    "question": question,
                    "category": category,
                    "query_source": query_source,
                    "status": "ERROR",
                    "row_count": 0,
                    "build_time_ms": build_time_ms,
                    "query_time_ms": 0.0,
                    "total_time_ms": build_time_ms,
                    "sample_result": "",
                    "error_message": error_message,
                    "query": query.strip(),
                }
            )
            non_working_questions.append(question)

    # text files
    write_text_file(data_dir / "working_questions.txt", working_questions)
    write_text_file(data_dir / "non_working_questions.txt", non_working_questions)
    write_text_file(data_dir / "fallback_questions.txt", fallback_questions)
    write_text_file(data_dir / "rule_based_questions.txt", rule_based_questions)

    # csv
    csv_path = data_dir / "evaluation_results.csv"
    fieldnames = [
        "question",
        "category",
        "query_source",
        "status",
        "row_count",
        "build_time_ms",
        "query_time_ms",
        "total_time_ms",
        "sample_result",
        "error_message",
        "query",
    ]

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    total = len(results)
    working_rule_count = sum(1 for r in results if r["status"] == "WORKING_RULE")
    working_fallback_count = sum(1 for r in results if r["status"] == "WORKING_FALLBACK")
    zero_rows_count = sum(1 for r in results if r["status"] == "ZERO_ROWS")
    no_query_count = sum(1 for r in results if r["status"] == "NO_QUERY")
    unsupported_count = sum(1 for r in results if r["status"] == "UNSUPPORTED")
    error_count = sum(1 for r in results if r["status"] == "ERROR")

    overall_working = working_rule_count + working_fallback_count
    overall_success_rate = round((overall_working / total) * 100, 2) if total else 0.0
    rule_success_rate = round((working_rule_count / total) * 100, 2) if total else 0.0
    fallback_success_rate = round((working_fallback_count / total) * 100, 2) if total else 0.0
    avg_total_time = round(sum(r["total_time_ms"] for r in results) / total, 2) if total else 0.0

    category_breakdown = defaultdict(lambda: {"total": 0, "rule": 0, "fallback": 0})
    for r in results:
        category_breakdown[r["category"]]["total"] += 1
        if r["status"] == "WORKING_RULE":
            category_breakdown[r["category"]]["rule"] += 1
        elif r["status"] == "WORKING_FALLBACK":
            category_breakdown[r["category"]]["fallback"] += 1

    status_counter = Counter(r["status"] for r in results)

    report_lines = []
    report_lines.append("DBpedia QA Evaluation Report")
    report_lines.append("=" * 80)
    report_lines.append("")
    report_lines.append("Overall Summary")
    report_lines.append("-" * 80)
    report_lines.append(f"Total questions: {total}")
    report_lines.append(f"Working via rule-based: {working_rule_count}")
    report_lines.append(f"Working via LLM fallback: {working_fallback_count}")
    report_lines.append(f"Overall working: {overall_working}")
    report_lines.append(f"Zero rows: {zero_rows_count}")
    report_lines.append(f"No query: {no_query_count}")
    report_lines.append(f"Unsupported: {unsupported_count}")
    report_lines.append(f"Errors: {error_count}")
    report_lines.append(f"Rule-based success rate: {rule_success_rate}%")
    report_lines.append(f"Fallback success rate: {fallback_success_rate}%")
    report_lines.append(f"Overall success rate: {overall_success_rate}%")
    report_lines.append(f"Average total latency: {avg_total_time} ms")
    report_lines.append("")

    report_lines.append("Status Counts")
    report_lines.append("-" * 80)
    for status, count in sorted(status_counter.items()):
        report_lines.append(f"{status}: {count}")
    report_lines.append("")

    report_lines.append("Category Breakdown")
    report_lines.append("-" * 80)
    for category in sorted(category_breakdown.keys()):
        total_cat = category_breakdown[category]["total"]
        rule_cat = category_breakdown[category]["rule"]
        fallback_cat = category_breakdown[category]["fallback"]
        working_cat = rule_cat + fallback_cat
        rate_cat = round((working_cat / total_cat) * 100, 2) if total_cat else 0.0
        report_lines.append(
            f"{category}: {working_cat}/{total_cat} working "
            f"(rule={rule_cat}, fallback={fallback_cat}, success={rate_cat}%)"
        )
    report_lines.append("")

    report_lines.append("Fallback Questions")
    report_lines.append("-" * 80)
    if fallback_questions:
        report_lines.extend(fallback_questions)
    else:
        report_lines.append("None")
    report_lines.append("")

    report_lines.append("Detailed Results")
    report_lines.append("-" * 80)
    for r in results:
        report_lines.append(f"Question: {r['question']}")
        report_lines.append(f"Category: {r['category']}")
        report_lines.append(f"Query source: {r['query_source']}")
        report_lines.append(f"Status: {r['status']}")
        report_lines.append(f"Rows: {r['row_count']}")
        report_lines.append(f"Build time (ms): {r['build_time_ms']}")
        report_lines.append(f"Query time (ms): {r['query_time_ms']}")
        report_lines.append(f"Total time (ms): {r['total_time_ms']}")
        report_lines.append(f"Sample result: {r['sample_result']}")
        report_lines.append(f"Error / note: {r['error_message']}")
        report_lines.append("SPARQL Query:")
        report_lines.append(r["query"] if r["query"] else "[NO QUERY GENERATED]")
        report_lines.append("-" * 80)

    write_text_file(data_dir / "evaluation_report.txt", report_lines)

    print("\n" + "=" * 80)
    print("Finished.")
    print(f"Working via rule-based: {working_rule_count}")
    print(f"Working via fallback: {working_fallback_count}")
    print(f"Overall success rate: {overall_success_rate}%")
    print("Files updated in data/:")
    print("  - working_questions.txt")
    print("  - non_working_questions.txt")
    print("  - fallback_questions.txt")
    print("  - rule_based_questions.txt")
    print("  - evaluation_report.txt")
    print("  - evaluation_results.csv")
    print("=" * 80)


if __name__ == "__main__":
    main()