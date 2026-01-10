from pydantic import BaseModel, Field
from typing import List, Dict, Any



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


class Message(BaseModel):
    """A single message in a conversation."""
    role: str = Field(..., description="Message role: system, user, assistant, or tool")
    content: str|None = Field(None, description="Message content")

    class Config:
        json_schema_extra = {
            "example": {
                "role": "user",
                "content": "Find flights to paris"
            }
        }

    
class ConversationHistory(BaseModel):
    """Full conversation history for a session."""
    session_id: str
    messages: List[Dict[str, Any]]
    message_count: int

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "abc123",
                "messages": [
                    {"role": "user", "content": "Hello"},
                    {"role": "assistant", "content": "Hi! How can I help?"}
                ],
                "message_count": 2
            }
        }
