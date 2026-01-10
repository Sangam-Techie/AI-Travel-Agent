import httpx
import asyncio


async def test_api():
    """Test the API endpoints."""
    base_url = "http://localhost:8000"

    async with httpx.AsyncClient() as client:
        print("="*60)
        print("TESTING TRAVEL AGENT API")
        print("="*60)

        #Test 1: Health check
        print("\n1. Testing health endpoint...")
        response = await client.get(f"{base_url}/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")

        # Test 2: Simple chat
        print("\n2. Testing chat endpoint...")
        chat_data = {
            "message": "Find me a flights from San Francisco to Tokyo"
        }
        response = await client.post(f"{base_url}/chat", json=chat_data, timeout=30.0)
        result = response.json()
        print(f"Status: {response.status_code}")
        print(f"Session ID: {result['session_id']}")
        print(f"Response preview: {result['response'][:200]}...")

        # Test 3: Conversation continuity
        print("\n3. Testing conversation continuity...")
        session_id = result['session_id']

        follow_up_data = {
            "message": "What about the weather there",
            "session_id": session_id
        }

        response = await client.post(f"{base_url}/chat", json=follow_up_data)
        result = response.json()
        print(f"Status: {response.status_code}")
        print(f"Response preview: {result['response'][:200]}...")


        # Test 4: List sessions
        print("\n4. Checking active sessions...")
        response = await client.get(f"{base_url}/sessions")
        sessions = response.json()
        print(f"Active sessions: {sessions['active_sessions']}")

        print("\n All tests passed!")



if __name__ == "__main__":
    asyncio.run(test_api())