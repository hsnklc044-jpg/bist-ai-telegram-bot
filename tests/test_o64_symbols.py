"""Self-audit 11 (17.11.2026), Ö64: Turkish capital İ in /risk and /senaryo."""

import pytest

from core.alerts import budget as B
from core.analytics import scenarios as S


@pytest.mark.parametrize("word", ["İSCTR", "ŞAHOL"])
def test_risk_add_rejects_a_non_ascii_symbol_instead_of_inventing_one(word):
    """Ö64: 'İSCTR' became 'İSCTR.IS', a ticker that does not exist, without an error."""
    with pytest.raises(ValueError):
        B.parse_args(["ekle", word, "5"])


def test_risk_add_still_accepts_normal_symbols():
    assert B.parse_args(["ekle", "isctr", "5"]) == ("add", "paper", ("ISCTR.IS", 5.0))


def test_scenario_rejects_a_non_ascii_symbol():
    with pytest.raises(ValueError):
        S.parse_args(["İSCTR"])
