import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.pipeline.explore import ExploreStep
from app.schemas.api import ExploreOutput
from app.services.llm import LLMClient
from app.tools.base import Tool


class FakeListTablesTool(Tool):
    name = "list_tables"
    description = "Returns all available tables."
    parameters: dict = {}

    async def execute(self, params: dict):
        return {"tables": ["companies", "orders"]}


class FakeShowSchemaTool(Tool):
    name = "show_schema"
    description = "Returns schema for a table."
    parameters = {
        "type": "object",
        "properties": {"table": {"type": "string"}},
        "required": ["table"],
    }

    async def execute(self, params: dict):
        return {
            "table": params["table"],
            "columns": [
                {"column_name": "id", "data_type": "integer"},
                {"column_name": "name", "data_type": "varchar"},
            ],
        }


@pytest.fixture
def llm():
    return LLMClient()


@pytest.fixture
def explore_step():
    return ExploreStep()


@pytest.fixture
def tools():
    return [FakeListTablesTool(), FakeShowSchemaTool()]


def _make_tool_call(call_id, name, arguments):
    tc = MagicMock()
    tc.id = call_id
    tc.function.name = name
    tc.function.arguments = json.dumps(arguments)
    return tc


def _assistant_response(content=None, tool_calls=None):
    message = MagicMock()
    message.content = content
    message.tool_calls = tool_calls
    choice = MagicMock()
    choice.message = message
    response = MagicMock()
    response.choices = [choice]
    return response


@pytest.mark.asyncio
async def test_explore_step(explore_step, llm, tools):
    """Test the agentic loop: LLM calls list_tables, then finishes, then summarizes."""
    # Turn 1: LLM calls list_tables tool
    tc = _make_tool_call("call_1", "list_tables", {})
    resp_with_tool = _assistant_response(content=None, tool_calls=[tc])

    # Turn 2: LLM decides it's done (no tool calls)
    resp_done = _assistant_response(content="I have gathered the data.")

    # Turn 3: Summary as ExploreOutput JSON
    summary_json = json.dumps({
        "queries_executed": [
            {"sql": "list_tables()", "result_summary": "Found companies, orders"}
        ],
        "raw_data": {"tables": ["companies", "orders"]},
        "exploration_notes": "Listed available tables",
        "schema_context": {"companies": ["id", "name"], "orders": ["id", "total"]},
    })
    resp_summary = _assistant_response(content=summary_json)

    with patch(
        "app.services.llm.litellm.acompletion",
        new_callable=AsyncMock,
        side_effect=[resp_with_tool, resp_done, resp_summary],
    ):
        result = await explore_step.execute(
            {
                "plan": {
                    "reasoning": "Need to explore available tables",
                    "query_strategy": "List tables then query",
                    "expected_answer_type": "scalar",
                    "suggested_chart_type": None,
                    "tables_to_explore": ["companies"],
                },
                "available_tools": tools,
            },
            llm,
        )

    assert isinstance(result, ExploreOutput)
    assert len(result.queries_executed) > 0
    assert result.raw_data is not None
    assert result.schema_context is not None


@pytest.mark.asyncio
async def test_explore_step_multiple_tool_calls(explore_step, llm, tools):
    """Test that multiple tool calls in a single response are all executed."""
    tc1 = _make_tool_call("call_1", "list_tables", {})
    tc2 = _make_tool_call("call_2", "show_schema", {"table": "companies"})
    resp_multi = _assistant_response(content=None, tool_calls=[tc1, tc2])

    resp_done = _assistant_response(content="Done exploring.")

    summary_json = json.dumps({
        "queries_executed": [
            {"sql": "list_tables()", "result_summary": "Found tables"},
            {"sql": "show_schema(companies)", "result_summary": "Got schema"},
        ],
        "raw_data": {"tables": ["companies"]},
        "exploration_notes": "Listed tables and schema",
        "schema_context": {"companies": ["id", "name"]},
    })
    resp_summary = _assistant_response(content=summary_json)

    with patch(
        "app.services.llm.litellm.acompletion",
        new_callable=AsyncMock,
        side_effect=[resp_multi, resp_done, resp_summary],
    ):
        result = await explore_step.execute(
            {
                "plan": {
                    "reasoning": "Explore tables and schema",
                    "query_strategy": "List then describe",
                    "expected_answer_type": "dataset",
                    "suggested_chart_type": None,
                    "tables_to_explore": ["companies"],
                },
                "available_tools": tools,
            },
            llm,
        )

    assert isinstance(result, ExploreOutput)
    assert len(result.queries_executed) == 2


@pytest.mark.asyncio
async def test_explore_step_unknown_tool(explore_step, llm, tools):
    """Test that calling an unknown tool returns an error without crashing."""
    tc = _make_tool_call("call_1", "nonexistent_tool", {})
    resp_with_bad_tool = _assistant_response(content=None, tool_calls=[tc])

    resp_done = _assistant_response(content="Done.")

    summary_json = json.dumps({
        "queries_executed": [],
        "raw_data": {},
        "exploration_notes": "Tool not found",
        "schema_context": {},
    })
    resp_summary = _assistant_response(content=summary_json)

    with patch(
        "app.services.llm.litellm.acompletion",
        new_callable=AsyncMock,
        side_effect=[resp_with_bad_tool, resp_done, resp_summary],
    ):
        result = await explore_step.execute(
            {
                "plan": {
                    "reasoning": "Test unknown tool",
                    "query_strategy": "Try bad tool",
                    "expected_answer_type": "scalar",
                    "suggested_chart_type": None,
                    "tables_to_explore": ["companies"],
                },
                "available_tools": tools,
            },
            llm,
        )

    assert isinstance(result, ExploreOutput)
