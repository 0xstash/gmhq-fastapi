from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
import uuid
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI()


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None


class ChatResponse(BaseModel):
    message: str
    conversation_id: str


@app.post("/api/chat")
async def chat(request: ChatRequest) -> ChatResponse:
    # Generate a new conversation ID if none provided
    conversation_id = request.conversation_id or str(uuid.uuid4())

    # For now, just echo back the message
    return ChatResponse(
        message=f"Received: {request.message}", conversation_id=conversation_id
    )


@app.get("/")
async def root():
    return {"message": "Welcome to the Chat API"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, port=8000)
