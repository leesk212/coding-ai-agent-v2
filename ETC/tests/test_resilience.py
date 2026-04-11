from __future__ import annotations

import unittest

from coding_agent.resilience import POLICIES, get_policy


class ResiliencePolicyTests(unittest.TestCase):
    def test_required_policies_exist(self) -> None:
        required = {
            "model_timeout",
            "no_progress_loop",
            "tool_call_error",
            "subagent_failure",
            "external_api_error",
            "safe_stop",
        }
        self.assertTrue(required.issubset(POLICIES))

    def test_policy_fields_are_populated(self) -> None:
        policy = get_policy("subagent_failure")
        self.assertEqual(policy.failure_type, "subagent_failure")
        self.assertGreaterEqual(policy.max_retries, 1)
        self.assertTrue(policy.user_status)
        self.assertTrue(policy.safe_stop_condition)


if __name__ == "__main__":
    unittest.main()
