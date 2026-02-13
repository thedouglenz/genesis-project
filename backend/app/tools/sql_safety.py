import re

DANGEROUS_KEYWORDS = [
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER",
    "TRUNCATE", "CREATE", "GRANT", "REVOKE",
]

_dangerous_pattern = re.compile(
    r"\b(" + "|".join(DANGEROUS_KEYWORDS) + r")\b",
    re.IGNORECASE,
)


def validate_sql(sql: str) -> str:
    cleaned = sql.strip()

    if not cleaned:
        raise ValueError("SQL query cannot be empty")

    if ";" in cleaned:
        raise ValueError("Multiple statements are not allowed")

    if not cleaned.upper().startswith("SELECT"):
        raise ValueError("Only SELECT queries are allowed")

    match = _dangerous_pattern.search(cleaned)
    if match:
        raise ValueError(f"Forbidden keyword: {match.group(0).upper()}")

    return cleaned
