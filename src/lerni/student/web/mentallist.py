"""A MentalMap as a list: add, open, rename, and remove goals and interests, or put them back.

The handlers are plain functions over the server-resolved viewer, so their role
checks can be tested without a browser; :func:`mental_list` draws the list with
``gr.render`` on My MentalMap and MentalMaps. The render itself gets no request,
so whose map it shows comes from a server-side State that only checked handlers set,
and every edit names that map, so it never lands on another account's.
"""

from __future__ import annotations

import re
import time
from contextlib import nullcontext
from datetime import date
from typing import Any

import gradio as gr
from gradio.context import get_blocks_context

from lerni.student.interests import (
    MAX_NAME,
    MAX_NOTES,
    STRENGTH_LABELS,
    Entry,
    InterestMap,
    MapError,
    MapStore,
    add_goal,
    add_interest,
    children,
    delete_for_good,
    details,
    family,
    group,
    not_the_same,
    parents,
    put_back,
    remove,
    rename,
    set_notes,
    strength,
    ungroup,
)
from lerni.student.results import ResultsLog
from lerni.student.signin import SignIn
from lerni.student.students import StudentStore
from lerni.student.web.accounts import PRIVATE, cleared
from lerni.student.web.maps import _act

# one draw at a time, server-wide: Gradio's block ids aren't safe across parallel draws
DRAW_QUEUE = {"concurrency_id": "mental-list", "concurrency_limit": 1}


def add_item(
    maps, students, viewer, requested, kind: str, name: str, notes: str, expected: str | None = None
) -> str:
    """Add a goal or an interest to a MentalMap this viewer may edit."""
    if kind == "Goal":
        change, done = (lambda m: add_goal(m, name, notes)), "Goal added."
    else:
        change, done = (lambda m: add_interest(m, name)), "Interest added."
    return _act(maps, students, viewer, requested, change, done, expected)


def remove_item(
    maps, students, viewer, requested, entry_id: str, expected: str | None = None
) -> str:
    """Remove an item; it waits in Removed, and Lerni steers away from a removed interest."""
    return _act(
        maps,
        students,
        viewer,
        requested,
        lambda m: remove(m, entry_id or ""),
        "Removed. Put it back from Removed any time.",
        expected,
    )


def put_back_item(maps, students, viewer, requested, name: str, expected: str | None = None) -> str:
    """Put a removed item back."""
    return _act(
        maps, students, viewer, requested, lambda m: put_back(m, name or ""), "Put back.", expected
    )


def delete_item(maps, students, viewer, requested, name: str, expected: str | None = None) -> str:
    """Delete a removed item's history for good; its name stays so it's never re-added."""
    return _act(
        maps,
        students,
        viewer,
        requested,
        lambda m: delete_for_good(m, name or ""),
        "Deleted for good.",
        expected,
    )


def rename_item(
    maps, students, viewer, requested, entry_id: str, name: str, expected: str | None = None
) -> str:
    """Rename an item."""
    return _act(
        maps,
        students,
        viewer,
        requested,
        lambda m: rename(m, entry_id or "", name),
        "Renamed.",
        expected,
    )


def save_notes(
    maps, students, viewer, requested, entry_id: str, notes: str, expected: str | None = None
) -> str:
    """Save a goal's notes for Lerni."""
    return _act(
        maps,
        students,
        viewer,
        requested,
        lambda m: set_notes(m, entry_id or "", notes),
        "Notes saved.",
        expected,
    )


def group_item(maps, students, viewer, requested, entry_id: str, group_name: str,
               expected: str | None = None) -> str:
    """Put an interest under a group on the same map."""
    def change(m: InterestMap) -> None:
        top = m.find(group_name or "")
        if top is None:
            raise MapError("Pick a group on the map.")
        group(m, entry_id or "", top.id)

    return _act(maps, students, viewer, requested, change, "Grouped.", expected)


