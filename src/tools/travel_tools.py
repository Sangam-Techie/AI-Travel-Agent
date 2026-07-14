import os
import re
import asyncio
import httpx
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()


def _parse_iso8601_duration_minutes(duration: str) -> int:
    """Parse an ISO 8601 duration like 'PT7H30M' into total minutes."""
    match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?", duration or "")
    if not match:
        return 0
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    return hours * 60 + minutes


def _price_value(price_str: str) -> float:
    """Extract a comparable float from a '$450.00 USD' style string."""
    try:
        return float(price_str.lstrip("$").split(" ")[0])
    except (ValueError, IndexError):
        return float("inf")


class TravelTools:
    """Real travel API integrations: Amadeus (flights + airport lookup) and OpenWeatherMap (current + forecast)."""

    AMADEUS_BASE = "https://test.api.amadeus.com"
    OPENWEATHER_BASE = "https://api.openweathermap.org/data/2.5"

    def __init__(self):
        self.amadeus_key = os.getenv("AMADEUS_API_KEY")
        self.amadeus_secret = os.getenv("AMADEUS_API_SECRET")
        self.weather_key = os.getenv("OPENWEATHER_API_KEY")

        self._amadeus_token: Optional[str] = None
        self._amadeus_token_expiry: Optional[datetime] = None
        self._token_lock = asyncio.Lock()

    # ---------------------------------------------------------------------
    # internal helpers
    # ---------------------------------------------------------------------

    async def _get_amadeus_token(self, force_refresh: bool = False) -> str:
        """Get (and cache/refresh) an OAuth token from Amadeus. Thread-safe."""
        async with self._token_lock:
            if (
                not force_refresh
                and self._amadeus_token
                and self._amadeus_token_expiry
                and datetime.now() < self._amadeus_token_expiry
            ):
                return self._amadeus_token

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.AMADEUS_BASE}/v1/security/oauth2/token",
                    data={
                        "grant_type": "client_credentials",
                        "client_id": self.amadeus_key,
                        "client_secret": self.amadeus_secret,
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    timeout=15.0,
                )
                response.raise_for_status()
                data = response.json()
                self._amadeus_token = data["access_token"]
                # refresh a minute early so we never hand out a token that expires mid-request
                self._amadeus_token_expiry = datetime.now() + timedelta(
                    seconds=data.get("expires_in", 1800) - 60
                )

            return self._amadeus_token

    async def _amadeus_get(self, path: str, params: Dict, retries: int = 2) -> httpx.Response:
        """GET against Amadeus with auto token-refresh-on-401 and backoff on 429/5xx."""
        response = None
        for attempt in range(retries + 1):
            token = await self._get_amadeus_token(force_refresh=(attempt > 0 and response is not None and response.status_code == 401))
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.AMADEUS_BASE}{path}",
                    params=params,
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=15.0,
                )

            if response.status_code == 200:
                return response

            if response.status_code == 401:
                # token was likely stale/revoked - loop again and force a fresh one
                continue

            if response.status_code == 429 or response.status_code >= 500:
                await asyncio.sleep(1.5 * (attempt + 1))
                continue

            return response  # a "real" 4xx (bad request, invalid airport code, etc.) - don't retry

        return response

    async def _weather_get(self, path: str, params: Dict, retries: int = 2) -> httpx.Response:
        """GET against OpenWeatherMap with backoff on 429/5xx."""
        response = None
        for attempt in range(retries + 1):
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.OPENWEATHER_BASE}{path}", params=params, timeout=10.0
                )
            if response.status_code == 200:
                return response
            if response.status_code == 429 or response.status_code >= 500:
                await asyncio.sleep(1.5 * (attempt + 1))
                continue
            return response
        return response

    # ---------------------------------------------------------------------
    # public tools
    # ---------------------------------------------------------------------

    async def search_airports(self, keyword: str) -> Dict:
        """
        Resolve a city or airport name into IATA codes.

        Args:
            keyword: City or airport name, e.g. 'London', 'New York', 'Charles de Gaulle'

        Returns:
            Dict with a list of matching airports/cities and their IATA codes.
        """
        try:
            response = await self._amadeus_get(
                "/v1/reference-data/locations",
                params={"subType": "AIRPORT,CITY", "keyword": keyword, "page[limit]": 8},
            )

            if response.status_code != 200:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}",
                    "message": f"Could not look up airports for '{keyword}': {response.text[:200]}",
                }

            data = response.json()
            results = []
            for loc in data.get("data", []):
                address = loc.get("address", {})
                results.append(
                    {
                        "name": loc.get("name"),
                        "iata_code": loc.get("iataCode"),
                        "type": loc.get("subType"),
                        "city": address.get("cityName"),
                        "country": address.get("countryName"),
                    }
                )

            return {
                "success": True,
                "query": keyword,
                "matches": results,
                "count": len(results),
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"An error occurred looking up '{keyword}'.",
            }

    async def search_flights(
        self,
        origin: str,
        destination: str,
        departure_date: Optional[str] = None,
        return_date: Optional[str] = None,
        adults: int = 1,
        travel_class: Optional[str] = None,
        nonstop_only: bool = False,
        max_results: int = 5,
    ) -> Dict:
        """
        Search for flights using the Amadeus flight-offers API.

        Args:
            origin: Origin IATA airport code (e.g. 'JFK')
            destination: Destination IATA airport code (e.g. 'CDG')
            departure_date: YYYY-MM-DD. Defaults to 7 days from today if omitted.
            return_date: YYYY-MM-DD for round trips. Omit for one-way.
            adults: Number of adult travelers.
            travel_class: ECONOMY, PREMIUM_ECONOMY, BUSINESS, or FIRST.
            nonstop_only: If True, only return nonstop itineraries.
            max_results: Max number of offers to return.

        Returns:
            Dict with flight offers including price, times, stops, and layovers.
            The cheapest and fastest options (if any results) are marked with a "tags" field.
        """
        if not departure_date:
            departure_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")

        try:
            dep_dt = datetime.strptime(departure_date, "%Y-%m-%d")
        except ValueError:
            return {
                "success": False,
                "error": "invalid_date",
                "message": f"'{departure_date}' isn't a valid YYYY-MM-DD date.",
            }

        if dep_dt.date() < datetime.now().date():
            return {
                "success": False,
                "error": "past_date",
                "message": f"{departure_date} is in the past. Please choose a future date.",
            }

        params = {
            "originLocationCode": origin.upper(),
            "destinationLocationCode": destination.upper(),
            "departureDate": departure_date,
            "adults": adults,
            "max": max_results,
        }
        if return_date:
            params["returnDate"] = return_date
        if travel_class:
            params["travelClass"] = travel_class.upper()
        if nonstop_only:
            params["nonStop"] = "true"

        try:
            response = await self._amadeus_get("/v2/shopping/flight-offers", params=params)

            if response.status_code != 200:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}",
                    "message": f"Flight search failed: {response.text[:300]}",
                }

            data = response.json()
            flights: List[Dict] = []

            for offer in data.get("data", [])[:max_results]:
                itinerary_out = offer["itineraries"][0]
                segments_out = itinerary_out["segments"]
                first_seg, last_seg = segments_out[0], segments_out[-1]

                flight = {
                    "price": f"${offer['price']['total']} {offer['price']['currency']}",
                    "airline": first_seg["carrierCode"],
                    "flight_number": f"{first_seg['carrierCode']}{first_seg['number']}",
                    "departure": {
                        "time": first_seg["departure"]["at"],
                        "airport": first_seg["departure"]["iataCode"],
                    },
                    "arrival": {
                        "time": last_seg["arrival"]["at"],
                        "airport": last_seg["arrival"]["iataCode"],
                    },
                    "duration": itinerary_out["duration"],
                    "stops": len(segments_out) - 1,
                    "layover_airports": [s["arrival"]["iataCode"] for s in segments_out[:-1]],
                }

                if len(offer["itineraries"]) > 1:
                    itinerary_ret = offer["itineraries"][1]
                    segments_ret = itinerary_ret["segments"]
                    r_first, r_last = segments_ret[0], segments_ret[-1]
                    flight["return"] = {
                        "departure": {
                            "time": r_first["departure"]["at"],
                            "airport": r_first["departure"]["iataCode"],
                        },
                        "arrival": {
                            "time": r_last["arrival"]["at"],
                            "airport": r_last["arrival"]["iataCode"],
                        },
                        "duration": itinerary_ret["duration"],
                        "stops": len(segments_ret) - 1,
                    }

                flights.append(flight)

            # Sort cheapest-first and tag the cheapest / fastest so the agent can call them out
            flights.sort(key=lambda f: _price_value(f["price"]))
            if flights:
                cheapest_idx = 0
                fastest_idx = min(
                    range(len(flights)),
                    key=lambda i: _parse_iso8601_duration_minutes(flights[i]["duration"]),
                )
                tag_map: Dict[int, List[str]] = {}
                tag_map.setdefault(cheapest_idx, []).append("cheapest")
                tag_map.setdefault(fastest_idx, []).append("fastest")
                for idx, tags in tag_map.items():
                    flights[idx]["tags"] = tags

            return {
                "success": True,
                "origin": origin.upper(),
                "destination": destination.upper(),
                "departure_date": departure_date,
                "return_date": return_date,
                "flights": flights,
                "count": len(flights),
                "note": (
                    None
                    if flights
                    else "No inventory found for this route/date in the Amadeus test environment — "
                    "try a major route (e.g. JFK-CDG) or a different date."
                ),
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "An error occurred while searching flights.",
            }

    async def get_weather(self, city: str) -> Dict:
        """
        Get CURRENT weather conditions for a city.

        Args:
            city: City name (e.g., 'Paris', 'New York')

        Returns:
            Dict with current weather information.
        """
        try:
            response = await self._weather_get(
                "/weather", params={"q": city, "appid": self.weather_key, "units": "metric"}
            )

            if response.status_code != 200:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}",
                    "message": f"Could not fetch weather for {city}. Check the city name.",
                }

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

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "An error occurred while fetching weather.",
            }

    async def get_weather_forecast(self, city: str, target_date: Optional[str] = None) -> Dict:
        """
        Get a weather forecast for a city, up to 5 days out.

        Args:
            city: City name.
            target_date: YYYY-MM-DD date to forecast for. If omitted, returns the full 5-day outlook.

        Returns:
            Dict with the forecast entry closest to the target date, or a 5-day daily summary.
        """
        try:
            response = await self._weather_get(
                "/forecast", params={"q": city, "appid": self.weather_key, "units": "metric"}
            )

            if response.status_code != 200:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}",
                    "message": f"Could not fetch forecast for {city}. Check the city name.",
                }

            data = response.json()
            entries = data.get("list", [])

            if target_date:
                try:
                    target = datetime.strptime(target_date, "%Y-%m-%d").date()
                except ValueError:
                    return {
                        "success": False,
                        "error": "invalid_date",
                        "message": f"'{target_date}' isn't a valid YYYY-MM-DD date.",
                    }

                same_day = [e for e in entries if datetime.fromtimestamp(e["dt"]).date() == target]
                if not same_day:
                    return {
                        "success": False,
                        "error": "out_of_range",
                        "message": f"{target_date} is beyond the 5-day forecast window for {city}. "
                        "OpenWeatherMap's free tier only forecasts ~5 days ahead.",
                    }

                # pick the entry closest to midday for a representative daytime reading
                best = min(same_day, key=lambda e: abs(datetime.fromtimestamp(e["dt"]).hour - 12))
                return {
                    "success": True,
                    "city": data["city"]["name"],
                    "date": target_date,
                    "temperature": best["main"]["temp"],
                    "feels_like": best["main"]["feels_like"],
                    "condition": best["weather"][0]["main"],
                    "description": best["weather"][0]["description"],
                    "humidity": best["main"]["humidity"],
                    "wind_speed": best["wind"]["speed"],
                }

            # no target date -> daily summary across the whole forecast window
            daily: Dict[str, List[Dict]] = {}
            for e in entries:
                day = datetime.fromtimestamp(e["dt"]).strftime("%Y-%m-%d")
                daily.setdefault(day, []).append(e)

            summary = []
            for day, day_entries in list(daily.items())[:5]:
                temps = [e["main"]["temp"] for e in day_entries]
                best = min(day_entries, key=lambda e: abs(datetime.fromtimestamp(e["dt"]).hour - 12))
                summary.append(
                    {
                        "date": day,
                        "low": round(min(temps), 1),
                        "high": round(max(temps), 1),
                        "condition": best["weather"][0]["main"],
                        "description": best["weather"][0]["description"],
                    }
                )

            return {"success": True, "city": data["city"]["name"], "forecast": summary}

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "An error occurred while fetching the forecast.",
            }


