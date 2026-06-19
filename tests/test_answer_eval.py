#!/usr/bin/env python3
"""Offline tests for the answer-accuracy track (answer_eval, distillation_eval).

These exercise the full plumbing — ranking -> answer -> judge, and
distill -> index -> retrieve -> answer -> judge — with the offline echo answerer
and exact judge, so no API key is required.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "benchmarks"))
sys.path.insert(0, os.path.join(ROOT, "templates", "vault", "_meta"))

import answer_eval as ans  # noqa: E402
import distillation_eval as dist  # noqa: E402


def assert_true(c, m=""):
    if not c:
        raise AssertionError(m or "expected True")


def assert_equal(a, b, m=""):
    if a != b:
        raise AssertionError(f"{m}: {a!r} != {b!r}")


class FakeBlock:
    def __init__(self, text):
        self.type, self.text = "text", text


class FakeResp:
    def __init__(self, text, stop_reason="end_turn"):
        self.content, self.stop_reason = [FakeBlock(text)], stop_reason


class TestPromptsAndJudges:
    def test_answer_prompt_includes_context_and_question(self):
        p = ans.build_answer_prompt("What is X?", ["alpha", "beta"])
        assert_true("alpha" in p and "beta" in p and "What is X?" in p, "prompt content")

    def test_exact_judge_substring_both_directions(self):
        j = ans.exact_judge()
        assert_true(j("q", "Paris", "The answer is Paris."), "gold in pred")
        assert_true(j("q", "Paris, France", "Paris"), "pred in gold")
        assert_true(not j("q", "Paris", "Berlin"), "mismatch")
        assert_true(not j("q", "", "anything"), "empty gold is never correct")

    def test_echo_answerer_returns_top_context(self):
        a = ans.echo_answerer()
        assert_equal(a("q", ["top", "second"]), "top", "echo top")
        assert_equal(a("q", []), "", "no context")

    def test_text_extraction_and_refusal(self):
        assert_equal(ans._text(FakeResp("hi")), "hi", "text block")
        assert_equal(ans._text(FakeResp("partial", stop_reason="refusal")), "",
                     "refusal -> empty")


class TestEvaluateAnswers:
    def _prepared(self):
        units = [
            ("u1", "Paris is the capital of France. The Eiffel Tower is in Paris.",
             frozenset({"u1"})),
            ("u2", "Berlin is the capital of Germany.", frozenset({"u2"})),
        ]
        qas = [{"question": "What is the capital of France?", "answer": "Paris",
                "category": "geo"}]
        return [(units, qas)]

    def test_end_to_end_offline(self):
        rows = ans.evaluate_answers(self._prepared(), "bm25", 1,
                                    ans.echo_answerer(), ans.exact_judge())
        assert_equal(len(rows), 1, "one row")
        assert_equal(rows[0], ("geo", True), "bm25 retrieves Paris note -> correct")

    def test_report_returns_accuracy(self):
        acc = ans.report_answers([("geo", True), ("geo", False)], "bm25", 1,
                                 "T", "echo", "exact")
        assert_true(abs(acc - 0.5) < 1e-9, "accuracy 50%")


class TestDistillationLoop:
    def test_run_entry_offline(self):
        entry = {
            "haystack_sessions": [
                [{"role": "user", "content": "Paris is the capital of France."}],
                [{"role": "user", "content": "Berlin is the capital of Germany."}],
            ],
            "question": "What is the capital of France?",
            "answer": "Paris",
            "question_type": "geo",
        }
        ok = dist.run_entry(entry, dist.echo_distiller(), ans.echo_answerer(),
                            ans.exact_judge(), k=1)
        assert_true(ok, "distill -> index -> retrieve -> answer finds Paris")


if __name__ == "__main__":
    for cls in [TestPromptsAndJudges, TestEvaluateAnswers, TestDistillationLoop]:
        print(f"Running {cls.__name__} tests...")
        inst = cls()
        for name in dir(inst):
            if name.startswith("test_"):
                getattr(inst, name)()
                print(f"  ✅ {name}")
    print("All tests passed!")
