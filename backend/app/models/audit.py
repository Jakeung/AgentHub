from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, func
from app.models.base import Base


class SysOperationLog(Base):
    __tablename__ = "sys_operation_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("sys_user.id"), nullable=True, index=True)
    action = Column(String(100), nullable=False, index=True)
    target_type = Column(String(50), default="", index=True)
    target_id = Column(Integer, nullable=True)
    detail = Column(Text, default="{}")
    ip_address = Column(String(50), default="")
    created_at = Column(DateTime, server_default=func.now(), index=True)


class InstanceRuntimeLog(Base):
    __tablename__ = "instance_runtime_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    instance_id = Column(Integer, ForeignKey("agent_instance.id"), nullable=False, index=True)
    level = Column(String(20), default="info")
    message = Column(Text, default="")
    logged_at = Column(DateTime, server_default=func.now())
