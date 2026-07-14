import os
import asyncio
import httpx
from dotenv import load_dotenv
from typing import Any, List, Dict, Optional

load_dotenv()

class LLMClient:
    """Simple client for Groq API"""

    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY not found in environment variables")

        self.base_url = "https://api.groq.com/openai/v1"
        self.model = "llama-3.3-70b-versatile"

    async def _post_with_retry(self, payload: Dict, retries: int = 2) -> Dict:
        """POST to the chat completions endpoint with backoff on 429/5xx."""
        last_response = None
        for attempt in range(retries + 1):
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                    timeout=30.0
                )

            if response.status_code == 200:
                return response.json()

            last_response = response
            if (response.status_code == 429 or response.status_code >= 500) and attempt < retries:
                await asyncio.sleep(1.5 * (attempt + 1))
                continue

            print(f"API Error {response.status_code}: {response.text}")
            response.raise_for_status()

        # Should be unreachable, but keeps control flow explicit
        last_response.raise_for_status()

    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 1500,
    ) -> str:
        """Send messages to LLM and get response.

        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Creativity (0.0 = focused, 2.0 = creative)
            max_tokens: Cap on generated tokens

        Returns:
            The assistant's response text
        """
        data = await self._post_with_retry({
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        })
        return data["choices"][0]["message"]["content"]

    async def chat_with_tools(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict]] = None,
        temperature: float = 0.7,
        max_tokens: int = 1500,
    ) -> Dict[str, Any]:
        """
        Send messages with tool definitions to LLM.

        Args:
            messages: Conversation history
            tools: Available tool definitions
            temperature: Creativity level
            max_tokens: Cap on generated tokens

        Returns:
            Full response including tool calls if any
        """
        request_body = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if tools:
            request_body["tools"] = tools
            request_body["tool_choice"] = "auto"

        return await self._post_with_retry(request_body)


async def test_tool_calling():
    """Test that the LLM can decide to call tools."""
    client = LLMClient()

    tools = [{
        "type": "function",
        "function":{
            "name": "get_weather",
            "description": "Get weather for a city",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "City name"
                    }
                },
                "required": ["city"]
            }
        }
    }

    ]

    messages = [
        {
            "role": "system",
            "content": "You are a helpful assistant with access to tools."
        },
        {
            "role": "user",
            "content": "What's the weather in Paris?"
        }
    ]
    print("Testing tool calling...\n")
    print("User: What's the weather in Paris?\n")

    response = await client.chat_with_tools(messages, tools)

    message = response["choices"][0]["message"]

    if message.get("tool_calls"):
        tool_call = message["tool_calls"][0]
        print(f"LLM decided to call tool: {tool_call['function']['name']}")
        print(f"Arguments: {tool_call['function']['arguments']}")
    else:
        print(f"LLM responded without tools: {message['content']}")

async def test_llm():
    """Test that we can talk to the LLM."""
    client = LLMClient()

    print("Testing LLM connection...\n")

    messages = [
        {
            "role": "system",
            "content": "You are a helpful assistant that responds concisely."      
        },
        {
            "role": "user",
            "content": "Say hello and tell me you're working!"
        }
    ]
    response = await client.chat(messages)
    print(f"LLM Response: {response}\n")
    print("LLM connection working!")

if __name__ == "__main__":
    import asyncio
    # asyncio.run(test_llm())
    asyncio.run(test_tool_calling())