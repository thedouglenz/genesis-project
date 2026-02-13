from typing import Any

from app.pipeline.base import PipelineStep
from app.schemas.api import AnswerOutput


class AnswerStep(PipelineStep):
    """Step 3: Format the explored data into a clear answer.

    Takes PlanOutput + ExploreOutput + the original question and produces an
    AnswerOutput with text, optional table, and optional chart data.
    """

    name = "answer"
    output_schema = AnswerOutput
    system_prompt = (
        "You are a data analyst. Format the explored data into a clear, well-presented "
        "answer. Choose the appropriate format (text, table, chart) based on the plan."
    )

    async def execute(self, input_data: Any) -> AnswerOutput:
        raise NotImplementedError
