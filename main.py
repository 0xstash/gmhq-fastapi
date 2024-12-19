from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
import uuid

app = FastAPI()


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = str(uuid.uuid4())


class ChatResponse(BaseModel):
    message: str
    conversation_id: str


@app.post("/api/chat")
async def chat(request: ChatRequest) -> ChatResponse:
    conversation_id = (
        request.conversation_id if request.conversation_id else str(uuid.uuid4())
    )

    # Simply echo back the message
    return ChatResponse(message=request.message, conversation_id=conversation_id)


@app.get("/")
async def root():
    return {"message": "Welcome to the GMHQ Jungle"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, port=8000)
