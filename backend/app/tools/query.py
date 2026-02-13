from typing import Any

from app.tools.base import Tool


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
        raise NotImplementedError
