"""Self-audit 11 (17.11.2026), Ö63: heartbeat misfire grace."""

from telegram.ext import ApplicationBuilder

from bot import scheduler


def test_heartbeat_tolerates_a_late_start():
    """Ö63: 17.11 08:30:45 the heartbeat was skipped, missed by 1.2 s (default grace 1 s)."""
    app = ApplicationBuilder().token("123:ABC").build()
    assert scheduler.schedule_heartbeat(app)
    job = app.job_queue.get_jobs_by_name(scheduler.HEARTBEAT_JOB)[0]
    assert 60 <= getattr(job.job, "misfire_grace_time", 1) < 300  # unset: scheduler default 1 s
    assert getattr(job.job, "coalesce", False)
