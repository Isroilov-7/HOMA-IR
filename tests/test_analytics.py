from app.analytics import compute_changes, format_dynamics, verdict


def _row(i, homa, g=5.0, ins=10.0, date="2026-01-01 08:00:00"):
    return {"id": i, "homa_ir": homa, "fasting_glucose": g, "fasting_insulin": ins,
            "bmi": None, "waist": None, "findrisc": None, "created_at": date}


def test_verdict_thresholds():
    assert verdict(-15)[1] == "yaxshilandi"
    assert verdict(15)[1] == "yomonlashdi"
    assert verdict(5)[1] == "barqaror"
    assert verdict(None)[1] == "barqaror"


def test_changes_vs_previous_and_first():
    rows = [_row(3, 2.0, date="2026-07-01 08:00:00"), _row(2, 3.0, date="2026-04-01 08:00:00"),
            _row(1, 4.0, date="2026-01-01 08:00:00")]  # yangi → eski
    homa = next(c for c in compute_changes(rows) if c.key == "homa_ir")
    assert (homa.first, homa.prev, homa.last, homa.n) == (4.0, 3.0, 2.0, 3)
    assert round(homa.pct_prev) == -33 and round(homa.pct_first) == -50


def test_dynamics_text_single_and_multi():
    assert "kamida <b>2 ta</b>" in format_dynamics([_row(1, 2.0)])
    txt = format_dynamics([_row(2, 2.0, date="2026-04-01 08:00:00"), _row(1, 3.0)])
    assert "yaxshilandi" in txt and "Toifa o'zgardi" in txt
    assert "Hali natija yo'q" in format_dynamics([])
