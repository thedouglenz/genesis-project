from typing import Any

from app.pipeline.base import PipelineStep
from app.schemas.api import AnswerOutput
from app.services.llm import LLMClient


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

    async def execute(self, input_data: Any, llm_client: LLMClient) -> AnswerOutput:
        question = input_data["question"]
        plan = input_data["plan"]
        exploration = input_data["exploration"]

        answer_type = plan["expected_answer_type"]

        format_instructions = "Always include a clear text_answer."
        if answer_type == "chart":
            chart_type = plan.get("suggested_chart_type", "bar")
            format_instructions += (
                f" Include chart_data with type '{chart_type}'. "
                "Provide a title, x_axis label, y_axis label, and data points."
            )
        elif answer_type == "dataset":
            format_instructions += (
                " Include table_data with columns and rows representing the dataset."
            )

        messages = [
            {
                "role": "system",
                "content": (
                    f"{self.system_prompt}\n\n"
                    f"Format instructions: {format_instructions}"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Question: {question}\n\n"
                    f"Plan: {plan}\n\n"
                    f"Exploration notes: {exploration.get('exploration_notes', '')}\n\n"
                    f"Raw data: {exploration.get('raw_data', '')}"
                ),
            },
        ]

        return await llm_client.chat_json(messages, AnswerOutput)
