import pytest
from unittest.mock import AsyncMock

from app.pipeline.answer import AnswerStep
from app.schemas.api import AnswerOutput


@pytest.mark.asyncio
async def test_answer_step_with_exploration():
    """Answer step works normally when exploration data is provided."""
    mock_llm = AsyncMock()
    mock_llm.chat_json = AsyncMock(return_value=AnswerOutput(
        text_answer="42 companies", table_data=None, chart_data=None
    ))

    step = AnswerStep()
    result = await step.execute(
        {
            "question": "How many companies?",
            "plan": {"expected_answer_type": "scalar", "reasoning": "count"},
            "exploration": {"exploration_notes": "Found 42", "raw_data": [{"count": 42}]},
            "history": [],
        },
        mock_llm,
    )

    assert result.text_answer == "42 companies"
    # Should NOT include history in messages (exploration path)
    call_args = mock_llm.chat_json.call_args
    messages = call_args[0][0]
    assert len(messages) == 2  # system + user


@pytest.mark.asyncio
async def test_answer_step_without_exploration():
    """Answer step uses conversation history when exploration is None."""
    mock_llm = AsyncMock()
    mock_llm.chat_json = AsyncMock(return_value=AnswerOutput(
        text_answer="Here is the pie chart.", table_data=None, chart_data=None
    ))

    step = AnswerStep()
    result = await step.execute(
        {
            "question": "Show that as a pie chart",
            "plan": {"expected_answer_type": "chart", "suggested_chart_type": "pie", "reasoning": "reformat"},
            "exploration": None,
            "history": [
                {"role": "user", "content": "How many companies per industry?"},
                {"role": "assistant", "content": "Construction: 34, Legal Tech: 31..."},
            ],
        },
        mock_llm,
    )

    assert result.text_answer == "Here is the pie chart."
    # Should include history in messages (no-exploration path)
    call_args = mock_llm.chat_json.call_args
    messages = call_args[0][0]
    # system + history (2 messages) + user = 4
    assert len(messages) == 4
