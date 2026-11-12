"""v4.7: guidance, level changes, and answer keys through Tell Lerni, saved only from a tick."""

import json
import re
from datetime import date

from lerni.student.bank import BankStore
from lerni.student.batch import write_batch
from lerni.student.concepts import ConceptStore
from lerni.student.educator_agent import (
    EducatorChats,
    educator_map_text,
    parse_educator_proposals,
    save_question_proposals,
)
from lerni.student.guidance import GuidanceStore
from lerni.student.interests import MapStore, add_goal, add_interest, remove
from lerni.student.points import PointsStore
from lerni.student.race import WRITE_SIZE, RaceDesk

TODAY = date(2026, 11, 12)
REPLY = "Got it: centimeters from now on.\n```proposals\n" + json.dumps({"proposals": [
    {"kind": "guidance", "name": "", "notes": "Use cm, not inches."},
    {"kind": "level", "name": "Measuring length", "direction": "harder"},
    {"kind": "key", "name": "Telling time", "question": "Short hand on 3, long hand on 12?",
     "answer": "3:00", "wrong": ["12:15", "3:12"], "why": "The long hand on 12 is o'clock."},
]}) + "\n```"


class Chat:
    """Streams one canned Tell Lerni reply."""

    def stream(self, system, turns):
        yield REPLY


class Checker:
    """Answers blind, and always picks 12:15: a disagreement."""

    def write(self, system, prompt, schema, timeout):
        letter = re.search(r"([ABC]): 12:15", prompt).group(1)  # wherever 12:15 landed
        return {"picks": [{"work": "", "pick": letter}]}


class Quizzer:
    """Writes questions on the first goal; keeps each prompt to read."""

    def __init__(self):
        self.prompts = []

    def write(self, system, prompt):
        self.prompts.append(prompt)
        return {"questions": [{"goal": "Measuring length", "question": f"How long, {n}?",
                               "choices": ["4", "2", "6"], "answer": 0, "why": "Because.",
                               "concept": f"length {n}"} for n in range(WRITE_SIZE)]}


def setup(tmp_path):
    maps = MapStore(tmp_path)
    maps.change("sam", lambda m: [add_goal(m, g) for g in ("Measuring length", "Telling time")])
    chats = EducatorChats(Chat(), maps)
    chats.guidance, chats.concepts = GuidanceStore(tmp_path), ConceptStore(tmp_path)
    chats.bank, chats.checker = BankStore(tmp_path), Checker()
    "".join(chats.ask("ed", "sam", "Too easy. Use cm. Worksheet: 3:00 for short 3, long 12."))
    return maps, chats


def test_ticked_guidance_level_and_key_reach_the_next_race(tmp_path):
    maps, chats = setup(tmp_path)
    found = chats.proposals("ed", "sam")  # the reply's checked proposals, none saved yet
    assert [p.kind for p in found] == ["guidance", "level", "key"]
    assert found[2].doubt == "12:15" and "yours wins" in found[2].label  # the check disagreed
    saved, _ = save_question_proposals("sam", found, maps.get("sam"), chats.guidance,
                                       chats.concepts, chats.bank, TODAY)  # all three ticked
    assert saved == found
    length = maps.get("sam").find("Measuring length")
    assert chats.concepts.levels("sam")[length.id] == 4  # one step up from 3
    time_id = maps.get("sam").find("Telling time").id
    assert chats.bank.good("sam", time_id)[0]["question"] == "Short hand on 3, long hand on 12?"
    races = RaceDesk(Quizzer(), maps, PointsStore(tmp_path), chats.concepts,
                     guidance=chats.guidance)  # as the app wires it
    races._write("sam", supervised=True, today=TODAY)  # one write, its prompt kept
    assert "All goals: Use cm, not inches." in races.quizzer.prompts[0]


def test_nothing_is_saved_without_a_tick(tmp_path):
    maps, chats = setup(tmp_path)
    assert chats.guidance.notes("sam") == [] and chats.bank.items("sam") == []  # asked only
    level = [p for p in chats.proposals("ed", "sam") if p.kind == "level"]
    save_question_proposals("sam", level, maps.get("sam"), chats.guidance, chats.concepts,
                            chats.bank, TODAY)  # only the level ticked
    assert chats.bank.items("sam") == [] and chats.guidance.notes("sam") == []


def test_a_note_touching_something_set_aside_never_reaches_a_prompt(tmp_path):
    maps = MapStore(tmp_path)
    maps.change("sam", lambda m: [add_goal(m, "Measuring length"), add_interest(m, "dinosaurs")])
    guidance = GuidanceStore(tmp_path)
    guidance.add("sam", "More dinosaur questions.", "", TODAY)  # kept before it was set aside
    maps.change("sam", lambda m: remove(m, m.find("dinosaurs").id))
    races = RaceDesk(Quizzer(), maps, PointsStore(tmp_path), ConceptStore(tmp_path),
                     guidance=guidance)
    races._write("sam", supervised=True, today=TODAY)
    prompt = races.quizzer.prompts[0]
    assert "dinosaur questions" not in prompt and "guidance" not in prompt  # only "never use"


def test_review_v47_a_key_or_kept_note_on_a_set_aside_never_reaches_a_prompt(tmp_path):
    maps = MapStore(tmp_path)
    maps.change("sam", lambda m: [add_goal(m, "Telling time"), add_interest(m, "dinosaurs")])
    maps.change("sam", lambda m: remove(m, m.find("dinosaurs").id))
    m = maps.get("sam")
    block = "```proposals\n" + json.dumps({"proposals": [
        {"kind": "key", "name": "Telling time", "question": "A dinosaur wakes at 3. What time?",
         "answer": "3:00", "wrong": ["12:15", "3:12"], "why": "o'clock"}]}) + "\n```"
    assert parse_educator_proposals(block, m, {}) == []  # never proposed, so never checked
    text = educator_map_text(m, {}, [("", "More dinosaur questions.")])  # kept before
    assert "dinosaur questions" not in text


def test_review_v47_a_batch_follows_guidance(tmp_path):
    maps = MapStore(tmp_path)
    maps.change("sam", lambda m: add_goal(m, "Measuring length"))
    GuidanceStore(tmp_path).add("sam", "Use cm, not inches.", "", TODAY)
    quizzer = Quizzer()
    write_batch(tmp_path, "sam", quizzer, supervised=True, today=TODAY, per_goal=1)
    assert "Use cm, not inches." in quizzer.prompts[0]  # read from the batch's copy


class BrokenBank:
    """A bank whose file can't be read."""

    def add_labels(self, *args):
        raise OSError("unreadable")


def test_review_v47_a_tick_sets_its_shown_level_and_a_failed_save_waits(tmp_path):
    maps, chats = setup(tmp_path)
    found = chats.proposals("ed", "sam")  # the level label says 3 → 4
    length = maps.get("sam").find("Measuring length").id
    chats.concepts.set_level("sam", length, 4)  # races moved it before the tick
    saved, skipped = save_question_proposals("sam", found, maps.get("sam"), chats.guidance,
                                             chats.concepts, BrokenBank(), TODAY)
    assert chats.concepts.levels("sam")[length] == 4  # the shown level, never 5
    assert [p.kind for p in saved] == ["guidance", "level"] and len(skipped) == 1  # key waits
