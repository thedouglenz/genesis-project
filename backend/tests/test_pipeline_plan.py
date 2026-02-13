import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from app.pipeline.plan import PlanStep
from app.schemas.api import PlanOutput
from app.services.llm import LLMClient


@pytest.fixture
def llm():
    return LLMClient()


@pytest.fixture
def plan_step():
    return PlanStep()


def _fake_response(content: str):
    message = MagicMock()
    message.content = content
    choice = MagicMock()
    choice.message = message
    response = MagicMock()
    response.choices = [choice]
    return response


@pytest.mark.asyncio
async def test_plan_step_scalar(plan_step, llm):
    plan_json = json.dumps(
        {
            "reasoning": "Need to count rows in companies table",
            "query_strategy": "SELECT COUNT(*) FROM companies",
            "expected_answer_type": "scalar",
            "suggested_chart_type": None,
            "tables_to_explore": ["companies"],
        }
    )
    fake = _fake_response(plan_json)

    with patch("app.services.llm.litellm.acompletion", new_callable=AsyncMock, return_value=fake):
        result = await plan_step.execute(
            {"question": "How many companies are in the dataset?"}, llm
        )

    assert isinstance(result, PlanOutput)
    assert result.expected_answer_type == "scalar"
    assert len(result.tables_to_explore) > 0
    assert "companies" in result.tables_to_explore


@pytest.mark.asyncio
async def test_plan_step_chart(plan_step, llm):
    plan_json = json.dumps(
        {
            "reasoning": "Need ARR grouped by industry for a bar chart",
            "query_strategy": "SELECT industry, SUM(arr) FROM companies GROUP BY industry",
            "expected_answer_type": "chart",
            "suggested_chart_type": "bar",
            "tables_to_explore": ["companies"],
        }
    )
    fake = _fake_response(plan_json)

    with patch("app.services.llm.litellm.acompletion", new_callable=AsyncMock, return_value=fake):
        result = await plan_step.execute(
            {"question": "Show me ARR by industry as a bar chart"}, llm
        )

    assert isinstance(result, PlanOutput)
    assert result.expected_answer_type == "chart"
    assert result.suggested_chart_type == "bar"


@pytest.mark.asyncio
async def test_plan_step_with_schema_context(plan_step, llm):
    plan_json = json.dumps(
        {
            "reasoning": "Count companies using known schema",
            "query_strategy": "SELECT COUNT(*) FROM companies",
            "expected_answer_type": "scalar",
            "suggested_chart_type": None,
            "tables_to_explore": ["companies"],
        }
    )
    fake = _fake_response(plan_json)

    with patch("app.services.llm.litellm.acompletion", new_callable=AsyncMock, return_value=fake) as mock_comp:
        result = await plan_step.execute(
            {
                "question": "How many companies?",
                "schema_context": {"companies": ["id", "name", "industry"]},
            },
            llm,
        )

    assert isinstance(result, PlanOutput)
    # Verify schema context was included in the system prompt
    call_messages = mock_comp.call_args.kwargs["messages"]
    system_msg = call_messages[0]["content"]
    assert "companies" in system_msg
    assert "industry" in system_msg


@pytest.mark.asyncio
async def test_plan_step_with_history(plan_step, llm):
    plan_json = json.dumps(
        {
            "reasoning": "Follow-up: break down by industry",
            "query_strategy": "SELECT industry, COUNT(*) FROM companies GROUP BY industry",
            "expected_answer_type": "dataset",
            "suggested_chart_type": None,
            "tables_to_explore": ["companies"],
        }
    )
    fake = _fake_response(plan_json)

    with patch("app.services.llm.litellm.acompletion", new_callable=AsyncMock, return_value=fake) as mock_comp:
        result = await plan_step.execute(
            {
                "question": "Break that down by industry",
                "history": [
                    {"role": "user", "content": "How many companies?"},
                    {"role": "assistant", "content": "There are 150 companies."},
                ],
            },
            llm,
        )

    assert isinstance(result, PlanOutput)
    # Verify history was included in messages
    call_messages = mock_comp.call_args.kwargs["messages"]
    assert call_messages[1]["role"] == "user"
    assert call_messages[1]["content"] == "How many companies?"


@pytest.mark.asyncio
async def test_execute_with_retry_succeeds_on_second_attempt(plan_step, llm):
    bad_json = '{"reasoning": "oops"}'  # Missing required fields
    good_json = json.dumps(
        {
            "reasoning": "Count companies",
            "query_strategy": "SELECT COUNT(*) FROM companies",
            "expected_answer_type": "scalar",
            "suggested_chart_type": None,
            "tables_to_explore": ["companies"],
        }
    )

    fake_bad = _fake_response(bad_json)
    fake_good = _fake_response(good_json)

    with patch(
        "app.services.llm.litellm.acompletion",
        new_callable=AsyncMock,
        side_effect=[fake_bad, fake_good],
    ):
        result = await plan_step.execute_with_retry(
            {"question": "How many companies?"}, llm
        )

    assert isinstance(result, PlanOutput)
    assert result.expected_answer_type == "scalar"


@pytest.mark.asyncio
async def test_execute_with_retry_exhausts_retries(plan_step, llm):
    bad_json = '{"reasoning": "oops"}'
    fake_bad = _fake_response(bad_json)

    with patch(
        "app.services.llm.litellm.acompletion",
        new_callable=AsyncMock,
        return_value=fake_bad,
    ):
        with pytest.raises(ValidationError):
            await plan_step.execute_with_retry(
                {"question": "How many companies?"}, llm
            )
