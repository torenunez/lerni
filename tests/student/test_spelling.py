"""v4.10: Spelling: a round of 5 graded by code, missed words back tomorrow, and nothing typed
kept on disk."""

from datetime import date, timedelta

import pytest

from lerni.student.interests import MapStore, add_interest
from lerni.student.points import PointsStore
from lerni.student.spelling import SpellingDesk, SpellingStore, checked_picks, mistake

TODAY = date(2026, 11, 17)
PICKS = {"words": [  # what the small model sends: two bad rows among good ones
    {"word": "fossil", "sentence": "The fossil was very old.", "kind": "other"},
    {"word": "enormous", "sentence": "An enormous dinosaur walked by.", "kind": "adjective"},
    {"word": "unhappy", "sentence": "The unhappy dragon sat alone.", "kind": "prefix",
     "parts": ["un", "happy"]},
    {"word": "careful", "sentence": "Be careful with the bricks.", "kind": "suffix",
     "parts": ["care", "ful"]},
    {"word": "speedy", "sentence": "The speedy car won.", "kind": "adjective"},
    {"word": "T-Rex", "sentence": "The T-Rex roared.", "kind": "other"},  # not plain letters
    {"word": "scaly", "sentence": "Its skin was rough.", "kind": "adjective"},  # word not used
]}


class Writer:
    """The small model: Lerni's picks, or sentences for class words."""

    def __init__(self):
        self.calls = 0

    def write(self, system, prompt, schema, timeout):
        self.calls += 1
        if "sentences" in schema["properties"]:
            return {"sentences": [{"word": "because", "sentence": "I smiled because it rained."}]}
        return PICKS


def desk(tmp_path, writer=None):
    maps = MapStore(tmp_path)
    maps.change("lee", lambda m: add_interest(m, "dinosaurs"))
    return SpellingDesk(SpellingStore(tmp_path), PointsStore(tmp_path), maps,
                        writer=writer or Writer())


def test_a_round_is_graded_by_code_and_missed_words_come_back(tmp_path):
    d = desk(tmp_path)
    d.set_class_list("lee", "because\nfriend\n\nfriend\ntwo words", TODAY)  # one refused
    r = d.start("lee", TODAY)  # the class list first, then Lerni's picks (written now)
    assert r.words[:2] == ["because", "friend"] and len(r.words) == 5
    typed = ["Because ", "frend", *r.words[2:]]  # case and spaces don't count; one missed
    turns = [d.answer("lee", r.id, i, t, TODAY) for i, t in enumerate(typed)]
    assert [t.right for t in turns] == [True, False, True, True, True]
    assert turns[1].label == "missing" and turns[-1].done
    assert PointsStore(tmp_path).get("lee").balance == 8  # 4 right × 2, no bonus
    words = {w["word"]: w for w in SpellingStore(tmp_path).get("lee")["words"]}
    assert words["friend"]["due"] == (TODAY + timedelta(days=1)).isoformat()  # back tomorrow
    assert words["because"]["due"] == (TODAY + timedelta(days=1)).isoformat()  # first box: 1
    assert words["friend"]["mistakes"] == {"missing": 1}
    assert SpellingStore(tmp_path).get("lee")["level"] == 2  # 4 of 5: up a level
    assert d.answer("lee", r.id, 4, "again", TODAY) is None  # a repeated tap: nothing
    # regression: a word asked again before it's due doesn't move up a box (review, v4.10)
    again = d.start("lee", TODAY)
    for i, word in enumerate(again.words):
        d.answer("lee", again.id, i, word, TODAY)
    words = {w["word"]: w for w in SpellingStore(tmp_path).get("lee")["words"]}
    assert words["because"]["streak"] == 1 and words["because"]["right"] == 2
    # a new list: earlier words stay, as Lerni's, with their counts (review, v4.10)
    d.set_class_list("lee", "said", TODAY)
    words = {w["word"]: w for w in SpellingStore(tmp_path).get("lee")["words"]}
    assert words["friend"]["source"] == "lerni" and words["friend"]["missed"] == 1


def test_nothing_typed_is_kept_on_disk(tmp_path):
    d = desk(tmp_path)
    r = d.start("lee", TODAY)
    d.answer("lee", r.id, 0, "zqxwv-typed", TODAY)
    files = [p for p in tmp_path.rglob("*") if p.is_file()]
    assert files and not any(b"zqxwv" in p.read_bytes() for p in files)  # rule 6


def test_claudes_words_are_checked_and_removed_words_never_come_back(tmp_path):
    kept = [p["word"] for p in checked_picks(PICKS, {"speedy"})]
    assert kept == ["fossil", "enormous", "unhappy", "careful"]  # bad rows and known dropped
    assert checked_picks(PICKS, set())[2]["parts"] == ["un", "happy"]
    d = desk(tmp_path)
    d.write_picks("lee", TODAY)
    d.remove("lee", ["fossil"])
    d.write_picks("lee", TODAY)  # the same picks again: fossil stays out
    assert "fossil" not in {w["word"] for w in SpellingStore(tmp_path).get("lee")["words"]}


@pytest.mark.parametrize(("word", "typed", "label"), [
    ("rabbit", "rabit", "double"),
    ("frog", "frogg", "double"),
    ("receive", "recieve", "ie-ei"),
    ("stone", "ston", "silent-e"),
    ("from", "form", "swap"),
    ("set", "sat", "vowel"),
    ("friend", "frend", "missing"),
    ("cat", "cart", "extra"),
    ("because", "becuz", "other"),
    ("Monday", " monday ", ""),
    ("don't", "don’t", ""),  # regression: the iPad's curly apostrophe is right (review)
])
def test_mistake_labels(word, typed, label):
    assert mistake(word, typed) == label
