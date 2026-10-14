
import os
from urllib.parse import quote

from authlib.integrations.starlette_client import OAuth, OAuthError
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from database.db import get_db
from database.models import User
from schemas.auth import (
    RegisterRequest,
    LoginRequest,
    AuthResponse,
    UserResponse,
)
from services.auth_service import AuthService
from dependencies.auth_dependency import get_current_user


router = APIRouter(prefix="/auth", tags=["auth"])

oauth = OAuth()
oauth.register(
    name="google",
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    server_metadata_url=(
        "https://accounts.google.com/.well-known/openid-configuration"
    ),
    client_kwargs={"scope": "openid email profile"},
)


def _frontend_callback_url(fragment: str) -> str:
    frontend_url = os.getenv(
        "FRONTEND_URL", "http://localhost:3000"
    ).rstrip("/")
    return f"{frontend_url}/auth/callback#{fragment}"


@router.post("/register", response_model=AuthResponse, status_code=201)
async def register(
    payload: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    service = AuthService(db)
    result = await service.register_user(payload)
    return AuthResponse(**result)


@router.post("/login", response_model=AuthResponse)
async def login(
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    service = AuthService(db)
    result = await service.login_user(
        payload.email, payload.password
    )
    return AuthResponse(**result)


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_user),
):
    return UserResponse(
        id=str(current_user.id),
        full_name=current_user.full_name,
        email=current_user.email,
        role=current_user.role,
    )


@router.get("/google")
async def google_login(request: Request):
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")

    if not client_id or not client_secret:
        raise HTTPException(
            status_code=503,
            detail="Google OAuth is not configured on the server.",
        )

    redirect_uri = os.getenv(
        "GOOGLE_REDIRECT_URI",
        "http://127.0.0.1:8000/auth/google/callback",
    )

    return await oauth.google.authorize_redirect(
        request,
        redirect_uri,
    )


@router.get("/google/callback")
async def google_callback(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    try:
        token = await oauth.google.authorize_access_token(request)
        userinfo = token.get("userinfo")

        if not userinfo:
            raise ValueError("Google user information is missing")

        email = userinfo.get("email")
        email_verified = userinfo.get("email_verified")
        full_name = userinfo.get("name") or (
            email.split("@")[0] if email else ""
        )

        if not email or email_verified is not True:
            raise ValueError("Google email is not verified")

        result = await AuthService(db).login_or_register_google(
            email=email,
            full_name=full_name,
        )

        # Tokens go in the URL fragment, not query parameters, so the
        # browser does not send them to the frontend web server.
        fragment = (
            f"access_token={quote(result['access_token'], safe='')}"
            f"&refresh_token={quote(result['refresh_token'], safe='')}"
        )
        return RedirectResponse(
            _frontend_callback_url(fragment),
            status_code=302,
        )

    except (OAuthError, ValueError):
        return RedirectResponse(
            _frontend_callback_url("error=google_auth_failed"),
            status_code=302,
        )
