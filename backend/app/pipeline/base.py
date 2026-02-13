from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, ValidationError

from app.services.llm import LLMClient


class PipelineStep(ABC):
    """Abstract base class for pipeline steps with structured output and retry logic."""

    name: str
    input_schema: type[BaseModel]
    output_schema: type[BaseModel]
    system_prompt: str
    max_retries: int = 3

    @abstractmethod
    async def execute(self, input_data: Any, llm_client: LLMClient) -> BaseModel:
        """Execute the pipeline step and return validated output."""
        ...

    async def execute_with_retry(self, input_data: Any, llm_client: LLMClient) -> BaseModel:
        """Execute with retry on validation errors."""
        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                return await self.execute(input_data, llm_client)
            except (ValidationError, ValueError) as exc:
                last_error = exc
                if attempt == self.max_retries:
                    break
                # Append error context so next attempt can correct
                input_data = {**input_data, "_last_error": str(exc)}
        raise last_error  # type: ignore[misc]

    def validate_output(self, raw: dict) -> BaseModel:
        """Parse raw LLM output against the output schema. Raises ValidationError on failure."""
        return self.output_schema.model_validate(raw)