def ungroup_item(maps, students, viewer, requested, entry_id: str, group_id: str,
                 expected: str | None = None) -> str:
    """Take an interest out of a group; the tagger won't put it back."""
    return _act(maps, students, viewer, requested,
                lambda m: ungroup(m, entry_id or "", group_id or ""), "Taken out.", expected)


def split_item(maps, students, viewer, requested, entry_id: str, name: str,
               expected: str | None = None) -> str:
    """Say one of an item's other names is not the same thing; it's never joined again."""
    return _act(maps, students, viewer, requested,
                lambda m: not_the_same(m, entry_id or "", name or ""), "Split off.", expected)


def _tree(m: InterestMap, items: list[Entry]) -> list[tuple[Entry, int]]:
    """Items in list order with their depth: each group, then its kinds (under its first group)."""
    ids, out, seen = {e.id for e in items}, [], set()

    def walk(e: Entry, depth: int) -> None:
        if e.id in seen:
            return
        seen.add(e.id)
        out.append((e, depth))
        for kid in (x for x in items if x.id in children(m, e.id)):
            walk(kid, depth + 1)

    for e in items:  # top-level items first, in the order they were added
        if not any(p in ids for p in parents(m, e.id)):
            walk(e, 0)
    for e in items:
        walk(e, 0)  # anything left (never expected): still listed
    return out


def bump() -> int:
    """A new list version: always different, so two quick edits both redraw."""
    return time.monotonic_ns()


LINK_KINDS = {"Bridges": "bridge", "Related": "related"}  # list headings with a link record


def _md(text: str) -> str:
    """Text shown as-is in Markdown: its formatting characters escaped."""
    return re.sub(r"([\\`*_{}\[\]()#+\-.!|<>~])", r"\\\1", text)


def _tie(tie: tuple[str, int, int] | None, bridge: bool) -> str:
    """ " 💪" for a link's strength; a bridge adds how it held ("· held 5 days · bounced once")."""
    if tie is None:
        return ""
    alive, held, bounced = tie
    text = " " + STRENGTH_LABELS[alive].split()[0]
    if bridge:
        text += f" · held {_plural(held, 'day')}"
        text += f" · bounced {'once' if bounced == 1 else f'{bounced} times'}" if bounced else ""
    return text


def _plural(n: int, word: str) -> str:
    return f"{n} {word}{'s' * (n != 1)}"


