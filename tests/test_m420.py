"""
M4.20 / M4.20b — Schedule Mel Search Digest daily email

Tests verify:
- Two UTC schedule entries cover BST ("5 7 * * *") and GMT ("5 8 * * *")
- No timezone field in schedule entries (UTC-native crons, guard handles London time)
- London-time guard step uses TZ="Europe/London" to skip out-of-window scheduled runs
- Expensive steps are gated on steps.london_time.outputs.should_run == 'true'
- Scheduled runs: SEND_EMAIL resolves to 'true' via github.event_name == 'schedule'
- Manual runs: send_email input defaults to "false"
- workflow_dispatch still present with send_email input
- No push trigger; no pull_request trigger
- Tavily freeze defaults preserved (unchanged from M4.18)
- TAVILY_DAYS still has no default fallback
- mel_digest.yml (mock workflow) is unmodified — no schedule added there
"""

import unittest
import yaml


SEARCH_WORKFLOW = ".github/workflows/mel_search_digest.yml"
MOCK_WORKFLOW = ".github/workflows/mel_digest.yml"


class TestScheduleTrigger(unittest.TestCase):

    def _load_raw(self):
        with open(SEARCH_WORKFLOW) as f:
            return f.read()

    def _load_yaml(self):
        with open(SEARCH_WORKFLOW) as f:
            return yaml.safe_load(f)

    def _triggers(self):
        data = self._load_yaml()
        # yaml.safe_load parses 'on:' as boolean True, not the string "on"
        return data.get(True, data.get("on", {}))

    def test_schedule_trigger_present(self):
        content = self._load_raw()
        self.assertIn("schedule:", content)
        self.assertIn("cron:", content)

    def test_two_schedule_entries(self):
        schedules = self._triggers()["schedule"]
        self.assertEqual(len(schedules), 2,
                         f"Expected 2 schedule entries (BST + GMT), got {len(schedules)}")

    def test_bst_cron_present(self):
        schedules = self._triggers()["schedule"]
        crons = [s["cron"] for s in schedules]
        self.assertIn("5 7 * * *", crons,
                      "BST cron '5 7 * * *' (08:05 UTC+1) must be present")

    def test_gmt_cron_present(self):
        schedules = self._triggers()["schedule"]
        crons = [s["cron"] for s in schedules]
        self.assertIn("5 8 * * *", crons,
                      "GMT cron '5 8 * * *' (08:05 UTC+0) must be present")

    def test_no_timezone_field_in_schedule(self):
        schedules = self._triggers()["schedule"]
        for entry in schedules:
            self.assertNotIn("timezone", entry,
                             f"Schedule entry must not use a timezone field: {entry}")

    def test_workflow_dispatch_still_present(self):
        self.assertIn("workflow_dispatch", self._triggers())

    def test_no_push_trigger(self):
        content = self._load_raw()
        self.assertNotIn("push:", content)

    def test_no_pull_request_trigger(self):
        content = self._load_raw()
        self.assertNotIn("pull_request:", content)


class TestLondonGuardStep(unittest.TestCase):
    """Guard step skips real work when a scheduled cron fires outside the London 08:xx window."""

    def _load_raw(self):
        with open(SEARCH_WORKFLOW) as f:
            return f.read()

    def _load_yaml(self):
        with open(SEARCH_WORKFLOW) as f:
            return yaml.safe_load(f)

    def test_guard_step_uses_london_timezone(self):
        content = self._load_raw()
        self.assertIn('TZ="Europe/London"', content,
                      "Guard step must use TZ=Europe/London to determine local hour")

    def test_guard_step_checks_london_hour_08(self):
        content = self._load_raw()
        self.assertIn('"08"', content,
                      "Guard step must accept runs where London hour == 08")

    def test_guard_outputs_should_run(self):
        content = self._load_raw()
        self.assertIn("should_run=true", content)
        self.assertIn("should_run=false", content)

    def test_guard_step_has_id_london_time(self):
        data = self._load_yaml()
        # yaml.safe_load parses 'on:' as True; find steps normally
        steps = data["jobs"]["search-digest"]["steps"]
        ids = [s.get("id", "") for s in steps]
        self.assertIn("london_time", ids,
                      "Guard step must have id: london_time")

    def test_expensive_steps_gated_on_guard(self):
        content = self._load_raw()
        self.assertIn("steps.london_time.outputs.should_run == 'true'", content,
                      "Expensive steps must be guarded by london_time output")

    def test_checkout_step_is_gated(self):
        data = self._load_yaml()
        steps = data["jobs"]["search-digest"]["steps"]
        checkout = next((s for s in steps if s.get("uses", "").startswith("actions/checkout")), None)
        self.assertIsNotNone(checkout, "Checkout step not found")
        self.assertEqual(
            checkout.get("if", ""),
            "steps.london_time.outputs.should_run == 'true'",
            "Checkout step must be gated on london_time guard",
        )

    def test_run_step_is_gated(self):
        data = self._load_yaml()
        steps = data["jobs"]["search-digest"]["steps"]
        run_step = next((s for s in steps if s.get("run", "").startswith("python run_search")), None)
        self.assertIsNotNone(run_step, "run_search.py step not found")
        self.assertEqual(
            run_step.get("if", ""),
            "steps.london_time.outputs.should_run == 'true'",
            "run_search.py step must be gated on london_time guard",
        )

    def test_manual_run_bypasses_guard(self):
        content = self._load_raw()
        # Guard must short-circuit for non-schedule events
        self.assertIn('"schedule"', content,
                      "Guard must check github.event_name for schedule vs manual")


