from pydantic import BaseModel, Field
from typing import List, Dict



class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    message: str = Field(..., min_length=1, description="User's message to the agent")
    session_id: str|None = Field(None, description="Session ID for conversation continuity")


    class Config:
        json_schema_extra = {
            "example": {
                "message": "Find me flights from NYC to Paris",
                "session_id": "user123"
            }
        }

class ChatResponse(BaseModel):
    """Response model for chat endpoint."""
    response: str = Field(..., description="Agent's response")
    session_id: str = Field(..., description="Session ID for this conversation")

    class Config:
        json_schema_extra = {
            "example": {
                "response": "I found 3 flights from NYC to Paris",
                "session_id": "user123"
            }
        }


class HealthResponse(BaseModel):
    """Response model for health check."""
    status: str
    message: str
    version: str