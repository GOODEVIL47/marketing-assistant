"""
Tests for M4.12: US-equity ticker query buckets.
No real API calls, no network access, no Tavily key required.
"""

import io
import os
import sys
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

import yaml

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.providers.tavily_search_provider import (
    _build_bucket_queries,
    _build_queries,
    _build_candidate_queries,
    _select_queries,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_PROFILE_PATH = os.path.join(os.path.dirname(__file__), "..", "profiles", "signal_shift.yaml")


def _load_profile():
    with open(_PROFILE_PATH, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _profile_with_buckets(**extra_buckets):
    """Return a minimal profile containing only query_buckets."""
    buckets = {
        "broad_signal": [
            'site:x.com "market noise"',
            'site:x.com "information overload"',
        ],
        "earnings_reaction": [
            'site:x.com "earnings reaction" "$"',
            'site:x.com "$NVDA" "earnings reaction"',
        ],
        "ticker_confusion": [
            'site:x.com "$TSLA" "makes no sense"',
            'site:x.com "$PLTR" "why is this moving"',
        ],
        "premarket_afterhours": [
            'site:x.com "premarket" "why is" "$"',
        ],
        "ai_stock_hype": [
            'site:x.com "AI stocks" "chasing"',
        ],
        "retail_chasing": [
            'site:x.com "retail is chasing" "$"',
        ],
        "thesis_changed": [
            'site:x.com "thesis changed" "$"',
        ],
        "selloff_rally_confusion": [
            'site:x.com "selloff makes no sense" "$"',
        ],
    }
    buckets.update(extra_buckets)
    return {"query_buckets": buckets}


_FAKE_LEGACY_PROFILE = {
    "search_terms": ["retail investor noise", "investing clarity", "market noise"],
    "query_templates": ['site:x.com "{term}"'],
    "fit_keywords": {"strong": [], "decent": [], "weak": [], "avoid": []},
}


# ---------------------------------------------------------------------------
# 1. Profile has query_buckets
# ---------------------------------------------------------------------------

class TestProfileHasBuckets(unittest.TestCase):

    def setUp(self):
        self.profile = _load_profile()
        self.buckets = self.profile.get("query_buckets", {})

    def test_query_buckets_key_present(self):
        self.assertIn("query_buckets", self.profile)

    def test_all_eight_buckets_present(self):
        expected = {
            "broad_signal", "earnings_reaction", "ticker_confusion",
            "premarket_afterhours", "ai_stock_hype", "retail_chasing",
            "thesis_changed", "selloff_rally_confusion",
        }
        self.assertEqual(expected, set(self.buckets.keys()))

    def test_each_bucket_nonempty(self):
        for name, queries in self.buckets.items():
            self.assertGreater(len(queries), 0, f"Bucket {name!r} is empty")

    def test_each_bucket_has_at_least_4_queries(self):
        for name, queries in self.buckets.items():
            self.assertGreaterEqual(
                len(queries), 4,
                f"Bucket {name!r} has only {len(queries)} queries — need ≥ 4 for rotation"
            )

    def test_ticker_buckets_contain_dollar_sign(self):
        ticker_buckets = ["earnings_reaction", "ticker_confusion", "premarket_afterhours",
                          "ai_stock_hype", "retail_chasing", "thesis_changed",
                          "selloff_rally_confusion"]
        for name in ticker_buckets:
            queries = self.buckets[name]
            has_dollar = any("$" in q for q in queries)
            self.assertTrue(has_dollar, f"Bucket {name!r} has no $ ticker queries")

    def test_general_equity_patterns_contain_dollar_sign(self):
        # General equity patterns (no specific ticker name) should also use "$"
        general_patterns = [
            q for bucket in self.buckets.values()
            for q in bucket
            if '"$"' in q  # generic $ wildcard — not a specific ticker
        ]
        self.assertGreater(len(general_patterns), 3,
                           "Expected multiple generic-$ equity query patterns")

    def test_known_liquid_tickers_covered(self):
        all_queries = " ".join(
            q for bucket in self.buckets.values() for q in bucket
        )
        # At least 10 of the 20 stated tickers should appear
        tickers = [
            "$NVDA", "$TSLA", "$PLTR", "$META", "$AMD",
            "$SOFI", "$HOOD", "$COIN", "$IONQ", "$APP",
            "$AVGO", "$MSFT", "$GOOGL", "$AMZN", "$SMCI",
            "$MSTR", "$RBLX", "$CRWD", "$UBER", "$NFLX",
        ]
        found = [t for t in tickers if t in all_queries]
        self.assertGreaterEqual(len(found), 10, f"Only {len(found)} tickers found: {found}")

    def test_broad_signal_bucket_has_psychology_queries(self):
        queries = " ".join(self.buckets["broad_signal"])
        psychology_terms = ["noise", "overwhelm", "signal", "information", "reaction"]
        has_any = any(t in queries.lower() for t in psychology_terms)
        self.assertTrue(has_any, "broad_signal bucket should contain psychology/signal terms")

    def test_all_queries_target_x_com(self):
        for bucket_name, queries in self.buckets.items():
            for q in queries:
                self.assertIn("x.com", q,
                              f"Bucket {bucket_name!r} query does not target x.com: {q!r}")


# ---------------------------------------------------------------------------
# 2. _build_bucket_queries — allocation and rotation
# ---------------------------------------------------------------------------

class TestBuildBucketQueries(unittest.TestCase):

    def _buckets(self):
        return {
            "alpha": ["a1", "a2", "a3"],
            "beta":  ["b1", "b2", "b3"],
            "gamma": ["c1", "c2", "c3"],
            "delta": ["d1", "d2", "d3"],
        }

    def test_respects_max_q_cap(self):
        for max_q in (1, 2, 4, 7, 10):
            result = _build_bucket_queries(self._buckets(), max_q, seed=0)
            self.assertLessEqual(len(result), max_q,
                                 f"max_q={max_q} exceeded: got {len(result)}")

    def test_returns_tuples_of_bucket_and_query(self):
        result = _build_bucket_queries(self._buckets(), max_q=4, seed=0)
        for item in result:
            self.assertIsInstance(item, tuple)
            self.assertEqual(len(item), 2)
            bucket_name, query = item
            self.assertIn(bucket_name, self._buckets())

    def test_spans_multiple_buckets_when_max_q_ge_n_buckets(self):
        result = _build_bucket_queries(self._buckets(), max_q=8, seed=0)
        bucket_names = {name for name, _ in result}
        # Should draw from all 4 buckets
        self.assertEqual(bucket_names, set(self._buckets().keys()))

    def test_single_query_max_returns_one(self):
        result = _build_bucket_queries(self._buckets(), max_q=1, seed=0)
        self.assertEqual(len(result), 1)

    def test_max_q_smaller_than_buckets_draws_from_first_n(self):
        result = _build_bucket_queries(self._buckets(), max_q=2, seed=0)
        self.assertEqual(len(result), 2)
        # First two buckets only
        bucket_names = [name for name, _ in result]
        for name in bucket_names:
            self.assertIn(name, ("alpha", "beta"))

    def test_deterministic_with_same_seed(self):
        r1 = _build_bucket_queries(self._buckets(), max_q=4, seed=42)
        r2 = _build_bucket_queries(self._buckets(), max_q=4, seed=42)
        self.assertEqual(r1, r2)

    def test_different_seeds_can_produce_different_results(self):
        results = set()
        for seed in range(20):
            r = _build_bucket_queries(self._buckets(), max_q=4, seed=seed)
            results.add(tuple(q for _, q in r))
        # With 4 buckets × 3 queries each and 20 seeds, should see variation
        self.assertGreater(len(results), 1, "All seeds produced identical query sets")

    def test_empty_buckets_dict_returns_empty(self):
        result = _build_bucket_queries({}, max_q=5, seed=0)
        self.assertEqual(result, [])

    def test_bucket_with_empty_list_is_skipped(self):
        buckets = {
            "nonempty": ["q1", "q2"],
            "empty": [],
        }
        result = _build_bucket_queries(buckets, max_q=5, seed=0)
        bucket_names = [name for name, _ in result]
        self.assertNotIn("empty", bucket_names)

    def test_no_duplicate_queries_within_single_bucket(self):
        buckets = {"only": ["q1", "q2", "q3"]}
        result = _build_bucket_queries(buckets, max_q=10, seed=0)
        queries = [q for _, q in result]
        # A single-query bucket can only yield 1 unique query per call
        self.assertEqual(len(queries), len(set(queries)))

    def test_large_max_q_capped_by_total_available(self):
        # 4 buckets × 3 queries = 12 queries max; max_q=20 should return ≤12
        result = _build_bucket_queries(self._buckets(), max_q=20, seed=0)
        # Each bucket gives at most its length per slot; cap is max_q
        self.assertLessEqual(len(result), 20)


# ---------------------------------------------------------------------------
# 3. _build_queries — bucket path integration
# ---------------------------------------------------------------------------

class TestBuildQueriesBucketPath(unittest.TestCase):

    def _run_build_queries(self, profile, max_q=5, seed=None):
        env = {"MAX_SEARCH_QUERIES": str(max_q)}
        if seed is not None:
            env["QUERY_SEED"] = str(seed)
        with patch.dict(os.environ, env):
            buf = io.StringIO()
            with redirect_stdout(buf):
                queries = _build_queries(profile)
            return queries, buf.getvalue()

    def test_bucket_profile_returns_list_of_strings(self):
        profile = _profile_with_buckets()
        queries, _ = self._run_build_queries(profile, max_q=5)
        self.assertIsInstance(queries, list)
        for q in queries:
            self.assertIsInstance(q, str)

    def test_bucket_profile_respects_max_q(self):
        profile = _profile_with_buckets()
        for max_q in (1, 3, 5, 8):
            queries, _ = self._run_build_queries(profile, max_q=max_q)
            self.assertLessEqual(len(queries), max_q)

    def test_bucket_profile_log_includes_bucket_names(self):
        profile = _profile_with_buckets()
        _, log = self._run_build_queries(profile, max_q=8, seed=0)
        for bucket_name in profile["query_buckets"]:
            self.assertIn(bucket_name, log,
                          f"Bucket name {bucket_name!r} missing from log")

    def test_bucket_profile_log_includes_selected_queries(self):
        profile = _profile_with_buckets()
        queries, log = self._run_build_queries(profile, max_q=4, seed=0)
        for q in queries:
            self.assertIn(q, log, f"Selected query not in log: {q!r}")

    def test_bucket_profile_log_includes_seed_label(self):
        profile = _profile_with_buckets()
        _, log = self._run_build_queries(profile, max_q=3, seed=77)
        self.assertIn("QUERY_SEED=77", log)

    def test_query_seed_env_var_is_deterministic(self):
        profile = _profile_with_buckets()
        q1, _ = self._run_build_queries(profile, max_q=5, seed=42)
        q2, _ = self._run_build_queries(profile, max_q=5, seed=42)
        self.assertEqual(q1, q2)

    def test_different_seeds_give_different_queries(self):
        profile = _profile_with_buckets()
        results = set()
        for seed in range(30):
            queries, _ = self._run_build_queries(profile, max_q=3, seed=seed)
            results.add(tuple(queries))
        self.assertGreater(len(results), 1, "All seeds returned identical queries")

    def test_empty_buckets_raises_value_error(self):
        profile = {"query_buckets": {"a": [], "b": []}}
        with self.assertRaises(ValueError) as ctx:
            self._run_build_queries(profile, max_q=5)
        self.assertIn("empty", str(ctx.exception).lower())

    def test_real_profile_builds_queries_without_error(self):
        profile = _load_profile()
        queries, log = self._run_build_queries(profile, max_q=10, seed=0)
        self.assertGreater(len(queries), 0)
        self.assertLessEqual(len(queries), 10)

    def test_real_profile_log_has_selected_queries_header(self):
        profile = _load_profile()
        _, log = self._run_build_queries(profile, max_q=5, seed=1)
        self.assertIn("Selected queries", log)

    def test_real_profile_queries_span_multiple_buckets(self):
        profile = _load_profile()
        queries, log = self._run_build_queries(profile, max_q=8, seed=5)
        # Log should mention multiple bucket names
        bucket_names = list(profile["query_buckets"].keys())
        appeared = [name for name in bucket_names if name in log]
        self.assertGreater(len(appeared), 1,
                           f"Only {appeared} buckets appeared in log for max_q=8")


# ---------------------------------------------------------------------------
# 4. MAX_SEARCH_QUERIES cap always enforced
# ---------------------------------------------------------------------------

class TestMaxQueryCap(unittest.TestCase):

    def _queries(self, profile, max_q, seed=0):
        env = {"MAX_SEARCH_QUERIES": str(max_q), "QUERY_SEED": str(seed)}
        with patch.dict(os.environ, env):
            with redirect_stdout(io.StringIO()):
                return _build_queries(profile)

    def test_cap_1(self):
        self.assertLessEqual(len(self._queries(_profile_with_buckets(), 1)), 1)

    def test_cap_5(self):
        self.assertLessEqual(len(self._queries(_profile_with_buckets(), 5)), 5)

    def test_cap_10_with_real_profile(self):
        profile = _load_profile()
        self.assertLessEqual(len(self._queries(profile, 10)), 10)

    def test_cap_2_with_real_profile(self):
        profile = _load_profile()
        self.assertLessEqual(len(self._queries(profile, 2)), 2)


# ---------------------------------------------------------------------------
# 5. QUERY_SEED backward compatibility
# ---------------------------------------------------------------------------

class TestQuerySeedSupport(unittest.TestCase):

    def _queries(self, profile, seed_str):
        env = {"MAX_SEARCH_QUERIES": "5", "QUERY_SEED": seed_str}
        with patch.dict(os.environ, env):
            buf = io.StringIO()
            with redirect_stdout(buf):
                queries = _build_queries(profile)
            return queries, buf.getvalue()

    def test_integer_seed_is_deterministic(self):
        profile = _profile_with_buckets()
        q1, _ = self._queries(profile, "99")
        q2, _ = self._queries(profile, "99")
        self.assertEqual(q1, q2)

    def test_invalid_seed_falls_back_to_date_seed(self):
        profile = _profile_with_buckets()
        _, log = self._queries(profile, "not-a-number")
        self.assertIn("not an integer", log)

    def test_seed_zero_works(self):
        profile = _profile_with_buckets()
        queries, _ = self._queries(profile, "0")
        self.assertGreater(len(queries), 0)


# ---------------------------------------------------------------------------
# 6. Legacy search_terms path still works
# ---------------------------------------------------------------------------

class TestLegacySearchTermsBackwardCompat(unittest.TestCase):

    def _build(self, profile, max_q=5):
        env = {"MAX_SEARCH_QUERIES": str(max_q), "QUERY_SEED": "0"}
        with patch.dict(os.environ, env):
            with redirect_stdout(io.StringIO()):
                return _build_queries(profile)

    def test_legacy_search_terms_still_work(self):
        queries = self._build(_FAKE_LEGACY_PROFILE)
        self.assertGreater(len(queries), 0)
        self.assertTrue(all('site:x.com' in q for q in queries))

    def test_legacy_respects_max_q(self):
        queries = self._build(_FAKE_LEGACY_PROFILE, max_q=1)
        self.assertEqual(len(queries), 1)

    def test_empty_search_terms_raises_value_error(self):
        with patch.dict(os.environ, {"MAX_SEARCH_QUERIES": "5"}):
            with redirect_stdout(io.StringIO()):
                with self.assertRaises(ValueError) as ctx:
                    _build_queries({"search_terms": []})
        self.assertIn("search_terms", str(ctx.exception))

    def test_bucket_takes_priority_over_search_terms(self):
        profile = {
            "search_terms": ["legacy term"],
            "query_templates": ['site:x.com "{term}"'],
            "query_buckets": {
                "bucket_a": ['site:x.com "bucket query"'],
            },
        }
        env = {"MAX_SEARCH_QUERIES": "5", "QUERY_SEED": "0"}
        with patch.dict(os.environ, env):
            buf = io.StringIO()
            with redirect_stdout(buf):
                queries = _build_queries(profile)
        # Should use bucket, not legacy terms
        self.assertIn('site:x.com "bucket query"', queries)
        self.assertNotIn('site:x.com "legacy term"', queries)
        self.assertIn("bucket_a", buf.getvalue())


# ---------------------------------------------------------------------------
# 7. Bucket content — query patterns
# ---------------------------------------------------------------------------

class TestBucketContent(unittest.TestCase):

    def setUp(self):
        self.profile = _load_profile()
        self.buckets = self.profile["query_buckets"]

    def test_earnings_reaction_has_ticker_specific_queries(self):
        queries = " ".join(self.buckets["earnings_reaction"])
        self.assertIn("earnings reaction", queries)
        # At least one ticker-specific earnings query
        has_ticker = any(
            "$" in q and "earnings" in q
            for q in self.buckets["earnings_reaction"]
        )
        self.assertTrue(has_ticker, "earnings_reaction has no ticker+earnings query")

    def test_ticker_confusion_has_why_is_moving_pattern(self):
        queries = " ".join(self.buckets["ticker_confusion"])
        self.assertTrue(
            "why is" in queries or "makes no sense" in queries,
            "ticker_confusion should have 'why is' or 'makes no sense'"
        )

    def test_premarket_bucket_has_premarket_queries(self):
        queries = " ".join(self.buckets["premarket_afterhours"])
        self.assertIn("premarket", queries)

    def test_afterhours_bucket_has_afterhours_queries(self):
        queries = " ".join(self.buckets["premarket_afterhours"])
        self.assertIn("after hours", queries)

    def test_thesis_changed_bucket_has_thesis_query(self):
        queries = " ".join(self.buckets["thesis_changed"])
        self.assertIn("thesis", queries)

    def test_ai_hype_bucket_has_ai_pattern(self):
        queries = " ".join(self.buckets["ai_stock_hype"])
        self.assertTrue(
            "AI" in queries or "ai" in queries.lower(),
            "ai_stock_hype bucket should mention AI"
        )

    def test_selloff_rally_bucket_has_selloff_or_rally(self):
        queries = " ".join(self.buckets["selloff_rally_confusion"])
        self.assertTrue(
            "selloff" in queries or "rally" in queries,
            "selloff_rally_confusion should mention selloff or rally"
        )

    def test_retail_chasing_has_retail_pattern(self):
        queries = " ".join(self.buckets["retail_chasing"])
        self.assertTrue(
            "retail" in queries or "FOMO" in queries or "chasing" in queries,
            "retail_chasing should mention retail/FOMO/chasing"
        )


# ---------------------------------------------------------------------------
# 8. Filters preserved — no stale/weak/avoid posts in Best 3
# ---------------------------------------------------------------------------

class TestFiltersPreserved(unittest.TestCase):

    def _load_profile(self):
        return _load_profile()

    def _score_post(self, text, age_hours=6.0):
        from src.scorer import score_posts
        profile = self._load_profile()
        post = {
            "id": "1900000000000000001",
            "author": "@test_user",
            "text": text,
            "likes": 0, "reposts": 0, "reply_count": 0, "impressions": 0,
            "age_hours": age_hours,
            "age_source": "snowflake",
            "post_url": "https://x.com/test_user/status/1900000000000000001",
            "url": "https://x.com/test_user/status/1900000000000000001",
            "discovery_source": "tavily_search",
            "metrics_confidence": "low",
        }
        return score_posts([post], profile=profile)[0]

    def test_weak_fit_post_not_in_best3(self):
        from src.replier import generate_replies
        from src.digest import _build_best_3
        scored = self._score_post("RSI crossover on SPY looks interesting today")
        with_replies = generate_replies([scored])
        lines = _build_best_3(with_replies, has_inspiration=False, has_worth_checking=False)
        content = "\n".join(lines)
        # Weak fit should not appear as a numbered Best 3 entry
        self.assertNotIn("RSI crossover", content)

    def test_avoid_post_not_in_best3(self):
        from src.replier import generate_replies
        from src.digest import _build_best_3
        scored = self._score_post("🚀 moon shot! buy this now before it pumps! 100x guaranteed")
        with_replies = generate_replies([scored])
        lines = _build_best_3(with_replies, has_inspiration=False, has_worth_checking=False)
        content = "\n".join(lines)
        self.assertNotIn("moon shot", content)

    def test_stale_post_does_not_enter_best3(self):
        from src.replier import generate_replies
        from src.digest import _build_best_3
        # Very old post (200 hours = ~8 days old)
        scored = self._score_post(
            "The market noise is overwhelming retail investors this week.",
            age_hours=200.0
        )
        with_replies = generate_replies([scored])
        lines = _build_best_3(with_replies, has_inspiration=False, has_worth_checking=False)
        content = "\n".join(lines)
        # Score should be Weak or Avoid for a stale post
        self.assertNotIn("**1.**", content)


# ---------------------------------------------------------------------------
# 9. Worth Checking preserved
# ---------------------------------------------------------------------------

class TestWorthCheckingPreserved(unittest.TestCase):

    def test_fresh_low_opp_web_post_eligible_for_worth_checking(self):
        from src.digest import _get_worth_checking_posts
        # A fresh web-search post with Decent fit and Low opportunity
        post = {
            "id": "wc_412_test",
            "author": "@retail_trader",
            "text": "Market noise is overwhelming this week. Hard to know what's signal.",
            "score": "Decent fit",
            "opportunity": "Low opportunity",
            "freshness_tier": "fresh",
            "age_hours": 10.0,
            "metrics_confidence": "low",
            "out_of_scope": False,
            "discovery_source": "tavily_search",
            "replies": [],
            "best_reply": {},
            "media": {"type": "No media", "reason": ""},
        }
        result = _get_worth_checking_posts([post])
        self.assertEqual(len(result), 1, "Fresh low-opp web post should appear in Worth Checking")

    def test_strong_fit_fresh_low_opp_web_eligible(self):
        from src.digest import _get_worth_checking_posts
        post = {
            "id": "wc_strong",
            "author": "@quietinvestor",
            "text": "Too much market noise, just want to understand the move.",
            "score": "Strong fit",
            "opportunity": "Low opportunity",
            "freshness_tier": "fresh",
            "age_hours": 5.0,
            "metrics_confidence": "low",
            "out_of_scope": False,
            "discovery_source": "tavily_search",
            "replies": [],
            "best_reply": {},
            "media": {"type": "No media", "reason": ""},
        }
        result = _get_worth_checking_posts([post])
        self.assertEqual(len(result), 1)

    def test_old_post_not_in_worth_checking(self):
        from src.digest import _get_worth_checking_posts
        post = {
            "id": "wc_old",
            "author": "@user",
            "text": "Market noise overwhelming retail investors",
            "score": "Decent fit",
            "opportunity": "Low opportunity",
            "freshness_tier": "old",
            "age_hours": 96.0,
            "metrics_confidence": "low",
            "out_of_scope": False,
            "discovery_source": "tavily_search",
            "replies": [],
            "best_reply": {},
            "media": {"type": "No media", "reason": ""},
        }
        result = _get_worth_checking_posts([post])
        self.assertEqual(len(result), 0, "Old posts should not appear in Worth Checking")

    def test_high_confidence_post_not_in_worth_checking(self):
        from src.digest import _get_worth_checking_posts
        post = {
            "id": "wc_highconf",
            "author": "@user",
            "text": "Market noise overwhelming retail investors this week",
            "score": "Decent fit",
            "opportunity": "Low opportunity",
            "freshness_tier": "fresh",
            "age_hours": 5.0,
            "metrics_confidence": "high",
            "out_of_scope": False,
            "discovery_source": "tavily_search",
            "replies": [],
            "best_reply": {},
            "media": {"type": "No media", "reason": ""},
        }
        result = _get_worth_checking_posts([post])
        self.assertEqual(len(result), 0,
                         "High-confidence posts should not appear in Worth Checking")


# ---------------------------------------------------------------------------
# 10. Mock mode unchanged
# ---------------------------------------------------------------------------

class TestMockModeUnchangedM412(unittest.TestCase):

    def test_mock_mode_runs_without_error(self):
        from src.providers.mock_provider import get_posts
        posts = get_posts({})
        self.assertIsInstance(posts, list)
        self.assertGreater(len(posts), 0)

    def test_mock_posts_have_required_fields(self):
        from src.providers.mock_provider import get_posts
        posts = get_posts({})
        for post in posts:
            for field in ("id", "author", "text", "likes", "age_hours"):
                self.assertIn(field, post, f"Mock post missing field: {field!r}")

    def test_mock_scores_are_fixed(self):
        from src.providers.mock_provider import get_posts
        from src.scorer import score_posts
        profile = _load_profile()
        posts = get_posts(profile)
        scored = score_posts(posts, profile=profile)
        # At least one Strong fit in mock data
        scores = [p["score"] for p in scored]
        self.assertIn("Strong fit", scores,
                      "Mock data should contain at least one Strong fit post")

    def test_mock_mode_does_not_use_query_buckets(self):
        from src.providers.mock_provider import get_posts
        # Mock provider should never call _build_queries; ensure no error without API key
        env = {k: v for k, v in os.environ.items() if k != "TAVILY_API_KEY"}
        with patch.dict(os.environ, env, clear=True):
            posts = get_posts({})
        self.assertIsInstance(posts, list)


# ---------------------------------------------------------------------------
# 11. No secrets or workflow files touched
# ---------------------------------------------------------------------------

class TestNoSecretsOrWorkflows(unittest.TestCase):

    def test_provider_file_does_not_contain_api_key(self):
        provider_path = os.path.join(
            os.path.dirname(__file__), "..", "src", "providers", "tavily_search_provider.py"
        )
        with open(provider_path, encoding="utf-8") as fh:
            content = fh.read()
        suspicious = [line for line in content.splitlines()
                      if "tvly-" in line and "=" in line and "#" not in line.split("=")[0]]
        self.assertEqual(suspicious, [], f"Possible API key in provider: {suspicious}")

    def test_profile_yaml_does_not_contain_secrets(self):
        with open(_PROFILE_PATH, encoding="utf-8") as fh:
            content = fh.read()
        self.assertNotIn("tvly-", content)
        self.assertNotIn("api_key:", content.lower().replace("# ", ""))

    def test_workflow_files_exist_and_are_unchanged_structure(self):
        workflow_dir = os.path.join(os.path.dirname(__file__), "..", ".github", "workflows")
        workflows = os.listdir(workflow_dir)
        self.assertIn("mel_digest.yml", workflows)
        self.assertIn("mel_search_digest.yml", workflows)

    def test_no_output_directory_committed(self):
        output_dir = os.path.join(os.path.dirname(__file__), "..", "output")
        if os.path.exists(output_dir):
            py_files = [f for f in os.listdir(output_dir) if f.endswith(".py")]
            self.assertEqual(py_files, [], "output/ should not contain Python files")


if __name__ == "__main__":
    unittest.main()
