"""
Authentication for Project Raven.
Local PostgreSQL auth — no Supabase dependency.
Dev mode: accepts any token and resolves user from DB.
"""
import os
import logging
from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from pydantic import BaseModel

from db.database import AsyncSessionLocal, get_db
from db.models import User, Organisation

logger = logging.getLogger(__name__)

bearer_scheme = HTTPBearer(auto_error=False)


class UserProfile(BaseModel):
    id: UUID
    email: str
    full_name: Optional[str] = None
    role: str
    org_id: Optional[UUID] = None
    org_name: Optional[str] = None


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> UserProfile:
    """
    Resolves the current authenticated user.
    Dev mode: token is treated as user ID.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    async with AsyncSessionLocal() as db:
        try:
            # Dev mode: token is the user ID (UUID)
            user_result = await db.execute(
                select(User).where(User.id == token)
            )
            user = user_result.scalar_one_or_none()

            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found",
                )

            org_name = None
            if user.org_id:
                org_result = await db.execute(
                    select(Organisation).where(Organisation.id == user.org_id)
                )
                org = org_result.scalar_one_or_none()
                if org:
                    org_name = org.name

            return UserProfile(
                id=user.id,
                email=user.email,
                full_name=user.full_name,
                role=user.role,
                org_id=user.org_id,
                org_name=org_name,
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Auth lookup failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Auth lookup failed",
            )


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> Optional[UserProfile]:
    """Same as get_current_user but returns None instead of raising 401."""
    if credentials is None:
        return None
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None


def require_super_admin(current_user: UserProfile = Depends(get_current_user)) -> UserProfile:
    if current_user.role != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin access required",
        )
    return current_user


def require_admin(current_user: UserProfile = Depends(get_current_user)) -> UserProfile:
    if current_user.role not in ("admin", "super_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user
