"""Checks that the numbers and the calendar hold together."""
from pipeline.build import compute, load

m = load()
c = compute(m)


def test_five_colleges_five_days():
    assert [d["key"] for d in m["days"]] == ["mon", "tue", "wed", "thu", "fri"]
    assert len({d["college"] for d in m["days"]}) == 5


def test_option_costs():
    r = m["rates"]
    A, B = c["options"]["A"], c["options"]["B"]
    assert B["wtu_sem"] == 15 and A["wtu_sem"] == 21
    assert round(B["faculty"]) == round(30 * r["wtu_cost"]) == 74652
    assert round(A["faculty"]) == round(42 * r["wtu_cost"]) == 104513
    assert c["students"] == 60 * 32 * 18 == 34560
    assert round(B["total"]) == 113475 and round(A["total"]) == 143336
    assert round(A["gap"]) == 37550 and round(B["gap"]) == 7689


def test_hours():
    assert c["lead_hours_sem"] == 135 and c["lead_hours_week"] == 9
    assert c["options"]["B"]["hours_sem"] == 675 and c["options"]["A"]["hours_sem"] == 945
    assert c["pool_hours_day"] == 12 and c["college_days_sem"] == 75


def test_no_overlapping_blocks_and_every_day_complete():
    for d in m["days"]:
        blocks = sorted(m["schedule"][d["key"]], key=lambda b: b["start"])
        for a, b in zip(blocks, blocks[1:]):
            assert a["end"] <= b["start"], (d["key"], a["label"], b["label"])
        kinds = {b["kind"] for b in blocks}
        assert {"college", "catapult"} <= kinds, d["key"]
        assert all(7.5 <= b["start"] < b["end"] <= 17 for b in blocks)


def test_two_speaker_series_on_different_days():
    days = [k for k, bl in m["schedule"].items() if any(b["kind"] == "speaker" for b in bl)]
    assert days == ["tue", "thu"]


def test_five_student_groups_weekly():
    assert len({d["group"] for d in m["days"]}) == 5