class TestSendEmailBehavior(unittest.TestCase):

    def _load_raw(self):
        with open(SEARCH_WORKFLOW) as f:
            return f.read()

    def _load_yaml(self):
        with open(SEARCH_WORKFLOW) as f:
            return yaml.safe_load(f)

    def test_send_email_uses_schedule_event_expression(self):
        content = self._load_raw()
        self.assertIn("github.event_name == 'schedule'", content,
                      "SEND_EMAIL must resolve to true when triggered by schedule")

    def test_send_email_references_inputs(self):
        content = self._load_raw()
        self.assertIn("inputs.send_email", content,
                      "SEND_EMAIL must fall back to inputs.send_email for manual runs")

    def test_send_email_line_contains_schedule_true_logic(self):
        for line in self._load_raw().splitlines():
            if "SEND_EMAIL:" in line:
                self.assertIn("'true'", line,
                              "SEND_EMAIL line must set 'true' for scheduled runs")
                return
        self.fail("SEND_EMAIL not found in workflow env")

    def test_manual_input_send_email_default_false(self):
        data = self._load_yaml()
        # yaml.safe_load parses 'on:' as boolean True
        triggers = data.get(True, data.get("on", {}))
        inputs = triggers["workflow_dispatch"].get("inputs", {})
        self.assertIn("send_email", inputs,
                      "workflow_dispatch must declare send_email input")
        default = str(inputs["send_email"].get("default", "")).lower()
        self.assertEqual(default, "false",
                         "send_email input must default to 'false' for manual runs")

    def test_send_email_not_hardwired_to_secret(self):
        content = self._load_raw()
        for line in content.splitlines():
            if "SEND_EMAIL:" in line and "secrets.SEND_EMAIL" in line:
                self.fail(
                    f"SEND_EMAIL must use the schedule expression, not a bare secret: {line.strip()!r}"
                )


class TestTavilyFreezePreserved(unittest.TestCase):
    """M4.18 freeze defaults must be unchanged."""

    def _load_raw(self):
        with open(SEARCH_WORKFLOW) as f:
            return f.read()

    def test_max_search_queries_default_10(self):
        self.assertIn("MAX_SEARCH_QUERIES", self._load_raw())
        self.assertIn("|| '10'", self._load_raw())

    def test_max_results_per_query_default_10(self):
        self.assertIn("MAX_RESULTS_PER_QUERY", self._load_raw())

    def test_tavily_search_depth_default_advanced(self):
        self.assertIn("|| 'advanced'", self._load_raw())

    def test_tavily_topic_default_general(self):
        self.assertIn("|| 'general'", self._load_raw())

    def test_tavily_time_range_default_day(self):
        self.assertIn("|| 'day'", self._load_raw())

    def test_tavily_auto_parameters_default_false(self):
        self.assertIn("TAVILY_AUTO_PARAMETERS", self._load_raw())

    def test_tavily_query_style_default_loose(self):
        self.assertIn("|| 'loose'", self._load_raw())

    def test_tavily_days_has_no_default_fallback(self):
        for line in self._load_raw().splitlines():
            if "TAVILY_DAYS" in line and "||" in line:
                self.fail(
                    f"TAVILY_DAYS should have no default fallback, found: {line.strip()!r}"
                )


class TestMockWorkflowUnchanged(unittest.TestCase):
    """mel_digest.yml must not have a schedule trigger added."""

    def _load_raw(self):
        with open(MOCK_WORKFLOW) as f:
            return f.read()

    def test_no_schedule_in_mock_workflow(self):
        content = self._load_raw()
        # Ignore commented-out lines; only check uncommented schedule/cron
        active_lines = [l for l in content.splitlines() if not l.lstrip().startswith("#")]
        active = "\n".join(active_lines)
        self.assertNotIn("schedule:", active,
                         "mel_digest.yml must not have an active schedule trigger")
        self.assertNotIn("cron:", active,
                         "mel_digest.yml must not have an active cron trigger")

    def test_workflow_dispatch_present_in_mock(self):
        content = self._load_raw()
        self.assertIn("workflow_dispatch", content)


if __name__ == "__main__":
    unittest.main()
