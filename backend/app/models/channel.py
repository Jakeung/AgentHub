from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, func, UniqueConstraint
from app.models.base import Base


class InstanceChannelConfig(Base):
    __tablename__ = "instance_channel_config"
    __table_args__ = (
        UniqueConstraint("instance_id", "platform", name="uq_instance_platform"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    instance_id = Column(Integer, ForeignKey("agent_instance.id"), nullable=False)
    platform = Column(String(50), nullable=False)
    config_encrypted = Column(Text, nullable=False)
    status = Column(String(20), default="pending")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
