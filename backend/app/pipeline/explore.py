import json
from typing import Any

from app.pipeline.base import PipelineStep
from app.schemas.api import ExploreOutput, PlanOutput
from app.services.llm import LLMClient
from app.tools.base import Tool

MAX_ITERATIONS = 20


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

    async def execute(
        self, input_data: dict[str, Any], llm_client: LLMClient
    ) -> ExploreOutput:
        plan: dict = input_data["plan"]
        available_tools: list[Tool] = input_data["available_tools"]

        tool_map = {t.name: t for t in available_tools}
        tool_defs = [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                },
            }
            for t in available_tools
        ]

        plan_obj = PlanOutput.model_validate(plan) if isinstance(plan, dict) else plan

        system_content = (
            f"{self.system_prompt}\n\n"
            f"Plan reasoning: {plan_obj.reasoning}\n"
            f"Query strategy: {plan_obj.query_strategy}\n"
            f"Tables to explore: {', '.join(plan_obj.tables_to_explore)}"
        )

        messages: list[dict] = [{"role": "system", "content": system_content}]
        messages.append(
            {"role": "user", "content": "Execute the plan. Call tools to gather the data needed."}
        )

        for _ in range(MAX_ITERATIONS):
            response = await llm_client.chat(messages, tools=tool_defs)
            assistant_msg = response.choices[0].message

            if not assistant_msg.tool_calls:
                # LLM is done exploring — append its final message
                messages.append({"role": "assistant", "content": assistant_msg.content or ""})
                break

            # Append the assistant message with tool calls
            messages.append(
                {
                    "role": "assistant",
                    "content": assistant_msg.content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in assistant_msg.tool_calls
                    ],
                }
            )

            # Execute each tool call and append results
            for tc in assistant_msg.tool_calls:
                tool = tool_map.get(tc.function.name)
                if tool is None:
                    result = {"error": f"Unknown tool: {tc.function.name}"}
                else:
                    try:
                        params = json.loads(tc.function.arguments)
                        result = await tool.execute(params)
                    except Exception as e:
                        result = {"error": str(e)}

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps(result, default=str),
                    }
                )

        # Ask the LLM to summarize the exploration
        messages.append(
            {
                "role": "user",
                "content": (
                    "Summarize the data exploration you just performed. "
                    "Include all queries executed, the raw data gathered, "
                    "exploration notes, and the schema context discovered."
                ),
            }
        )
        return await llm_client.chat_json(messages, ExploreOutput, tools=tool_defs)
