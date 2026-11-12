"""v4.6: the map picture shows general interests only, sized by their days."""

import re
from datetime import date, timedelta

from lerni.student.interests import InterestMap, Link, add_goal, add_interest, group, roots
from lerni.student.web.mapdraw import map_svg

TODAY = date(2026, 11, 12)


def days(n: int) -> list[str]:
    return sorted((TODAY - timedelta(days=i)).isoformat() for i in range(n))


def test_roots_climbs_to_the_top_level_groups():
    m = InterestMap()
    animals, sharks, bull = (add_interest(m, n) for n in ("animals", "sharks", "bull shark"))
    ocean, orca, trains = (add_interest(m, n) for n in ("ocean", "orca", "trains"))
    group(m, sharks.id, animals.id)
    group(m, bull.id, sharks.id)  # bull shark › sharks › animals
    group(m, orca.id, animals.id)
    group(m, orca.id, ocean.id)  # in two groups
    assert roots(m, bull.id) == [animals.id]
    assert roots(m, trains.id) == [trains.id]  # in no group: itself
    assert roots(m, orca.id) == sorted([animals.id, ocean.id])


def test_roots_never_loops_forever_on_a_stored_loop():
    m = InterestMap()
    a, b = add_interest(m, "cars"), add_interest(m, "race cars")
    day = "2026-11-01"
    m.links += [Link(a.id, b.id, "kind_of", day), Link(b.id, a.id, "kind_of", day)]
    assert roots(m, a.id) and roots(m, b.id)  # returns, never empty


def test_the_picture_shows_general_interests_sized_by_their_days():
    m = InterestMap()
    goal = add_goal(m, "Telling time")
    trains, steam, soccer = (add_interest(m, n) for n in ("trains", "steam trains", "soccer"))
    group(m, steam.id, trains.id)
    steam.days, soccer.days = days(9), days(1)  # only the kind came up, on 9 days
    m.links.append(Link(steam.id, goal.id, "bridge", TODAY.isoformat()))  # bridged from the kind
    svg = map_svg(m, TODAY, "k")
    assert f'data-id="{steam.id}"' not in svg  # the kind stays in the list
    assert f'data-a="{trains.id}" data-b="{goal.id}" data-k="bridge"' in svg  # its bridge moves up

    def r(entry_id: str) -> int:
        return int(re.search(rf'data-id="{entry_id}".*?r="(\d+)"', svg).group(1))  # its circle

    assert r(trains.id) > r(soccer.id)  # a group counts its kinds' days
