import unittest
from copy import deepcopy
from unittest.mock import patch

import workload
from workload import fit


class ToolOrderTest(unittest.TestCase):
    def setUp(self):
        workload.steps.cache_clear()
        self.addCleanup(workload.steps.cache_clear)

    def test_fit_counts_first_kinds_and_followers_within_each_turn(self):
        def step(kind):
            return {
                "kind": kind,
                "reasoning": 0,
                "text": 0,
                "arguments": 1,
                "result": 1,
            }

        final = {"reasoning": 0, "text": 1}
        turns = [
            ([step("read"), step("edit"), step("edit")], final),
            ([], final),
            ([step("shell")], final),
        ]
        with patch.object(fit, "turns", return_value=iter(turns)):
            profile = fit.fit(None)

        self.assertEqual(profile["source"], {"turns": 3, "steps": 4})
        self.assertEqual(profile["turn"]["first"], {"read": 1, "shell": 1})
        self.assertEqual(
            {kind: tool["next"] for kind, tool in profile["tools"].items()},
            {"read": {"edit": 1}, "edit": {"edit": 1}, "shell": {}},
        )

    def test_each_kind_follows_the_emitted_kind_before_it(self):
        profile = deepcopy(workload.PROFILE)
        profile["turn"]["first"] = {"edit": 1}
        for kind, tool in profile["tools"].items():
            tool["next"] = {"read": {"edit": 1}, "edit": {"shell": 1}}.get(
                kind, {"shell": 1}
            )
        with patch.object(workload, "PROFILE", profile):
            for turn in (0, 1):
                read, edit, shell = workload.steps(turn, calls=3)
                self.assertEqual(
                    (read.kind, edit.kind, shell.kind), ("read", "edit", "shell")
                )
                self.assertEqual(edit.path, read.path)
