#!/usr/bin/env python3
"""Tests for _meta/wiki.py — deterministic wiki mutations (real ingest / file-back)."""
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
META_SRC = os.path.join(ROOT, "templates", "vault", "_meta")
WIKI_SRC = os.path.join(META_SRC, "wiki.py")
CONFIG_SRC = os.path.join(META_SRC, "vault_config.py")


def assert_true(cond, msg=""):
    if not cond:
        raise AssertionError(msg or "expected True")


def assert_in(item, container, msg=""):
    if item not in container:
        raise AssertionError(msg or f"{item!r} not in {container!r}")


def make_vault(categories: str | None = None):
    """A throwaway vault skeleton with the headings wiki.py expects.

    Pass `categories` to write a custom `_meta/categories` override and exercise
    configurability.
    """
    d = tempfile.mkdtemp()
    os.makedirs(os.path.join(d, "_meta"))
    for cat in ("concepts", "sources"):
        os.makedirs(os.path.join(d, cat))
    shutil.copy(WIKI_SRC, os.path.join(d, "_meta", "wiki.py"))
    shutil.copy(CONFIG_SRC, os.path.join(d, "_meta", "vault_config.py"))
    if categories is not None:
        with open(os.path.join(d, "_meta", "categories"), "w") as fh:
            fh.write(categories)
    with open(os.path.join(d, "index.md"), "w") as fh:
        fh.write("# Wiki Index\n\n## Concepts\n\n## Sources\n\n## Analysis\n## Runbooks\n")
    with open(os.path.join(d, "log.md"), "w") as fh:
        fh.write("# Wiki Log\n")
    return d


def run_new(vault, *args):
    return subprocess.run(
        [sys.executable, os.path.join(vault, "_meta", "wiki.py"), "new", *args],
        capture_output=True, text=True,
    )


class TestWikiNew:
    def test_creates_page_index_and_log(self):
        v = make_vault()
        try:
            r = run_new(v, "--category", "sources", "--title", "RFC 9110",
                        "--source", "raw/rfc-9110.txt", "--summary", "HTTP semantics spec",
                        "--tags", "knowledge,backend", "--op", "INGEST")
            assert_true(r.returncode == 0, f"exit {r.returncode}: {r.stderr}")
            page = os.path.join(v, "sources", "rfc-9110.md")
            assert_true(os.path.isfile(page), "page file not created")
            body = open(page).read()
            assert_in("category: sources", body)
            assert_in("sources: [raw/rfc-9110.txt]", body, "provenance not recorded")
            assert_in("summary: HTTP semantics spec", body)
            assert_in("raw/rfc-9110.txt", body, "raw provenance note missing from body")
            # registered under the Sources heading in index.md
            idx = open(os.path.join(v, "index.md")).read()
            assert_in("[[rfc-9110]]", idx, "page not catalogued in index.md")
            sources_section = idx.split("## Sources", 1)[1]
            assert_in("[[rfc-9110]]", sources_section.split("##", 1)[0],
                      "page filed under the wrong heading")
            # logged
            log = open(os.path.join(v, "log.md")).read()
            assert_in("INGEST", log)
            assert_in('page="sources/rfc-9110"', log)
        finally:
            shutil.rmtree(v)

    def test_link_avoids_orphan(self):
        v = make_vault()
        try:
            r = run_new(v, "--category", "concepts", "--title", "Idempotency",
                        "--link", "rest-api-design", "--op", "FILE")
            assert_true(r.returncode == 0, f"exit {r.returncode}: {r.stderr}")
            body = open(os.path.join(v, "concepts", "idempotency.md")).read()
            assert_in("[[rest-api-design]]", body, "cross-link not written")
        finally:
            shutil.rmtree(v)

    def test_no_overwrite(self):
        v = make_vault()
        try:
            run_new(v, "--category", "concepts", "--title", "Dup")
            r = run_new(v, "--category", "concepts", "--title", "Dup")
            assert_true(r.returncode == 1, "second create should refuse (exit 1)")
            # index has exactly one entry for the stem
            idx = open(os.path.join(v, "index.md")).read()
            assert_true(idx.count("[[dup]]") == 1, "duplicate index entry written")
        finally:
            shutil.rmtree(v)

    def test_rejects_unknown_category(self):
        v = make_vault()
        try:
            r = run_new(v, "--category", "bogus", "--title", "X")
            assert_true(r.returncode == 2, "unknown category should exit 2")
        finally:
            shutil.rmtree(v)

    def test_configurable_categories(self):
        # A custom _meta/categories defines the valid set: a custom category is accepted,
        # and a former default not listed is now rejected.
        v = make_vault(categories="# custom\nconcepts\nrunbooks\n")
        try:
            ok = run_new(v, "--category", "runbooks", "--title", "Deploy steps")
            assert_true(ok.returncode == 0, f"custom category rejected: {ok.stderr}")
            assert_true(os.path.isfile(os.path.join(v, "runbooks", "deploy-steps.md")))
            nope = run_new(v, "--category", "sources", "--title", "Y")
            assert_true(nope.returncode == 2, "category not in override should be rejected")
        finally:
            shutil.rmtree(v)


if __name__ == "__main__":
    for cls in [TestWikiNew]:
        print(f"Running {cls.__name__} tests...")
        instance = cls()
        for name in dir(instance):
            if name.startswith("test_"):
                getattr(instance, name)()
                print(f"  ✅ {name}")
    print("All tests passed!")
