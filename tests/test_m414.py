"""
Tests for M4.14: optional Tavily freshness parameters.
Verifies that TAVILY_SEARCH_DEPTH, TAVILY_TOPIC, TAVILY_DAYS, TAVILY_TIME_RANGE
are correctly read from env vars, merged into the POST payload, and logged.
No real API calls are made — requests.post is patched throughout.
"""

import io
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.providers.tavily_search_provider import (
    _build_optional_params,
    _post,
    get_posts,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_resp(status=200, body=None):
    """Return a mock requests.Response."""
    mock = MagicMock()
    mock.status_code = status
    mock.json.return_value = body or {"results": []}
    mock.headers = {}
    return mock


def _captured_payload(mock_requests_post):
    """Return the JSON payload sent in the last requests.post call."""
    _, kwargs = mock_requests_post.call_args
    return kwargs.get("json", mock_requests_post.call_args[0][1]
                      if len(mock_requests_post.call_args[0]) > 1 else {})


def _env(**overrides):
    """Return a patch.dict context that clears the four Tavily env vars then sets overrides."""
    base = {
        "TAVILY_SEARCH_DEPTH": "",
        "TAVILY_TOPIC": "",
        "TAVILY_DAYS": "",
        "TAVILY_TIME_RANGE": "",
    }
    base.update(overrides)
    return patch.dict(os.environ, base)


# ---------------------------------------------------------------------------
# 1. _build_optional_params — env var parsing
# ---------------------------------------------------------------------------

class TestBuildOptionalParams(unittest.TestCase):

    def test_default_search_depth_when_no_env_var(self):
        with _env():
            params = _build_optional_params()
        self.assertEqual(params["search_depth"], "basic")

    def test_search_depth_advanced(self):
        with _env(TAVILY_SEARCH_DEPTH="advanced"):
            params = _build_optional_params()
        self.assertEqual(params["search_depth"], "advanced")

    def test_topic_news(self):
        with _env(TAVILY_TOPIC="news"):
            params = _build_optional_params()
        self.assertEqual(params["topic"], "news")

    def test_topic_absent_when_not_set(self):
        with _env():
            params = _build_optional_params()
        self.assertNotIn("topic", params)

    def test_days_integer(self):
        with _env(TAVILY_DAYS="1"):
            params = _build_optional_params()
        self.assertEqual(params["days"], 1)
        self.assertIsInstance(params["days"], int)

    def test_days_absent_when_not_set(self):
        with _env():
            params = _build_optional_params()
        self.assertNotIn("days", params)

    def test_days_invalid_non_integer_skipped(self):
        with _env(TAVILY_DAYS="not-a-number"):
            params = _build_optional_params()
        self.assertNotIn("days", params)

    def test_days_invalid_non_integer_logs_warning(self):
        buf = io.StringIO()
        with _env(TAVILY_DAYS="banana"), patch("sys.stdout", buf):
            _build_optional_params()
        self.assertIn("TAVILY_DAYS", buf.getvalue())
        self.assertIn("not an integer", buf.getvalue())

    def test_time_range_day(self):
        with _env(TAVILY_TIME_RANGE="day"):
            params = _build_optional_params()
        self.assertEqual(params["time_range"], "day")

    def test_time_range_absent_when_not_set(self):
        with _env():
            params = _build_optional_params()
        self.assertNotIn("time_range", params)

    def test_all_params_together(self):
        with _env(TAVILY_SEARCH_DEPTH="advanced", TAVILY_TOPIC="news",
                  TAVILY_DAYS="3", TAVILY_TIME_RANGE="week"):
            params = _build_optional_params()
        self.assertEqual(params["search_depth"], "advanced")
        self.assertEqual(params["topic"], "news")
        self.assertEqual(params["days"], 3)
        self.assertEqual(params["time_range"], "week")

    def test_whitespace_stripped(self):
        with _env(TAVILY_SEARCH_DEPTH="  advanced  ", TAVILY_TOPIC="  news  "):
            params = _build_optional_params()
        self.assertEqual(params["search_depth"], "advanced")
        self.assertEqual(params["topic"], "news")

    def test_empty_string_env_var_uses_default_depth(self):
        with _env(TAVILY_SEARCH_DEPTH=""):
            params = _build_optional_params()
        self.assertEqual(params["search_depth"], "basic")


# ---------------------------------------------------------------------------
# 2. _post — optional_params merged into payload
# ---------------------------------------------------------------------------

class TestPostPayload(unittest.TestCase):

    def _call_post(self, optional_params, env=None):
        """Call _post with a mocked TAVILY_API_KEY and requests.post."""
        env = env or {}
        env.setdefault("TAVILY_API_KEY", "test-key")
        mock_resp = _mock_resp()
        with patch.dict(os.environ, env), \
             patch("requests.post", return_value=mock_resp) as mock_post:
            _post("site:x.com NVDA", 5, optional_params=optional_params)
            return mock_post

    def test_default_basic_depth_in_payload(self):
        with _env():
            params = _build_optional_params()
        mock_post = self._call_post(params)
        payload = _captured_payload(mock_post)
        self.assertEqual(payload["search_depth"], "basic")

    def test_advanced_depth_in_payload(self):
        with _env(TAVILY_SEARCH_DEPTH="advanced"):
            params = _build_optional_params()
        mock_post = self._call_post(params)
        payload = _captured_payload(mock_post)
        self.assertEqual(payload["search_depth"], "advanced")

    def test_topic_in_payload_when_set(self):
        with _env(TAVILY_TOPIC="news"):
            params = _build_optional_params()
        mock_post = self._call_post(params)
        payload = _captured_payload(mock_post)
        self.assertEqual(payload["topic"], "news")

    def test_topic_absent_in_payload_when_not_set(self):
        with _env():
            params = _build_optional_params()
        mock_post = self._call_post(params)
        payload = _captured_payload(mock_post)
        self.assertNotIn("topic", payload)

    def test_days_in_payload_as_int(self):
        with _env(TAVILY_DAYS="2"):
            params = _build_optional_params()
        mock_post = self._call_post(params)
        payload = _captured_payload(mock_post)
        self.assertEqual(payload["days"], 2)
        self.assertIsInstance(payload["days"], int)

    def test_days_absent_in_payload_when_invalid(self):
        with _env(TAVILY_DAYS="bad"):
            params = _build_optional_params()
        mock_post = self._call_post(params)
        payload = _captured_payload(mock_post)
        self.assertNotIn("days", payload)

    def test_time_range_in_payload_when_set(self):
        with _env(TAVILY_TIME_RANGE="day"):
            params = _build_optional_params()
        mock_post = self._call_post(params)
        payload = _captured_payload(mock_post)
        self.assertEqual(payload["time_range"], "day")

    def test_time_range_absent_in_payload_when_not_set(self):
        with _env():
            params = _build_optional_params()
        mock_post = self._call_post(params)
        payload = _captured_payload(mock_post)
        self.assertNotIn("time_range", payload)

    def test_no_optional_params_uses_hardcoded_basic(self):
        """Passing optional_params=None keeps the hardcoded basic default."""
        mock_resp = _mock_resp()
        with patch.dict(os.environ, {"TAVILY_API_KEY": "test-key"}), \
             patch("requests.post", return_value=mock_resp) as mock_post:
            _post("query", 5, optional_params=None)
        payload = _captured_payload(mock_post)
        self.assertEqual(payload["search_depth"], "basic")
        self.assertNotIn("topic", payload)
        self.assertNotIn("days", payload)
        self.assertNotIn("time_range", payload)


# ---------------------------------------------------------------------------
# 3. get_posts — logging of non-default params
# ---------------------------------------------------------------------------

class TestGetPostsLogging(unittest.TestCase):

    def _run_get_posts(self, extra_env=None):
        """Run get_posts with a minimal profile, capturing stdout."""
        profile = {
            "search_terms": ["NVDA confusion"],
            "query_templates": ['site:x.com "{term}"'],
        }
        env = {
            "TAVILY_API_KEY": "test-key",
            "MAX_SEARCH_QUERIES": "1",
            "MAX_RESULTS_PER_QUERY": "1",
            "QUERY_SEED": "0",
        }
        env.update(extra_env or {})
        # Clear optional params that might leak from environment
        for k in ("TAVILY_SEARCH_DEPTH", "TAVILY_TOPIC", "TAVILY_DAYS", "TAVILY_TIME_RANGE"):
            env.setdefault(k, "")

        mock_resp = _mock_resp(body={"results": []})
        buf = io.StringIO()
        with patch.dict(os.environ, env, clear=False), \
             patch("requests.post", return_value=mock_resp), \
             patch("sys.stdout", buf):
            get_posts(profile)
        return buf.getvalue()

    def test_no_freshness_log_when_all_defaults(self):
        output = self._run_get_posts()
        self.assertNotIn("Active freshness params", output)

    def test_logs_advanced_depth(self):
        output = self._run_get_posts({"TAVILY_SEARCH_DEPTH": "advanced"})
        self.assertIn("Active freshness params", output)
        self.assertIn("search_depth", output)
        self.assertIn("advanced", output)

    def test_logs_topic(self):
        output = self._run_get_posts({"TAVILY_TOPIC": "news"})
        self.assertIn("Active freshness params", output)
        self.assertIn("topic", output)
        self.assertIn("news", output)

    def test_logs_days(self):
        output = self._run_get_posts({"TAVILY_DAYS": "1"})
        self.assertIn("Active freshness params", output)
        self.assertIn("days", output)

    def test_logs_time_range(self):
        output = self._run_get_posts({"TAVILY_TIME_RANGE": "week"})
        self.assertIn("Active freshness params", output)
        self.assertIn("time_range", output)
        self.assertIn("week", output)

    def test_no_api_key_in_logs(self):
        output = self._run_get_posts({"TAVILY_TOPIC": "news"})
        self.assertNotIn("test-key", output)

    def test_basic_depth_not_logged_as_non_default(self):
        output = self._run_get_posts({"TAVILY_SEARCH_DEPTH": "basic"})
        self.assertNotIn("Active freshness params", output)


# ---------------------------------------------------------------------------
# 4. Backward compatibility — existing tests must not regress
# ---------------------------------------------------------------------------

class TestBackwardCompat(unittest.TestCase):

    def test_post_still_works_without_optional_params(self):
        """_post called with no optional_params arg must not raise."""
        mock_resp = _mock_resp()
        with patch.dict(os.environ, {"TAVILY_API_KEY": "k"}), \
             patch("requests.post", return_value=mock_resp) as mock_post:
            result = _post("q", 3)
        self.assertIsNotNone(result)
        payload = _captured_payload(mock_post)
        self.assertEqual(payload["search_depth"], "basic")

    def test_days_zero_is_valid_integer(self):
        with _env(TAVILY_DAYS="0"):
            params = _build_optional_params()
        self.assertEqual(params["days"], 0)

    def test_days_large_integer(self):
        with _env(TAVILY_DAYS="30"):
            params = _build_optional_params()
        self.assertEqual(params["days"], 30)

    def test_float_days_rejected(self):
        with _env(TAVILY_DAYS="1.5"):
            params = _build_optional_params()
        self.assertNotIn("days", params)


if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(__import__("__main__"))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
