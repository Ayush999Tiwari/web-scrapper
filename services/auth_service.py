
import secrets

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database.models import User
from auth.password import password_manager
from auth.jwt_manager import jwt_manager
from schemas.auth import RegisterRequest
from core.exceptions import UserAlreadyExistsError, InvalidCredentialsError


_DUMMY_HASH = password_manager.hash_password("dummy-password-for-timing-safety")


class TokenPair:
    __slots__ = ("access_token", "refresh_token", "token_type")

    def __init__(self, access_token: str, refresh_token: str):
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.token_type = "bearer"


class AuthService:
    """Authentication business logic."""

    def __init__(self, db: AsyncSession):
        self.db = db

    def _issue_tokens(self, user: User) -> TokenPair:
        return TokenPair(
            access_token=jwt_manager.create_access_token(
                user_id=str(user.id),
                email=user.email,
                role=user.role,
            ),
            refresh_token=jwt_manager.create_refresh_token(
                user_id=str(user.id),
                email=user.email,
                role=user.role,
            ),
        )

    def _auth_result(self, user: User) -> dict:
        tokens = self._issue_tokens(user)
        return {
            "user_id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "access_token": tokens.access_token,
            "refresh_token": tokens.refresh_token,
            "token_type": tokens.token_type,
        }

    async def register_user(self, payload: RegisterRequest) -> dict:
        email = str(payload.email).strip().lower()

        existing = await self.db.execute(
            select(User).where(User.email == email)
        )
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
            await self.db.rollback()
            raise UserAlreadyExistsError("Email already registered")

        await self.db.refresh(new_user)
        return self._auth_result(new_user)

    async def login_user(self, email: str, password: str) -> dict:
        email = email.strip().lower()

        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        user = result.scalar_one_or_none()

        if not user:
            password_manager.verify_password(password, _DUMMY_HASH)
            raise InvalidCredentialsError("Invalid credentials")

        if not password_manager.verify_password(password, user.password_hash):
            raise InvalidCredentialsError("Invalid credentials")

        return self._auth_result(user)

    async def login_or_register_google(
        self,
        email: str,
        full_name: str,
    ) -> dict:
        """Log in an existing account or create a Google-verified account."""
        email = email.strip().lower()
        full_name = full_name.strip() or email.split("@")[0]

        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        user = result.scalar_one_or_none()

        if user:
            # Google callback calls this only after verifying Google's
            # identity and the email_verified claim.
            if not user.is_verified:
                user.is_verified = True
                await self.db.commit()
                await self.db.refresh(user)

            return self._auth_result(user)

        # The existing database model requires password_hash. A random,
        # unshared password means the Google account cannot use a known
        # password to sign in.
        user = User(
            full_name=full_name,
            email=email,
            password_hash=password_manager.hash_password(
                secrets.token_urlsafe(48)
            ),
            role="USER",
            is_verified=True,
        )
        self.db.add(user)

        try:
            await self.db.commit()
            await self.db.refresh(user)
        except IntegrityError:
            # Handles two simultaneous first-time Google sign-ins for
            # the same email. The unique DB constraint remains the guard.
            await self.db.rollback()

            result = await self.db.execute(
                select(User).where(User.email == email)
            )
            user = result.scalar_one_or_none()

            if user is None:
                raise

            if not user.is_verified:
                user.is_verified = True
                await self.db.commit()
                await self.db.refresh(user)

        return self._auth_result(user)
