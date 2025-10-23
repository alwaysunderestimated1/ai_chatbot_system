from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.security import OAuth2PasswordRequestForm
from app.limiter import limiter
from app.models.user import UserCreate, UserResponse, UserInDB, Token, RefreshRequest
from app.services.auth_service import (
    hash_password, verify_password,
    create_access_token, create_refresh_token,
    decode_token, get_current_user,
)
from app.database.mongodb import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=201)
@limiter.limit("10/minute")
async def register(request: Request, body: UserCreate):
    db = get_db()
    if await db.users.find_one({"$or": [{"username": body.username}, {"email": body.email}]}):
        raise HTTPException(status_code=409, detail="Username or email already exists.")
    user = UserInDB(
        username=body.username,
        email=body.email,
        hashed_password=hash_password(body.password),
    )
    await db.users.insert_one(user.model_dump())
    return UserResponse(**user.model_dump())


@router.post("/token", response_model=Token)
@limiter.limit("10/minute")
async def login(request: Request, form: OAuth2PasswordRequestForm = Depends()):
    db = get_db()
    doc = await db.users.find_one({"username": form.username})
    if not doc or not verify_password(form.password, doc["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid username or password.")
    user = UserInDB(**doc)
    if not user.is_active:
        raise HTTPException(status_code=403, detail="User account is inactive.")
    return Token(
        access_token=create_access_token(user.user_id, user.username),
        refresh_token=create_refresh_token(user.user_id),
    )


@router.post("/refresh", response_model=Token)
@limiter.limit("20/minute")
async def refresh(request: Request, body: RefreshRequest):
    payload = decode_token(body.refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type.")
    user_id = payload.get("sub")
    db = get_db()
    doc = await db.users.find_one({"user_id": user_id})
    if not doc:
        raise HTTPException(status_code=401, detail="User not found.")
    user = UserInDB(**doc)
    if not user.is_active:
        raise HTTPException(status_code=403, detail="User account is inactive.")
    return Token(
        access_token=create_access_token(user.user_id, user.username),
        refresh_token=create_refresh_token(user.user_id),
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: UserInDB = Depends(get_current_user)):
    return UserResponse(**current_user.model_dump())