# ---------------------------------------------------------------------------
# Manual test harness
# ---------------------------------------------------------------------------
async def test_travel_tools():
    """Test the real APIs end to end."""
    tools = TravelTools()

    print("=" * 60)
    print("TESTING REAL TRAVEL APIs")
    print("=" * 60)

    print("\nTest 1: Resolving 'London' to airport codes...")
    airports = await tools.search_airports("London")
    if airports["success"]:
        for match in airports["matches"]:
            print(f"   {match['iata_code']} - {match['name']} ({match['type']})")
    else:
        print(f"   Error: {airports['message']}")

    print("\nTest 2: Searching flights JFK to CDG...")
    flights = await tools.search_flights("JFK", "CDG")
    if flights["success"]:
        print(f"Found {flights['count']} flights")
        for i, flight in enumerate(flights["flights"], 1):
            tags = f" [{', '.join(flight['tags'])}]" if "tags" in flight else ""
            print(f"\n Flight {i}{tags}:")
            print(f"   {flight['airline']} {flight['flight_number']} - {flight['stops']} stop(s)")
            print(f"   Price: {flight['price']}")
            print(f"   Departure: {flight['departure']['time']} -> Arrival: {flight['arrival']['time']}")
    else:
        print(f" Error: {flights.get('message')}")

    print("\n" + "-" * 60)
    print("\nTest 3: Current weather in Paris...")
    weather = await tools.get_weather("Paris")
    if weather["success"]:
        print(f"   {weather['temperature']}°C, {weather['description']}")
    else:
        print(f" Error: {weather['message']}")

    print("\nTest 4: 5-day forecast for Paris...")
    forecast = await tools.get_weather_forecast("Paris")
    if forecast["success"]:
        for day in forecast["forecast"]:
            print(f"   {day['date']}: {day['low']}-{day['high']}°C, {day['description']}")
    else:
        print(f" Error: {forecast['message']}")


if __name__ == "__main__":
    asyncio.run(test_travel_tools())