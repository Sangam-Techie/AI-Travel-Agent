import asyncio
import re
import httpx
import time

async def fetch_url(url: str, delay: int):
    """Simulate fetching a URL with a delay."""
    print(f"Fetching {url}")
    await asyncio.sleep(delay)
    print(f"Got {url}!")
    return f"Data from {url}"

async def blocking_version():
    """Sequential - slow way."""
    start = time.time()

    result1 = await fetch_url("api.example.com/flights", 2)
    result2 = await fetch_url("api.example.com/weather", 2)
    result3 = await fetch_url("api.example.com/hotels", 2)

    elapsed = time.time() - start
    print(f"\nBlocking version took: {elapsed:.1f} seconds")
    return [result1, result2, result3]

async def async_version():
    """Concurrent - fast way."""
    start = time.time()

    results = await asyncio.gather(
        fetch_url("api.example.com/flights", 2),
        fetch_url("api.example.com/weather", 2),
        fetch_url("api.example.com/hotels", 2),
    )

    elapsed = time.time() - start
    print(f"\nAsync version took: {elapsed:.1f} seconds")
    return results

async def main():
    print("=== Running Blocking Version ===")
    await blocking_version()

    print("\n" + "="*40 + "\n")

    print("=== Running Async Version ===")
    await async_version()

if __name__ == "__main__":
    asyncio.run(main())