"""Background tasks - health checks, cleanup, monitoring."""
import asyncio
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone, timedelta

from app.models.instance import AgentInstance
from app.models.base import async_session

logger = logging.getLogger(__name__)


class HealthCheckService:
    """Periodically check health of all running instances."""

    @staticmethod
    async def check_all_instances(db: AsyncSession):
        """Check health of all running instances."""
        result = await db.execute(
            select(AgentInstance).where(AgentInstance.status == "running")
        )
        instances = result.scalars().all()

        unhealthy = []

        for inst in instances:
            try:
                # TODO: Replace with actual health check to instance port
                # For now, just log that we checked
                logger.debug(f"Health check for instance {inst.name} (port={inst.port})")

                # Mark as healthy if no errors detected
                if inst.health_status != "healthy":
                    inst.health_status = "healthy"
                    logger.info(f"Instance {inst.name} recovered")

            except asyncio.TimeoutError:
                unhealthy.append(inst)
                inst.health_status = "timeout"
                logger.warning(f"Instance {inst.name} health check timeout")

            except Exception as e:
                unhealthy.append(inst)
                inst.health_status = f"error: {type(e).__name__}"
                logger.error(f"Instance {inst.name} health check error: {e}")

        await db.commit()
        return unhealthy

    @staticmethod
    async def cleanup_old_deleted_instances(db: AsyncSession, days: int = 30):
        """Clean up soft-deleted instances older than specified days."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        result = await db.execute(
            select(AgentInstance).where(
                AgentInstance.status == "deleted", AgentInstance.deleted_at < cutoff
            )
        )
        old_instances = result.scalars().all()

        for inst in old_instances:
            await db.delete(inst)
            logger.info(f"Cleaned up old deleted instance {inst.name}")

        await db.commit()
        return len(old_instances)


async def health_check_loop():
    """Background loop for periodic health checks (every 30 seconds)."""
    while True:
        try:
            async with async_session() as db:
                unhealthy = await HealthCheckService.check_all_instances(db)

                if unhealthy:
                    logger.warning(f"{len(unhealthy)} instances are unhealthy")
                    # TODO: Integrate with alerting system
                    # await send_alert(unhealthy)

        except Exception as e:
            logger.error(f"Health check loop error: {e}", exc_info=True)

        # Check every 30 seconds
        await asyncio.sleep(30)


async def cleanup_loop():
    """Background loop for periodic cleanup (every 24 hours)."""
    while True:
        try:
            async with async_session() as db:
                count = await HealthCheckService.cleanup_old_deleted_instances(
                    db, days=30
                )
                if count > 0:
                    logger.info(f"Cleaned up {count} old deleted instances")

        except Exception as e:
            logger.error(f"Cleanup loop error: {e}", exc_info=True)

        # Cleanup once per day
        await asyncio.sleep(86400)
