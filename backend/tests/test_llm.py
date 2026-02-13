from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import BaseModel

from app.services.llm import LLMClient


@pytest.fixture
def llm():
    return LLMClient()


def _fake_response(content="Hello", tool_calls=None):
    """Build a fake litellm response object."""
    message = MagicMock()
    message.content = content
    message.tool_calls = tool_calls

    choice = MagicMock()
    choice.message = message

    response = MagicMock()
    response.choices = [choice]
    return response


@pytest.mark.asyncio
async def test_llm_chat_basic(llm):
    fake = _fake_response(content="Hello")

    with patch("app.services.llm.litellm.acompletion", new_callable=AsyncMock, return_value=fake) as mock_completion:
        response = await llm.chat(
            messages=[{"role": "user", "content": "Say hello in one word"}]
        )

    assert response.choices[0].message.content == "Hello"
    mock_completion.assert_awaited_once()
    call_kwargs = mock_completion.call_args
    assert call_kwargs.kwargs["model"] == llm.model
    assert call_kwargs.kwargs["api_base"] == llm.base_url
    assert call_kwargs.kwargs["api_key"] == llm.api_key


@pytest.mark.asyncio
async def test_llm_chat_with_tools(llm):
    tool_call = MagicMock()
    tool_call.function.name = "get_weather"
    tool_call.function.arguments = '{"city": "Paris"}'
    fake = _fake_response(content=None, tool_calls=[tool_call])

    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get the weather for a city",
                "parameters": {
                    "type": "object",
                    "properties": {"city": {"type": "string"}},
                    "required": ["city"],
                },
            },
        }
    ]

    with patch("app.services.llm.litellm.acompletion", new_callable=AsyncMock, return_value=fake) as mock_completion:
        response = await llm.chat(
            messages=[{"role": "user", "content": "What is the weather in Paris?"}],
            tools=tools,
        )

    msg = response.choices[0].message
    assert msg.tool_calls is not None
    assert msg.tool_calls[0].function.name == "get_weather"
    call_kwargs = mock_completion.call_args.kwargs
    assert call_kwargs["tools"] == tools


class SimpleAnswer(BaseModel):
    answer: str
    confidence: float


@pytest.mark.asyncio
async def test_llm_chat_json(llm):
    fake = _fake_response(content='{"answer": "4", "confidence": 0.99}')

    with patch("app.services.llm.litellm.acompletion", new_callable=AsyncMock, return_value=fake):
        result = await llm.chat_json(
            messages=[{"role": "user", "content": "What is 2+2?"}],
            schema=SimpleAnswer,
        )

    assert isinstance(result, SimpleAnswer)
    assert result.answer == "4"
    assert result.confidence == 0.99


@pytest.mark.asyncio
async def test_llm_chat_json_handles_markdown_code_block(llm):
    fake = _fake_response(content='```json\n{"answer": "4", "confidence": 0.95}\n```')

    with patch("app.services.llm.litellm.acompletion", new_callable=AsyncMock, return_value=fake):
        result = await llm.chat_json(
            messages=[{"role": "user", "content": "What is 2+2?"}],
            schema=SimpleAnswer,
        )

    assert isinstance(result, SimpleAnswer)
    assert result.answer == "4"
    assert result.confidence == 0.95


@pytest.mark.asyncio
async def test_llm_chat_json_handles_bare_code_block(llm):
    fake = _fake_response(content='```\n{"answer": "4", "confidence": 0.8}\n```')

    with patch("app.services.llm.litellm.acompletion", new_callable=AsyncMock, return_value=fake):
        result = await llm.chat_json(
            messages=[{"role": "user", "content": "What is 2+2?"}],
            schema=SimpleAnswer,
        )

    assert isinstance(result, SimpleAnswer)
    assert result.answer == "4"
    assert result.confidence == 0.8
