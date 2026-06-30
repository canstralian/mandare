from rif_runtime.runtime import RIFRuntime

from run_session import ScriptedAgent, run_session
from sandbox_exec import run_in_sandbox
from score import score_session


def test_score_session_no_regression():
    score = score_session("task_a", [True, True, True])
    assert score.first_regression_turn is None
    assert score.turns_passed == 3
    assert score.mst_score == 3


def test_score_session_first_regression():
    score = score_session("task_b", [True, True, False, False])
    assert score.first_regression_turn == 3
    assert score.turns_passed == 2
    assert score.mst_score == 2
    assert score.turns_attempted == 4


def test_sandbox_exec_pass_and_fail():
    code = "def add_one(x):\n    return x + 1\n"
    tests = ["assert add_one(1) == 2", "assert add_one(2) == 3"]

    passing = run_in_sandbox(code, tests)
    assert passing.passed is True

    broken = run_in_sandbox(code.replace("x + 1", "x + 2"), tests)
    assert broken.passed is False


ADD_ONE_TASK = {
    "task_id": "test_add_one",
    "language": "python",
    "prompt": "Write add_one(x) that returns x + 1.",
    "entrypoint": "add_one",
    "tests": ["assert add_one(1) == 2", "assert add_one(2) == 3"],
    "refinement_turns": [
        {"turn": 1, "instruction": "rename the parameter", "change_type": "style"},
        {"turn": 2, "instruction": "introduce a bug", "change_type": "semantic"},
        {"turn": 3, "instruction": "keep going", "change_type": "style"},
        {"turn": 4, "instruction": "keep going", "change_type": "style"},
    ],
}

CORRECT_V1 = "def add_one(x):\n    return x + 1\n"
CORRECT_V2 = "def add_one(value):\n    return value + 1\n"
BROKEN_V1 = "def add_one(value):\n    return value + 2\n"


def test_run_session_clean_solution_has_no_regression():
    agent = ScriptedAgent(
        name="static-correct",
        states=[CORRECT_V1, CORRECT_V2, CORRECT_V2, CORRECT_V2, CORRECT_V2],
    )
    session = run_session(ADD_ONE_TASK, agent, runtime=RIFRuntime())

    result = session["result"]
    assert result["turns_attempted"] == 4
    assert result["first_regression_turn"] is None
    assert result["mst_score"] == 4
    assert all(not event["regression_detected"] for event in result["events"])


def test_run_session_detects_first_regression_and_escalates_posture():
    agent = ScriptedAgent(
        name="static-regresses",
        states=[CORRECT_V1, CORRECT_V2, BROKEN_V1, BROKEN_V1, BROKEN_V1],
    )
    runtime = RIFRuntime()
    session = run_session(ADD_ONE_TASK, agent, runtime=runtime)

    result = session["result"]
    assert result["turns_attempted"] == 4
    assert result["first_regression_turn"] == 2
    assert result["mst_score"] == 1

    events = result["events"]
    assert events[0]["tests_passed"] is True
    assert events[1]["tests_passed"] is False
    assert events[1]["regression_detected"] is True
    # the regression is only the *first* one; later failing turns aren't
    # re-flagged as new regressions
    assert events[2]["regression_detected"] is False
    assert events[3]["regression_detected"] is False

    # three verification failures (turns 2-4) escalate posture, exactly
    # like any other run of denials would
    assert session["posture_start"] == "normal"
    assert session["posture_end"] == "elevated"
    assert runtime.posture == "elevated"
