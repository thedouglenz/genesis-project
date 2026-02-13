from typing import Any

from app.tools.base import Tool


class ListTablesTool(Tool):
    """Returns all available tables in the target database."""

    name = "list_tables"
    description = "Returns all available tables in the target database."
    parameters: dict = {}

    async def execute(self, params: dict) -> Any:
        raise NotImplementedError
