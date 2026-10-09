"""The map, drawn: an inline SVG picture and the same in words.

Returned as text to a viewer already allowed to see the map; never saved as a
file (Gradio serves files to anyone signed in). Every name is escaped, and
styles are attributes because Gradio strips <style> from HTML.
"""

from __future__ import annotations

import html
import math
from datetime import date

from lerni.student.interests import Entry, InterestMap, faded

MAX_DRAWN = 15
GREEN, CORAL, GREY = "#009E73", "#D55E00", "#9a9a9a"  # color-blind safe pair
SIZE, CENTER, RING = 360, 180, 125
RADII = (16, 24, 32)  # three sizes


def _size(e: Entry) -> int:
    count = len(e.explained) if e.kind == "goal" else len(e.days)
    return RADII[0] if count <= 1 else RADII[1] if count <= 4 else RADII[2]


def _drawn(m: InterestMap) -> list[Entry]:
    goals = [e for e in m.entries if e.kind == "goal"]
    interests = sorted((e for e in m.entries if e.kind == "interest"), key=lambda e: -len(e.days))
    chosen = {e.id for e in [*goals, *interests][:MAX_DRAWN]}
    return [e for e in m.entries if e.id in chosen]  # creation order: a stable layout


def map_svg(m: InterestMap, today: date) -> str:
    """The picture: green interests, coral goals, dashed bridges, grey related lines."""
    drawn = _drawn(m)
    if not drawn:
        return ""
    at = {}
    for i, e in enumerate(drawn):  # a ring in creation order, so nothing jumps on refresh
        angle = 2 * math.pi * i / len(drawn) - math.pi / 2
        at[e.id] = (CENTER + RING * math.cos(angle), CENTER + RING * math.sin(angle))
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {SIZE} {SIZE}" '
             f'width="100%" role="img" aria-label="Interest map; the list below says the same">']
    for k in m.links:
        if k.a in at and k.b in at:
            (x1, y1), (x2, y2) = at[k.a], at[k.b]
            style = (f'stroke="{CORAL}" stroke-width="2" stroke-dasharray="6 4"'
                     if k.kind == "bridge" else f'stroke="{GREY}" stroke-width="1"')
            parts.append(f'<line x1="{x1:.0f}" y1="{y1:.0f}" x2="{x2:.0f}" y2="{y2:.0f}" {style}/>')
    for e in drawn:
        x, y = at[e.id]
        color = GREEN if e.kind == "interest" else CORAL
        # a goal not discussed yet is only outlined
        fill = "white" if e.kind == "goal" and not e.days else color
        opacity = "0.35" if faded(e, today) else "1"
        parts.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{_size(e)}" fill="{fill}" '
                     f'stroke="{color}" stroke-width="3" opacity="{opacity}"/>')
        parts.append(f'<text x="{x:.0f}" y="{y + _size(e) + 14:.0f}" text-anchor="middle" '
                     f'font-size="12" fill="#222">{html.escape(e.name)}</text>')
    parts.append("</svg>")
    return "".join(parts)


def map_words(m: InterestMap, today: date) -> str:
    """The same map in words (Markdown), so it reads without colors or sizes."""
    names = {e.id: e.name for e in m.entries}
    lines = []
    for g in (e for e in m.entries if e.kind == "goal"):
        state = ("not yet" if not g.days else
                 f"explained on {len(g.explained)} day{'s' * (len(g.explained) > 1)} "
                 "(Lerni's guess)" if g.explained else "came up")
        froms = sorted({names[k.a] for k in m.links if k.kind == "bridge" and k.b == g.id})
        bridge = f", from {', '.join(html.escape(f) for f in froms)}" if froms else ""
        lines.append(f"- 🎯 **{html.escape(g.name)}**: {state}{bridge}")
    for e in sorted((e for e in m.entries if e.kind == "interest"), key=lambda e: -len(e.days)):
        fade = ", not lately" if faded(e, today) else ""
        lines.append(f"- 💚 {html.escape(e.name)}: {len(e.days)} day"
                     f"{'s' * (len(e.days) != 1)}{fade}")
    return "\n".join(lines) or "Nothing yet: talk with Lerni, or add a goal."
