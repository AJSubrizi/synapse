#!/usr/bin/env python3
"""Tests for _meta/metrics.py — loop metrics report."""
import datetime as dt
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
META_SRC = os.path.join(ROOT, "templates", "vault", "_meta")


def assert_true(cond, msg=""):
    if not cond:
        raise AssertionError(msg or "expected True")


def assert_eq(a, b, msg=""):
    if a != b:
        raise AssertionError(msg or f"{a!r} != {b!r}")


def make_vault():
    d = tempfile.mkdtemp()
    os.makedirs(os.path.join(d, "_meta"))
    for f in ("metrics.py", "vault_config.py"):
        shutil.copy(os.path.join(META_SRC, f), os.path.join(d, "_meta", f))
    today = dt.date.today().isoformat()
    old = (dt.date.today() - dt.timedelta(days=120)).isoformat()
    os.makedirs(os.path.join(d, "concepts"))
    os.makedirs(os.path.join(d, "techniques"))
    os.makedirs(os.path.join(d, "raw"))

    def note(path, created):
        with open(path, "w") as fh:
            fh.write(f"---\ntitle: t\ncategory: x\ncreated: {created}\n---\n# t\n")

    note(os.path.join(d, "concepts", "a.md"), today)
    note(os.path.join(d, "concepts", "b.md"), today)
    note(os.path.join(d, "techniques", "c.md"), old)
    with open(os.path.join(d, "raw", "src.txt"), "w") as fh:
        fh.write("source")
    with open(os.path.join(d, "raw", "README.md"), "w") as fh:
        fh.write("# raw")
    with open(os.path.join(d, "log.md"), "w") as fh:
        fh.write("# Log\n")
        fh.write(f"- [{today}T00:00:00Z] INGEST page=\"sources/x\" source=\"raw/src.txt\"\n")
        fh.write(f"- [{today}T00:01:00Z] FILE page=\"concepts/a\"\n")
        fh.write(f"- [{today}T00:02:00Z] FILE page=\"concepts/b\"\n")
    return d


def run_metrics(vault, *args):
    return subprocess.run(
        [sys.executable, os.path.join(vault, "_meta", "metrics.py"), *args],
        capture_output=True, text=True,
    )


class TestMetrics:
    def test_json_counts(self):
        v = make_vault()
        try:
            r = run_metrics(v, "--json")
            assert_true(r.returncode == 0, f"exit {r.returncode}: {r.stderr}")
            m = json.loads(r.stdout)
            assert_eq(m["pages_total"], 3, "should count 3 content notes")
            assert_eq(m["by_category"]["concepts"], 2)
            assert_eq(m["by_category"]["techniques"], 1)
            assert_eq(m["raw_sources"], 1, "raw/ README must be excluded")
            assert_eq(m["added_7d"], 2, "two notes created today")
            assert_eq(m["ops"]["INGEST"], 1)
            assert_eq(m["ops"]["FILE"], 2)
        finally:
            shutil.rmtree(v)

    def test_report_loop_signal_live(self):
        v = make_vault()
        try:
            r = run_metrics(v)
            assert_true(r.returncode == 0, f"exit {r.returncode}: {r.stderr}")
            assert_true("loop is live" in r.stdout, "recent activity should read as live")
            assert_true("Loop activity" in r.stdout)
        finally:
            shutil.rmtree(v)

    def test_stall_signal(self):
        v = make_vault()
        try:
            # with --stale-days 0, even today's activity is "older than 0 days"? No:
            # days_since_activity is 0, 0 <= 0 -> live. Use a vault with no activity instead.
            os.remove(os.path.join(v, "log.md"))
            for n in ("a", "b"):
                os.remove(os.path.join(v, "concepts", f"{n}.md"))
            os.remove(os.path.join(v, "techniques", "c.md"))
            r = run_metrics(v)
            assert_true("no activity recorded yet" in r.stdout, r.stdout)
        finally:
            shutil.rmtree(v)


if __name__ == "__main__":
    for cls in [TestMetrics]:
        print(f"Running {cls.__name__} tests...")
        instance = cls()
        for name in dir(instance):
            if name.startswith("test_"):
                getattr(instance, name)()
                print(f"  ✅ {name}")
    print("All tests passed!")
