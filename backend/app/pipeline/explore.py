from typing import Any

from app.pipeline.base import PipelineStep
from app.schemas.api import ExploreOutput


class ExploreStep(PipelineStep):
    """Step 2: Execute the plan by calling tools in an agentic loop.

    This is the agentic tool-call loop step. The LLM calls tools iteratively
    (list_tables, show_schema, sample_data, query) until it determines it has
    enough data to answer the user's question.
    """

    name = "explore"
    output_schema = ExploreOutput
    system_prompt = (
        "You are a data exploration agent. Execute the plan by calling the available "
        "tools. You may call tools multiple times. Gather all data needed to answer "
        "the user's question."
    )

    async def execute(self, input_data: Any) -> ExploreOutput:
        raise NotImplementedError
