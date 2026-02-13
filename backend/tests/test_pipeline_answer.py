from unittest.mock import AsyncMock, patch

import pytest

from app.pipeline.answer import AnswerStep
from app.schemas.api import (
    AnswerOutput,
    ChartData,
    ChartDataPoint,
    TableData,
)


@pytest.fixture
def answer_step():
    step = AnswerStep()
    return step


def _scalar_input():
    return {
        "question": "How many users signed up last month?",
        "plan": {
            "reasoning": "Simple count query",
            "query_strategy": "SELECT COUNT(*) FROM users WHERE created_at > ...",
            "expected_answer_type": "scalar",
            "suggested_chart_type": None,
            "tables_to_explore": ["users"],
        },
        "exploration": {
            "raw_data": [{"count": 142}],
            "exploration_notes": "Found 142 users signed up in January.",
            "queries_executed": [
                {"sql": "SELECT COUNT(*) FROM users", "result_summary": "142"}
            ],
            "schema_context": {},
        },
    }


def _chart_input():
    return {
        "question": "Show revenue by industry",
        "plan": {
            "reasoning": "Group by industry and sum revenue",
            "query_strategy": "SELECT industry, SUM(revenue) FROM companies GROUP BY industry",
            "expected_answer_type": "chart",
            "suggested_chart_type": "bar",
            "tables_to_explore": ["companies"],
        },
        "exploration": {
            "raw_data": [
                {"industry": "Tech", "revenue": 5000000},
                {"industry": "Finance", "revenue": 3000000},
                {"industry": "Healthcare", "revenue": 2000000},
            ],
            "exploration_notes": "Revenue breakdown across 3 industries.",
            "queries_executed": [
                {
                    "sql": "SELECT industry, SUM(revenue) FROM companies GROUP BY industry",
                    "result_summary": "3 rows",
                }
            ],
            "schema_context": {},
        },
    }


def _dataset_input():
    return {
        "question": "List all departments and their headcounts",
        "plan": {
            "reasoning": "Show tabular department data",
            "query_strategy": "SELECT department, COUNT(*) FROM employees GROUP BY department",
            "expected_answer_type": "dataset",
            "suggested_chart_type": None,
            "tables_to_explore": ["employees"],
        },
        "exploration": {
            "raw_data": [
                {"department": "Engineering", "headcount": 50},
                {"department": "Sales", "headcount": 30},
            ],
            "exploration_notes": "2 departments found.",
            "queries_executed": [
                {
                    "sql": "SELECT department, COUNT(*) FROM employees GROUP BY department",
                    "result_summary": "2 rows",
                }
            ],
            "schema_context": {},
        },
    }


@pytest.mark.asyncio
async def test_answer_step_scalar(answer_step):
    fake_answer = AnswerOutput(
        text_answer="142 users signed up last month.",
        table_data=None,
        chart_data=None,
    )

    with patch.object(
        answer_step.llm_client, "chat_json", new_callable=AsyncMock, return_value=fake_answer
    ) as mock_chat:
        result = await answer_step.execute(_scalar_input())

    assert isinstance(result, AnswerOutput)
    assert result.text_answer == "142 users signed up last month."
    assert result.table_data is None
    assert result.chart_data is None
    mock_chat.assert_awaited_once()

    # Verify the messages passed to chat_json
    call_args = mock_chat.call_args
    messages = call_args[0][0]
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    assert "How many users signed up" in messages[1]["content"]


@pytest.mark.asyncio
async def test_answer_step_chart(answer_step):
    fake_answer = AnswerOutput(
        text_answer="Revenue is highest in Tech at $5M.",
        chart_data=ChartData(
            type="bar",
            title="Revenue by Industry",
            x_axis="Industry",
            y_axis="Revenue ($)",
            data=[
                ChartDataPoint(label="Tech", value=5000000),
                ChartDataPoint(label="Finance", value=3000000),
                ChartDataPoint(label="Healthcare", value=2000000),
            ],
        ),
    )

    with patch.object(
        answer_step.llm_client, "chat_json", new_callable=AsyncMock, return_value=fake_answer
    ) as mock_chat:
        result = await answer_step.execute(_chart_input())

    assert isinstance(result, AnswerOutput)
    assert result.text_answer == "Revenue is highest in Tech at $5M."
    assert result.chart_data is not None
    assert result.chart_data.type == "bar"
    assert len(result.chart_data.data) == 3
    assert result.table_data is None
    mock_chat.assert_awaited_once()

    # Verify chart format instructions were included in system prompt
    messages = mock_chat.call_args[0][0]
    system_content = messages[0]["content"]
    assert "chart_data" in system_content
    assert "bar" in system_content


@pytest.mark.asyncio
async def test_answer_step_dataset(answer_step):
    fake_answer = AnswerOutput(
        text_answer="Here are the departments and headcounts.",
        table_data=TableData(
            columns=["Department", "Headcount"],
            rows=[["Engineering", 50], ["Sales", 30]],
        ),
    )

    with patch.object(
        answer_step.llm_client, "chat_json", new_callable=AsyncMock, return_value=fake_answer
    ) as mock_chat:
        result = await answer_step.execute(_dataset_input())

    assert isinstance(result, AnswerOutput)
    assert result.text_answer == "Here are the departments and headcounts."
    assert result.table_data is not None
    assert result.table_data.columns == ["Department", "Headcount"]
    assert len(result.table_data.rows) == 2
    assert result.chart_data is None
    mock_chat.assert_awaited_once()

    # Verify dataset format instructions were included in system prompt
    messages = mock_chat.call_args[0][0]
    system_content = messages[0]["content"]
    assert "table_data" in system_content
