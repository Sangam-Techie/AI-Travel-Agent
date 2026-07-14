from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Optional
import uuid
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path


from src.api.models import ChatRequest, ChatResponse, HealthResponse, ConversationHistory
from src.agents.travel_agent import create_travel_agent
from src.agents.base_agent import AgentLoop
from src.api.config import settings
import logging
from fastapi.responses import FileResponse

# src/api/server.py -> src/api -> src -> project root
STATIC_DIR = Path(__file__).resolve().parent.parent.parent / "static"


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


sessions: Dict[str, AgentLoop] = {}
_cleanup_task: Optional[asyncio.Task] = None


def _purge_expired_sessions() -> int:
    """Remove sessions that have been idle longer than session_timeout_minutes."""
    cutoff = datetime.now() - timedelta(minutes=settings.session_timeout_minutes)
    expired = [sid for sid, agent in sessions.items() if agent.last_active < cutoff]
    for sid in expired:
        del sessions[sid]
    if expired:
        logger.info(f"Purged {len(expired)} expired session(s).")
    return len(expired)


async def _cleanup_loop():
    """Periodically purge idle sessions so memory doesn't grow unbounded."""
    while True:
        await asyncio.sleep(settings.session_cleanup_interval_minutes * 60)
        try:
            _purge_expired_sessions()
        except Exception as e:
            logger.error(f"Session cleanup error: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup and shutdown context manager for the Travel Agent API.

    Starts a background task that periodically expires idle sessions, and
    clears the session cache on shutdown.
    """
    global _cleanup_task
    # Startup
    print(" Starting Travel Agent API...")
    print(" API docs available at: http://localhost:8000/docs")
    _cleanup_task = asyncio.create_task(_cleanup_loop())
    yield
    # Shutdown
    print(" Shutting down Travel Agent API...")
    if _cleanup_task:
        _cleanup_task.cancel()
    sessions.clear()


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="An intelligent travel assistant powered by LLMs and real-time APIs",
    version=settings.app_version,
    debug=settings.debug,
    lifespan=lifespan
)


# Add CORS middleware (allows frontend apps to call this API).
# Configure ALLOWED_ORIGINS in .env for production instead of the "*" default.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_or_create_agent(session_id: str) -> AgentLoop:
    """
    Get or create an AgentLoop instance for a given session ID.

    If the session already exists, its last-active timestamp is refreshed.
    If it doesn't, expired sessions are purged first, and if the active-session
    cap is still reached, the least-recently-active session is evicted to make room.

    Args:
        session_id (str): Session ID to retrieve or create an AgentLoop instance for.

    Returns:
        AgentLoop: The AgentLoop instance for the given session ID.
    """
    if session_id in sessions:
        sessions[session_id].last_active = datetime.now()
        return sessions[session_id]

    _purge_expired_sessions()

    if len(sessions) >= settings.max_active_sessions:
        oldest_id = min(sessions, key=lambda sid: sessions[sid].last_active)
        del sessions[oldest_id]
        logger.warning(f"Max active sessions reached; evicted oldest session {oldest_id}.")

    sessions[session_id] = create_travel_agent()
    return sessions[session_id]


@app.get("/", include_in_schema=False)
async def serve_frontend():
    """Serve the chat UI. API docs remain available at /docs regardless."""
    return FileResponse(STATIC_DIR / "index.html")



@app.get("/health", response_model=HealthResponse, status_code=status.HTTP_200_OK)
async def health_check():
    """
    Health check endpoint.

    Returns the status of the API and the number of active sessions.
    """
    _purge_expired_sessions()
    return HealthResponse(
        status="healthy",
        message=f"API operational. Active sessions: {len(sessions)}/{settings.max_active_sessions}",
        version=settings.app_version
    )


@app.post("/chat", response_model=ChatResponse, status_code=status.HTTP_201_CREATED)
async def chat(request: ChatRequest):
    """
    Main chat endpoint - send a message to the travel agent.

    The agent maintains conversation history within a session.
    """
    # Generate session ID if not provided
    session_id = request.session_id or str(uuid.uuid4())

    logger.info(f"Chat request - Session: {session_id}, Message length: {len(request.message)}")

    try:
        
        # Get or create agent for this session
        agent = get_or_create_agent(session_id)

        start_time = datetime.now()
        # Run the agent
        response = await agent.run(request.message)
        duration = (datetime.now() - start_time).total_seconds()

        logger.info(f"Response generated - Session: {session_id}, Duration: {duration:.2f}s")

        return ChatResponse(
            response=response,
            session_id=session_id,
        )
    except Exception as e:
        # Log the error
        logger.error(f"Error in chat - Session: {session_id}, Error: {str(e)}", exc_info=True)

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
    _purge_expired_sessions()
    return {
        "active_sessions": len(sessions),
        "max_sessions": settings.max_active_sessions,
        "sessions": [
            {"session_id": sid, "last_active": agent.last_active.isoformat()}
            for sid, agent in sessions.items()
        ],
    }

@app.get("/history/{session_id}", response_model=ConversationHistory)
async def get_conversation_history(session_id: str):
    """
    Get the full conversation history for a session.

    This allows users to review what they've discussed with the agent.
    """
    if session_id not in sessions:
        raise HTTPException(
            status_code=404,
            detail=f"Session {session_id} not found"
        )

    agent = sessions[session_id]
    messages = agent.get_conversation_history()

    return ConversationHistory(
        session_id=session_id,
        messages=messages,
        message_count=len(messages)
    )

@app.get("/traces/{session_id}")
async def get_traces(session_id: str):
    """
    OBSERVABILITY ENDPOINT: Returns the raw traces of the agent's logic.
    This is a huge 'Hire Me' feature.
    """
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    agent = sessions[session_id]
    return {"traces": agent.get_traces()}