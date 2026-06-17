#!/usr/bin/env python3
"""Tests for dedup.py."""
import os
import sys
import tempfile

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from templates.vault._meta.dedup import (
    split_frontmatter,
    parse_tags,
    tokenize,
    jaccard,
)


def assert_equal(a, b, msg=""):
    if a != b:
        raise AssertionError(f"{msg}: {a!r} != {b!r}")


def assert_in(item, container, msg=""):
    if item not in container:
        raise AssertionError(f"{msg}: {item!r} not in {container!r}")


def assert_not_in(item, container, msg=""):
    if item in container:
        raise AssertionError(f"{msg}: {item!r} should not be in {container!r}")


def assert_almost_equal(a, b, msg="", tolerance=1e-6):
    if abs(a - b) > tolerance:
        raise AssertionError(f"{msg}: {a!r} != {b!r} (tolerance: {tolerance})")


class TestSplitFrontmatter:
    """Test frontmatter splitting."""

    def test_basic_frontmatter(self):
        text = """---
title: Test Note
category: concepts
---

This is the body.
"""
        fm, body = split_frontmatter(text)
        assert fm == {"title": "Test Note", "category": "concepts"}
        assert "This is the body." in body

    def test_no_frontmatter(self):
        text = "This is just a note."
        fm, body = split_frontmatter(text)
        assert fm == {}
        assert body == text

    def test_incomplete_frontmatter(self):
        text = """---
title: Test Note
"""
        fm, body = split_frontmatter(text)
        assert fm == {}
        assert body == text


class TestParseTags:
    """Test tag parsing."""

    def test_basic_tags(self):
        tags = parse_tags("[tag1, tag2, tag3]")
        assert tags == {"tag1", "tag2", "tag3"}

    def test_tags_with_spaces(self):
        tags = parse_tags("[ tag1 , tag2 ]")
        assert tags == {"tag1", "tag2"}

    def test_empty_tags(self):
        tags = parse_tags("")
        assert tags == set()


class TestTokenize:
    """Test tokenization."""

    def test_basic_tokenize(self):
        body = "This is a test body."
        tokens = tokenize(body)
        assert "test" in tokens
        assert "body" in tokens
        assert "this" not in tokens  # Stopword
        assert "is" not in tokens    # Stopword
        assert "a" not in tokens     # Stopword

    def test_tokenize_with_code(self):
        body = "Use `python3` for scripts. ```python\nprint('hello')\n```"
        tokens = tokenize(body)
        assert "python3" not in tokens  # Inline code stripped
        assert "print" not in tokens    # Code block stripped
        assert "scripts" in tokens
        assert "for" not in tokens  # Stopword

    def test_tokenize_with_wikilinks(self):
        body = "See [[workflow]] for details."
        tokens = tokenize(body)
        assert "workflow" not in tokens  # Wikilink stripped
        assert "see" in tokens
        assert "details" in tokens

    def test_tokenize_short_words(self):
        body = "a an the and or but"
        tokens = tokenize(body)
        assert len(tokens) == 0  # All stopwords or too short


class TestJaccard:
    """Test Jaccard similarity."""

    def test_identical_sets(self):
        a = {"a", "b", "c"}
        b = {"a", "b", "c"}
        assert_equal(jaccard(a, b), 1.0)

    def test_disjoint_sets(self):
        a = {"a", "b"}
        b = {"c", "d"}
        assert_equal(jaccard(a, b), 0.0)

    def test_partial_overlap(self):
        a = {"a", "b", "c"}
        b = {"a", "b", "d"}
        assert_almost_equal(jaccard(a, b), 0.5)  # 2/4 = 0.5

    def test_empty_sets(self):
        a = set()
        b = set()
        assert_equal(jaccard(a, b), 0.0)

    def test_one_empty_set(self):
        a = {"a", "b"}
        b = set()
        assert_equal(jaccard(a, b), 0.0)


if __name__ == "__main__":
    # Run all tests
    test_classes = [TestSplitFrontmatter, TestParseTags, TestTokenize, TestJaccard]
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
