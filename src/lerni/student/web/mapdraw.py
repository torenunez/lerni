"""The map, drawn: an inline SVG picture (the list is ``mentallist.py``; taps: ``mapview.js``).

Linked entries settle near each other and goals stay in the middle, from a seeded
spring layout, so the same map always draws the same picture. Returned as text to
a viewer already allowed to see the map; never saved as a file (Gradio serves
files to anyone signed in). Every name is escaped, and styles are attributes
because Gradio strips <style> from HTML.
"""

from __future__ import annotations

import hashlib
import html
import math
from datetime import date
from functools import lru_cache

from lerni.student.interests import InterestMap, backed_off, faded, strength

GREEN, CORAL, GREY, DARK = "#009E73", "#D55E00", "#9a9a9a", "#555555"  # color-blind safe
SIZE = 400
CENTER = SIZE / 2
RADII = {"strong": 20, "growing": 14, "faint": 10, "not yet": 11}  # the list's strength
SPACING = 42  # how far apart linked entries settle
GOAL_RING = 45  # goals sit on a small ring in the middle
LABEL_H = 18  # the label under a circle, with a little room


def owner_key(owner: str) -> str:
    """A short, opaque key for the page to remember zoom per map (never the username)."""
    return hashlib.sha256(owner.encode()).hexdigest()[:10]


def _seed(entry_id: str) -> tuple[float, float]:
    """A start position from the id alone, so a redraw starts (and ends) the same."""
    h = hashlib.sha256(entry_id.encode()).digest()
    return CENTER + (h[0] / 255 - 0.5) * 240, CENTER + (h[1] / 255 - 0.5) * 240


@lru_cache(maxsize=64)
def _layout(
    entries: tuple[tuple[str, str, int, int], ...], links: tuple[tuple[str, str, bool], ...]
) -> dict[str, tuple[float, float]]:
    """Positions for (id, kind, radius, label width) entries joined by (a, b, close) links."""
    goals = [e[0] for e in entries if e[1] == "goal"]
    pos = {e[0]: list(_seed(e[0])) for e in entries}
    for n, g in enumerate(goals):  # pinned: the middle of the picture
        angle = 2 * math.pi * n / len(goals) - math.pi / 2
        ring = 0 if len(goals) == 1 else max(GOAL_RING, 16 * len(goals))  # room for labels
        pos[g] = [CENTER + ring * math.cos(angle), CENTER + ring * math.sin(angle)]
    pinned, ids = set(goals), [e[0] for e in entries]
    step = 20.0
    for _ in range(250):  # a spring layout: links pull, everything pushes apart
        move = {i: [0.0, 0.0] for i in ids}
        for x, a in enumerate(ids):
            for b in ids[x + 1 :]:
                dx, dy = pos[a][0] - pos[b][0], pos[a][1] - pos[b][1]
                dist = max(math.hypot(dx, dy), 0.01)
                push = SPACING**2 / dist * (4 if a in pinned or b in pinned else 1)
                move[a][0] += dx / dist * push
                move[a][1] += dy / dist * push
                move[b][0] -= dx / dist * push
                move[b][1] -= dy / dist * push
        for a, b, close in links:  # a kind sits close to its group
            dx, dy = pos[a][0] - pos[b][0], pos[a][1] - pos[b][1]
            dist = max(math.hypot(dx, dy), 0.01)
            pull = dist**2 / (SPACING * (0.6 if close else 1))
            move[a][0] -= dx / dist * pull
            move[a][1] -= dy / dist * pull
            move[b][0] += dx / dist * pull
            move[b][1] += dy / dist * pull
        for i in ids:
            if i in pinned:
                continue
            move[i][0] -= (pos[i][0] - CENTER) * 1.6  # a gentle pull to the middle
            move[i][1] -= (pos[i][1] - CENTER) * 1.6
            length = max(math.hypot(*move[i]), 0.01)
            pos[i][0] += move[i][0] / length * min(length, step)
            pos[i][1] += move[i][1] / length * min(length, step)
        step *= 0.985
    size = {e[0]: (max(2 * e[2], e[3]), 2 * e[2] + LABEL_H) for e in entries}
    for _ in range(200):  # then nudge apart circles and labels that still overlap
        for x, a in enumerate(ids):
            for b in ids[x + 1 :]:
                over_x = (size[a][0] + size[b][0]) / 2 + 4 - abs(pos[a][0] - pos[b][0])
                over_y = (size[a][1] + size[b][1]) / 2 + 2 - abs(pos[a][1] - pos[b][1])
                if over_x <= 0 or over_y <= 0:
                    continue
                axis, over = (0, over_x) if over_x < over_y else (1, over_y)
                sign = 1 if pos[a][axis] >= pos[b][axis] else -1
                share = 0 if a in pinned else 1 if b in pinned else 0.5
                pos[a][axis] += sign * over * share
                pos[b][axis] -= sign * over * (1 - share)
    return {i: (pos[i][0], pos[i][1]) for i in ids}


