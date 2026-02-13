from typing import Any

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
        raise NotImplementedError
