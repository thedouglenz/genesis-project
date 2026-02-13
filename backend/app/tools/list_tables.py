from typing import Any

from sqlalchemy import text

from app.database import target_engine
from app.tools.base import Tool


class ListTablesTool(Tool):
    """Returns all available tables in the target database."""

    name = "list_tables"
    description = "Returns all available tables in the target database."
    parameters: dict = {}

    async def execute(self, params: dict) -> Any:
        async with target_engine.connect() as conn:
            result = await conn.execute(
                text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
            )
            tables = [row[0] for row in result.fetchall()]
        return {"tables": tables}
