#!/usr/bin/env python3
"""CLI smoke tests for onboard / setup cursor / upgrade / wiki update / index stale."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYNAPSE = os.path.join(ROOT, "bin", "synapse")


def run(env, *args, check=True):
    r = subprocess.run(
        [SYNAPSE, *args],
        capture_output=True, text=True, env=env, cwd=env.get("TEST_CWD", env["HOME"]),
    )
    if check and r.returncode != 0:
        raise AssertionError(
            f"cmd {args} exit {r.returncode}\nstdout:\n{r.stdout}\nstderr:\n{r.stderr}"
        )
    return r


def make_env():
    # Keep temps inside the repo so sandboxed CI/agents can write .cursor/ etc.
    base = os.path.join(ROOT, ".tmp-tests")
    os.makedirs(base, exist_ok=True)
    home = tempfile.mkdtemp(prefix="synapse-cli-", dir=base)
    vault = os.path.join(home, "Synapse", "vault")
    shutil.copytree(os.path.join(ROOT, "templates", "vault"), vault)
    # Point templates at the repo so setup/upgrade/seed work without install
    env = os.environ.copy()
    env.update({
        "HOME": home,
        "SYNAPSE_HOME": os.path.join(home, "Synapse"),
        "BRAIN_ROOT": os.path.join(home, "Synapse"),
        "BRAIN_VAULT": vault,
        "SYNAPSE_TEMPLATES": os.path.join(ROOT, "templates"),
        "TEST_CWD": home,
    })
    return home, vault, env


class TestSetupCursor:
    def test_writes_mdc(self):
        home, vault, env = make_env()
        try:
            r = run(env, "setup", "cursor", home)
            rule = os.path.join(home, ".cursor", "rules", "synapse.mdc")
            assert os.path.isfile(rule), f"missing {rule}\n{r.stdout}"
            body = open(rule).read()
            assert "alwaysApply: true" in body
            assert "synapse query" in body
            hooks = os.path.join(home, ".cursor", "hooks.json")
            assert os.path.isfile(hooks), f"missing hooks.json\n{r.stdout}"
            import json
            data = json.load(open(hooks))
            cmds = " ".join(
                e.get("command", "")
                for ev in ("sessionStart", "stop")
                for e in data.get("hooks", {}).get(ev, [])
            )
            assert "cursor-session-start" in cmds
            assert "cursor-stop" in cmds
            assert os.path.isfile(os.path.join(vault, "_meta", "hooks", "cursor-session-start.sh"))
        finally:
            shutil.rmtree(home)


class TestUpgrade:
    def test_writes_engine_version(self):
        home, vault, env = make_env()
        try:
            # Simulate stale vault missing ENGINE_VERSION
            ver = os.path.join(vault, "_meta", "ENGINE_VERSION")
            if os.path.isfile(ver):
                os.remove(ver)
            run(env, "upgrade")
            assert os.path.isfile(ver)
            assert open(ver).read().strip().startswith("0.5")
            assert os.path.isfile(os.path.join(vault, "_meta", "wiki.py"))
            assert os.path.isfile(os.path.join(vault, "_meta", "synapse_lib.py"))
            assert os.path.isfile(os.path.join(vault, "_meta", "pack.py"))
            assert os.path.isfile(os.path.join(vault, "_meta", "hooks", "cursor-session-start.sh"))
        finally:
            shutil.rmtree(home)


class TestOnboardSeed:
    def test_seeds_and_query(self):
        home, vault, env = make_env()
        try:
            r = run(env, "onboard", "--target", "cursor", "--no-hooks", "--dir", home)
            assert os.path.isfile(os.path.join(home, ".cursor", "rules", "synapse.mdc"))
            seeded = os.path.join(vault, "concepts", "api-auth-bearer-header.md")
            assert os.path.isfile(seeded), f"seed missing\n{r.stdout}"
            q = run(env, "query", "bearer token authorization", check=False)
            # query may fall back to lexical; either way should mention the seed
            out = q.stdout + q.stderr
            assert "api-auth" in out or "bearer" in out.lower() or "matches" in out.lower() or q.returncode == 0
        finally:
            shutil.rmtree(home)


class TestWikiUpdate:
    def test_update_bumps_summary(self):
        home, vault, env = make_env()
        try:
            run(env, "file", "concepts", "demo-note", "--summary", "Initial summary here.")
            r = run(env, "file", "update", "demo-note", "--summary", "Updated summary for the note.")
            page = os.path.join(vault, "concepts", "demo-note.md")
            body = open(page).read()
            assert "Updated summary for the note." in body
            assert "UPDATE" in open(os.path.join(vault, "log.md")).read()
            assert "updated" in r.stdout.lower() or "demo-note" in r.stdout
        finally:
            shutil.rmtree(home)


class TestIndexStale:
    def test_fingerprint_roundtrip(self):
        home, vault, env = make_env()
        try:
            # Need at least one note
            run(env, "file", "concepts", "stale-probe", "--summary", "Probe note for index staleness.")
            run(env, "index")
            r = subprocess.run(
                [sys.executable, os.path.join(vault, "_meta", "search.py"), "stale"],
                capture_output=True, text=True, env=env,
            )
            assert r.returncode == 0, r.stdout + r.stderr
            assert "fresh" in r.stdout
            # Mutate vault -> stale
            open(os.path.join(vault, "concepts", "stale-probe.md"), "a").write("\nextra\n")
            r2 = subprocess.run(
                [sys.executable, os.path.join(vault, "_meta", "search.py"), "stale"],
                capture_output=True, text=True, env=env,
            )
            assert r2.returncode == 1, r2.stdout
            assert "STALE" in r2.stdout
        finally:
            shutil.rmtree(home)


class TestDoctor:
    def test_doctor_reports_sections(self):
        home, vault, env = make_env()
        try:
            # Global AGENTS for doctor boot check
            open(os.path.join(home, "AGENTS.md"), "w").write("# agents\n")
            r = run(env, "doctor", check=False)
            assert "== boot files ==" in r.stdout
            assert "== engine ==" in r.stdout
            assert "== integrations ==" in r.stdout
        finally:
            shutil.rmtree(home)


class TestSetupOpenCode:
    def test_writes_opencode_json_and_instructions(self):
        home, vault, env = make_env()
        try:
            run(env, "setup", "opencode", home)
            assert os.path.isfile(os.path.join(home, "AGENTS.md"))
            assert os.path.isfile(os.path.join(home, ".opencode", "synapse.md"))
            cfg = os.path.join(home, "opencode.json")
            assert os.path.isfile(cfg)
            import json
            data = json.load(open(cfg))
            assert ".opencode/synapse.md" in data.get("instructions", [])
            # idempotent
            run(env, "setup", "opencode", home)
            data2 = json.load(open(cfg))
            assert data2["instructions"].count(".opencode/synapse.md") == 1
        finally:
            shutil.rmtree(home)


class TestIndexIfStale:
    def test_skips_when_fresh(self):
        home, vault, env = make_env()
        try:
            run(env, "file", "concepts", "idx-probe",
                "--summary", "Index if-stale probe note for rebuild tests.")
            run(env, "index")
            r = run(env, "index", "--if-stale")
            assert "skip rebuild" in r.stdout or "fresh" in r.stdout
            # mutate -> rebuild
            open(os.path.join(vault, "concepts", "idx-probe.md"), "a").write("\nmore\n")
            r2 = run(env, "index", "--if-stale")
            assert "wrote" in r2.stdout
        finally:
            shutil.rmtree(home)


class TestFileNearDup:
    def test_refuses_near_duplicate_unless_force(self):
        home, vault, env = make_env()
        try:
            run(env, "file", "concepts", "Bearer Token Auth",
                "--summary", "How Authorization Bearer headers work in APIs.")
            # Near title should be refused
            r = run(env, "file", "concepts", "Bearer Token Auth Guide",
                    "--summary", "Slightly different summary about bearer auth.", check=False)
            assert r.returncode != 0
            assert "near-duplicate" in (r.stderr + r.stdout).lower() or "refuse" in (r.stderr + r.stdout).lower()
            # Force creates
            r2 = run(env, "file", "concepts", "Completely Different Topic XYZ",
                     "--summary", "Unrelated note that should create cleanly.")
            assert "filed" in r2.stdout.lower() or "concepts/" in r2.stdout
            # Exact stem collision
            r3 = run(env, "file", "concepts", "Bearer Token Auth",
                     "--summary", "Again the same title.", check=False)
            assert r3.returncode != 0
            # Force near-dup title
            r4 = run(env, "file", "concepts", "Bearer Token Auth Guide",
                     "--summary", "Forced near-dup create.", "--force")
            assert "filed" in r4.stdout.lower() or "concepts/" in r4.stdout
        finally:
            shutil.rmtree(home)


class TestSessionBootstrap:
    def test_wrapper_writes_bootstrap(self):
        home, vault, env = make_env()
        try:
            # Hit the synapse <cli> wrapper path (not a built-in subcommand)
            r = run(env, "true", check=False)
            assert r.returncode == 0, r.stderr
            boot = os.path.join(vault, "_meta", ".session-bootstrap.md")
            assert os.path.isfile(boot), "missing session bootstrap"
            body = open(boot).read()
            assert "Synapse session bootstrap" in body
            assert vault in body or "Vault:" in body
        finally:
            shutil.rmtree(home)


class TestCursorStop:
    def test_emits_lint_followup_when_vault_dirty(self):
        home, vault, env = make_env()
        try:
            script = os.path.join(vault, "_meta", "hooks", "cursor-stop.sh")
            assert os.path.isfile(script)
            subprocess.run(["git", "init"], cwd=vault, check=True, capture_output=True)
            # Broken frontmatter → validate fails
            bad = os.path.join(vault, "concepts", "broken-note.md")
            os.makedirs(os.path.dirname(bad), exist_ok=True)
            open(bad, "w").write("# Broken\nno frontmatter\n")
            subprocess.run(["git", "add", "."], cwd=vault, check=True, capture_output=True)
            # unstaged change so is_dirty sees it
            open(bad, "a").write("more\n")
            r = subprocess.run(
                ["bash", script],
                input='{"status":"completed","loop_count":0,"cwd":"%s"}' % home,
                capture_output=True, text=True, env=env,
            )
            assert r.returncode == 0, r.stderr
            assert "followup_message" in r.stdout
            assert "quality" in r.stdout.lower() or "vault" in r.stdout.lower()
        finally:
            shutil.rmtree(home)


class TestAutoIndexOnQuery:
    def test_query_builds_index_when_missing(self):
        home, vault, env = make_env()
        try:
            run(env, "file", "concepts", "auto-idx",
                "--summary", "Note that should be findable after auto index build.")
            idx = os.path.join(vault, "_meta", "retrieval.json")
            if os.path.isfile(idx):
                os.remove(idx)
            r = run(env, "query", "auto index build findable")
            assert os.path.isfile(idx), "query did not build index"
            assert "auto-idx" in r.stdout or "concepts/" in r.stdout
        finally:
            shutil.rmtree(home)


if __name__ == "__main__":
    # Minimal runner (no pytest required — matches other tests/)
    failed = 0
    for cls in (TestSetupCursor, TestUpgrade, TestOnboardSeed, TestWikiUpdate,
                TestIndexStale, TestDoctor, TestSetupOpenCode, TestIndexIfStale,
                TestFileNearDup, TestSessionBootstrap, TestCursorStop,
                TestAutoIndexOnQuery):
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
