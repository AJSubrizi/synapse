#!/usr/bin/env python3
"""Tests for memory packs + catalog refresh + query --all fusion."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYNAPSE = os.path.join(ROOT, "bin", "synapse")


def make_vault():
    base = os.path.join(ROOT, ".tmp-tests")
    os.makedirs(base, exist_ok=True)
    d = tempfile.mkdtemp(prefix="pack-", dir=base)
    vault = os.path.join(d, "vault")
    shutil.copytree(os.path.join(ROOT, "templates", "vault"), vault)
    env = os.environ.copy()
    env.update({
        "BRAIN_VAULT": vault,
        "SYNAPSE_TEMPLATES": os.path.join(ROOT, "templates"),
        "BRAIN_QUIET": "1",
        "HOME": d,
    })
    return d, vault, env


def run(env, *args, check=True):
    r = subprocess.run([SYNAPSE, *args], capture_output=True, text=True, env=env)
    if check and r.returncode != 0:
        raise AssertionError(f"{args} -> {r.returncode}\n{r.stdout}\n{r.stderr}")
    return r


class TestPack:
    def test_export_import_roundtrip(self):
        d, vault, env = make_vault()
        try:
            run(env, "file", "concepts", "pack-alpha",
                "--summary", "Alpha note for pack roundtrip testing.")
            archive = os.path.join(d, "alpha.tar.gz")
            run(env, "pack", "export", "alpha", "--pages", "pack-alpha",
                "--archive", archive)
            assert os.path.isfile(archive)
            os.remove(os.path.join(vault, "concepts", "pack-alpha.md"))
            run(env, "pack", "import", archive)
            assert os.path.isfile(os.path.join(vault, "concepts", "pack-alpha.md"))
            assert "PACK" in open(os.path.join(vault, "log.md")).read()
        finally:
            shutil.rmtree(d)


class TestCatalog:
    def test_digest_writes_catalog(self):
        d, vault, env = make_vault()
        try:
            run(env, "file", "concepts", "cat-note",
                "--summary", "Catalog generation probe note here.")
            run(env, "digest")
            cat = os.path.join(vault, "_meta", "catalog.md")
            assert os.path.isfile(cat), "catalog.md not written"
            body = open(cat).read()
            assert "cat-note" in body
            assert "auto-generated" in body.lower() or "Catalog" in body
        finally:
            shutil.rmtree(d)


class TestEvalFloors:
    def test_parser_reads_percent(self):
        sys.path.insert(0, os.path.join(ROOT, "scripts"))
        import check_eval_floors as cef
        sample = """
nDCG@10 with 95% cluster-bootstrap CI:
  lexical      95.9%   [95.9%, 95.9%]
  bm25         82.7%   [82.7%, 82.7%]

Recall@5 by category:
"""
        assert abs(cef.bm25_ndcg(sample) - 0.827) < 1e-6


if __name__ == "__main__":
    failed = 0
    for cls in (TestPack, TestCatalog, TestEvalFloors):
        inst = cls()
        for name in dir(inst):
            if not name.startswith("test_"):
                continue
            try:
                getattr(inst, name)()
                print(f"ok  {cls.__name__}.{name}")
            except Exception as exc:
                failed += 1
                print(f"FAIL {cls.__name__}.{name}: {exc}")
    sys.exit(1 if failed else 0)
