from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel


class PipelineStep(ABC):
    """Abstract base class for pipeline steps with structured output and retry logic."""

    name: str
    input_schema: type[BaseModel]
    output_schema: type[BaseModel]
    system_prompt: str
    max_retries: int = 10

    @abstractmethod
    async def execute(self, input_data: Any) -> Any:
        """Execute the pipeline step and return validated output."""
        ...

    def validate_output(self, raw: dict) -> BaseModel:
        """Parse raw LLM output against the output schema. Raises ValidationError on failure."""
        return self.output_schema.model_validate(raw)
