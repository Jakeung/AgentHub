from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, UniqueConstraint, func
from app.models.base import Base


class ToolRegistry(Base):
    __tablename__ = "tool_registry"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False)
    display_name = Column(String(100), nullable=False)
    description = Column(Text, default="")
    category = Column(String(30), default="")
    icon = Column(String(50), default="")
    config_schema = Column(Text, default="{}")
    default_config = Column(Text, default="{}")
    is_active = Column(Boolean, default=True)
    requires_api_key = Column(Boolean, default=False)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class InstanceToolConfig(Base):
    __tablename__ = "instance_tool_config"
    __table_args__ = (
        UniqueConstraint("instance_id", "tool_name", name="uq_instance_tool"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    instance_id = Column(Integer, ForeignKey("agent_instance.id"), nullable=False, index=True)
    tool_name = Column(String(50), nullable=False)
    enabled = Column(Boolean, default=False)
    config = Column(Text, default="{}")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class InstanceSkillConfig(Base):
    __tablename__ = "instance_skill_config"
    __table_args__ = (
        UniqueConstraint("instance_id", "skill_name", name="uq_instance_skill"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    instance_id = Column(Integer, ForeignKey("agent_instance.id"), nullable=False, index=True)
    skill_name = Column(String(100), nullable=False)
    source = Column(String(20), default="builtin")
    enabled = Column(Boolean, default=True)
    custom_content = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
