#!/usr/bin/env python3
"""Tests for the freshness check's drift classification.

Two of #3's criteria were implemented but never exercised: the could-not-check
path, and telling a build in progress from one cancelled or absent. Neither fires
in normal operation -- the fetch keeps succeeding and the site keeps matching --
so waiting for real traffic to exercise them means they stay unverified
indefinitely, which is indistinguishable from broken.
"""
from __future__ import annotations

import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_freshness as cf  # noqa: E402


def run(status: str, conclusion: str | None = None, age_minutes: int = 1) -> dict:
    created = datetime.now(timezone.utc) - timedelta(minutes=age_minutes)
    return {
        "id": 12345,
        "status": status,
        "conclusion": conclusion,
        "created_at": created.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "html_url": "https://example.invalid/run/12345",
    }


class ExplainDrift(unittest.TestCase):
    """Criterion 4: distinguish in-progress from cancelled or absent."""

    def test_absent_build_is_drift(self):
        self.assertEqual(cf.explain_drift(None), cf.DRIFT)

    def test_recent_in_progress_is_not_drift(self):
        for status in ("queued", "in_progress", "waiting", "pending"):
            with self.subTest(status=status):
                self.assertEqual(cf.explain_drift(run(status, age_minutes=2)), cf.OK)

    def test_stuck_in_progress_is_drift(self):
        stuck = int(cf.STUCK_AFTER.total_seconds() // 60) + 10
        self.assertEqual(cf.explain_drift(run("queued", age_minutes=stuck)), cf.DRIFT)

    def test_cancelled_is_drift(self):
        """The case that holds a divergence open, and the one Pages mislabels."""
        self.assertEqual(cf.explain_drift(run("completed", "cancelled")), cf.DRIFT)

    def test_success_with_differing_bytes_is_drift(self):
        self.assertEqual(cf.explain_drift(run("completed", "success")), cf.DRIFT)

    def test_failure_is_drift(self):
        self.assertEqual(cf.explain_drift(run("completed", "failure")), cf.DRIFT)


class CouldNotCheck(unittest.TestCase):
    """Criterion 3: a fetch failure is reported, never passed."""

    def test_fetch_failure_returns_none_after_retries(self):
        with mock.patch.object(cf.urllib.request, "urlopen",
                               side_effect=OSError("network down")):
            self.assertIsNone(cf.fetch_live())

    def test_main_reports_could_not_check_not_ok(self):
        with mock.patch.object(cf, "fetch_live", return_value=None):
            rc = cf.main()
        self.assertEqual(rc, cf.COULD_NOT_CHECK)
        self.assertNotEqual(rc, cf.OK, "a failed fetch must never read as in-sync")

    def test_could_not_check_is_a_nonzero_exit(self):
        """Exit 3 must fail the job -- a guard that could not look is not a pass."""
        self.assertNotEqual(cf.COULD_NOT_CHECK, 0)
        self.assertNotEqual(cf.COULD_NOT_CHECK, cf.DRIFT)


class SettleOnCacheLag(unittest.TestCase):
    """A just-deployed page can serve stale bytes briefly; that is not drift."""

    def test_mismatch_that_resolves_on_retry_is_in_sync(self):
        want = (cf.ROOT / "index.html").read_bytes()
        responses = [b"stale bytes", want]
        with mock.patch.object(cf, "fetch_live", side_effect=responses), \
             mock.patch.object(cf.time, "sleep"):
            self.assertEqual(cf.main(), cf.OK)

    def test_persistent_mismatch_falls_through_to_explain(self):
        with mock.patch.object(cf, "fetch_live", return_value=b"different"), \
             mock.patch.object(cf.time, "sleep"), \
             mock.patch.object(cf, "latest_pages_run", return_value=None):
            self.assertEqual(cf.main(), cf.DRIFT)


if __name__ == "__main__":
    unittest.main(verbosity=2)
