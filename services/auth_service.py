from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database.models import User
from auth.password import password_manager
from auth.jwt_manager import jwt_manager
from schemas.auth import RegisterRequest
from core.exceptions import UserAlreadyExistsError, InvalidCredentialsError

# Precomputed once at import time. Used to run verify_password() on the
# "user not found" path in login_user(), so that path takes roughly the
# same time as the "wrong password" path. Without this, an attacker can
# tell registered vs unregistered emails apart just by response timing.
_DUMMY_HASH = password_manager.hash_password("dummy-password-for-timing-safety")


class TokenPair:
    __slots__ = ("access_token", "refresh_token", "token_type")

    def __init__(self, access_token: str, refresh_token: str):
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.token_type = "bearer"


class AuthService:
    """
    Core authentication business logic.
    No HTTP logic here. Pure business layer.

    Failure modes raise domain exceptions (core.exceptions.AppError
    subclasses) instead of returning {"success": False, ...} dicts.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    def _issue_tokens(self, user: User) -> TokenPair:
        access_token = jwt_manager.create_access_token(
            user_id=str(user.id), email=user.email, role=user.role
        )
        refresh_token = jwt_manager.create_refresh_token(
            user_id=str(user.id), email=user.email, role=user.role
        )
        return TokenPair(access_token, refresh_token)

    # -----------------------------
    # REGISTER USER
    # -----------------------------
    async def register_user(self, payload: RegisterRequest) -> dict:
        email = payload.email.strip().lower()

        # Fast-path check: good UX (fail fast) but NOT the actual guarantee.
        existing = await self.db.execute(select(User).where(User.email == email))
        if existing.scalar_one_or_none():
            raise UserAlreadyExistsError("Email already registered")

        new_user = User(
            full_name=payload.full_name,
            email=email,
            password_hash=password_manager.hash_password(payload.password),
            role="USER",
            is_verified=False,
        )
        self.db.add(new_user)

        try:
            await self.db.commit()
        except IntegrityError:
            # Real guarantee: the DB's unique constraint on email catches
            # the case where two requests both passed the pre-check above.
            await self.db.rollback()
            raise UserAlreadyExistsError("Email already registered")

        await self.db.refresh(new_user)
        tokens = self._issue_tokens(new_user)

        return {
            "user_id": str(new_user.id),
            "email": new_user.email,
            "full_name": new_user.full_name,
            "access_token": tokens.access_token,
            "refresh_token": tokens.refresh_token,
            "token_type": tokens.token_type,
        }

    # -----------------------------
    # LOGIN USER
    # -----------------------------
    async def login_user(self, email: str, password: str) -> dict:
        email = email.strip().lower()

        result = await self.db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if not user:
            # Burn roughly the same time as a real verify, then fail the
            # same way as a wrong-password attempt.
            password_manager.verify_password(password, _DUMMY_HASH)
            raise InvalidCredentialsError("Invalid credentials")

        if not password_manager.verify_password(password, user.password_hash):
            raise InvalidCredentialsError("Invalid credentials")

        tokens = self._issue_tokens(user)

        return {
            "user_id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "access_token": tokens.access_token,
            "refresh_token": tokens.refresh_token,
            "token_type": tokens.token_type,
        }