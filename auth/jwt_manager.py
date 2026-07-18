"""
JWT Token Manager
Responsible for:
- Access Token Generation
- Refresh Token Generation
- Token Validation
- Token Decoding
"""

from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4
from jose import JWTError, jwt

class JWTManager:
    """
    Handles creation and validation of JWT tokens.
    """
    def __init__(
        self,
        secret_key: str,
        algorithm: str,
        access_token_expire_minutes: int,
        refresh_token_expire_days: int,
    ) -> None:
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_expire = access_token_expire_minutes
        self.refresh_expire = refresh_token_expire_days
    def _create_token(
        self,
        *,
        user_id: str,
        email: str,
        role: str,
        token_type: str,
        expires_delta: timedelta,
    ) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "sub": user_id,
            "email": email,
            "role": role,
            "type": token_type,
            "iat": now,
            "exp": now + expires_delta,
            "jti": str(uuid4()),
        }
        return jwt.encode(
            payload,
            self.secret_key,
            algorithm=self.algorithm,
        )
    def create_access_token(
        self,
        *,
        user_id: str,
        email: str,
        role: str,
    ) -> str:
        return self._create_token(
            user_id=user_id,
            email=email,
            role=role,
            token_type="access",
            expires_delta=timedelta(
                minutes=self.access_expire
            ),
        )
    def create_refresh_token(
        self,
        *,
        user_id: str,
        email: str,
        role: str,
    ) -> str:
        return self._create_token(
            user_id=user_id,
            email=email,
            role=role,
            token_type="refresh",
            expires_delta=timedelta(
                days=self.refresh_expire
            ),
        )
    def decode_token(
        self,
        token: str,
    ) -> dict[str, Any]:
        return jwt.decode(
            token,
            self.secret_key,
            algorithms=[self.algorithm],
        )
    def verify_token(
        self,
        token: str,
        expected_type: str,
    ) -> dict[str, Any]:
        try:
            payload = self.decode_token(token)
            if payload.get("type") != expected_type:
                raise ValueError("Invalid token type")
            return payload
        except JWTError as exc:
            raise ValueError("Invalid or expired token") from exc
from core.config import get_settings
settings = get_settings()
jwt_manager = JWTManager(
     secret_key=settings.SECRET_KEY,
     algorithm=settings.ALGORITHM,
     access_token_expire_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
     refresh_token_expire_days=settings.REFRESH_TOKEN_EXPIRE_DAYS,

)