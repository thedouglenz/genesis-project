from typing import Any

from app.tools.base import Tool


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
        raise NotImplementedError
