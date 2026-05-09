from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, func
from app.models.base import Base


class AgentInstance(Base):
    __tablename__ = "agent_instance"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    container_name = Column(String(200), unique=True, nullable=False)
    container_id = Column(String(100), nullable=True)
    port = Column(Integer, unique=True, nullable=False)
    status = Column(String(20), default="creating", index=True)
    health_status = Column(String(20), default="unknown")
    cpu_limit = Column(Float, default=1.0)
    memory_limit_mb = Column(Integer, default=2048)
    data_dir = Column(String(500), nullable=False)
    env_config = Column(Text, default="{}")
    api_server_key = Column(String(100), unique=True, nullable=True)
    deleted_at = Column(DateTime, nullable=True)
    owner_user_id = Column(Integer, ForeignKey("sys_user.id"), nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    @property
    def is_deleted(self) -> bool:
        return self.status == "deleted"


class InstanceModelConfig(Base):
    __tablename__ = "instance_model_config"

    id = Column(Integer, primary_key=True, autoincrement=True)
    instance_id = Column(Integer, ForeignKey("agent_instance.id"), unique=True, nullable=False)
    provider = Column(String(50), default="deepseek")
    model_name = Column(String(100), default="deepseek-chat")
    api_base_url = Column(String(500), default="")
    temperature = Column(Float, default=0.7)
    max_tokens = Column(Integer, default=4096)
    system_prompt = Column(Text, default="")
    extra_params = Column(Text, default="{}")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

