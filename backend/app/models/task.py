from sqlalchemy import Column, Integer, String, DateTime, Text, func
from app.models.base import Base


class AsyncTask(Base):
    __tablename__ = "async_task"

    id = Column(String(36), primary_key=True)
    type = Column(String(50), nullable=False)
    status = Column(String(20), default="pending")
    progress = Column(Integer, default=0)
    message = Column(String(500), default="")
    result = Column(Text, default="{}")
    error = Column(Text, default="")
    created_at = Column(DateTime, server_default=func.now())
    completed_at = Column(DateTime, nullable=True)
