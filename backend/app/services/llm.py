import json

import litellm
from pydantic import BaseModel

from app.config import settings


class LLMClient:
    """Wrapper around LiteLLM for calling the LLM proxy."""

    def __init__(self):
        self.base_url = settings.LITELLM_PROXY_URL
        self.api_key = settings.LITELLM_API_KEY
        self.model = "openai/claude-sonnet-4-5"

    async def chat(self, messages: list[dict], tools=None, tool_choice=None, **kwargs):
        """Send a chat completion request. Returns the full response."""
        response = await litellm.acompletion(
            model=self.model,
            messages=messages,
            api_base=self.base_url,
            api_key=self.api_key,
            tools=tools,
            tool_choice=tool_choice,
            **kwargs,
        )
        return response

    async def chat_json(self, messages: list[dict], schema: type[BaseModel], **kwargs):
        """Chat expecting JSON output, parse into Pydantic model."""
        schema_instruction = (
            f"Respond with JSON matching this schema: {json.dumps(schema.model_json_schema())}"
        )
        enhanced_messages = list(messages)
        if enhanced_messages and enhanced_messages[0]["role"] == "system":
            enhanced_messages[0] = {
                **enhanced_messages[0],
                "content": enhanced_messages[0]["content"] + "\n\n" + schema_instruction,
            }
        else:
            enhanced_messages.insert(0, {"role": "system", "content": schema_instruction})

        response = await self.chat(enhanced_messages, **kwargs)
        content = response.choices[0].message.content

        # Handle markdown code blocks in LLM responses
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        return schema.model_validate_json(content.strip())
