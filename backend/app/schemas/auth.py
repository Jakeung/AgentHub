from pydantic import BaseModel, Field
import re


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_]+$")
    password: str = Field(min_length=6)
    email: str | None = None
    invitation_code: str = Field(min_length=1, max_length=32)


class LoginRequest(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    name: str
    email: str | None
    role: str
    permissions: list[str] = []
    last_login_at: str | None = None

    model_config = {"from_attributes": True}
