from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict
import uuid
from contextlib import asynccontextmanager


from src.api.models import ChatRequest, ChatResponse, HealthResponse
from src.agents.travel_agent import create_travel_agent
from src.agents.base_agent import AgentLoop




sessions: Dict[str, AgentLoop] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup and shutdown context manager for the Travel Agent API.

    Prints a message on startup and shutdown, and clears the session cache on shutdown.
    """
    # Startup
    print(" Starting Travel Agent API...")
    print(" API docs available at: http://localhost:8000/docs")
    yield
    # Shutdown
    print(" Shutting down Travel Agent API...")
    sessions.clear()


#Create FastAPI app
app = FastAPI(
    title= "AI Travel Agent API",
    description="An intelligent travel assistant powered by LLMs and real-time APIs",
    version="1.0.0",
    lifespan=lifespan
)


# Add CORS middleware (allows frontend apps to call this API)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods= ["*"],
    allow_headers=["*"],

)


def get_or_create_agent(session_id: str) -> AgentLoop:
    """
    Get or create an AgentLoop instance for a given session ID.

    If the session ID does not exist in the session cache, create a new AgentLoop instance and add it to the cache.

    Args:
        session_id (str): Session ID to retrieve or create an AgentLoop instance for.

    Returns:
        AgentLoop: The AgentLoop instance for the given session ID.
    """
    if session_id not in sessions:
        sessions[session_id] = create_travel_agent()
    return sessions[session_id]



@app.get("/health", response_model=HealthResponse, status_code=status.HTTP_200_OK)
async def health_check():
    """
    Health check endpoint.

    Returns the status of the API, the number of active sessions, and the version of the API.
    """
    return HealthResponse(
        status="healthy",
        message=f"API operational. Active sessions: {len(sessions)}",
        version="1.0.0"
    )


@app.post("/chat", response_model=ChatResponse, status_code=status.HTTP_201_CREATED)
async def chat(request: ChatRequest):
    """
    Main chat endpoint - send a message to the travel agent.

    The agent maintains conversation history within a session.
    """
    try:
        # Generate session ID if not provided
        session_id = request.session_id or str(uuid.uuid4())

        # Get or create agent for this session
        agent = get_or_create_agent(session_id)

        # Run the agent
        response = await agent.run(request.message)

        return ChatResponse(
            response=response,
            session_id=session_id
        )
    except Exception as e:
        # Log the error
        print(f"Error in chat endpoint: {str(e)}")

        raise HTTPException(
            status_code=500,
            detail=f"An error occurred processing your request: {str(e)}"
        )


@app.post("/reset/{session_id}", status_code=status.HTTP_202_ACCEPTED)
async def reset_session(session_id: str):
    """

    Reset a conversation session.

    This clears the conversation history for the given session.
    """
    if session_id in sessions:
        sessions[session_id].reset()
        return {"message": f"Session {session_id} reset successfully."}
    else:
        raise HTTPException(
            status_code=404,
            detail=f"Session {session_id} not found"
        )


@app.delete("/session/{session_id}", status_code=status.HTTP_202_ACCEPTED)
async def delete_session(session_id: str):
    """

    Delete a conversation session.

    This removes the session completely from memory.
    """
    if session_id in sessions:
        del sessions[session_id]
        return {"message": f"Session {session_id} deleted successfully"}
    else:
        raise HTTPException(
            status_code=404,
            detail=f"Session {session_id} not found"
        )

@app.get("/sessions", status_code=status.HTTP_200_OK)
async def list_sessions():
    """
    List all active sessions (for debugging).

    In production, you'd want to secure this endpoint.
    """
    return {
        "active_sessions": len(sessions),
        "session_ids": list(sessions.keys())
    }