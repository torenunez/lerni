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