def _frame(at: dict[str, tuple[float, float]], boxes: dict[str, tuple[float, float]]) -> str:
    """A square viewBox around every circle and label, so nothing is cut off or squeezed."""
    left = min(at[i][0] - boxes[i][0] / 2 for i in at) - 6
    right = max(at[i][0] + boxes[i][0] / 2 for i in at) + 6
    top = min(at[i][1] - boxes[i][1] / 2 for i in at) - 6
    bottom = max(at[i][1] + boxes[i][1] / 2 for i in at) + 10
    side = max(right - left, bottom - top, SIZE * 0.6)  # a small map isn't blown up
    x, y = (left + right - side) / 2, (top + bottom - side) / 2
    return f"{x:.0f} {y:.0f} {side:.0f} {side:.0f}"


def map_svg(m: InterestMap, today: date, key: str = "") -> str:
    """The picture: green interests, coral goals, dashed bridges, grey related lines.

    Args:
        key: :func:`owner_key` of whose map it is, so the page keeps its zoom per map.
    """
    if not m.entries:
        return ""
    radius = {e.id: RADII[strength(e, today, m)] for e in m.entries}  # a group counts its kinds
    shown = [k for k in m.links if k.kind != "not_kind_of"]  # an undone group isn't drawn
    shape = tuple((e.id, e.kind, radius[e.id], len(e.name) * 6 + 4) for e in m.entries)
    at = _layout(shape, tuple((k.a, k.b, k.kind == "kind_of") for k in shown))
    frame = _frame(at, {e[0]: (max(2 * e[2], e[3]), 2 * e[2] + LABEL_H) for e in shape})
    parts = [
        f'<div class="lerni-map-wrap" data-key="{html.escape(key)}">',
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{frame}" width="100%" '
        'style="touch-action: pan-x pan-y" role="img" '
        'aria-label="MentalMap picture; the list below says the same">',
    ]
    for k in shown:
        if k.a in at and k.b in at:
            (x1, y1), (x2, y2) = at[k.a], at[k.b]
            style = {
                "bridge": f'stroke="{CORAL}" stroke-width="2" stroke-dasharray="6 4"',
                "kind_of": f'stroke="{DARK}" stroke-width="2"',  # a kind and its group
            }.get(k.kind, f'stroke="{GREY}" stroke-width="1"')
            parts.append(
                f'<line data-a="{k.a}" data-b="{k.b}" data-k="{k.kind}" '
                f'x1="{x1:.0f}" y1="{y1:.0f}" '
                f'x2="{x2:.0f}" y2="{y2:.0f}" {style}/>'
            )
    for e in m.entries:
        (x, y), r = at[e.id], radius[e.id]
        color = GREEN if e.kind == "interest" else CORAL
        fill = "white" if e.kind == "goal" and not e.days else color  # not discussed yet
        dash = ' stroke-dasharray="4 3"' if e.kind == "goal" and backed_off(e, today) else ""
        opacity = "0.4" if faded(e, today, m) else "1"
        parts.append(
            f'<g class="lerni-node" data-id="{e.id}" opacity="{opacity}">'
            f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r}" fill="{fill}" '
            f'stroke="{color}" stroke-width="3"{dash}/>'
            f'<text x="{x:.0f}" y="{y + r + 12:.0f}" text-anchor="middle" '
            # the theme's text color, so names read in dark mode too
            f'font-size="11" fill="currentColor">{html.escape(e.name)}</text></g>'
        )
    parts.append('</svg><button class="lerni-map-reset" type="button">Reset view</button></div>')
    return "".join(parts)
