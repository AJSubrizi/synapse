#!/usr/bin/env python3
"""Tests for validate.py."""
import os
import sys
import tempfile

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from templates.vault._meta.validate import (
    parse_frontmatter,
    parse_tags,
    load_taxonomy_tags,
    strip_code,
)


def assert_equal(a, b, msg=""):
    if a != b:
        raise AssertionError(f"{msg}: {a!r} != {b!r}")


def assert_in(item, container, msg=""):
    if item not in container:
        raise AssertionError(f"{msg}: {item!r} not in {container!r}")


def assert_none(obj, msg=""):
    if obj is not None:
        raise AssertionError(f"{msg}: {obj!r} is not None")


class TestParseFrontmatter:
    """Test frontmatter parsing."""

    def test_basic_frontmatter(self):
        text = """---
title: Test Note
category: concepts
tags: [test, example]
---

This is the body.
"""
        fm = parse_frontmatter(text)
        assert fm is not None, "Frontmatter should not be None"
        assert_equal(fm["title"], "Test Note")
        assert_equal(fm["category"], "concepts")
        assert_equal(fm["tags"], "[test, example]")

    def test_frontmatter_with_spaces(self):
        text = """  
---
title: Test Note
category: concepts
---

Body.
"""
        fm = parse_frontmatter(text)
        assert fm is not None, "Frontmatter should not be None"
        assert_equal(fm["title"], "Test Note")

    def test_no_frontmatter(self):
        text = "This is just a note without frontmatter."
        fm = parse_frontmatter(text)
        assert_none(fm)

    def test_incomplete_frontmatter(self):
        text = """---
title: Test Note
category: concepts
"""
        fm = parse_frontmatter(text)
        assert_none(fm)

    def test_frontmatter_with_comments(self):
        text = """---
title: Test Note
# This is a comment
category: concepts
---

Body.
"""
        fm = parse_frontmatter(text)
        assert fm is not None, "Frontmatter should not be None"
        assert_equal(fm["title"], "Test Note")
        assert_equal(fm["category"], "concepts")


class TestParseTags:
    """Test tag parsing."""

    def test_basic_tags(self):
        tags = parse_tags("[tag1, tag2, tag3]")
        assert_equal(tags, ["tag1", "tag2", "tag3"])

    def test_tags_with_spaces(self):
        tags = parse_tags("[ tag1 , tag2 , tag3 ]")
        assert_equal(tags, ["tag1", "tag2", "tag3"])

    def test_empty_tags(self):
        tags = parse_tags("")
        assert_equal(tags, [])

    def test_no_brackets(self):
        tags = parse_tags("tag1,tag2,tag3")
        assert_equal(tags, ["tag1", "tag2", "tag3"])


class TestStripCode:
    """Test code stripping."""

    def test_strip_inline_code(self):
        text = "This is `code` in a sentence."
        assert_equal(strip_code(text), "This is  in a sentence.")

    def test_strip_code_block(self):
        text = "```python\nprint('hello')\n```\nSome text."
        assert_equal(strip_code(text), "\nSome text.")

    def test_strip_multiple_code_blocks(self):
        text = "```\ncode1\n```\nText\n```\ncode2\n```"
        assert_equal(strip_code(text), "\nText\n")


class TestLoadTaxonomyTags:
    """Test taxonomy tag loading."""

    def test_load_taxonomy(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("# Tag Taxonomy\n\nUse 1-5 lowercase tags.\n\n## Canonical Tags\n\n- `knowledge`\n- `workflow`\n- `memory`\n")
            f.flush()
            try:
                # Mock the TAXONOMY path
                import templates.vault._meta.validate as validate_module
                original_taxonomy = validate_module.TAXONOMY
                validate_module.TAXONOMY = f.name
                tags = load_taxonomy_tags()
                assert_in("knowledge", tags)
                assert_in("workflow", tags)
                assert_in("memory", tags)
                validate_module.TAXONOMY = original_taxonomy
            finally:
                os.unlink(f.name)


if __name__ == "__main__":
    # Run all tests
    test_classes = [TestParseFrontmatter, TestParseTags, TestStripCode, TestLoadTaxonomyTags]
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
