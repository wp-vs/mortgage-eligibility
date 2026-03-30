from pydantic import BaseModel


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    customer_id: int
    message: str


class ChatResponse(BaseModel):
    customer_id: int
    conversation_id: int
    message: str
    tool_calls: list[dict] | None = None
