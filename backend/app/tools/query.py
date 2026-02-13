from typing import Any

from sqlalchemy import text

from app.database import target_engine
from app.tools.base import Tool
from app.tools.sql_safety import validate_sql

MAX_ROWS = 1000


class QueryTool(Tool):
    """Executes a read-only SQL query against the target database.

    Safety: validates SQL is SELECT-only, uses read-only database user,
    enforces result size limits.
    """

    name = "query"
    description = "Executes a read-only SQL query against the target database."
    parameters = {
        "type": "object",
        "properties": {"sql": {"type": "string", "description": "SQL SELECT query to execute"}},
        "required": ["sql"],
    }

    async def execute(self, params: dict) -> Any:
        sql = validate_sql(params["sql"])

        async with target_engine.connect() as conn:
            result = await conn.execute(text(sql))
            columns = list(result.keys())
            rows = [list(row) for row in result.fetchmany(MAX_ROWS)]

        return {"columns": columns, "rows": rows, "row_count": len(rows)}
