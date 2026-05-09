from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, func
from app.models.base import Base


class ApiSecret(Base):
    __tablename__ = "api_secret"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    provider = Column(String(50), nullable=False)
    model_name = Column(String(100), nullable=True, default="")
    encrypted_key = Column(String(500), nullable=False)
    key_suffix = Column(String(10), default="")
    is_active = Column(Boolean, default=False)
    owner_user_id = Column(Integer, ForeignKey("sys_user.id"), nullable=False)
    last_used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
