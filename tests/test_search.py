#!/usr/bin/env python3
"""Tests for the shipped retriever (templates/vault/_meta/search.py).

Covers the BM25 default backend, the index/query roundtrip, the search filters,
and that the benchmark harness shares this module's canonical tokenizer (so the
published numbers describe what users actually run).
"""
import contextlib
import io
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "templates", "vault", "_meta"))
sys.path.insert(0, os.path.join(ROOT, "benchmarks"))

import search  # noqa: E402


def assert_equal(a, b, msg=""):
    if a != b:
        raise AssertionError(f"{msg}: {a!r} != {b!r}")


def assert_true(cond, msg=""):
    if not cond:
        raise AssertionError(msg or "expected True")


NOTES = {
    "concepts/rate-limit.md": (
        "---\ntitle: Rate-limit FastAPI endpoints\ncategory: concepts\n"
        "tags: [backend, security]\n"
        "summary: Per-route rate limiting with slowapi and Redis, 429 plus Retry-After.\n"
        "---\nUse slowapi with a Redis backend. Decorate routes. Return 429.\n"
    ),
    "concepts/docker-deploy.md": (
        "---\ntitle: Deploy FastAPI to Docker\ncategory: concepts\n"
        "tags: [devops, backend]\n"
        "summary: Build the image, run alembic migrations, health-check traffic.\n"
        "---\nBuild with docker build. Run alembic upgrade head. Check /healthz.\n"
    ),
}


@contextlib.contextmanager
def temp_vault():
    """Point the search module's globals at a throwaway vault, then restore them."""
    with tempfile.TemporaryDirectory() as d:
        for rel, body in NOTES.items():
            path = os.path.join(d, rel)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            open(path, "w", encoding="utf-8").write(body)
        saved = (search.VAULT, search.META, search.INDEX, search.DIGEST)
        meta = os.path.join(d, "_meta")
        os.makedirs(meta, exist_ok=True)
        search.VAULT, search.META = d, meta
        search.INDEX = os.path.join(meta, "retrieval.json")
        search.DIGEST = os.path.join(meta, "digest.md")
        try:
            yield d
        finally:
            search.VAULT, search.META, search.INDEX, search.DIGEST = saved


def capture(fn, *args, **kwargs):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = fn(*args, **kwargs)
    return rc, buf.getvalue()


class TestBackendDefault:
    def test_bm25_is_default(self):
        saved = os.environ.pop("SYNAPSE_RETRIEVAL_BACKEND", None)
        try:
            assert_equal(search.backend_name(), "bm25", "default backend")
        finally:
            if saved is not None:
                os.environ["SYNAPSE_RETRIEVAL_BACKEND"] = saved


class TestBm25IndexAndQuery:
    def test_index_writes_bm25(self):
        with temp_vault():
            rc, _ = capture(search.cmd_index, "")  # "" -> backend_name() -> bm25
            assert_equal(rc, 0, "index rc")
            import json
            idx = json.load(open(search.INDEX, encoding="utf-8"))
            assert_equal(idx["backend"], "bm25", "backend")
            assert_equal(len(idx["docs"]), 2, "doc count")
            assert_true("avgdl" in idx and idx["idf"], "bm25 fields present")

    def test_query_ranks_relevant_note_first(self):
        with temp_vault():
            search.cmd_index("")
            _, out = capture(search.cmd_query, "redis rate limiting", 10)
            assert_true("rate-limit.md" in out, "redis query finds rate-limit note")
            first = out.strip().splitlines()[0]
            assert_true("rate-limit.md" in first, f"rate-limit ranked first, got: {first}")

            _, out2 = capture(search.cmd_query, "docker alembic migrations", 10)
            first2 = out2.strip().splitlines()[0]
            assert_true("docker-deploy.md" in first2, f"docker ranked first, got: {first2}")

    def test_tfidf_backend_still_available(self):
        with temp_vault():
            search.cmd_index("tfidf")
            import json
            assert_equal(json.load(open(search.INDEX, encoding="utf-8"))["backend"],
                         "tfidf", "explicit tfidf backend")


