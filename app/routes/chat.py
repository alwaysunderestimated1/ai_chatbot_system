from fastapi import APIRouter, HTTPException
from app.models.chat import ChatRequest, ChatResponse
from app.services import chat_service

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/", response_model=ChatResponse)
async def send_message(request: ChatRequest):
    try:
        reply, history = await chat_service.chat(
            session_id=request.session_id,
            user_message=request.message,
            system_prompt=request.system_prompt,
        )
        return ChatResponse(session_id=request.session_id, reply=reply, history=history)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{session_id}")
async def get_history(session_id: str):
    history = await chat_service.get_history(session_id)
    return {"session_id": session_id, "history": history}


@router.delete("/session/{session_id}")
async def clear_session(session_id: str):
    await chat_service.clear_session(session_id)
    return {"message": f"Session {session_id} cleared."}
