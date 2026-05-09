from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from app.models.base import Base


class SysRole(Base):
    __tablename__ = "sys_role"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(String(200), default="")
    created_at = Column(DateTime, server_default=func.now())


class SysPermission(Base):
    __tablename__ = "sys_permission"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(50), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    module = Column(String(50), nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class SysRolePermission(Base):
    __tablename__ = "sys_role_permission"

    id = Column(Integer, primary_key=True, autoincrement=True)
    role_id = Column(Integer, ForeignKey("sys_role.id"), nullable=False, index=True)
    permission_id = Column(Integer, ForeignKey("sys_permission.id"), nullable=False, index=True)
