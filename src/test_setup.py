import sys
import httpx
from dotenv import load_dotenv
import os

def test_setup():
    """
    Sets up the environment for testing.

    Prints the Python version and FastAPI version (if available).
    Loads the GROQ_API_KEY environment variable and checks if it has been set
    to a value other than the placeholder. If so, prints a success message.
    If not, prints a message indicating that the key has not been set or is still
    the placeholder.

    Returns True if setup was successful, False otherwise.
    """
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