import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from config import JOB_HOUR, JOB_MINUTE, TIMEZONE

logger = logging.getLogger(__name__)


def start_scheduler(job_func) -> None:
    scheduler = BlockingScheduler(timezone=TIMEZONE)
    scheduler.add_job(
        job_func,
        CronTrigger(hour=JOB_HOUR, minute=JOB_MINUTE, timezone=TIMEZONE),
        id="daily_stock_analysis",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    logger.info("Scheduler started: daily %02d:%02d %s", JOB_HOUR, JOB_MINUTE, TIMEZONE)
    scheduler.start()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    def demo_job():
        print("scheduler demo job")

    start_scheduler(demo_job)
