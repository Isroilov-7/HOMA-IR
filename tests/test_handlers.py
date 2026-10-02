from app.calculator import quick_report
from app.handlers.history import patients, rows_for
from app.handlers.quick import compare_line, format_quick, read_glucose, read_insulin


def test_read_glucose_units_and_ranges():
    assert read_glucose("5,4")[0] == 5.4
    g, note = read_glucose("97 mg/dl")
    assert round(g, 2) == 5.38 and "mg/dL" in note
    assert read_glucose("abc")[0] is None
    assert read_glucose("1.0")[0] is None
    assert read_insulin("11.2")[0] == 11.2 and read_insulin("0")[0] is None


def test_format_quick_escapes_name():
    rep = quick_report(glucose=5.0, insulin=10)
    txt = format_quick(1, "<b>Ali</b>", 30, 5.0, 10.0, rep)
    assert "&lt;b&gt;Ali" in txt and "HOMA-IR: 2.22" in txt


def test_compare_line():
    assert compare_line(None, 2.0) == ""
    assert "yaxshilandi" in compare_line({"homa_ir": 3.0}, 2.0)


def test_patients_grouping_case_insensitive():
    rows = [{"patient_name": "Ali Vali"}, {"patient_name": "ali  vali"}, {"patient_name": "Olim"}]
    assert patients(rows) == ["Ali Vali", "Olim"]
    assert len(rows_for(rows, "ALI VALI")) == 2
