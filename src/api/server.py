from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict
import uuid
from contextlib import asynccontextmanager


from src.api.models import ChatRequest, ChatResponse, HealthResponse, ConversationHistory
from src.agents.travel_agent import create_travel_agent
from src.agents.base_agent import AgentLoop
import logging
from datetime import datetime
from fastapi.responses import RedirectResponse




# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)




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

from src.api.config import settings
#Create FastAPI app
app = FastAPI(
    title= settings.app_name,
    description="An intelligent travel assistant powered by LLMs and real-time APIs",
    version=settings.app_version,
    debug=settings.debug,
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


@app.get("/", include_in_schema=False)
async def docs_redirect():
    return RedirectResponse(url="/docs")



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
    return {
        "active_sessions": len(sessions),
        "session_ids": list(sessions.keys())
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
