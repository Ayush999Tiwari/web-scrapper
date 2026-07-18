from typing import Final
from passlib.context import CryptContext
class PasswordManager:
    """
    Handles password hashing and verification.
    This class abstracts Passlib so that if we ever migrate
    to Argon2 or another algorithm, only this file changes.
    """
    _SCHEMES: Final[list[str]] = ["bcrypt"]
    def __init__(self) -> None:
        self._pwd_context = CryptContext(
            schemes=self._SCHEMES,
            deprecated="auto",
            bcrypt__rounds=12
        )
    def hash_password(self, password: str) -> str:
        """
        Hash a plain text password.
        Args:
            password: User's plain password.
        Returns:
            Secure bcrypt hash.
        """
        return self._pwd_context.hash(password)
    def verify_password(
        self,
        plain_password: str,
        hashed_password: str
    ) -> bool:
        """
        Verify a password against its hash.
        Args:
            plain_password: Password entered by user.
            hashed_password: Password stored in database.
        Returns:
            True if passwords match.
        """
        return self._pwd_context.verify(
            plain_password,
            hashed_password
        )
password_manager = PasswordManager()