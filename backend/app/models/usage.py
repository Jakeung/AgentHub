"""Usage statistics models: daily aggregation and model pricing."""
from sqlalchemy import Column, Integer, String, Float, Boolean, Date, DateTime, ForeignKey, UniqueConstraint, func
from app.models.base import Base


class DailyUsageStats(Base):
    __tablename__ = "daily_usage_stats"
    __table_args__ = (
        UniqueConstraint("user_id", "instance_id", "model_name", "date", name="uq_daily_usage"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("sys_user.id"), nullable=False, index=True)
    instance_id = Column(Integer, ForeignKey("agent_instance.id"), nullable=False, index=True)
    model_name = Column(String(100), default="")
    date = Column(Date, nullable=False, index=True)
    request_count = Column(Integer, default=0)
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    estimated_cost = Column(Float, default=0.0)
    created_at = Column(DateTime, server_default=func.now())


class ModelPricing(Base):
    __tablename__ = "model_pricing"

    id = Column(Integer, primary_key=True, autoincrement=True)
    model_name = Column(String(100), unique=True, nullable=False)
    provider = Column(String(50), default="")
    input_price_per_1k = Column(Float, default=0.0)
    output_price_per_1k = Column(Float, default=0.0)
    currency = Column(String(10), default="CNY")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
