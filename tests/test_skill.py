#!/usr/bin/env python3
"""Tests for skill.py."""
import os
import sys
import tempfile
import datetime as dt

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from templates.vault._meta.skill import (
    split_fm,
    get,
    card,
    today,
)


def assert_equal(a, b, msg=""):
    if a != b:
        raise AssertionError(f"{msg}: {a!r} != {b!r}")


def assert_none(obj, msg=""):
    if obj is not None:
        raise AssertionError(f"{msg}: {obj!r} is not None")


class TestSplitFm:
    """Test frontmatter splitting."""

    def test_basic_frontmatter(self):
        text = """---
title: Test Skill
uses: 5
score: 4.5
votes: 2
---

This is the body.
"""
        fm, rest = split_fm(text)
        assert len(fm) == 4
        assert "title: Test Skill" in fm or any("title" in line for line in fm)
        assert "This is the body." in rest

    def test_no_frontmatter(self):
        text = "This is just a note."
        fm, rest = split_fm(text)
        assert fm == []
        assert rest == text

    def test_incomplete_frontmatter(self):
        text = """---
title: Test Skill
"""
        fm, rest = split_fm(text)
        assert fm == []
        assert rest == text


class TestGet:
    """Test frontmatter key extraction."""

    def test_get_existing_key(self):
        fm = ["title: Test Skill", "uses: 5"]
        assert get(fm, "title") == "Test Skill"
        assert get(fm, "uses") == "5"

    def test_get_missing_key(self):
        fm = ["title: Test Skill"]
        assert get(fm, "missing") is None

    def test_get_with_quotes(self):
        fm = ["title: \"Test Skill\""]
        assert get(fm, "title") == "Test Skill"


class TestCard:
    """Test scorecard parsing."""

    def test_card_with_values(self):
        fm = ["uses: 5", "score: 4.5", "votes: 2"]
        c = card(fm)
        assert c["uses"] == 5
        assert c["score"] == 4.5
        assert c["votes"] == 2

    def test_card_with_missing_values(self):
        fm = ["uses: 0"]
        c = card(fm)
        assert c["uses"] == 0
        assert c["score"] == 0.0
        assert c["votes"] == 0

    def test_card_with_empty_frontmatter(self):
        fm = []
        c = card(fm)
        assert c["uses"] == 0
        assert c["score"] == 0.0
        assert c["votes"] == 0


class TestToday:
    """Test today's date formatting."""

    def test_today_format(self):
        date_str = today()
        # Should be in ISO format (YYYY-MM-DD)
        assert_equal(len(date_str), 10)
        assert_equal(date_str.count("-"), 2)
        # Verify it's a valid date
        dt.date.fromisoformat(date_str)


if __name__ == "__main__":
    # Run all tests
    test_classes = [TestSplitFm, TestGet, TestCard, TestToday]
    for cls in test_classes:
        print(f"Running {cls.__name__} tests...")
        instance = cls()
        for name in dir(instance):
            if name.startswith("test_"):
                try:
                    getattr(instance, name)()
                    print(f"  ✅ {name}")
                except Exception as e:
                    print(f"  ❌ {name}: {e}")
                    raise
    print("All tests passed!")
