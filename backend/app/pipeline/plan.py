from typing import Any

from app.pipeline.base import PipelineStep
from app.schemas.api import PlanOutput
from app.services.llm import LLMClient


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

    async def execute(self, input_data: dict[str, Any], llm_client: LLMClient) -> PlanOutput:
        question: str = input_data["question"]
        history: list[dict] = input_data.get("history", [])
        schema_context: dict | None = input_data.get("schema_context")

        system_content = self.system_prompt
        if schema_context:
            system_content += (
                "\n\nAvailable database schema:\n"
                + "\n".join(
                    f"- {table}: {', '.join(cols)}"
                    for table, cols in schema_context.items()
                )
            )

        if input_data.get("_last_error"):
            system_content += (
                f"\n\nYour previous response had a validation error: {input_data['_last_error']}"
                "\nPlease correct your output."
            )

        messages: list[dict] = [{"role": "system", "content": system_content}]
        messages.extend(history)
        messages.append({"role": "user", "content": question})

        return await llm_client.chat_json(messages, PlanOutput)
