"""Scheduler for automatic data refresh and display rotation."""

from __future__ import annotations

from datetime import datetime, time
from typing import Callable, Dict, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from .logging import get_logger

logger = get_logger("core.scheduler")


class HubScheduler:
    """
    Centralized scheduler for:
    - Provider data refresh (different intervals per provider)
    - Display rotation in auto mode
    - Quiet hours enforcement
    """

    def __init__(self) -> None:
        self._scheduler = AsyncIOScheduler()
        self._jobs: Dict[str, str] = {}  # name -> job_id
        self._quiet_start: Optional[time] = None
        self._quiet_end: Optional[time] = None
        self._rotation_paused = False

    async def start(self) -> None:
        """Start the scheduler."""
        if not self._scheduler.running:
            self._scheduler.start()
            logger.info("Scheduler started")

    async def stop(self) -> None:
        """Gracefully stop the scheduler."""
        if self._scheduler.running:
            self._scheduler.shutdown(wait=True)
            logger.info("Scheduler stopped")

    def schedule_provider_refresh(
        self,
        provider_name: str,
        callback: Callable,
        interval_minutes: int,
    ) -> None:
        """
        Schedule a provider's data refresh.

        Args:
            provider_name: Name of the provider
            callback: Async function to call for refresh
            interval_minutes: Refresh interval in minutes
        """
        job_name = f"provider_{provider_name}"

        # Remove existing job if any
        if job_name in self._jobs:
            self._scheduler.remove_job(self._jobs[job_name])

        job = self._scheduler.add_job(
            callback,
            IntervalTrigger(minutes=interval_minutes),
            id=job_name,
            name=job_name,
            replace_existing=True,
        )

        self._jobs[job_name] = job.id
        logger.info(
            f"Scheduled provider refresh: {provider_name} every {interval_minutes} min"
        )

    def schedule_display_rotation(
        self,
        callback: Callable,
        interval_minutes: int,
    ) -> None:
        """
        Schedule automatic display rotation.

        Args:
            callback: Async function to call for rotation
            interval_minutes: Rotation interval in minutes
        """
        job_name = "display_rotation"

        # Remove existing job if any
        if job_name in self._jobs:
            self._scheduler.remove_job(self._jobs[job_name])

        job = self._scheduler.add_job(
            self._rotation_wrapper(callback),
            IntervalTrigger(minutes=interval_minutes),
            id=job_name,
            name=job_name,
            replace_existing=True,
        )

        self._jobs[job_name] = job.id
        logger.info(f"Scheduled display rotation every {interval_minutes} min")

    def _rotation_wrapper(self, callback: Callable) -> Callable:
        """Wrap rotation callback with quiet hours and pause checks."""

        async def wrapper():
            if self._rotation_paused:
                logger.debug("Rotation skipped: paused")
                return

            if self._is_quiet_hours():
                logger.debug("Rotation skipped: quiet hours")
                return

            await callback()

        return wrapper

    def _is_quiet_hours(self) -> bool:
        """Check if current time is within quiet hours."""
        if not self._quiet_start or not self._quiet_end:
            return False

        now = datetime.now().time()

        # Handle overnight quiet hours (e.g., 22:00 - 07:00)
        if self._quiet_start > self._quiet_end:
            return now >= self._quiet_start or now <= self._quiet_end
        else:
            return self._quiet_start <= now <= self._quiet_end

    def set_quiet_hours(
        self,
        start_time: str,  # "22:00"
        end_time: str,  # "07:00"
    ) -> None:
        """
        Configure quiet hours when display won't auto-update.

        Args:
            start_time: Start of quiet hours (HH:MM)
            end_time: End of quiet hours (HH:MM)
        """
        try:
            start_parts = [int(p) for p in start_time.split(":")]
            end_parts = [int(p) for p in end_time.split(":")]

            self._quiet_start = time(start_parts[0], start_parts[1])
            self._quiet_end = time(end_parts[0], end_parts[1])

            logger.info(f"Quiet hours set: {start_time} - {end_time}")
        except (ValueError, IndexError) as e:
            logger.error(f"Invalid quiet hours format: {e}")

    def pause_rotation(self) -> None:
        """Pause auto-rotation (for manual override)."""
        self._rotation_paused = True
        logger.info("Display rotation paused")

    def resume_rotation(self) -> None:
        """Resume auto-rotation."""
        self._rotation_paused = False
        logger.info("Display rotation resumed")

    def trigger_now(self, job_name: str) -> None:
        """
        Manually trigger a scheduled job immediately.

        Args:
            job_name: Name of the job (e.g., "provider_strava")
        """
        if job_name in self._jobs:
            job = self._scheduler.get_job(self._jobs[job_name])
            if job:
                job.modify(next_run_time=datetime.now())
                logger.info(f"Triggered job: {job_name}")
        else:
            logger.warning(f"Job not found: {job_name}")

    def remove_job(self, job_name: str) -> None:
        """Remove a scheduled job."""
        if job_name in self._jobs:
            self._scheduler.remove_job(self._jobs[job_name])
            del self._jobs[job_name]
            logger.info(f"Removed job: {job_name}")

    def list_jobs(self) -> Dict[str, str]:
        """List all scheduled jobs with their next run time."""
        result = {}
        for name, job_id in self._jobs.items():
            job = self._scheduler.get_job(job_id)
            if job:
                next_run = job.next_run_time
                result[name] = next_run.isoformat() if next_run else "paused"
        return result
