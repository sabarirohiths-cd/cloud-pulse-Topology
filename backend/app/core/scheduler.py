import asyncio
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from app.core.database import SessionLocal
from app.models import ControlResource, ConfigCloudAccount, ControlActionLog
from app.core.security import decrypt_credentials
from app.services.control_service import control_service
from app.services.notifier import notifier_service
from app.services.action_logger import log_control_action

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def is_time_between(start_str: str, stop_str: str, current_time: datetime) -> bool:
    try:
        start_time = datetime.strptime(start_str, "%H:%M").time()
        stop_time = datetime.strptime(stop_str, "%H:%M").time()
        current = current_time.time()

        if start_time < stop_time:
            return start_time <= current < stop_time
        else: # Over midnight
            return current >= start_time or current < stop_time
    except Exception as e:
        logger.error(f"Error parsing time boundaries: {e}")
        return True # Default to running on error

async def evaluate_resource(session, sched: ControlResource):
    try:
        tz = ZoneInfo(sched.timezone or "UTC")
        now = datetime.now(tz)
        
        # 1. Override check
        if sched.override_state in ['EXTENDED', 'SKIPPED'] and sched.override_until:
            if now.replace(tzinfo=None) < sched.override_until:
                logger.info(f"[{sched.resource_id}] Override active ({sched.override_state}) until {sched.override_until}. Skipping evaluation.")
                return
            else:
                logger.info(f"[{sched.resource_id}] Override expired. Reverting to normal state.")
                sched.override_state = 'NORMAL'
                sched.override_until = None
                await session.commit()

        # 2. Target State evaluation
        should_be_running = is_time_between(sched.start_time, sched.stop_time, now)
        
        # 2.5 Schedule Pattern evaluation
        if sched.schedule_pattern == 'mon_fri':
            # 0=Monday, 6=Sunday
            if now.weekday() >= 5:
                should_be_running = False
                
        target_action = 'START' if should_be_running else 'STOP'

        # 3. Pre-warning notification logic (1 hour before shutdown)
        if should_be_running:
            stop_time_parsed = datetime.strptime(sched.stop_time, "%H:%M").time()
            stop_dt = datetime.combine(now.date(), stop_time_parsed).replace(tzinfo=tz)
            
            # If over midnight and current time is before midnight but stop time is after
            if stop_time_parsed < now.time():
                stop_dt += timedelta(days=1)
                
            time_until_stop = (stop_dt - now).total_seconds()
            
            # If within 60-65 mins of stopping, send warning
            if 3600 <= time_until_stop <= 3900:
                logger.info(f"[{sched.resource_id}] Sending pre-shutdown warning.")
                urls = await notifier_service.send_pre_shutdown_warning(
                    sched.resource_id, sched.service_type, sched.account_name, sched.stop_time
                )
                logger.info(f"[{sched.resource_id}] Pre-warning sent. Extend URL: {urls['extend_url']}")
        
        # 4. Optimize AWS API calls (Removed transition logic as per read-only mode)
        
        # 5. Fetch Cloud Config
        stmt = select(ConfigCloudAccount).where(ConfigCloudAccount.account_name == sched.account_name)
        res = await session.execute(stmt)
        config = res.scalars().first()
        if not config:
            logger.warning(f"[{sched.resource_id}] ConfigCloudAccount for {sched.account_name} not found.")
            return

        creds = decrypt_credentials(config.encrypted_credentials)
        
        # 6. Fetch actual live state
        live_state = await control_service.get_resource_state(config.provider, creds, sched.region, sched.service_type, sched.resource_id)
        
        # 7. Execute action if out of sync
        # Simplification: EC2 uses 'running', 'stopped'
        live_state_lower = live_state.lower() if live_state else ""
        is_live_running = live_state_lower in ['running', 'available']
        is_live_stopped = live_state_lower in ['stopped', 'paused', 'terminated']
        
        # Start/stop execution logic has been removed entirely as requested.
            
        # 8. Keep DB status perfectly in sync and detect completions
        normalized_live = live_state.upper() if live_state else "UNKNOWN"
        if sched.status != normalized_live:
            sched.status = normalized_live
            await session.commit()

    except Exception as e:
        logger.error(f"Error evaluating resource {sched.resource_id}: {e}")


async def run_control_scheduler():
    """
    Background loop for power scheduling:
    1. Pre-warning check (1h before shutdown): Triggers notification email
    2. Shutdown check: Stops resources if no active override
    3. Startup check: Powers up scheduled resources
    4. TTL Cleanup: Deletes old system notifications
    """
    logger.info("Control Module Automation Scheduler started...")
    from app.models.system.system_notification import SystemNotification
    from sqlalchemy import delete
    from datetime import timedelta
    
    last_cleanup_hour = -1

    while True:
        try:
            now = datetime.now()
            
            async with SessionLocal() as session:
                # 1. TTL Cleanup (Run once per hour)
                if now.hour != last_cleanup_hour:
                    cutoff = datetime.utcnow() - timedelta(days=2)
                    await session.execute(
                        delete(SystemNotification).where(SystemNotification.created_at < cutoff)
                    )
                    await session.commit()
                    last_cleanup_hour = now.hour

                # 2. Automation scheduling
                stmt = select(ControlResource).where(ControlResource.is_automation_enabled == True)
                res = await session.execute(stmt)
                schedules = res.scalars().all()
                
                for sched in schedules:
                    await evaluate_resource(session, sched)
                    
        except Exception as e:
            logger.error(f"Error in control scheduler loop: {e}")
            
        # Sleep until the exact start of the next minute for zero-delay triggering
        now = datetime.now()
        sleep_seconds = 60 - now.second - (now.microsecond / 1000000.0)
        await asyncio.sleep(max(1, sleep_seconds + 0.1))


