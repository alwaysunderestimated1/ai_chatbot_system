from fastapi import APIRouter, HTTPException, Depends, Query
from app.models.chat import SessionListResponse, SessionUpdate, Session
from app.models.user import UserInDB
from app.services import session_service
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("/", response_model=SessionListResponse)
async def list_sessions(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: UserInDB = Depends(get_current_user),
):
    return await session_service.list_sessions(
        user_id=current_user.user_id, page=page, page_size=page_size
    )


@router.get("/{session_id}", response_model=Session)
async def get_session(
    session_id: str,
    current_user: UserInDB = Depends(get_current_user),
):
    try:
        return await session_service.get_session(session_id, user_id=current_user.user_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/{session_id}", response_model=Session)
async def update_session(
    session_id: str,
    body: SessionUpdate,
    current_user: UserInDB = Depends(get_current_user),
):
    try:
        return await session_service.update_session(
            session_id=session_id,
            title=body.title,
            system_prompt=body.system_prompt,
            user_id=current_user.user_id,
        )
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{session_id}", status_code=204)
async def delete_session(
    session_id: str,
    current_user: UserInDB = Depends(get_current_user),
):
    try:
        await session_service.delete_session(session_id, user_id=current_user.user_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
