"""S4 dry run finding (18.11.2026): one number format in the decision, the draft and the drift reasons."""

import math

from core.reports import s4_decision as s4


def test_percentages_use_the_report_format():
    assert s4._p(0.0149) == "+%1,49"
    assert s4._p(-0.0005) == "-%0,05"
    assert s4._p(0.0) == "+%0,00"


def test_missing_values_stay_a_dash():
    assert s4._p(None) == "—"
    assert s4._p(math.nan) == "—"


def test_draft_dates_are_day_month_year():
    decision = {"views": [], "first_day": "2026-11-02", "last_day": "2027-01-04"}
    from datetime import date

    text = s4.research_log_draft(date(2027, 1, 6), decision)
    assert "kayıt günleri 02.11.2026 – 04.01.2027" in text
