from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from app.models.base import Base


class SysUser(Base):
    __tablename__ = "sys_user"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(200), nullable=False)
    name = Column(String(100), default="")
    email = Column(String(200), unique=True, nullable=True)
    role_id = Column(Integer, ForeignKey("sys_role.id"), nullable=False, default=2)
    status = Column(String(20), default="active")
    last_login_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
