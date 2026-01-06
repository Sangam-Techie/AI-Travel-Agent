import os
import httpx
from typing import Dict
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()


class TravelTools:
    """Real travel API integrations."""

    def __init__(self):
        # Amadeus credentials
        self.amadeus_key = os.getenv("AMADEUS_API_KEY")
        self.amadeus_secret = os.getenv("AMADEUS_API_SECRET")

        #OpenWeather key
        self.weather_key = os.getenv("OPENWEATHER_API_KEY")

        # Amadeus token (will be fetched on first use)
        self._amadeus_token: str|None = None

    async def _get_amadeus_token(self) -> str:
        """
        Get OAuth token from Amadeus.

        Amadeus uses OAuth2, so we need to exchange credentials for a token.
        Token is cached and reused until it expires.
        """
        if self._amadeus_token:
            return self._amadeus_token

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://test.api.amadeus.com/v1/security/oauth2/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.amadeus_key,
                    "client_secret": self.amadeus_secret
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )

            if response.status_code != 200:
                error_detail = response.text
                print(f"API Error {response.status_code}: {error_detail}")
                response.raise_for_status()

            data = response.json()
            self._amadeus_token = data["access_token"]

        return self._amadeus_token

    async def search_flights(self, origin: str, destination: str, departure_date: str|None = None, max_results: int = 3) -> Dict:
        """
        Search for flights using Amadeus API.

        Args:
        origin: IATA airport code (e.g., 'JFK', 'NYC')
        destination: IATA airport code (e.g., 'CDG', 'PAR')
        departure_date: Date in YYYY-MM-DD format (defaults to 7 days from now)
        max results: Maximun number of flights to return

        Returns:
        Dict with flight information
        """
        # Default to 7 days from now if no date provided
        if not departure_date:
            future_date = datetime.now() + timedelta(days=7)
            departure_date = future_date.strftime("%Y-%m-%d")

        try:
            token = await self._get_amadeus_token()

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://test.api.amadeus.com/v2/shopping/flight-offers",
                    params={
                        "originLocationCode": origin.upper(),
                        "destinationLocationCode": destination.upper(),
                        "departureDate": departure_date,
                        "adults": 1,
                        "max": max_results
                    },
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=15.0
                )

                if response.status_code != 200:
                    error_detail = response.text
                    print(f"API Error {response.status_code}: {error_detail}")
                    
                data = response.json()

                # Parse and simplify the response
                flights = []
                for offer in data.get("data", [])[:max_results]:
                    # Amadeus returns complex nested data - let's simplify it
                    first_segment = offer["itineraries"][0]["segments"][0]

                    flight = {
                        "price": f"${offer['price']['total']} {offer['price']['currency']}",
                        "airline": first_segment["carrierCode"],
                        "flight_number": f"{first_segment['carrierCode']}{first_segment['number']}",
                        "departure": {
                            "time": first_segment["departure"]["at"],
                            "airport": first_segment["departure"]["iataCode"]
                                                    },
                                                    "arrival": {
                        "time": first_segment["arrival"]["at"],
                        "airport": first_segment["arrival"]["iataCode"]
                    },
                    "duration": offer["itineraries"][0]["duration"]
                    
                    }
                    flights.append(flight)

                return {
                    "success": True,
                    "origin": origin.upper(),
                    "destination": destination.upper(),
                    "flights": flights,
                    "count": len(flights)
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "An error occurred while searching flights."
            }
        
    async def get_weather(self, city: str) -> Dict:
        """
        Get current weather for a city using OpenweatherMap API.

        Args:
            city: City name (e.g., 'Paris', 'New York')

        Returns:
            Dict with weather information
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.openweathermap.org/data/2.5/weather",
                    params={
                        "q": city,
                        "appid": self.weather_key,
                        "units": "metric" #Celsius
                    },
                    timeout=10.0
                )

                if response.status_code != 200:
                    error_detail = response.text
                    print(f"API Error {response.status_code}: {error_detail}")
                    response.raise_for_status()

                data = response.json()

                return {
                    "success": True,
                    "city": data["name"],
                    "country": data["sys"]["country"],
                    "temperature": data["main"]["temp"],
                    "feels_like": data["main"]["feels_like"],
                    "humidity": data["main"]["humidity"],
                    "condition": data["weather"][0]["main"],
                    "description": data["weather"][0]["description"],
                    "wind_speed": data["wind"]["speed"],
                }
        
        except httpx.HTTPStatusError as e:
            return {
                "success": False,
                "error": f"API error: {e.response.status_code}",
                "message": f"Could not fetch weather for {city}. Check city name."
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "An error occurred while fetching weather"
            }

# Test the tools
async def test_travel_tools():
    """Test both real APIs."""
    tools = TravelTools()

    print("="*60)
    print("TESTING REAL TRAVEL APIs")
    print("="*60)

    # Test 1: Flight search
    print("\nTest 1: Searching flights NYC to Paris...")
    flights = await tools.search_flights("NYC", "P")

    if flights["success"]:
        print(f"Found {flights['count']} flights")
        for i, flight in enumerate(flights["flights"], 1):
            print(f"\n Flight {i}:")
            print(f"   {flight['airline']} {flight['flight_number']}")
            print(f"   Price: {flight['price']}")
            print(f"   Departure: {flight['departure']['time']}")
    else:
        print(f" Error: {flights['message']}")

    # Test 2: Weather
    print("\n" + "-"*60)
    print("\nTest 2: Getting weather for Paris...")
    weather = await tools.get_weather("Paris")

    if weather["success"]:
        print(f"Weather in {weather['city'], {weather['country']}}")
        print(f"   Temperature: {weather['temperature']}°C (feels like {weather['feels_like']}°C)")
        print(f"   Condition: {weather['description']}")
        print(f"   Humidity: {weather['humidity']}%")
    else:
        print(f" Error: {weather['message']}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_travel_tools())