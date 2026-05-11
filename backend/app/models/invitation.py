from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, func
from app.models.base import Base


class InvitationCode(Base):
    __tablename__ = "invitation_code"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(32), unique=True, nullable=False, index=True)
    max_uses = Column(Integer, default=1)
    used_count = Column(Integer, default=0)
    created_by = Column(Integer, ForeignKey("sys_user.id"), nullable=False)
    expires_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
