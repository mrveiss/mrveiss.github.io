#!/usr/bin/env python3
"""Report when the repository and the live site disagree.

Observed 2026-09-09: for roughly forty minutes the live root page served 11,965
bytes while this repository held 20,489. Nothing reported it -- the window closed
because a queued build finished, not because anything was watching. See
mrveiss.github.io#3.

Runs on a schedule rather than on push, deliberately: a divergence caused by a
build that never completed produces no push, so a push-triggered check cannot see
the case it exists for.

`pages/builds` is NOT used. It reports a cancelled deploy as "Page build failed."
with a null detail, indistinguishable from a real content failure, and it cannot
tell queued from stuck. The Actions runs API can.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

from outcomes import Outcome

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "index.html"
LIVE = "https://mrveiss.github.io/"
REPO = os.environ.get("GITHUB_REPOSITORY", "mrveiss/mrveiss.github.io")
PAGES_WORKFLOW = "dynamic/pages/pages-build-deployment"
STUCK_AFTER = timedelta(minutes=30)
TIMEOUT = 20
SETTLE_ATTEMPTS = 3
SETTLE_SECONDS = 20

# Named for what they mean here; the exit codes come from the shared vocabulary so
# "could not check" is one concept across both checkers rather than two spellings.
OK = Outcome.PASS.exit_code
DRIFT = Outcome.FAIL.exit_code
COULD_NOT_CHECK = Outcome.UNKNOWN.exit_code


def api(path: str) -> dict | None:
    """GitHub API GET. Returns None when the call could not be made."""
    req = urllib.request.Request(
        f"https://api.github.com/{path}",
        headers={"Accept": "application/vnd.github+json",
                 "User-Agent": "mrveiss.github.io-freshness"},
    )
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return json.load(r)
    except Exception as e:  # noqa: BLE001
        print(f"  (runs API unavailable: {type(e).__name__}: {e})")
        return None


def latest_pages_run() -> dict | None:
    data = api(f"repos/{REPO}/actions/runs?per_page=20")
    if not data:
        return None
    runs = [r for r in data.get("workflow_runs", []) if r.get("path") == PAGES_WORKFLOW]
    return runs[0] if runs else None


def fetch_live() -> bytes | None:
    """Fetch the served page. Returns None only after every attempt failed.

    Retried because a single transport blip on a scheduled job would otherwise
    read as drift -- but a total failure returns None and is reported as
    could-not-check, never as a pass.
    """
    last = ""
    for _ in range(3):
        req = urllib.request.Request(
            LIVE, headers={"User-Agent": "mrveiss.github.io-freshness",
                           "Cache-Control": "no-cache"})
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001
            last = f"{type(e).__name__}: {e}"
    print(f"::error title=Could not check::fetching {LIVE} failed on every attempt "
          f"-- {last}. Reported as could-not-check, NOT as in-sync.")
    return None


def _explain_in_flight(run: dict, status: str, age, where: str) -> int:
    """A deploy still running explains a divergence; one stuck past the threshold does not."""
    if age > STUCK_AFTER:
        print(f"::error title=Deploy stuck::Build {run['id']} has been {status} for "
              f"{age} (> {STUCK_AFTER}), holding the divergence open. {where}")
        return DRIFT
    print(f"BUILD IN PROGRESS: {run['id']} {status} for {age}; divergence is expected "
          f"to close when it finishes. {where}")
    return OK


def explain_drift(run: dict | None) -> int:
    """Name the cause of a divergence. Never returns OK."""
    if run is None:
        print("::error title=Drift with no deploy::The served page differs from this "
              "repository and no Pages build explains it -- nothing is in flight and "
              "nothing recently ran. This divergence is not transient.")
        return DRIFT

    status, conclusion = run.get("status"), run.get("conclusion")
    started = datetime.fromisoformat(run["created_at"].replace("Z", "+00:00"))
    age = datetime.now(timezone.utc) - started
    where = run.get("html_url", "")

    if status in ("queued", "in_progress", "waiting", "pending"):
        return _explain_in_flight(run, status, age, where)

    if conclusion == "cancelled":
        print(f"::error title=Deploy cancelled::Build {run['id']} was CANCELLED, so the "
              f"divergence will not close on its own. Note the Pages API reports this as "
              f'"Page build failed." with a null detail -- it is a cancellation, not a '
              f"content defect. {where}")
        return DRIFT

    print(f"::error title=Drift after {conclusion} deploy::Build {run['id']} finished with "
          f"conclusion={conclusion}, yet the served bytes differ from this repository. "
          f"{where}")
    return DRIFT


def _settle(want_hash: str) -> int | None:
    """Re-fetch before calling a mismatch drift.

    This runs ON deploy completion, and a just-finished deploy can still be served
    from cache for a few seconds -- so the first mismatch after a healthy deploy is
    expected. Crying drift there would make the check noisy enough to ignore, which
    is worse than not having it.

    Returns a exit code when it resolves, or None to fall through to classification.
    """
    for attempt in range(SETTLE_ATTEMPTS):
        time.sleep(SETTLE_SECONDS)
        again = fetch_live()
        if again is None:
            return COULD_NOT_CHECK
        if hashlib.sha256(again).hexdigest() == want_hash:
            print(f"\nIN SYNC after settling {(attempt + 1) * SETTLE_SECONDS}s "
                  "(cache lag, not drift).")
            return OK
    return None


def main() -> int:
    if not PAGE.exists():
        print(f"COULD NOT CHECK: {PAGE} is missing -- nothing was compared")
        return COULD_NOT_CHECK

    want = PAGE.read_bytes()
    got = fetch_live()
    if got is None:
        return COULD_NOT_CHECK

    want_hash = hashlib.sha256(want).hexdigest()
    got_hash = hashlib.sha256(got).hexdigest()
    print(f"repo   {len(want):>7} bytes  sha256 {want_hash}")
    print(f"served {len(got):>7} bytes  sha256 {got_hash}")

    if want_hash == got_hash:
        print("\nIN SYNC: the served page is byte-identical to this repository.")
        return OK

    settled = _settle(want_hash)
    if settled is not None:
        return settled

    print(f"\nDIVERGENT: still differs after {SETTLE_ATTEMPTS * SETTLE_SECONDS}s -- "
          "not cache lag.")
    return explain_drift(latest_pages_run())


if __name__ == "__main__":
    sys.exit(main())
