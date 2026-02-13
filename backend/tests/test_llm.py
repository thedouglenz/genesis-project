import pytest
from pydantic import BaseModel

from app.services.llm import LLMClient


@pytest.fixture
def llm():
    return LLMClient()


@pytest.mark.asyncio
async def test_llm_chat_basic(llm):
    response = await llm.chat(
        messages=[{"role": "user", "content": "Say hello in one word"}]
    )
    content = response.choices[0].message.content
    assert content
    assert len(content) > 0


@pytest.mark.asyncio
async def test_llm_chat_with_tools(llm):
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
    response = await llm.chat(
        messages=[{"role": "user", "content": "What is the weather in Paris?"}],
        tools=tools,
    )
    msg = response.choices[0].message
    assert msg.content or msg.tool_calls


class SimpleAnswer(BaseModel):
    answer: str
    confidence: float


@pytest.mark.asyncio
async def test_llm_chat_json(llm):
    result = await llm.chat_json(
        messages=[{"role": "user", "content": "What is 2+2? Answer with the number and your confidence."}],
        schema=SimpleAnswer,
    )
    assert isinstance(result, SimpleAnswer)
    assert result.answer
    assert 0 <= result.confidence <= 1
