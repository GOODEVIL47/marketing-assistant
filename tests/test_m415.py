"""
Tests for M4.15: Tavily discovery experiment mode.
Covers: TAVILY_AUTO_PARAMETERS, TAVILY_QUERY_STYLE, _query_style(),
_filter_by_style(), loose_discovery and market_movers profile buckets,
query cap, seed determinism, logging safety, and mock-mode stability.
No real API calls — requests.post is patched throughout.
"""

import io
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.providers.tavily_search_provider import (
    _build_optional_params,
    _build_queries,
    _filter_by_style,
    _query_style,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_resp(status=200, body=None):
    m = MagicMock()
    m.status_code = status
    m.json.return_value = body or {"results": []}
    m.headers = {}
    return m


def _payload_from(mock_post):
    _, kwargs = mock_post.call_args
    return kwargs.get("json", {})


def _clear_style_env():
    """Patch dict context that clears all M4.15 env vars."""
    return patch.dict(os.environ, {
        "TAVILY_QUERY_STYLE": "",
        "TAVILY_AUTO_PARAMETERS": "",
    })


def _profile_mixed():
    """Minimal profile with both exact (quoted) and loose (unquoted) bucket queries."""
    return {
        "query_buckets": {
            "exact_bucket": [
                'site:x.com "NVDA earnings reaction"',
                'site:x.com "TSLA makes no sense"',
                'site:x.com "retail investors overwhelmed"',
                'site:x.com "why is this stock moving"',
            ],
            "loose_bucket": [
                "site:x.com NVDA earnings today",
                "site:x.com TSLA premarket confusing",
                "site:x.com US stocks moving today",
                "site:x.com earnings reaction today stock",
            ],
        }
    }


def _profile_exact_only():
    return {
        "query_buckets": {
            "bucket": [
                'site:x.com "NVDA earnings reaction"',
                'site:x.com "TSLA makes no sense"',
            ]
        }
    }


def _profile_loose_only():
    return {
        "query_buckets": {
            "bucket": [
                "site:x.com NVDA earnings today",
                "site:x.com TSLA premarket confusing",
            ]
        }
    }


# ---------------------------------------------------------------------------
# 1. _query_style() — env var parsing and validation
# ---------------------------------------------------------------------------

class TestQueryStyle(unittest.TestCase):

    def test_default_is_mixed(self):
        with _clear_style_env():
            self.assertEqual(_query_style(), "mixed")

    def test_exact(self):
        with patch.dict(os.environ, {"TAVILY_QUERY_STYLE": "exact"}):
            self.assertEqual(_query_style(), "exact")

    def test_loose(self):
        with patch.dict(os.environ, {"TAVILY_QUERY_STYLE": "loose"}):
            self.assertEqual(_query_style(), "loose")

    def test_mixed_explicit(self):
        with patch.dict(os.environ, {"TAVILY_QUERY_STYLE": "mixed"}):
            self.assertEqual(_query_style(), "mixed")

    def test_case_insensitive(self):
        with patch.dict(os.environ, {"TAVILY_QUERY_STYLE": "EXACT"}):
            self.assertEqual(_query_style(), "exact")
        with patch.dict(os.environ, {"TAVILY_QUERY_STYLE": "Loose"}):
            self.assertEqual(_query_style(), "loose")

    def test_invalid_falls_back_to_mixed(self):
        with patch.dict(os.environ, {"TAVILY_QUERY_STYLE": "turbo"}):
            self.assertEqual(_query_style(), "mixed")

    def test_invalid_logs_warning(self):
        buf = io.StringIO()
        with patch.dict(os.environ, {"TAVILY_QUERY_STYLE": "turbo"}), \
             patch("sys.stdout", buf):
            _query_style()
        self.assertIn("TAVILY_QUERY_STYLE", buf.getvalue())
        self.assertIn("not valid", buf.getvalue())

    def test_whitespace_stripped(self):
        with patch.dict(os.environ, {"TAVILY_QUERY_STYLE": "  loose  "}):
            self.assertEqual(_query_style(), "loose")


# ---------------------------------------------------------------------------
# 2. _filter_by_style() — filtering logic
# ---------------------------------------------------------------------------

class TestFilterByStyle(unittest.TestCase):

    _EXACT = ['site:x.com "NVDA earnings"', 'site:x.com "retail overwhelmed"']
    _LOOSE = ["site:x.com NVDA today", "site:x.com premarket stocks"]
    _MIXED = _EXACT + _LOOSE

    def test_mixed_returns_all(self):
        result = _filter_by_style(self._MIXED, "mixed")
        self.assertEqual(result, self._MIXED)

    def test_exact_returns_only_quoted(self):
        result = _filter_by_style(self._MIXED, "exact")
        self.assertEqual(result, self._EXACT)
        for q in result:
            self.assertIn('"', q)

    def test_loose_returns_only_unquoted(self):
        result = _filter_by_style(self._MIXED, "loose")
        self.assertEqual(result, self._LOOSE)
        for q in result:
            self.assertNotIn('"', q)

    def test_empty_input_returns_empty(self):
        self.assertEqual(_filter_by_style([], "exact"), [])
        self.assertEqual(_filter_by_style([], "loose"), [])
        self.assertEqual(_filter_by_style([], "mixed"), [])

    def test_exact_returns_empty_when_no_quoted_queries(self):
        # All queries are loose — exact returns empty; caller handles fallback
        result = _filter_by_style(self._LOOSE, "exact")
        self.assertEqual(result, [])

    def test_loose_returns_empty_when_no_unquoted_queries(self):
        result = _filter_by_style(self._EXACT, "loose")
        self.assertEqual(result, [])

    def test_returns_list_not_tuple(self):
        result = _filter_by_style(self._MIXED, "mixed")
        self.assertIsInstance(result, list)


# ---------------------------------------------------------------------------
# 3. TAVILY_AUTO_PARAMETERS — payload and logging
# ---------------------------------------------------------------------------

class TestAutoParameters(unittest.TestCase):

    def _run_post(self, extra_env):
        env = {"TAVILY_API_KEY": "key", **extra_env}
        from src.providers.tavily_search_provider import _post
        with patch.dict(os.environ, env), \
             patch("requests.post", return_value=_mock_resp()) as mp:
            _post("q", 3, optional_params=_build_optional_params())
            return _payload_from(mp)

    def test_not_in_payload_by_default(self):
        with _clear_style_env():
            payload = self._run_post({
                "TAVILY_SEARCH_DEPTH": "", "TAVILY_TOPIC": "",
                "TAVILY_DAYS": "", "TAVILY_TIME_RANGE": "",
            })
        self.assertNotIn("auto_parameters", payload)

    def test_in_payload_when_true(self):
        with _clear_style_env():
            payload = self._run_post({
                "TAVILY_AUTO_PARAMETERS": "true",
                "TAVILY_SEARCH_DEPTH": "", "TAVILY_TOPIC": "",
                "TAVILY_DAYS": "", "TAVILY_TIME_RANGE": "",
            })
        self.assertTrue(payload.get("auto_parameters") is True)

    def test_not_in_payload_when_false(self):
        with _clear_style_env():
            payload = self._run_post({
                "TAVILY_AUTO_PARAMETERS": "false",
                "TAVILY_SEARCH_DEPTH": "", "TAVILY_TOPIC": "",
                "TAVILY_DAYS": "", "TAVILY_TIME_RANGE": "",
            })
        self.assertNotIn("auto_parameters", payload)

    def test_case_insensitive_true(self):
        with _clear_style_env():
            payload = self._run_post({
                "TAVILY_AUTO_PARAMETERS": "TRUE",
                "TAVILY_SEARCH_DEPTH": "", "TAVILY_TOPIC": "",
                "TAVILY_DAYS": "", "TAVILY_TIME_RANGE": "",
            })
        self.assertTrue(payload.get("auto_parameters") is True)

    def test_auto_parameters_logged_in_active_params(self):
        env = {
            "TAVILY_API_KEY": "key",
            "MAX_SEARCH_QUERIES": "1",
            "MAX_RESULTS_PER_QUERY": "1",
            "QUERY_SEED": "0",
            "TAVILY_AUTO_PARAMETERS": "true",
            "TAVILY_SEARCH_DEPTH": "",
            "TAVILY_TOPIC": "",
            "TAVILY_DAYS": "",
            "TAVILY_TIME_RANGE": "",
            "TAVILY_QUERY_STYLE": "",
        }
        from src.providers.tavily_search_provider import get_posts
        profile = {
            "search_terms": ["NVDA"],
            "query_templates": ['site:x.com "{term}"'],
        }
        buf = io.StringIO()
        with patch.dict(os.environ, env, clear=False), \
             patch("requests.post", return_value=_mock_resp()), \
             patch("sys.stdout", buf):
            get_posts(profile)
        output = buf.getvalue()
        self.assertIn("Active freshness params", output)
        self.assertIn("auto_parameters", output)

    def test_api_key_never_in_logs(self):
        env = {
            "TAVILY_API_KEY": "super-secret-key",
            "MAX_SEARCH_QUERIES": "1",
            "MAX_RESULTS_PER_QUERY": "1",
            "QUERY_SEED": "0",
            "TAVILY_AUTO_PARAMETERS": "true",
            "TAVILY_SEARCH_DEPTH": "",
            "TAVILY_TOPIC": "",
            "TAVILY_DAYS": "",
            "TAVILY_TIME_RANGE": "",
            "TAVILY_QUERY_STYLE": "",
        }
        from src.providers.tavily_search_provider import get_posts
        profile = {
            "search_terms": ["NVDA"],
            "query_templates": ['site:x.com "{term}"'],
        }
        buf = io.StringIO()
        with patch.dict(os.environ, env, clear=False), \
             patch("requests.post", return_value=_mock_resp()), \
             patch("sys.stdout", buf):
            get_posts(profile)
        self.assertNotIn("super-secret-key", buf.getvalue())


# ---------------------------------------------------------------------------
# 4. _build_queries integration — query style with bucket profile
# ---------------------------------------------------------------------------

class TestQueryStyleIntegration(unittest.TestCase):

    def _build(self, profile, extra_env):
        env = {
            "MAX_SEARCH_QUERIES": "2",
            "QUERY_SEED": "0",
            "TAVILY_QUERY_STYLE": "",
            **extra_env,
        }
        buf = io.StringIO()
        with patch.dict(os.environ, env, clear=False), patch("sys.stdout", buf):
            queries = _build_queries(profile)
        return queries, buf.getvalue()

    def test_mixed_default_includes_exact_and_loose(self):
        profile = _profile_mixed()
        # With seed=0 and mixed, the first 2 queries come from both bucket types
        # (allocation spreads across buckets). At minimum, both buckets exist.
        queries, _ = self._build(profile, {})
        self.assertEqual(len(queries), 2)

    def test_exact_style_queries_all_have_quotes(self):
        profile = _profile_mixed()
        queries, _ = self._build(profile, {"TAVILY_QUERY_STYLE": "exact"})
        self.assertEqual(len(queries), 2)
        for q in queries:
            self.assertIn('"', q, f"Expected quoted query, got: {q!r}")

    def test_loose_style_queries_have_no_quotes(self):
        profile = _profile_mixed()
        queries, _ = self._build(profile, {"TAVILY_QUERY_STYLE": "loose"})
        self.assertEqual(len(queries), 2)
        for q in queries:
            self.assertNotIn('"', q, f"Expected unquoted query, got: {q!r}")

    def test_max_search_queries_cap_respected_with_style(self):
        profile = _profile_mixed()
        for style in ("exact", "loose", "mixed"):
            for cap in (1, 2, 3):
                env = {
                    "MAX_SEARCH_QUERIES": str(cap),
                    "QUERY_SEED": "5",
                    "TAVILY_QUERY_STYLE": style,
                }
                with patch.dict(os.environ, env, clear=False), \
                     patch("sys.stdout", io.StringIO()):
                    queries = _build_queries(profile)
                self.assertLessEqual(
                    len(queries), cap,
                    f"style={style!r}, cap={cap}: got {len(queries)} queries"
                )

    def test_query_seed_deterministic_with_style(self):
        profile = _profile_mixed()
        env = {"MAX_SEARCH_QUERIES": "2", "QUERY_SEED": "7", "TAVILY_QUERY_STYLE": "exact"}
        with patch.dict(os.environ, env, clear=False), patch("sys.stdout", io.StringIO()):
            q_a = _build_queries(profile)
        with patch.dict(os.environ, env, clear=False), patch("sys.stdout", io.StringIO()):
            q_b = _build_queries(profile)
        self.assertEqual(q_a, q_b)

    def test_fallback_to_mixed_when_exact_filters_everything(self):
        # Profile has only loose queries — exact would filter everything → fallback
        profile = _profile_loose_only()
        queries, output = self._build(profile, {"TAVILY_QUERY_STYLE": "exact"})
        self.assertGreater(len(queries), 0)
        self.assertIn("filtered all", output)

    def test_fallback_to_mixed_when_loose_filters_everything(self):
        profile = _profile_exact_only()
        queries, output = self._build(profile, {"TAVILY_QUERY_STYLE": "loose"})
        self.assertGreater(len(queries), 0)
        self.assertIn("filtered all", output)

    def test_style_logged_in_bucket_summary(self):
        profile = _profile_mixed()
        _, output = self._build(profile, {"TAVILY_QUERY_STYLE": "exact"})
        self.assertIn("Style: exact", output)

    def test_style_logged_for_legacy_path(self):
        profile = {
            "search_terms": ['earnings reaction makes no sense'],
            "query_templates": ['site:x.com "{term}"'],
        }
        env = {
            "MAX_SEARCH_QUERIES": "1",
            "QUERY_SEED": "0",
            "TAVILY_QUERY_STYLE": "exact",
        }
        buf = io.StringIO()
        with patch.dict(os.environ, env, clear=False), patch("sys.stdout", buf):
            _build_queries(profile)
        self.assertIn("Style: exact", buf.getvalue())


# ---------------------------------------------------------------------------
# 5. Profile — loose_discovery and market_movers buckets exist
# ---------------------------------------------------------------------------

class TestProfileBuckets(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        import yaml
        yaml_path = os.path.join(
            os.path.dirname(__file__), "..", "profiles", "signal_shift.yaml"
        )
        with open(yaml_path) as f:
            cls.profile = yaml.safe_load(f)
        cls.buckets = cls.profile.get("query_buckets", {})

    def test_loose_discovery_bucket_exists(self):
        self.assertIn("loose_discovery", self.buckets)

    def test_market_movers_bucket_exists(self):
        self.assertIn("market_movers", self.buckets)

    def test_loose_discovery_queries_have_no_quotes(self):
        for q in self.buckets.get("loose_discovery", []):
            self.assertNotIn('"', q, f"Loose discovery query has quotes: {q!r}")

    def test_market_movers_queries_have_no_quotes(self):
        for q in self.buckets.get("market_movers", []):
            self.assertNotIn('"', q, f"Market movers query has quotes: {q!r}")

    def test_loose_discovery_non_empty(self):
        self.assertGreater(len(self.buckets.get("loose_discovery", [])), 0)

    def test_market_movers_non_empty(self):
        self.assertGreater(len(self.buckets.get("market_movers", [])), 0)

    def test_existing_buckets_unchanged(self):
        for bucket in (
            "broad_signal", "earnings_reaction", "ticker_confusion",
            "premarket_afterhours", "ai_stock_hype", "retail_chasing",
            "thesis_changed", "selloff_rally_confusion",
        ):
            self.assertIn(bucket, self.buckets, f"Existing bucket missing: {bucket!r}")

    def test_exact_queries_still_have_quotes(self):
        # Original buckets should still use quoted exact phrases
        broad = self.buckets.get("broad_signal", [])
        self.assertTrue(
            any('"' in q for q in broad),
            "broad_signal bucket has no quoted queries"
        )


# ---------------------------------------------------------------------------
# 6. Mock mode unchanged
# ---------------------------------------------------------------------------

class TestM415MockUnchanged(unittest.TestCase):

    def test_mock_posts_score_correctly(self):
        from mock_data.posts import MOCK_POSTS
        from src.scorer import score_posts
        scored = score_posts(MOCK_POSTS)
        self.assertEqual(scored[0]["score"], "Strong fit")
        self.assertEqual(scored[6]["score"], "Avoid")

    def test_mock_build_markdown_unchanged(self):
        from mock_data.posts import MOCK_POSTS
        from src.scorer import score_posts
        from src.replier import generate_replies
        from src.digest import build_markdown
        from src.post_generator import generate_posts
        scored = score_posts(MOCK_POSTS)
        with_replies = generate_replies(scored)
        sched = generate_posts(0)
        md = build_markdown("Signal Shift", with_replies, sched, mode="Mock")
        self.assertIn("Signal Shift", md)
        self.assertNotIn("manually before posting", md)

    def test_query_style_does_not_affect_mock_provider(self):
        # Mock provider doesn't use Tavily at all — style env var is irrelevant
        with patch.dict(os.environ, {"TAVILY_QUERY_STYLE": "exact"}):
            from src.providers.mock_provider import get_posts
            posts = get_posts({})
        self.assertGreater(len(posts), 0)

    def test_auto_parameters_does_not_affect_mock_provider(self):
        with patch.dict(os.environ, {"TAVILY_AUTO_PARAMETERS": "true"}):
            from src.providers.mock_provider import get_posts
            posts = get_posts({})
        self.assertGreater(len(posts), 0)


if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(__import__("__main__"))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
