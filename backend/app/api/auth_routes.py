from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import (
    create_access_token,
    get_current_user,
    hash_password,
    sha256_hex,
    verify_password,
)
from ..db import get_session
from ..models import User
from ..schemas import TokenResponse, UserInfo, UserLogin, UserRegister

auth_router = APIRouter(prefix="/auth", tags=["auth"])


@auth_router.post("/register", response_model=UserInfo, status_code=status.HTTP_201_CREATED)
async def register(
    body: UserRegister,
    session: AsyncSession = Depends(get_session),
) -> UserInfo:
    existing = await session.execute(
        select(User).where((User.username == body.username) | (User.email == body.email))
    )
    if existing.scalars().first() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username or email already exists",
        )

    user = User(
        username=body.username,
        email=body.email,
        hashed_password=hash_password(body.password),
    )
    session.add(user)
    await session.flush()
    await session.commit()

    return UserInfo(
        id=user.id,
        username=user.username,
        email=user.email,
        created_at=user.created_at,
    )


@auth_router.post("/login", response_model=TokenResponse)
async def login(
    body: UserLogin,
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    result = await session.execute(
        select(User).where(User.username == body.username)
    )
    user = result.scalars().first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    password_matches = verify_password(body.password, user.hashed_password)
    if not password_matches:
        legacy_password = sha256_hex(body.password)
        password_matches = verify_password(legacy_password, user.hashed_password)

    if not password_matches:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    token, expires_in = create_access_token(user.id, user.username)
    return TokenResponse(
        access_token=token,
        expires_in=expires_in,
        user=UserInfo(
            id=user.id,
            username=user.username,
            email=user.email,
            created_at=user.created_at,
        ),
    )


@auth_router.get("/me", response_model=UserInfo)
async def me(current_user: User = Depends(get_current_user)) -> UserInfo:
    return UserInfo(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        created_at=current_user.created_at,
    )
