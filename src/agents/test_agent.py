import asyncio
from src.agents.base_agent import AgentLoop


#Define mock tools
async def mock_search_flights(origin: str, destination: str) -> dict:
    """Mock flight search - returns fake data."""
    await asyncio.sleep(0.5) #simiulate API delay
    return {
        "flights": [
            {
                "airline": "Air Mock",
                "price": 450,
                "departure": "10:00 AM",
                "duration": "7h 30m"
            },
            {
                "airline": "Mock Airways",
                "price": 520,
                "departure": "2:00 PM",
                "duration": "7h 15m"
            }
        ],
        "origin": origin,
        "destination": destination
    }

async def mock_get_weather(city: str) -> dict:
    """Mock weather - returns fake data."""
    await asyncio.sleep(0.5)
    return {
        "city": city,
        "temperature": 18,
        "condition": "Partly Cloudy",
        "humidity": 65
    }

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_flights",
            "description": "Search for flights between two cities",
            "parameters": {
                "type": "object",
                "properties":{
                    "origin":{
                        "type": "string",
                        "description": "Origin city or airport code"
                    },
                    "destination":{
                        "type": "string",
                        "description": "Destination city or airport code"
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
            "description": "Get current weather for a city",
            "parameters": {
                "type": "object",
                "properties":{
                    "city":{
                        "type": "string",
                        "description": "City name"
                    }
                },
                "required": ["city"]
            }
        }
    }
]

#Map tool names to functions
TOOL_FUNCTIONS = {
    "search_flights": mock_search_flights,
    "get_weather": mock_get_weather
}

# System prompt
SYSTEM_PROMPT = """You are a helpful travel assistant.

You have access to tools to search for flights and get weather information.
Use these tools to help the users plan their trips.

When providing flight information, be specific about prices and times.
When providing weather, mention temperature and conditions.

Be friendly and concise."""

async def test_agent():
    """Test the agent with various queries."""

    # Create agent
    agent = AgentLoop(
        system_prompt=SYSTEM_PROMPT,
        tools=TOOLS,
        tool_functions=TOOL_FUNCTIONS
    )

    print("="*60)
    print("TESTING AGENT LOOP")
    print("-"*60)

    #Test 1: Simple flight search
    print("\n"+"="*60)
    print("TEST 1: Simple flight search")
    print("="*60)
    response = await agent.run("Find me flights from NYC to Paris")
    print(f"\nFinal Response: \n{response}\n")

    #Reset for next test
    agent.reset()

    #Test 2: Multi-tool request
    print("\n"+"="*60)
    print("TEST 2: Multi-tool request")
    print("="*60)
    response = await agent.run(
        "I'm going to London. Show me flights from Boston and tell me the weather there."
    )
    print(f"\nFinal Response:\n{response}\n")

    #Reset for next test
    agent.reset()

    #Test 3: No tools needed
    print("\n"+"="*60)
    print("TEST 3: No tools needed")
    print("="*60)
    response = await agent.run("What documents do I need to travel to Europe?")
    print(f"\nFinal Response:\n{response}\n")


if __name__ == "__main__":
    asyncio.run(test_agent())