class TestSearchFilters:
    def test_tag_filter(self):
        with temp_vault():
            _, out = capture(search.cmd_search, "", 10, True, tag="security")
            assert_true("rate-limit.md" in out, "tag=security matches rate-limit")
            assert_true("docker-deploy.md" not in out, "tag=security excludes docker")

    def test_query_scores_title_over_body(self):
        with temp_vault():
            _, out = capture(search.cmd_search, "docker", 10, True)
            assert_true("docker-deploy.md" in out.strip().splitlines()[0],
                        "title hit dominates")

    def test_exact_substring(self):
        with temp_vault():
            _, out = capture(search.cmd_search, "Retry-After", 10, True, exact=True)
            assert_true("rate-limit.md" in out, "exact substring match")


class TestTokenizerParity:
    """The benchmark must score the same tokens the product indexes."""

    def test_harness_shares_canonical_tokenizer(self):
        import retrieval_eval as re_eval
        assert_equal(re_eval.STOPWORDS, search.STOPWORDS, "stopwords match")
        for s in ("Deploy FastAPI to Docker with Redis", "429 Retry-After header"):
            assert_equal(re_eval.tokenize(s), search.tokenize(s), f"tokenize({s!r})")


class TestChunkingAndFusion:
    """Dependency-free pieces of the embeddings/hybrid backends (T2)."""

    def test_note_hash_is_content_sensitive(self):
        assert_equal(search.note_hash("abc"), search.note_hash("abc"), "stable")
        assert_true(search.note_hash("abc") != search.note_hash("abd"), "differs")

    def test_short_note_one_chunk_with_header(self):
        chunks = search.chunk_note({"title": "T", "summary": "ctx"}, "short body", "stem")
        assert_equal(len(chunks), 1, "one chunk")
        assert_true("T" in chunks[0] and "ctx" in chunks[0], "header context present")

    def test_long_note_overlapping_chunks(self):
        body = " ".join(f"w{i}" for i in range(400))
        chunks = search.chunk_note({"title": "T", "summary": "s"}, body, "stem",
                                   max_words=160, overlap=20)
        assert_true(len(chunks) >= 2, "splits long notes")
        assert_true(all(c.startswith("T s") for c in chunks), "every chunk carries header")

    def test_rrf_fuses_rankings(self):
        fused = search._rrf([["a", "b", "c"], ["b", "a", "d"]])
        rels = [rel for _, rel in fused]
        assert_equal(sorted(rels), ["a", "b", "c", "d"], "union of both lists")
        assert_true(rels[0] in ("a", "b"), "top-ranked item wins fusion")


class TestEmbeddingsBackend:
    """Real embeddings/hybrid path — skipped cleanly when the model isn't installed."""

    @staticmethod
    def _has_st():
        try:
            import sentence_transformers  # noqa: F401
            return True
        except Exception:
            return False

    def test_chunked_incremental_and_hybrid(self):
        if not self._has_st():
            print("    (skipped: sentence-transformers not installed)")
            return
        import json
        import os as _os
        with temp_vault():
            capture(search.cmd_index, "embeddings")
            idx = json.load(open(search.INDEX, encoding="utf-8"))
            assert_equal(idx["backend"], "embeddings", "embeddings backend")
            assert_equal(idx["_stats"]["encoded"], 2, "first build encodes all")
            assert_true(idx.get("vectors") and idx.get("dim", 0) > 0, "binary sidecar recorded")
            assert_true(_os.path.isfile(search._vec_path()), "retrieval.vec written")
            assert_true(all(d.get("n_chunks", 0) > 0 for d in idx["docs"]), "per-note chunk counts")
            capture(search.cmd_index, "embeddings")  # rebuild, nothing changed
            idx2 = json.load(open(search.INDEX, encoding="utf-8"))
            assert_equal(idx2["_stats"]["reused"], 2, "rebuild reuses unchanged notes (binary)")
            _, out = capture(search.cmd_query, "capping how often clients call", 10)
            assert_true("rate-limit.md" in out, "semantic query finds throttling note")
            capture(search.cmd_index, "hybrid")
            idx3 = json.load(open(search.INDEX, encoding="utf-8"))
            assert_equal(idx3["backend"], "hybrid", "hybrid backend")
            assert_true("bm25" in idx3 and "embeddings" in idx3, "hybrid nests both")


if __name__ == "__main__":
    test_classes = [TestBackendDefault, TestBm25IndexAndQuery,
                    TestSearchFilters, TestTokenizerParity,
                    TestChunkingAndFusion, TestEmbeddingsBackend]
    for cls in test_classes:
        print(f"Running {cls.__name__} tests...")
        instance = cls()
        for name in dir(instance):
            if name.startswith("test_"):
                getattr(instance, name)()
                print(f"  ✅ {name}")
    print("All tests passed!")
