"""MST-RIF scoring: mean sustainable turns before the first verified regression."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SessionScore:
    task_id: str
    turns_attempted: int
    turns_passed: int
    first_regression_turn: int | None
    mst_score: int


def score_session(task_id: str, turn_results: list[bool | None]) -> SessionScore:
    """Score one session from its per-turn pass/fail outcomes.

    turn_results:
      True  = tests passed after this turn
      False = regression detected after this turn
      None  = turn was blocked by policy; tests were not run

    Every turn in `turn_results` was actually attempted, regardless of
    earlier failures — MST is computed post-hoc from the full trace.
    """
    first_failure = None

    for index, passed in enumerate(turn_results, start=1):
        if passed is False:
            first_failure = index
            break

    if first_failure is None:
        turns_passed = len(turn_results)
        mst_score = len(turn_results)
    else:
        turns_passed = first_failure - 1
        mst_score = turns_passed

    return SessionScore(
        task_id=task_id,
        turns_attempted=len(turn_results),
        turns_passed=turns_passed,
        first_regression_turn=first_failure,
        mst_score=mst_score,
    )
