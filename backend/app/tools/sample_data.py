import re
from typing import Any

from sqlalchemy import text

from app.database import target_engine
from app.tools.base import Tool

_VALID_TABLE_NAME = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


class SampleDataTool(Tool):
    """Returns sample rows to help the LLM understand data formats and value ranges."""

    name = "sample_data"
    description = "Returns sample rows from a table to understand data formats."
    parameters = {
        "type": "object",
        "properties": {
            "table": {"type": "string", "description": "Table name"},
            "limit": {"type": "integer", "description": "Number of rows to return", "default": 5},
        },
        "required": ["table"],
    }

    async def execute(self, params: dict) -> Any:
        table = params["table"]
        limit = params.get("limit", 5)

        if not _VALID_TABLE_NAME.match(table):
            raise ValueError(f"Invalid table name: {table}")

        async with target_engine.connect() as conn:
            check = await conn.execute(
                text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_name = :table AND table_schema = 'public'"
                ),
                {"table": table},
            )
            if not check.fetchone():
                raise ValueError(f"Table not found: {table}")

            result = await conn.execute(
                text(f"SELECT * FROM {table} LIMIT :limit"),
                {"limit": limit},
            )
            columns = list(result.keys())
            rows = [list(row) for row in result.fetchall()]

        return {"table": table, "columns": columns, "rows": rows}
