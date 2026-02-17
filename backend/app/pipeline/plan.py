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
        "to explore.\n\n"
        "Set skip_explore to true ONLY if:\n"
        "- The conversation history already contains sufficient data to answer "
        "(e.g. reformatting a prior answer as a different chart type, filtering already-fetched data)\n"
        "- The question is purely conversational and requires no data at all "
        "(e.g. greetings, clarifications about a prior answer)\n"
        "Do NOT skip_explore for questions about what data exists, schema discovery, "
        "or any question that requires looking at the database — even metadata questions "
        "like 'what tables are there?' need exploration.\n"
        "When skip_explore is true, tables_to_explore can be empty.\n\n"
        "If the conversation history is empty (this is the first message), also generate "
        "a short 3-5 word conversation name summarizing the user's question in the "
        "conversation_name field. Otherwise, leave conversation_name as null."
    )

    async def execute(self, input_data: dict[str, Any], llm_client: LLMClient) -> PlanOutput:
        question: str = input_data["question"]
        history: list[dict] = input_data.get("history", [])
        schema_context: dict | None = input_data.get("schema_context")

        system_content = self.system_prompt
        if schema_context:
            lines = []
            for table, cols in schema_context.items():
                if isinstance(cols, (list, tuple)):
                    lines.append(f"- {table}: {', '.join(str(c) for c in cols)}")
                elif isinstance(cols, dict):
                    lines.append(f"- {table}: {', '.join(cols.keys())}")
                else:
                    lines.append(f"- {table}: {cols}")
            system_content += "\n\nAvailable database schema:\n" + "\n".join(lines)

        if input_data.get("_last_error"):
            system_content += (
                f"\n\nYour previous response had a validation error: {input_data['_last_error']}"
                "\nPlease correct your output."
            )

        messages: list[dict] = [{"role": "system", "content": system_content}]
        messages.extend(history)
        messages.append({"role": "user", "content": question})

        return await llm_client.chat_json(messages, PlanOutput)
