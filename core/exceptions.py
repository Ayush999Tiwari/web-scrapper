class AppError(Exception):
    """
    Base class for domain-level errors.
    Services raise these; a global FastAPI exception handler
    (see main.py snippet below) converts them to HTTP responses.
    Never raise AppError directly — always a specific subclass.
    """
    status_code: int = 400

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class UserAlreadyExistsError(AppError):
    status_code = 409


class InvalidCredentialsError(AppError):
    status_code = 401


class InvalidTokenError(AppError):
    status_code = 401
