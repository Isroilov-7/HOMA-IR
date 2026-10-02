import pytest

from app import calculator as c


def test_homa_ir_matthews_formula():
    # 5.0 mmol/L × 10 μU/mL / 22.5 = 2.222
    assert c.calculate_homa_ir(5.0, 10.0) == pytest.approx(2.2222, abs=1e-4)


@pytest.mark.parametrize("v,cls", [(1.99, "normal"), (2.0, "chegara"), (2.49, "chegara"),
                                   (2.5, "insulin rezistentligi"), (3.8, "yuqori insulin rezistentligi")])
def test_homa_classes_boundaries(v, cls):
    assert c.classify_homa_ir(v) == cls


def test_homa_level_matches_class():
    assert [c.homa_ir_level(v) for v in (1.0, 2.2, 3.0, 5.0)] == [0, 1, 2, 3]


def test_homa_beta():
    # 20 × 10 / (5.5 − 3.5) = 100%
    assert c.calculate_homa_beta(5.5, 10) == pytest.approx(100.0)
    assert c.calculate_homa_beta(3.4, 10) is None


def test_quicki_known_value():
    # glukoza 5.0 mmol/L = 90.08 mg/dL; insulin 10 → 1/(1 + 1.9546) = 0.3385
    q = c.calculate_quicki(5.0, 10.0)
    assert q == pytest.approx(0.3385, abs=1e-3)
    assert c.classify_quicki(q) == "insulin rezistentligi"


@pytest.mark.parametrize("g,cls", [(3.5, "past (gipoglikemiya chegarasi)"), (5.5, "normal"),
                                   (5.6, "prediabet (IFG)"), (6.9, "prediabet (IFG)"),
                                   (7.0, "diabet diapazoni")])
def test_glucose_classes(g, cls):
    assert c.classify_glucose(g) == cls


def test_glucose_mgdl_autoconvert():
    g, conv = c.glucose_from_input(90.08)
    assert conv and g == pytest.approx(5.0, abs=0.01)
    assert c.glucose_from_input(5.4) == (5.4, False)


def test_findrisc_max_is_26():
    score, band = c.calculate_findrisc(age=70, bmi=35, waist=110, sex="M", activity_yes=False,
                                       veg_daily=False, bp_meds=True, high_glucose_hist=True,
                                       family_hx="first")
    assert (score, band) == (26, "juda yuqori")


def test_findrisc_min_is_0():
    assert c.calculate_findrisc(age=30, bmi=22, waist=70, sex="F", activity_yes=True, veg_daily=True,
                                bp_meds=False, high_glucose_hist=False, family_hx="none") == (0, "past")


def test_whtr():
    assert c.classify_whtr(c.calculate_whtr(85, 170)) == "oshgan xavf"  # 0.50


def test_quick_report_flags_diabetic_glucose():
    rep = c.quick_report(glucose=7.4, insulin=20)
    assert rep["level"] == 3
    assert any("7.0" in r for r in rep["recommendations"])


def test_combined_report_glucose_recommendation():
    rep = c.combined_risk_report(findrisc=5, findrisc_band="past", homa_ir=None, bmi=22,
                                 waist=70, sex="F", glucose=6.1)
    assert any("prediabet" in r for r in rep["recommendations"])
