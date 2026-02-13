from app.config import settings


class LLMClient:
    """Wrapper around LiteLLM for calling the LLM proxy."""

    def __init__(self):
        self.base_url = settings.LITELLM_PROXY_URL
        self.api_key = settings.LITELLM_API_KEY

    async def chat(self, messages: list[dict], **kwargs) -> dict:
        """Send a chat completion request to the LiteLLM proxy."""
        raise NotImplementedError
