"""Race checks by meaning (v3.40): rewordings and set-aside topics dropped; goals win."""

import subprocess
from datetime import date

import pytest

from lerni.student.adapters.llama_embed import LlamaEmbedder
from lerni.student.interests import (
    InterestMap,
    MapStore,
    add_goal,
    add_interest,
    remove,
    set_area,
)
from lerni.student.meaning import Meaning
from lerni.student.points import PointsStore
from lerni.student.race import Question, RaceDesk, check_questions, fits, race_view

TODAY = date(2026, 11, 10)


class TopicEmbedder:
    """A fake: texts sharing a topic word match fully; every other text is its own direction."""

    TOPICS = {"rifle": "guns", "guns": "guns", "math": "math", "pizza": "pizza"}

    def __init__(self, fail: bool = False):
        self.fail, self.dims = fail, {}

    def embed(self, texts):
        if self.fail:
            raise OSError("no model")
        keys = [next((v for k, v in self.TOPICS.items() if k in t.casefold()), t.casefold())
                for t in texts]
        for key in keys:
            self.dims.setdefault(key, len(self.dims))
        return [[1.0 if i == self.dims[key] else 0.0 for i in range(len(self.dims))]
                for key in keys]


def q(question: str, concept: str) -> dict:
    return {"goal": "Fractions", "question": question, "choices": ["4", "2", "6"], "answer": 0,
            "why": "Half means 2 equal parts.", "concept": concept}


class Quizzer:
    """Writes the same set each time and keeps the prompts it was sent."""

    def __init__(self):
        self.prompts = []

    def write(self, system, prompt):
        self.prompts.append(prompt)
        plain = [q(f"What is {n} halves?", f"idea {n}") for n in range(6)]
        return {"questions": [
            *plain,
            q("How far can a rifle shoot?", "range"),  # a set-aside topic in other words
            q("Is math about patterns?", "patterns"),  # names a set-aside name that's a goal's area
            q("Half a pizza is how many slices?", "pizza halves"),
            q("Cut a pizza in two: what's each part?", "halves of a pizza"),  # a rewording
        ]}


def desk(tmp_path, embedder):
    maps = MapStore(tmp_path)

    def fill(m):
        set_area(m, add_goal(m, "Fractions").id, "Math")
        remove(m, add_interest(m, "guns").id)
        remove(m, add_interest(m, "math").id)  # set aside for chat, but Math has goals

    maps.change("sam", fill)
    return RaceDesk(Quizzer(), maps, PointsStore(tmp_path), embedder=embedder)


def test_rewordings_and_set_aside_topics_are_dropped_and_goals_win(tmp_path, capsys):
    races = desk(tmp_path, TopicEmbedder())
    kept = races._write("sam", supervised=True, today=TODAY)
    shown = [k.question for k in kept]
    assert "How far can a rifle shoot?" not in shown  # near "guns", not its goal
    assert "Is math about patterns?" in shown  # "math" is skipped: Math has goals
    assert sum("pizza" in s for s in shown) == 1  # the rewording is gone
    told = races.quizzer.prompts[0]
    assert "guns" in told and "never use: math" not in told and ", math" not in told
    out = capsys.readouterr().out
    assert "by meaning: 1 repeats, 1 set aside" in out and "rifle" not in out  # numbers only


def test_without_the_embedder_the_word_match_decides(tmp_path):
    races = desk(tmp_path, TopicEmbedder(fail=True))
    shown = [k.question for k in races._write("sam", supervised=True, today=TODAY)]
    assert "How far can a rifle shoot?" in shown  # other words: today's match can't tell
    assert "Is math about patterns?" not in shown  # and "math" is set aside, as before
    assert len(shown) >= 5  # the race is still written


def test_goals_win_never_lets_a_set_aside_topic_through_as_a_probe():
    # regression: the race view let a "math tricks" probe race, then open Chat on it
    real = InterestMap()
    set_area(real, add_goal(real, "Fractions").id, "Math")
    add_interest(real, "sharks")
    remove(real, add_interest(real, "math").id)
    view = race_view(real, frozenset({"math"}))
    raw = {"questions": [{**q("What trick makes adding 9 quick?", "math tricks"), "goal": "",
                          "probe": "math tricks"}]}
    assert check_questions(raw, view, real=real, probes=True) == []
    probe = Question("", "Why?", ("a", "b", "c"), 0, "Because.", "math tricks",
                     probe="math tricks", level=1)
    assert not fits(probe, view, real)  # a held probe is checked against the map itself


def test_an_idea_due_for_review_is_never_dropped_as_a_rewording():
    m = InterestMap()
    add_goal(m, "Fractions")
    raw = {"questions": [q("Half a pizza is how many slices?", "halves of pizza")]}
    meaning = Meaning.build(TopicEmbedder(), ["pizza halves", "halves of pizza",
                                              "Half a pizza is how many slices? halves of pizza"])
    recent = ["pizza halves"]
    assert check_questions(raw, m, concepts=recent, meaning=meaning) == []
    kept = check_questions(raw, m, concepts=recent, meaning=meaning, due=["halves of pizza"])
    assert [k.concept for k in kept] == ["halves of pizza"]


def test_the_embedder_sends_texts_as_one_argument_and_checks_the_count():
    calls = []

    def runner(cmd, **kwargs):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, b"log line\n[[0.6, 0.8], [1.0, 0.0]]\n", b"")

    embedder = LlamaEmbedder("model.gguf", runner)
    assert embedder.embed(["a", "b"]) == [[0.6, 0.8], [1.0, 0.0]]
    prompt = calls[0][calls[0].index("-p") + 1]
    assert prompt.count("Query: a") == 1 and "Query: b" in prompt  # one argument, no file
    with pytest.raises(ValueError):
        embedder.embed(["a", "b", "c"])  # two vectors for three texts
