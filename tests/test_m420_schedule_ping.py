"""
M4.20c — Temporary schedule ping diagnostic

Tests verify schedule_ping.yml:
- File exists
- Has workflow_dispatch trigger
- Has schedule trigger with cron "*/5 * * * *"
- Does not reference secrets
- Does not reference Tavily
- Does not reference Resend or email
- Does not reference X API
- Does not use checkout
- No push trigger
- No pull_request trigger
"""

import os
import unittest
import yaml


PING_WORKFLOW = ".github/workflows/schedule_ping.yml"


class TestSchedulePingExists(unittest.TestCase):

    def test_file_exists(self):
        self.assertTrue(os.path.isfile(PING_WORKFLOW),
                        f"{PING_WORKFLOW} does not exist")


class TestSchedulePingTriggers(unittest.TestCase):

    def _load_raw(self):
        with open(PING_WORKFLOW) as f:
            return f.read()

    def _load_yaml(self):
        with open(PING_WORKFLOW) as f:
            return yaml.safe_load(f)

    def _triggers(self):
        data = self._load_yaml()
        # yaml.safe_load parses 'on:' as boolean True
        return data.get(True, data.get("on", {}))

    def test_workflow_dispatch_present(self):
        self.assertIn("workflow_dispatch", self._triggers())

    def test_schedule_trigger_present(self):
        self.assertIn("schedule", self._triggers())

    def test_cron_is_every_5_minutes(self):
        schedules = self._triggers()["schedule"]
        crons = [s["cron"] for s in schedules]
        self.assertIn("*/5 * * * *", crons,
                      "Cron must be '*/5 * * * *' for 5-minute diagnostic ping")

    def test_no_push_trigger(self):
        content = self._load_raw()
        self.assertNotIn("push:", content)

    def test_no_pull_request_trigger(self):
        content = self._load_raw()
        self.assertNotIn("pull_request:", content)


class TestSchedulePingIsolated(unittest.TestCase):
    """Diagnostic workflow must not touch secrets, APIs, or email."""

    def _load_raw(self):
        with open(PING_WORKFLOW) as f:
            return f.read()

    def test_no_secrets_referenced(self):
        content = self._load_raw()
        self.assertNotIn("secrets.", content,
                         "Ping workflow must not reference any secrets")

    def test_no_tavily_referenced(self):
        content = self._load_raw()
        self.assertNotIn("TAVILY", content.upper(),
                         "Ping workflow must not reference Tavily")

    def test_no_resend_or_email_referenced(self):
        content = self._load_raw()
        upper = content.upper()
        self.assertNotIn("RESEND", upper,
                         "Ping workflow must not reference Resend")
        self.assertNotIn("EMAIL", upper,
                         "Ping workflow must not reference email")

    def test_no_x_api_referenced(self):
        content = self._load_raw()
        upper = content.upper()
        self.assertNotIn("TWITTER", upper,
                         "Ping workflow must not reference Twitter/X API")
        self.assertNotIn("X_API", upper,
                         "Ping workflow must not reference X API")

    def test_no_checkout_step(self):
        content = self._load_raw()
        self.assertNotIn("actions/checkout", content,
                         "Ping workflow must not use checkout (nothing to clone)")


if __name__ == "__main__":
    unittest.main()
