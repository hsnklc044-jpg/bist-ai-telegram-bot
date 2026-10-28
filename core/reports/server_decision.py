"""
QuantBIST
The server decision of DECISIONS K-23, computed from the SLO records exactly as written there
before any data was seen. Window 02.11–13.11.2026 in two weeks; a server is recommended if in
either week:
  (a) bot uptime < 98% and most of the loss is the PC asleep, suspended or off (gaps with the
      same bot process, which was frozen, or gaps of 20+ minutes, longer than the bot task's own
      restarts), or
  (b) report delivery < 99% and a missed report was the PC's (no run that day, or the task
      started late because the PC was off), or
  (c) at least one gap of 20+ minutes: what Healthchecks reports as the bot DOWN (estimated from
      the records; Healthchecks itself is not read).
Yahoo or Telegram losses do not count (a server would not fix them); targets are not loosened.

    python -m core.reports.server_decision

Renting a server is the user's step (payment); this only computes the recommendation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path

from core.market.calendar import ISTANBUL, is_session_day

START = datetime(2026, 11, 2, tzinfo=ISTANBUL)
END = datetime(2026, 11, 13, 18, 0, tzinfo=ISTANBUL)  # the 13.11 report (18:30) decides
WEEKS = ((START, datetime(2026, 11, 9, tzinfo=ISTANBUL)), (datetime(2026, 11, 9, tzinfo=ISTANBUL), END))
LONG_GAP = timedelta(minutes=20)  # /durum and Healthchecks call the bot down after 20 minutes
TASK_GRACE = timedelta(minutes=15)  # the report task starts 18:30; later means the PC was off


@dataclass
class Week:
    start: datetime
    end: datetime
    bot: float | None = None
    down: timedelta = timedelta()
    sleep: timedelta = timedelta()
    long_gaps: int = 0
    report: float | None = None
    pc_missed: list[date] = field(default_factory=list)
    other_missed: list[date] = field(default_factory=list)

    @property
    def reasons(self) -> list[str]:
        found = []
        if self.bot is not None and self.bot < 0.98 and self.sleep > self.down / 2:
            found.append("(a) bot ayakta kalma %98'in altında, kaybın çoğu PC kapalı/uykudayken")
        if self.report is not None and self.report < 0.99 and self.pc_missed:
            found.append("(b) rapor teslimi %99'un altında, kaçan rapor PC'den")
        if self.long_gaps:
            found.append(f"(c) {self.long_gaps} kez 20 dakikadan uzun PC kaynaklı bot kesintisi")
        return found


@dataclass
class Decision:
    now: datetime
    weeks: list[Week]

    @property
    def complete(self) -> bool:
        return self.now >= END

    @property
    def server(self) -> bool:
        return any(w.reasons for w in self.weeks)


def _bot(week: Week, beats: list[tuple[datetime, str]], until: datetime) -> None:
    from core.reports.slo import BEAT

    inside = [(t, p) for t, p in beats if week.start <= t <= until]
    if not inside:
        return
    down = max(inside[0][0] - week.start - BEAT, timedelta())
    for (t1, p1), (t2, p2) in zip(inside, inside[1:], strict=False):
        gap = t2 - t1 - BEAT
        if gap > BEAT:
            down += gap
            # the PC's: the same process frozen (asleep/suspended), or a gap longer than the bot
            # task's own restarts (3 tries, 5 minutes apart): the PC was off
            if p1 == p2 or gap + BEAT >= LONG_GAP:
                week.sleep += gap
                week.long_gaps += gap + BEAT >= LONG_GAP
    down += max(until - inside[-1][0] - BEAT, timedelta())
    week.down = down
    week.bot = 1 - down / (until - week.start)


def _reports(week: Week, runs: list[dict], until: datetime) -> None:
    from core.reports.runs import SENT
    from core.reports.slo import _deadline, _when

    days = [week.start.date() + timedelta(days=i) for i in range((until - week.start).days + 1)]
    sessions = [d for d in days if is_session_day(d) and _deadline(d) <= until]
    if not sessions:
        return
    on_time = 0
    for d in sessions:
        sent = [_when(r["finished_at"]) for r in runs if r["status"] == SENT and r["data_day"] == d.isoformat()]
        if any(t and t <= _deadline(d) for t in sent):
            on_time += 1
            continue
        started = [t for r in runs if (t := _when(r["started_at"])) and t.date() == d]
        task = datetime(d.year, d.month, d.day, 18, 30, tzinfo=ISTANBUL) + TASK_GRACE
        (week.pc_missed if not started or min(started) > task else week.other_missed).append(d)
    week.report = on_time / len(sessions)


def decide(runs_path: Path | None = None, beats_path: Path | None = None, now: datetime | None = None) -> Decision:
    from core.reports import runs as runs_module
    from core.reports import slo

    now = now or END
    runs_path = Path(runs_path or runs_module.RUNS_FILE)
    beats_path = Path(beats_path or slo.HEARTBEATS_FILE)
    runs = slo._rows(runs_path) if runs_path.exists() else []
    beats = sorted((t, r["pid"]) for r in (slo._rows(beats_path) if beats_path.exists() else [])
                   if (t := slo._when(r["at"])))
    weeks = []
    for start, end in WEEKS:
        week = Week(start, end)
        until = min(end, now)
        if until > start:
            _bot(week, beats, until)
            _reports(week, runs, until)
        weeks.append(week)
    return Decision(now, weeks)


def _pct(x: float | None) -> str:
    return "—" if x is None else f"%{x * 100:.1f}"


def format_decision(d: Decision) -> str:
    lines = ["🖥️ Sunucu kararı (DECISIONS K-23, ölçüt 27.10'da veri görülmeden yazıldı)"]
    if not d.complete:
        lines.append(f"⏳ Ölçüm penceresi henüz bitmedi ({END:%d.%m %H:%M}); aşağıdaki ara sonuçtur, karar değildir.")
    for i, w in enumerate(d.weeks, 1):
        if w.bot is None and w.report is None:
            lines.append(f"Hafta {i} ({w.start:%d.%m}–{w.end:%d.%m}): veri yok")
            continue
        lines.append(f"Hafta {i} ({w.start:%d.%m}–{w.end:%d.%m}): bot {_pct(w.bot)} (kesinti "
                     f"{w.down.total_seconds() / 3600:.1f} sa, PC kapalı/uykuda {w.sleep.total_seconds() / 3600:.1f} sa, "
                     f"20+ dk kesinti {w.long_gaps}), rapor {_pct(w.report)}"
                     + (f", PC'den kaçan: {', '.join(f'{x:%d.%m}' for x in w.pc_missed)}" if w.pc_missed else "")
                     + (f", başka nedenle: {', '.join(f'{x:%d.%m}' for x in w.other_missed)}" if w.other_missed else ""))
        lines += [f"  {r}" for r in w.reasons]
    if not d.complete:
        lines.append("Ara durum: " + ("şu ana kadar ölçüt aşıldı (yukarıdaki maddeler)." if d.server
                                      else "şu ana kadar ölçüt aşılmadı."))
    elif d.server:
        lines += ["KARAR: SUNUCU ÖNERİLİR. Kayıplar PC'den; hedefler gevşetilmez.",
                  "BENİM ADIMLARIM: sunucu kiralamak (ödeme) senin adımın, kurulum docs/SERVER.md. "
                  "Ücretsiz seçenek: PC'yi 7/24 açık ve uykusuz tutmak (Güç ayarları: uyku 'Hiçbir zaman')."]
    else:
        lines.append("KARAR: PC'DE KALINIR. PC kaynaklı kayıp ölçütü aşmadı; aylık yeniden bakılır.")
    return "\n".join(lines)


def due(day: date) -> bool:
    """The report of the window's last day carries the decision."""

    return day == END.date()


def main(argv: list[str] | None = None) -> int:
    from core.infrastructure.console import utf8_output
    from core.market.calendar import now_istanbul

    utf8_output()
    print(format_decision(decide(now=min(now_istanbul(), END))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["Decision", "Week", "decide", "due", "format_decision"]
