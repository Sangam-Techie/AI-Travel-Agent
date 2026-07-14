from datetime import datetime
from src.agents.base_agent import AgentLoop
from src.tools.travel_tools import TravelTools
from src.api.config import settings


# Tool definitions for the LLM
TRAVEL_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_airports",
            "description": (
                "Resolve a city or airport name into IATA airport codes. Use this before "
                "search_flights whenever you're not 100% sure of the exact 3-letter code, or "
                "when a city has multiple airports (e.g. London, New York, Tokyo)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {
                        "type": "string",
                        "description": "City or airport name, e.g. 'London', 'Charles de Gaulle'",
                    }
                },
                "required": ["keyword"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_flights",
            "description": (
                "Search for available flights between two airports. Returns real flight data "
                "with prices, times, airlines, stops, and layovers. Cheapest and fastest options "
                "are flagged in the results."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "origin": {
                        "type": "string",
                        "description": "Origin IATA airport code (e.g. 'JFK')",
                    },
                    "destination": {
                        "type": "string",
                        "description": "Destination IATA airport code (e.g. 'CDG')",
                    },
                    "departure_date": {
                        "type": "string",
                        "description": (
                            "Departure date as YYYY-MM-DD. Ask the user if unspecified rather "
                            "than guessing far in the future."
                        ),
                    },
                    "return_date": {
                        "type": "string",
                        "description": "Return date as YYYY-MM-DD for round trips. Omit for one-way.",
                    },
                    "adults": {
                        "type": "integer",
                        "description": "Number of adult travelers. Defaults to 1.",
                    },
                    "travel_class": {
                        "type": "string",
                        "enum": ["ECONOMY", "PREMIUM_ECONOMY", "BUSINESS", "FIRST"],
                        "description": "Cabin class. Omit if the user has no preference.",
                    },
                    "nonstop_only": {
                        "type": "boolean",
                        "description": "Set true only if the user explicitly wants nonstop/direct flights.",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "How many offers to return, default 5.",
                    },
                },
                "required": ["origin", "destination"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": (
                "Get CURRENT weather conditions for a city. Use this only when the user is "
                "asking about weather right now/today, not for a future travel date."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "City name (e.g., 'Paris', 'London', 'Tokyo')",
                    }
                },
                "required": ["city"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather_forecast",
            "description": (
                "Get a weather FORECAST for a city, up to 5 days out. Use this whenever the "
                "user is planning travel for a future date, instead of get_weather."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "City name"},
                    "target_date": {
                        "type": "string",
                        "description": "YYYY-MM-DD date to forecast. Omit to get the full 5-day outlook.",
                    },
                },
                "required": ["city"],
            },
        },
    },
]


def _build_system_prompt() -> str:
    today = datetime.now()
    return f"""You are an expert travel assistant with access to real-time flight and weather data.

Today's date is {today:%Y-%m-%d} ({today:%A}). Use this to resolve relative dates like "next Friday" \
or "in two weeks", and never suggest or accept a departure date in the past.

Your capabilities:
- Look up IATA airport codes for cities (search_airports)
- Search real flights with current prices, stops, and layovers (search_flights)
- Check current weather (get_weather) or a forecast for a future travel date (get_weather_forecast)

Guidelines:
- Never guess an IATA airport code from memory if there's any ambiguity (multi-airport cities like \
London or New York, or unfamiliar cities). Call search_airports first.
- If the user hasn't given a specific date, ask for one before searching rather than silently \
defaulting — a guessed date is rarely what they actually want. If they clearly just want a general \
sense of options, you may proceed with a stated default (say what you assumed) instead of blocking.
- For weather tied to a future trip, use get_weather_forecast with the relevant date, not get_weather.
- Present flight options clearly: price, times, duration, number of stops, and layover airports if \
any. Flight results may include a "tags" field marking the cheapest and/or fastest option — call \
these out explicitly so the user can compare at a glance.
- Always mention when a search comes back empty and why (e.g. limited test-environment inventory), \
and suggest a concrete next step (a different date, or a major hub route) rather than a flat "no flights."
- Give at least two options when possible so the user has something to compare.
- If a tool returns an error, tell the user plainly what went wrong and what to try next — don't \
paper over it or pretend the search succeeded.
- Be concise but complete: a good response lets the user actually make a decision without a follow-up.

Be friendly, professional, and helpful!"""



def create_travel_agent() -> AgentLoop:
    """Create a travel agent with real API tools, wired to the app's configured limits."""
    tools_instance = TravelTools()

    tool_functions = {
        "search_flights": tools_instance.search_flights,
        "get_weather": tools_instance.get_weather,
        "get_weather_forecast": tools_instance.get_weather_forecast,
        "search_airports": tools_instance.search_airports,
    }

    return AgentLoop(
        system_prompt=_build_system_prompt(),
        tools=TRAVEL_TOOLS,
        tool_functions=tool_functions,
        max_iterations=settings.max_agent_iterations,
        temperature=settings.agent_temperature,
        max_tokens=settings.llm_max_tokens,
    )


# Test function
async def test_real_agent():
    """Test the agent with real APIs."""
    agent = create_travel_agent()

    print("=" * 60)
    print("TRAVEL AGENT WITH REAL APIs")
    print("=" * 60)

    query = input("What would you like to do? ")
    response = await agent.run(query)
    print(f"\nRESPONSE:\n{response}\n")

    agent.reset()


if __name__ == "__main__":
    import asyncio

    asyncio.run(test_real_agent())