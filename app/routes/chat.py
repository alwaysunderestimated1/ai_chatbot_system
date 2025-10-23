from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from app.models.chat import ChatRequest, ChatResponse
from app.models.user import UserInDB
from app.services import chat_service
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/", response_model=ChatResponse)
async def send_message(
    request: ChatRequest,
    current_user: UserInDB = Depends(get_current_user),
):
    try:
        reply, history, usage = await chat_service.chat(
            session_id=request.session_id,
            user_message=request.message,
            system_prompt=request.system_prompt,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            use_rag=request.use_rag,
            use_tools=request.use_tools,
            user_id=current_user.user_id,
        )
        return ChatResponse(session_id=request.session_id, reply=reply, history=history, usage=usage)
    except ValueError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stream")
async def stream_message(
    request: ChatRequest,
    current_user: UserInDB = Depends(get_current_user),
):
    try:
        generator = await chat_service.stream_chat(
            session_id=request.session_id,
            user_message=request.message,
            system_prompt=request.system_prompt,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            use_rag=request.use_rag,
            user_id=current_user.user_id,
        )
        return StreamingResponse(generator, media_type="text/event-stream")
    except ValueError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{session_id}")
async def get_history(
    session_id: str,
    current_user: UserInDB = Depends(get_current_user),
):
    try:
        history = await chat_service.get_history(session_id, user_id=current_user.user_id)
        return {"session_id": session_id, "history": history}
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
