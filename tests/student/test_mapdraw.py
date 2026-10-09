"""The map picture: inline, escaped, and never more than 15 entries."""

from datetime import date

from lerni.student.interests import InterestMap, add_goal
from lerni.student.web.mapdraw import MAX_DRAWN, map_svg, map_words

TODAY = date(2026, 10, 10)


def test_names_are_escaped_and_the_picture_stays_small():
    m = InterestMap()
    add_goal(m, "Fractions")
    m.entries[0].name = 'x"><script>alert(1)</script>'  # as if a bad name got in
    for i in range(30):
        e = m.new_entry(f"Interest {i}", "interest")
        e.days = [TODAY.isoformat()] * 1
        m.entries.append(e)
    svg = map_svg(m, TODAY)
    assert svg.startswith("<svg") and "<script>" not in svg and "&lt;script&gt;" in svg
    assert svg.count("<circle") == MAX_DRAWN
    words = map_words(m, TODAY)
    assert "not yet" in words and "Interest 0" in words and "<script>" not in words
