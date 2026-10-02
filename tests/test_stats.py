import pytest

from app import stats
from conftest import assert_telegram_html, make_rows


def test_wilson_ci_known_values():
    pct, lo, hi = stats.wilson_ci(5, 10)
    assert pct == 50 and lo == pytest.approx(23.66, abs=0.05) and hi == pytest.approx(76.34, abs=0.05)
    assert stats.wilson_ci(0, 0) == (0.0, 0.0, 0.0)


def test_baseline_uses_first_measurement_per_subject():
    rows = make_rows(20)
    base = stats.baseline_rows(rows, require_labs=True)
    assert len(base) == 20  # 15 takroriy sub'ekt bir marta sanaladi
    first_visit = {r["user_id"]: r for r in sorted(rows, key=lambda r: r["created_at"])[::-1]}
    for r in base:
        assert r["created_at"] == first_visit[r["user_id"]]["created_at"]


def test_quick_mode_patients_are_separate_subjects():
    rows = [{"id": 1, "user_id": 1, "patient_name": "Ali Valiyev", "created_at": "2026-01-01 00:00:00", "homa_ir": 2},
            {"id": 2, "user_id": 1, "patient_name": "Olim Karimov", "created_at": "2026-01-02 00:00:00", "homa_ir": 3},
            {"id": 3, "user_id": 1, "patient_name": "ali  valiyev", "created_at": "2026-01-03 00:00:00", "homa_ir": 4}]
    assert len(stats.baseline_rows(rows)) == 2


def test_cohort_report_full():
    rows = make_rows(80)
    rep = stats.cohort_report(rows)
    assert rep["n_subjects"] == 80 and rep["n_labs"] == 80 and rep["n_records"] == 95
    assert rep["sex"]["M"] + rep["sex"]["F"] == 80
    o = rep["ir_overall"]
    assert 0 <= o["lo"] <= o["pct"] <= o["hi"] <= 100
    assert sum(k for _, k in rep["homa_classes"]) == 80
    bmi = next(c for c in rep["correlations"] if c["key"] == "bmi")
    assert bmi["rho"] > 0.3 and bmi["p"] < 0.05  # sintetik ma'lumotda bog'liqlik bor
    lo = rep["longitudinal"]
    assert lo["n"] == 15 and lo["delta"]["median"] < 0 and lo["p"] < 0.05
    keys = {t["key"] for t in rep["table1"]}
    assert {"age", "bmi", "homa_ir", "quicki", "findrisc"} <= keys
    assert "Tadqiqot xulosasi" in stats.format_summary(rep)


def test_cohort_report_tiny_and_empty():
    for rows in ([], make_rows(2)):
        rep = stats.cohort_report(rows)
        stats.format_summary(rep)
        assert rep["reference"]["p75"] is None


def test_fmt_p():
    assert stats.fmt_p(0.0001) == "<0.001" and stats.fmt_p(0.0456) == "0.046" and stats.fmt_p(None) == "—"


def test_wilson_ci_contains_point_estimate_at_extremes():
    for k, n in ((0, 7), (7, 7), (1, 1), (33, 33)):
        pct, lo, hi = stats.wilson_ci(k, n)
        assert lo <= pct <= hi


def test_summary_is_valid_telegram_html():
    """Regression: 'p<0.001' ekranlanmasa Telegram xabarni rad etadi."""
    text = stats.format_summary(stats.cohort_report(make_rows(80)))
    assert "p&lt;0.001" in text
    assert_telegram_html(text)