def mental_list(
    signin: SignIn,
    students: StudentStore,
    maps: MapStore,
    owner: gr.State,
    requested: Any,
    version: gr.State,
    pick_id: str,
    empty: str = "",
    results: ResultsLog | None = None,
    folded: bool = False,
    add_form: bool = True,
) -> None:
    """The add form, then 🎯 Goals and 💚 Interests as rows to open, rename, or remove.

    Args:
        owner: Whose map to draw, set only by checked handlers ("" for none yet).
        requested: What edits ask :func:`map_owner` for: a ``gr.State(None)`` for
            My MentalMap, or on MentalMaps the same server-side owner the list shows.
        version: Bumped by every change, so the list redraws.
        pick_id: The hidden field the picture writes a tapped item's id to (mapview.js).
        empty: What shows before there's a map to draw.
        results: The race results, for each goal's Practice line (None: no line).
        folded: Goals and Interests in closed sections (the educator's student page).
        add_form: The Goal/Interest add row (the student's page adds through Lerni instead).
    """
    opened = gr.State(None)  # the open item's id
    confirm = gr.State(None)  # (map owner, removed name) waiting for a second Delete tap
    unfolded = gr.State([])  # the folded sections the viewer opened, kept across redraws
    with gr.Row(elem_classes="lerni-add", visible=add_form):
        kind = gr.Radio(["Goal", "Interest"], value="Goal", show_label=False, scale=0)
        name = gr.Textbox(show_label=False, placeholder="Name", max_length=MAX_NAME, scale=2)
        notes = gr.Textbox(
            show_label=False, placeholder="Notes for Lerni (goals)", max_length=MAX_NOTES, scale=2
        )
        add = gr.Button("Add", variant="primary", scale=0, min_width=70)
    status = gr.Markdown()
    pick = gr.Textbox(elem_id=pick_id, elem_classes="lerni-hide", container=False)
    pick_go = gr.Button(elem_id=f"{pick_id}-go", elem_classes="lerni-hide")  # mapview.js presses

    def run(action: Any, req: Any, who: str, *args: Any, request: gr.Request) -> str:
        # every edit re-checks who's asking, and that it's the map they're looking at
        viewer = signin.viewer(request.username)
        return action(maps, students, viewer, req, *args, expected=who or None)

    def done(message: str, v: int) -> list[Any]:
        return [message, bump() if message.startswith("✅") else v]

    def on_add(
        k: str, n: str, t: str, req: Any, who: str, v: int, request: gr.Request
    ) -> list[Any]:
        message = run(add_item, req, who, k, n, t, request=request)
        return [message, *cleared(2, message.startswith("✅")), done(message, v)[1]]

    # a new map opens with nothing open and no Delete waiting for its second tap
    owner.change(lambda: (None, None), None, [opened, confirm], **PRIVATE)
    pick_go.click(lambda i: i or None, pick, opened, **PRIVATE)  # a tap on the picture
    add.click(
        on_add,
        [kind, name, notes, requested, owner, version],
        [status, name, notes, version],
        **PRIVATE,
    )

    def wire_groups(who: str, e_id: str, pick_group: Any, put: Any,
                    outs: list[tuple[str, Any]]) -> None:
        """An open interest's Put under, and Not under X for each group it's in."""

        def on_put(name: str, req: Any, v: int, request: gr.Request) -> list[Any]:
            return done(run(group_item, req, who, e_id, name, request=request), v)

        put.click(on_put, [pick_group, requested, version], [status, version], **PRIVATE)
        for group_id, btn in outs:

            def on_out(req: Any, v: int, request: gr.Request, g: str = group_id) -> list[Any]:
                return done(run(ungroup_item, req, who, e_id, g, request=request), v)

            btn.click(on_out, [requested, version], [status, version], **PRIVATE)

    def wire_splits(who: str, e_id: str, splits: list[tuple[str, Any]]) -> None:
        """An open item's Not the same, one per other name."""
        for alias, btn in splits:

            def on_split(req: Any, v: int, request: gr.Request, a: str = alias) -> list[Any]:
                return done(run(split_item, req, who, e_id, a, request=request), v)

            btn.click(on_split, [requested, version], [status, version], **PRIVATE)

    def wire(who: str, e_id: str, row: Any, trash: Any, edits: tuple[Any, ...] = ()) -> None:
        """One item's events; edits are (name box, Rename, notes box, Save) when it's open."""

        def on_remove(req: Any, v: int, request: gr.Request) -> list[Any]:
            return done(run(remove_item, req, who, e_id, request=request), v)

        trash.click(on_remove, [requested, version], [status, version], **PRIVATE)
        row.click(lambda o: None if o == e_id else e_id, opened, opened, **PRIVATE)
        if not edits:
            return
        name_box, rename_btn, notes_box, notes_btn = edits

        def on_rename(new: str, req: Any, v: int, request: gr.Request) -> list[Any]:
            return done(run(rename_item, req, who, e_id, new, request=request), v)

        rename_btn.click(on_rename, [name_box, requested, version], [status, version], **PRIVATE)
        if notes_btn is not None:

            def on_notes(text: str, req: Any, v: int, request: gr.Request) -> list[Any]:
                return done(run(save_notes, req, who, e_id, text, request=request), v)

            notes_btn.click(on_notes, [notes_box, requested, version], [status, version], **PRIVATE)

    def back_button(who: str, gone: str, has_history: bool, sure: bool) -> None:
        """A removed item's row: Put back, and Delete for good (two taps) if it has a history."""
        with gr.Row(elem_classes="lerni-item"):
            gr.Markdown(gone, key=f"gone-{gone}")
            back = gr.Button("Put back", size="sm", scale=0, min_width=90, key=f"back-{gone}")
            if has_history:
                wipe = gr.Button(
                    "Tap again to delete" if sure else "Delete for good",
                    size="sm",
                    scale=0,
                    min_width=90,
                    variant="stop",
                    key=f"wipe-{gone}",
                )

                def on_wipe(req: Any, v: int, request: gr.Request) -> list[Any]:
                    if not sure:
                        return ["", v, (who, gone)]  # ask once more: it can't be undone
                    return [*done(run(delete_item, req, who, gone, request=request), v), None]

                wipe.click(on_wipe, [requested, version], [status, version, confirm], **PRIVATE)

        def on_back(req: Any, v: int, request: gr.Request) -> list[Any]:
            return done(run(put_back_item, req, who, gone, request=request), v)

        back.click(on_back, [requested, version], [status, version], **PRIVATE)

    # opening or closing a section isn't a redraw, so `unfolded` is read but doesn't trigger
    root = get_blocks_context().root_block
    triggers = [root.load, owner.change, version.change, opened.change, confirm.change]

    @gr.render(inputs=[owner, version, opened, confirm, unfolded], triggers=triggers,
               **DRAW_QUEUE)
    def draw(who: str, _v: int, open_id: str | None, sure_of: tuple[str, str] | None,
             shown: list[str]) -> None:
        if not who:
            gr.Markdown(empty)
            return
        m, today = maps.get(who), date.today()
        for title, kind_ in (("🎯 Goals", "goal"), ("💚 Interests", "interest")):
            items = [e for e in m.entries if e.kind == kind_]
            # folded (the student's page): closed sections, open as left or while editing
            unfold = kind_ in shown or any(e.id == open_id for e in items)
            with (gr.Accordion(f"{title} ({len(items)})", open=unfold, key=f"fold-{kind_}")
                  if folded else nullcontext()) as fold:
                if fold:  # remember it open or shut for the next redraw
                    fold.expand(lambda s, k=kind_: sorted({*s, k}), unfolded, unfolded, **PRIVATE)
                    fold.collapse(lambda s, k=kind_: [x for x in s if x != k], unfolded,
                                  unfolded, **PRIVATE)
                if not folded:  # open lists keep their heading
                    gr.Markdown(f"**{title}**" + ("" if items else ": none yet"),
                                key=f"h-{kind_}")
                for e, depth in _tree(m, items):
                    with gr.Row(elem_classes="lerni-item"):
                        alive = STRENGTH_LABELS[strength(e, today, m)]
                        label = "↳ " * depth + f"{e.name} · {alive}"
                        row = gr.Button(label, scale=1, key=f"open-{e.id}")
                        trash = gr.Button("🗑", scale=0, min_width=48, key=f"rm-{e.id}")
                    if open_id != e.id:
                        wire(who, e.id, row, trash)
                        continue
                    d = details(m, e.id, today)  # the open item: its facts, then edits and links
                    facts = [
                        STRENGTH_LABELS[d.strength],
                        f"came up on {_plural(d.days, 'day')}"
                        + (f" (counting {', '.join(d.through[:3])})" if d.through else "")
                        + (f", last on {d.last}" if d.last else ""),
                    ]
                    if e.kind == "goal":
                        facts.append(f"explained on {_plural(d.explained, 'day')} (Lerni's guess)")
                        facts += ["Lerni is giving it a rest"] if d.resting else []
                        # read for the open goal only, never on every redraw
                        p = results.practice(who, e.id, today) if results else None
                        if p is not None:  # how racing on it is going, read-only
                            parts = [f"raced {p.last}"] + ([f"this week {p.right}/{p.asked}"]
                                                           if p.asked else [])
                            # Claude's labels, shown as plain text
                            missed = ", ".join(_md(c) for c in p.missed)
                            parts += [f"missed lately: {missed}"] if p.missed else []
                            facts.append("Practice: " + " · ".join(parts))
                    # the list and item in a class, so a picture tap can scroll to it (mapview.js)
                    with gr.Column(elem_classes=["lerni-detail", f"{pick_id}-{e.id}"],
                                   key=f"d-{e.id}"):
                        gr.Markdown(" · ".join(facts), key=f"facts-{e.id}")
                        notes_box = notes_btn = None
                        if e.kind == "goal":
                            notes_box = gr.Textbox(
                                e.notes,
                                label="Notes for Lerni",
                                max_length=MAX_NOTES,
                                key=f"notes-{e.id}",
                            )
                            notes_btn = gr.Button("Save notes", size="sm", key=f"save-{e.id}")
                        name_box = gr.Textbox(
                            e.name, label="Name", max_length=MAX_NAME, key=f"name-{e.id}"
                        )
                        rename_btn = gr.Button("Rename", size="sm", key=f"ren-{e.id}")
                        if e.aliases:  # other names the student used: one item, split if wrong
                            gr.Markdown("**Also called** " + ", ".join(e.aliases),
                                        key=f"aka-{e.id}")
                            wire_splits(who, e.id, [
                                (a, gr.Button(f"Not the same: {a}", size="sm",
                                              key=f"ns-{e.id}-{i}"))
                                for i, a in enumerate(e.aliases)])
                        if e.kind == "interest":  # its groups: put it under one, or take it out
                            mine = {x.id for x in family(m, e)} | set(parents(m, e.id))
                            options = [x.name for x in m.entries
                                       if x.kind == "interest" and x.id not in mine]
                            with gr.Row(key=f"g-{e.id}"):
                                pick_group = gr.Dropdown(options, value=None, label="Kind of",
                                                         key=f"gp-{e.id}", scale=2)
                                put = gr.Button("Put under", size="sm", scale=1, key=f"gu-{e.id}")
                            outs = [(gid, gr.Button(f"Not under {gname}", size="sm",
                                                    key=f"go-{e.id}-{gid}"))
                                    for gid, gname in d.groups]
                            wire_groups(who, e.id, pick_group, put, outs)
                        for heading, ends in (("Kinds", d.kinds), ("Bridges", d.bridges),
                                              ("Related", d.related)):
                            if ends:
                                gr.Markdown(f"**{heading}**", key=f"{heading}-{e.id}")
                            for other_id, other in ends:  # a tap opens the other end
                                tie = d.ties.get((LINK_KINDS.get(heading, ""), other_id))
                                jump = gr.Button(
                                    f"→ {other}" + _tie(tie, heading == "Bridges"),
                                    size="sm", key=f"j-{e.id}-{heading}-{other_id}"
                                )
                                jump.click(lambda i=other_id: i, None, opened, **PRIVATE)
                    wire(who, e.id, row, trash, (name_box, rename_btn, notes_box, notes_btn))
        if m.removed:
            with gr.Accordion(
                f"Removed ({len(m.removed)})", open=sure_of is not None, key="removed"
            ):
                for gone in m.removed:
                    info = m.removed_info.get(gone.casefold(), {})
                    back_button(who, gone, set(info) - {"kind"} != set(), sure_of == (who, gone))
        if m.archived:  # rested to make room on a full map; read only
            with gr.Accordion(f"Older interests ({len(m.archived)})", open=False, key="resting"):
                lines = [f"- {a.name} · {_plural(len(a.days), 'day')}"
                         for a in reversed(m.archived)]
                gr.Markdown("Back with its history when it comes up again.\n\n" + "\n".join(lines),
                            key="resting-list")
