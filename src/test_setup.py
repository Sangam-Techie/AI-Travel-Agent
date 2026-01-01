import sys
import httpx
from dotenv import load_dotenv
import os

def test_setup():
    print("Testing environment setup...\n")

    print(f"Python version: {sys.version.split()[0]}")

    try:
        import fastapi
        import uvicorn
        print(f"FastAPI version: {fastapi.__version__}")
    except ImportError as e:
        print(f"FastAPI import failed: {e}")
        return False

    load_dotenv()
    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key and groq_key != "your_groq_api_key_here":
        print(f"GROQ_API_KEY found (ends with: ...{groq_key[-4:]})")
    else:
        print("GROQ_API_KEY not set or still placeholder")

    print("\n Setup complete! You're ready to build.")
    return True

if __name__ == "__main__":
    test_setup()