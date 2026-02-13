from typing import Any

from sqlalchemy import text

from app.database import target_engine
from app.tools.base import Tool


class ShowSchemaTool(Tool):
    """Returns column names, types, and constraints for a given table."""

    name = "show_schema"
    description = "Returns column names, types, and constraints for a table."
    parameters = {
        "type": "object",
        "properties": {"table": {"type": "string", "description": "Table name"}},
        "required": ["table"],
    }

    async def execute(self, params: dict) -> Any:
        table = params["table"]
        async with target_engine.connect() as conn:
            result = await conn.execute(
                text(
                    "SELECT column_name, data_type, is_nullable "
                    "FROM information_schema.columns "
                    "WHERE table_name = :table AND table_schema = 'public'"
                ),
                {"table": table},
            )
            columns = [
                {"column_name": row[0], "data_type": row[1], "is_nullable": row[2]}
                for row in result.fetchall()
            ]
        return {"table": table, "columns": columns}
