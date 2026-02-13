from typing import Any

from app.pipeline.base import PipelineStep
from app.schemas.api import PlanOutput


class PlanStep(PipelineStep):
    """Step 1: Analyze the user question and create an execution plan.

    Takes the user question, conversation history, and optional cached schema context.
    Produces a PlanOutput with reasoning, query strategy, expected answer type, and
    tables to explore.
    """

    name = "plan"
    output_schema = PlanOutput
    system_prompt = (
        "You are a data analysis planner. Given a user question about a dataset, "
        "reason about what data exploration is needed to answer it. Determine the "
        "expected answer format (scalar, dataset, or chart) and identify which tables "
        "to explore."
    )

    async def execute(self, input_data: Any) -> PlanOutput:
        raise NotImplementedError
