"""25.11.2026 repair queue 1 (recurring fault 19.11, 21.11, 24.11): the PC ran out of battery and slept 6 hours.

The bot checks the power state every 15 minutes and tells the owner once when the PC is on battery below 30%
(again below 15%), never between 23:00 and 07:00 (logged only; sent at 07:00 if still on battery)."""

import asyncio
from datetime import datetime
from types import SimpleNamespace

from telegram.ext import ApplicationBuilder

from bot import scheduler
from core.infrastructure import power

DAY = datetime(2026, 11, 25, 14, 0)
NIGHT = datetime(2026, 11, 25, 2, 0)
MORNING = datetime(2026, 11, 25, 7, 0)


def test_on_mains_at_25_percent_sends_nothing():
    watch = power.PowerWatch()
    assert watch.check(1, 25, DAY) is None


def test_on_battery_at_25_percent_sends_one_message_only():
    watch = power.PowerWatch()
    text = watch.check(0, 25, DAY)
    assert text == "Bilgisayar pilde, %25; prize takın"
    assert watch.check(0, 24, DAY) is None
    assert watch.check(0, 20, DAY) is None


def test_on_battery_above_30_percent_sends_nothing():
    assert power.PowerWatch().check(0, 30, DAY) is None
    assert power.PowerWatch().check(0, 80, DAY) is None


def test_second_message_below_15_percent_once():
    watch = power.PowerWatch()
    assert watch.check(0, 28, DAY)
    assert watch.check(0, 14, DAY) == "Bilgisayar pilde, %14; prize takın"
    assert watch.check(0, 12, DAY) is None


def test_first_look_below_15_sends_a_single_message():
    watch = power.PowerWatch()
    assert watch.check(0, 10, DAY)
    assert watch.check(0, 9, DAY) is None


def test_mains_returns_then_a_new_battery_cycle_may_message_again():
    watch = power.PowerWatch()
    assert watch.check(0, 25, DAY)
    assert watch.check(1, 40, DAY) is None
    assert watch.check(0, 25, DAY)


def test_night_is_silent_and_not_consumed():
    watch = power.PowerWatch()
    assert watch.check(0, 20, NIGHT) is None
    assert watch.check(0, 18, datetime(2026, 11, 25, 23, 0)) is None
    assert watch.check(0, 16, MORNING) == "Bilgisayar pilde, %16; prize takın"  # still on battery at 07:00


def test_unknown_power_state_is_silent():
    watch = power.PowerWatch()
    assert watch.check(None, None, DAY) is None
    assert watch.check(255, 255, DAY) is None
    assert watch.check(0, 255, DAY) is None
    assert watch.check(0, None, DAY) is None


def test_job_sends_to_the_owner_chat_and_registers_every_15_minutes():
    sent = []

    async def send_message(chat_id, text):
        sent.append((chat_id, text))

    watch = power.PowerWatch()
    context = SimpleNamespace(bot=SimpleNamespace(send_message=send_message), job=SimpleNamespace(chat_id=777))
    from unittest import mock

    with mock.patch.object(power, "read_status", return_value=(0, 22)), \
            mock.patch.object(scheduler, "_power_watch", watch), \
            mock.patch.object(scheduler, "now_istanbul", return_value=DAY):
        asyncio.run(scheduler.power_job(context))
        asyncio.run(scheduler.power_job(context))
    assert sent == [(777, "Bilgisayar pilde, %22; prize takın")]

    app = ApplicationBuilder().token("123:ABC").build()
    assert scheduler.schedule_power_watch(app, 777)
    job = app.job_queue.get_jobs_by_name(scheduler.POWER_JOB)[0]
    assert job.job.trigger.interval.total_seconds() == 900
    assert getattr(job.job, "coalesce", False)


def test_read_status_never_raises():
    status = power.read_status()
    assert isinstance(status, tuple) and len(status) == 2
