from pydantic import BaseModel, EmailStr, Field, ConfigDict
class AuthResponse(BaseModel):
    user_id: str
    email: EmailStr
    full_name: str
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
# REGISTER
class RegisterRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True
    )
    full_name: str = Field(min_length=3, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
class RegisterResponse(BaseModel):
    user_id: str
    email: EmailStr
    message: str
# LOGIn
class LoginRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True
    )
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
# ME (Current User)
class UserResponse(BaseModel):
    id: str
    full_name: str
    email: EmailStr
    role: str