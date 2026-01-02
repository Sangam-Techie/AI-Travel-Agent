import os
import httpx
from dotenv import load_dotenv
from typing import Any, List, Dict

load_dotenv()

class LLMClient:
    """Simple client for Groq API"""

    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY not found in environment variables")

        self.base_url = "https://api.groq.com/openai/v1"
        self.model = "openai/gpt-oss-120b"
    async def chat(self, messages: List[Dict[str, str]], temperature: float = 0.7) -> str:
        """Send messages to LLM and get response.

        Args:
            messages: List if message dicts with 'role' and 'content'
            temperature: Creativity (0.0 = focused, 2.0 = creative)

        Returns:
            The assistant's response text
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                },
                timeout=30.0
            )

            if response.status_code != 200:
                error_detail = response.text
                print(f"API Error {response.status_code}: {error_detail}")
                response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
    
    async def chat_with_tools(self, messages: List[Dict[str, str]], tools: List[Dict]|None = None, temperature: float = 0.7) -> Dict[str, Any]:
        """
        Send messages with tool definitions to LLM.

        Args:
            messages: Conversation history
            tools: Available tool definitions
            temperature: Creativity level
        
        Returns:
            Full response including tool calls if any
        """
        request_body = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature
        }

        if tools:
            request_body["tools"] = tools
            request_body["tool_choice"] = "auto"
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=request_body,
                timeout=30.0
            )

            if response.status_code != 200:
                error_detail = response.text
                print(f"API Error {response.status_code}: {error_detail}")
                response.raise_for_status()
            
            return response.json()


async def test_tool_calling():
    """Test that the LLM can decide to call tools."""
    client = LLMClient()

    tools = [{
        "type": "function",
        "function":{
            "name": "get_weather",
            "desscription": "Get weather for a city",
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

