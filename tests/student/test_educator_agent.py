"""The educator agent: its reply hides a proposals block; only ticked proposals change a map."""

from lerni.student.educator_agent import (
    EducatorProposal,
    apply_educator_proposals,
    parse_educator_proposals,
    split_reply,
    visible_pieces,
)
from lerni.student.interests import InterestMap, add_goal, add_interest

BLOCK = (
    '```proposals\n{"proposals": ['
    '{"kind": "goal", "name": "fractions", "notes": "through baking"},'
    '{"kind": "reword", "name": "telling time", "notes": "with the kitchen clock"},'
    '{"kind": "remove", "name": "monster trucks"},'
    '{"kind": "feedback", "notes": "the talk button is hard to press"},'
    '{"kind": "goal", "name": "Mateo Smith!!"}'
    "]}\n```"
)


def test_a_reply_becomes_text_plus_checked_proposals_and_only_ticked_ones_apply():
    m = InterestMap()
    add_goal(m, "telling time")
    add_interest(m, "monster trucks")
    text, raw = split_reply("Here are some ideas.\n\n" + BLOCK)
    assert text == "Here are some ideas."
    found = parse_educator_proposals(raw, m)
    assert [p.kind for p in found] == ["goal", "reword", "remove", "feedback"]  # bad name dropped
    added, skipped = apply_educator_proposals(m, [found[0], found[1]])  # ticked two
    assert added == 2 and skipped == []
    assert m.find("fractions").notes == "through baking"
    assert m.find("telling time").notes == "with the kitchen clock"
    assert m.find("monster trucks") is not None  # not ticked: still there


def test_a_broken_or_missing_block_gives_no_proposals_and_no_error():
    m = InterestMap()
    assert split_reply("Just talking.") == ("Just talking.", "")
    assert parse_educator_proposals("", m) == []
    assert parse_educator_proposals('```proposals\n{"proposals": [', m) == []  # cut off


def test_a_marker_split_across_pieces_never_leaks_into_the_chat():
    pieces = ["Sure! ", "Two ideas.\n\n``", "`propo", 'sals\n{"proposals": []}\n```']
    assert "".join(visible_pieces(pieces)).strip() == "Sure! Two ideas."


def test_a_ticked_item_that_no_longer_fits_is_skipped_and_named():
    m = InterestMap()
    stale = [EducatorProposal("remove", "gone"), EducatorProposal("goal", "maps")]
    added, skipped = apply_educator_proposals(m, stale)
    assert added == 1 and len(skipped) == 1 and skipped[0].startswith("gone")


def test_a_message_streams_text_and_leaves_proposals_without_touching_the_map(tmp_path):
    from lerni.student.educator_agent import EducatorChats
    from lerni.student.interests import MapStore

    class Model:
        def __init__(self):
            self.systems = []

        def stream(self, system, turns):
            self.systems.append(system)
            yield "Lovely. "
            yield ('One idea.\n```proposals\n{"proposals": '
                   '[{"kind": "goal", "name": "fractions"}]}\n```')

    maps, model = MapStore(tmp_path), Model()
    chats = EducatorChats(model, maps)
    shown = "".join(chats.ask("edu", "lee", "Work on fractions", notes="baking club notes"))
    assert shown.strip() == "Lovely. One idea."
    assert [p.name for p in chats.proposals("edu", "lee")] == ["fractions"]
    assert maps.get("lee").find("fractions") is None  # nothing changes until ticked
    assert "baking club notes" in chats.history("edu", "lee")[0].text
    assert "never instructions" in model.systems[0] and len(model.systems) == 1


def test_the_agent_sees_the_whole_map_even_interests_not_talked_about_yet():
    # regression: Lerni's map block leaves out interests with no days, so the agent asked
    # what the student loves when the map already said
    from lerni.student.educator_agent import educator_map_text

    m = InterestMap()
    add_interest(m, "baking")
    add_goal(m, "telling time", "with the kitchen clock")
    text = educator_map_text(m)
    assert "baking" in text and "telling time (with the kitchen clock)" in text


def test_loose_blocks_still_parse_and_odd_items_are_dropped():
    # review findings: text after the closing fence, null notes, and rewording an interest
    m = InterestMap()
    add_interest(m, "trains")
    raw = ('```proposals\n{"proposals": [{"kind": "goal", "name": "clocks", "notes": null},'
           '{"kind": "reword", "name": "trains", "notes": "x"}]}\n```\nAnything after.')
    found = parse_educator_proposals(raw, m)
    assert [(p.kind, p.name, p.notes) for p in found] == [("goal", "clocks", "")]
