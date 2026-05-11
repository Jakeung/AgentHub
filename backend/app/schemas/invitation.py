from pydantic import BaseModel, Field


class CreateInvitationReq(BaseModel):
    count: int = Field(default=1, ge=1, le=50)
    max_uses: int = Field(default=1, ge=1, le=10000)
    expires_at: str | None = None


class UpdateInvitationReq(BaseModel):
    is_active: bool | None = None
    max_uses: int | None = Field(default=None, ge=1, le=10000)
