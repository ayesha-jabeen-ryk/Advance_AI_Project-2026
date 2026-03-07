def format_answer(result: dict) -> str:
    bindings = result.get("results", {}).get("bindings", [])

    if not bindings:
        return "No answer found."

    first_row = bindings[0]
    values = []

    for key, value in first_row.items():
        values.append(f"{key}: {value.get('value', '')}")

    return " | ".join(values)