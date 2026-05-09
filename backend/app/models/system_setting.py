from sqlalchemy import Column, Integer, String, Text, DateTime, func
from app.models.base import Base


class SystemSetting(Base):
    __tablename__ = "system_setting"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=False, default="")
    description = Column(String(500), default="")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
