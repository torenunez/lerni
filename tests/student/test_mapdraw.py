"""The map picture: inline, escaped, every entry, and the same layout every time."""

from datetime import date

from lerni.student.interests import InterestMap, add_goal
from lerni.student.web.mapdraw import map_svg

TODAY = date(2026, 10, 10)


def test_every_entry_is_drawn_escaped_in_the_same_place_each_time():
    m = InterestMap()
    add_goal(m, "Fractions")
    m.entries[0].name = 'x"><script>alert(1)</script>'  # as if a bad name got in
    for i in range(30):
        e = m.new_entry(f"Interest {i}", "interest")
        e.days = [TODAY.isoformat()]
        m.entries.append(e)
    svg = map_svg(m, TODAY, "k")
    assert "<script>" not in svg and "&lt;script&gt;" in svg
    assert svg.count("<circle") == 31 and 'data-id="e31"' in svg  # no longer capped at 15
    assert map_svg(m, TODAY, "k") == svg  # a redraw never moves anything
