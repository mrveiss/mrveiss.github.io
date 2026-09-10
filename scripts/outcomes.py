"""One vocabulary for what a check concluded.

The two checkers in this directory each grew their own, and they disagreed on the
concept that matters most:

    check_page.py       PASS / FAIL / UNKNOWN / SKIP     (strings, per assertion)
    check_freshness.py  OK / DRIFT / COULD_NOT_CHECK     (ints, as exit codes)

`UNKNOWN` and `COULD_NOT_CHECK` are the same idea -- *the check did not run* --
under two names in one directory, which is precisely the distinction both scripts
exist to protect. A guard that cannot say "I did not look" in one consistent way is
a poor advertisement for the rule it enforces.

Exit codes are part of the contract with the workflows and are unchanged:

    0  everything that ran, passed (or did not apply)
    1  a check ran and found a defect
    3  a check could not run -- still fails the job, never reported as a pass
"""

from __future__ import annotations

from enum import Enum


class Outcome(Enum):
    """A check's verdict, and the exit code it implies."""

    PASS = ("PASS", 0)
    FAIL = ("FAIL", 1)
    UNKNOWN = ("UNKNOWN", 3)
    SKIP = ("SKIP", 0)

    def __init__(self, label: str, exit_code: int) -> None:
        self.label = label
        self.exit_code = exit_code

    def __str__(self) -> str:
        return self.label

    @property
    def is_problem(self) -> bool:
        """True when this outcome must fail the job.

        SKIP and PASS do not; UNKNOWN does, which is the whole point -- a check
        that could not look must never read as one that looked and found nothing.
        """
        return self.exit_code != 0
