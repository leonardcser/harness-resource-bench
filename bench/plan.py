"""Which cases a run measures, and in what order."""

import random

from workload import SEED, transcript

QUESTIONS = ("startup", "start-memory", "task", "long-session", "new-sessions", "idle")
# The order of the questions in a run. start-memory empties the file cache, so
# it runs last: the next case would read its files again and pay for them.
RUN_ORDER = (*(q for q in QUESTIONS if q != "start-memory"), "start-memory")
# A typical hosted model's streaming rate, in tokens per second.
TUI_RATE = 60
# Streaming rates for the coding task in the TUI, in tokens per second.
STREAM_RATES = (30, TUI_RATE, 120, 250, 1000)
REPETITIONS = 3
# Startup and memory at start take seconds and vary the most, so they repeat
# more often.
START_REPETITIONS = 10
# Tool calls of the coding task.
CODING_CALLS = 24
# Tool calls of the coding task in a setup check: one of each kind, so the check
# runs each tool of each agent. The read comes before the edit of its file.
SMOKE_CALLS = ("shell", "read", "edit", "search", "write")
# Checkpoints of the long session in turns, and of the new-session run in
# sessions. Both take the tool calls of each turn from the profile. 64 such
# turns hold about as much as the 98th percentile of real sessions.
TURNS = (1, 4, 16, 32, 64)
SESSIONS = (1, 2, 4, 8, 16)
IDLE_SECONDS = 300
# Points of the idle interval reported as `idle_*_after_S`, in seconds.
IDLE_MARKS = (0, 30, 60, 120, 300)


def plan(selected, smoke=False):
    """Every case, short questions first. Each repeat shuffles the agents."""
    calls = SMOKE_CALLS if smoke else CODING_CALLS
    cases = []
    for repeat in range(1 if smoke else START_REPETITIONS):
        block = []
        for agent in selected:
            common = {"agent": agent, "repeat": repeat}
            launch = dict(common, rate=0, turns=0, calls=0, checkpoints=[])
            block += [
                dict(launch, question="startup", frontend="tui"),
                dict(launch, question="start-memory", frontend="headless"),
            ]
            if repeat >= REPETITIONS:
                continue
            task = dict(common, question="task", turns=1, calls=calls, checkpoints=[1])
            block += [
                dict(task, frontend="headless", rate=TUI_RATE),
                *(dict(task, frontend="tui", rate=rate) for rate in STREAM_RATES),
            ]
            turns = [1, 2] if smoke else list(TURNS)
            sessions = [1, 2] if smoke else list(SESSIONS)
            block += [
                dict(
                    common,
                    question=question,
                    frontend="tui",
                    rate=1000,
                    turns=checkpoints[-1],
                    calls=None,
                    checkpoints=checkpoints,
                )
                for question, checkpoints in (
                    ("long-session", turns),
                    ("new-sessions", sessions),
                )
            ]
            block.append(
                dict(
                    common,
                    question="idle",
                    frontend="tui",
                    rate=1000,
                    turns=1,
                    calls=2 if smoke else calls,
                    idle_seconds=2 if smoke else IDLE_SECONDS,
                    checkpoints=[1],
                )
            )
        random.Random(SEED + repeat).shuffle(block)
        cases += block
    cases.sort(
        key=lambda c: (
            RUN_ORDER.index(c["question"]),
            -c["rate"],
            c["frontend"],
            c["turns"],
            c["repeat"],
        )
    )
    for index, case in enumerate(cases):
        case["id"] = (
            f"{index:04d}-{case['agent']}-{case['question']}"
            f"-{case['frontend']}-{case['rate']}"
        )
    return cases


def warmups(selected):
    """One practice run per agent and frontend, which no result counts."""
    return [
        {
            "id": f"warmup-{agent}-{frontend}",
            "agent": agent,
            "frontend": frontend,
            "question": "task",
            "rate": 1000,
            "turns": 1,
            "calls": 3,
            "checkpoints": [1],
        }
        for agent in selected
        for frontend in ("headless", "tui")
    ]


def work():
    """The coding task and the first turns of the long session."""
    return {
        "seed": SEED,
        "task": transcript(1, CODING_CALLS)[0],
        "session": transcript(4),
    }
