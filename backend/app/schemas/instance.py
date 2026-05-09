from pydantic import BaseModel, Field


class CreateInstanceRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    cpu_limit: float = Field(default=1.0, ge=0.5, le=4.0)
    memory_limit_mb: int = Field(default=2048, ge=512, le=8192)
    env_config: dict | None = None


class UpdateInstanceRequest(BaseModel):
    name: str | None = Field(default=None, max_length=100)
    cpu_limit: float | None = Field(default=None, ge=0.5, le=4.0)
    memory_limit_mb: int | None = Field(default=None, ge=512, le=8192)
    env_config: dict | None = None
