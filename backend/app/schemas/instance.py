from pydantic import BaseModel, Field, field_validator
import json


class CreateInstanceRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    cpu_limit: float = Field(default=1.0, ge=0.5, le=4.0)
    memory_limit_mb: int = Field(default=2048, ge=512, le=8192)
    env_config: dict | None = None

    @field_validator("env_config")
    @classmethod
    def validate_env_config_size(cls, v):
        if v and len(json.dumps(v)) > 16384:
            raise ValueError("env_config 超过 16KB 限制")
        return v


class UpdateInstanceRequest(BaseModel):
    name: str | None = Field(default=None, max_length=100)
    cpu_limit: float | None = Field(default=None, ge=0.5, le=4.0)
    memory_limit_mb: int | None = Field(default=None, ge=512, le=8192)
    env_config: dict | None = None

    @field_validator("env_config")
    @classmethod
    def validate_env_config_size(cls, v):
        if v and len(json.dumps(v)) > 16384:
            raise ValueError("env_config 超过 16KB 限制")
        return v
