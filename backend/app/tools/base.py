from abc import ABC, abstractmethod
from typing import Any


class Tool(ABC):
    """Abstract base class for tools the LLM can invoke during exploration."""

    name: str
    description: str
    parameters: dict

    @abstractmethod
    async def execute(self, params: dict) -> Any:
        """Execute the tool with the given parameters and return a result."""
        ...
