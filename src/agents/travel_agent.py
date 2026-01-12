from src.agents.base_agent import AgentLoop
from src.tools.travel_tools import TravelTools


# Tool definitions for LLM
TRAVEL_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_flights",
            "description": "Search for available flights between two cities. Returns real flight data with prices, times, and airlines.",
            "parameters": {
                "type": "object",
                "properties": {
                    "origin": {
                        "type": "string",
                        "description": "Origin city IATA airport code (e.g., 'NYC', 'JFK', 'SYD')"
                    },
                    "destination": {
                        "type": "string",
                        "description": "Destination city IATA airport code (e.g., 'PAR', 'CDG', 'LAX')"

                    }
                },
                "required": ["origin", "destination"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get current weather conditions for a city. Returns temperature, humidity, and weather description.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "City name (e.g., 'Paris', 'London', 'Tokyo')"
                    }
                },
                "required": ["city"]
            }
        }
    }
]

SYSTEM_PROMPT = """You are an expert travel assistant with access to real-time flight and weather data.

Your capabilities:
- Search for actual flights with current prices
- Check weather conditions for destinations
- Provide helpful travel advice

GuideLines:
- Always use tools to get current data rather than making assumptions
- Present flight options clearly with prices and times. provide options even though user may not give exact info like airport codes(provide at least two), cities.
- Mention weather in context of travel planning
- Be concise and informative
- If a tool returns an error, acknowledge it and offer alternatives

Be friendly, professional, and helpful!"""


def create_travel_agent() -> AgentLoop:
    """Create a travel agent with real API tools."""
    tools_instance = TravelTools()

    # Map tool names to actual async functions
    tool_functions = {
        "search_flights": tools_instance.search_flights,
        "get_weather": tools_instance.get_weather
    }

    return AgentLoop(
        system_prompt=SYSTEM_PROMPT,
        tools=TRAVEL_TOOLS,
        tool_functions=tool_functions
    )


# Test function
async def test_real_agent():
    """Test the agent with real APIs."""
    agent = create_travel_agent()

    print("="*60)
    print("TRAVEL AGENT WITH REAL APIs")
    print("="*60)

    # queries = [
    #     "I want to fly from Nepal to Australia next week. What are my options?",
    #     "What's the weather like in Nepal right now",
    #     "Find flights from LAX to Paris and tell me the weather there"
    # ]

    # for i, query in enumerate(queries, 1):
    #     print(f"\n{'='*60}")
    #     print(f"QUERY {i}: {query}")
    #     print("="*60)

    #     response = await agent.run(query)

    #     print(f"\nRESPONSE:\n{response}\n")

    #     #Reset for next query
    #     agent.reset()
    query = input("What would you like to do? ")
    response = await agent.run(query)
    print(f"\nRESPONSE:\n{response}\n")
    # with open("response.txt", "w") as f:
    #     f.write(response)

    #Reset for next query
    agent.reset()


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_real_agent())