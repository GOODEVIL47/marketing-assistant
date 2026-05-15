"""
Tests for M4.6: date-based query rotation, QUERY_SEED override, inspiration
message wording fix.
No real API calls, no network access.
"""

import sys
import os
import unittest
from unittest.mock import patch
from datetime import date, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.providers.tavily_search_provider import (
    _build_candidate_queries,
    _build_queries,
    _query_seed,
    _select_queries,
)
from src.scorer import score_posts
from src.replier import generate_replies
from src.digest import _build_best_3, _build_inspiration, build_markdown
from src.email_renderer import render_digest_html


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _profile_with_many_terms(n=20):
    return {
        "search_terms": [f"term {i}" for i in range(n)],
        "query_templates": [
            'site:x.com "{term}"',
            'site:x.com "{term}" "today"',
            'site:x.com "{term}" "this week"',
        ],
    }


def _make_web_post(tweet_id="1900000000000000001", age_hours=6,
                   fit_text="retail investor noise clarity signal"):
    return {
        "id": tweet_id,
        "author": f"@user_{tweet_id[-4:]}",
        "author_name": f"user_{tweet_id[-4:]}",
        "author_followers": 0,
        "author_profile_url": "https://x.com/user",
        "text": fit_text,
        "likes": 0, "reposts": 0, "reply_count": 0, "impressions": 0,
        "age_hours": age_hours,
        "age_source": "snowflake",
        "post_url": f"https://x.com/user/status/{tweet_id}",
        "url": f"https://x.com/user/status/{tweet_id}",
        "discovery_source": "tavily_search",
        "metrics_confidence": "low",
    }


def _minimal_profile():
    return {
        "fit_keywords": {
            "strong": ["noise", "clarity", "signal", "overload"],
            "decent": ["investor", "investing", "retail"],
            "weak": ["options strategy", "technical analysis"],
            "avoid": ["get rich quick", "100x"],
        }
    }


# ---------------------------------------------------------------------------
# 1. _query_seed — date and QUERY_SEED override
# ---------------------------------------------------------------------------

class TestQuerySeed(unittest.TestCase):

    def test_returns_integer_and_label(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("QUERY_SEED", None)
            seed, label = _query_seed()
        self.assertIsInstance(seed, int)
        self.assertIn("date=", label)

    def test_query_seed_env_overrides_date(self):
        with patch.dict(os.environ, {"QUERY_SEED": "42"}):
            seed, label = _query_seed()
        self.assertEqual(seed, 42)
        self.assertIn("QUERY_SEED=42", label)

    def test_query_seed_0_is_valid(self):
        with patch.dict(os.environ, {"QUERY_SEED": "0"}):
            seed, label = _query_seed()
        self.assertEqual(seed, 0)

    def test_non_integer_query_seed_falls_back_to_date(self):
        with patch.dict(os.environ, {"QUERY_SEED": "not-a-number"}):
            seed, label = _query_seed()
        self.assertIsInstance(seed, int)
        self.assertIn("date=", label)

    def test_same_day_same_seed(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("QUERY_SEED", None)
            seed1, _ = _query_seed()
            seed2, _ = _query_seed()
        self.assertEqual(seed1, seed2)


# ---------------------------------------------------------------------------
# 2. _select_queries — rotation properties
# ---------------------------------------------------------------------------

class TestSelectQueries(unittest.TestCase):

    def _candidates(self, n=30):
        return [f"query_{i}" for i in range(n)]

    def test_seed_0_returns_first_n(self):
        candidates = self._candidates(30)
        selected = _select_queries(candidates, 5, seed=0)
        self.assertEqual(selected, candidates[:5])

    def test_different_seeds_produce_different_selections(self):
        candidates = self._candidates(30)
        sel_a = _select_queries(candidates, 2, seed=0)
        sel_b = _select_queries(candidates, 2, seed=1)
        self.assertNotEqual(sel_a, sel_b)

    def test_same_seed_produces_same_selection(self):
        candidates = self._candidates(30)
        sel_a = _select_queries(candidates, 3, seed=999)
        sel_b = _select_queries(candidates, 3, seed=999)
        self.assertEqual(sel_a, sel_b)

    def test_cap_is_respected(self):
        candidates = self._candidates(50)
        for max_q in (1, 2, 5, 10):
            selected = _select_queries(candidates, max_q, seed=7)
            self.assertEqual(len(selected), max_q, f"cap={max_q} failed")

    def test_fewer_candidates_than_cap(self):
        candidates = self._candidates(3)
        selected = _select_queries(candidates, 10, seed=5)
        self.assertEqual(len(selected), 3)

    def test_empty_candidates_returns_empty(self):
        self.assertEqual(_select_queries([], 5, seed=0), [])

    def test_high_priority_queries_in_window(self):
        # Window = min(len, max_q * 10). With 50 candidates and max_q=2,
        # window=20. Only candidates[0:20] are ever selected.
        candidates = self._candidates(50)
        for seed in range(20):
            selected = _select_queries(candidates, 2, seed=seed)
            for q in selected:
                idx = int(q.split("_")[1])
                self.assertLess(idx, 20, f"seed={seed}: {q} is outside priority window")

    def test_rotation_cycles_through_window(self):
        # With window_size=20 and max_q=2, after 20 seeds (0..19),
        # every starting position in the window appears at least once.
        candidates = self._candidates(50)
        window_size = min(50, 2 * 10)  # = 20
        starting_queries = set()
        for seed in range(window_size):
            selected = _select_queries(candidates, 2, seed=seed)
            starting_queries.add(selected[0])
        self.assertEqual(len(starting_queries), window_size)


# ---------------------------------------------------------------------------
# 3. _build_queries — rotation via QUERY_SEED
# ---------------------------------------------------------------------------

class TestBuildQueriesRotation(unittest.TestCase):

    def test_seed_0_selects_first_n_candidates(self):
        profile = _profile_with_many_terms(5)
        with patch.dict(os.environ, {"MAX_SEARCH_QUERIES": "3", "QUERY_SEED": "0"}):
            queries = _build_queries(profile)
        candidates = _build_candidate_queries(profile)
        self.assertEqual(queries, candidates[:3])

    def test_different_seeds_produce_different_queries(self):
        profile = _profile_with_many_terms(20)
        with patch.dict(os.environ, {"MAX_SEARCH_QUERIES": "2", "QUERY_SEED": "0"}):
            q0 = _build_queries(profile)
        with patch.dict(os.environ, {"MAX_SEARCH_QUERIES": "2", "QUERY_SEED": "1"}):
            q1 = _build_queries(profile)
        self.assertNotEqual(q0, q1)

    def test_same_seed_produces_same_queries(self):
        profile = _profile_with_many_terms(20)
        with patch.dict(os.environ, {"MAX_SEARCH_QUERIES": "3", "QUERY_SEED": "77"}):
            q_a = _build_queries(profile)
        with patch.dict(os.environ, {"MAX_SEARCH_QUERIES": "3", "QUERY_SEED": "77"}):
            q_b = _build_queries(profile)
        self.assertEqual(q_a, q_b)

    def test_cap_still_enforced_with_rotation(self):
        profile = _profile_with_many_terms(20)
        with patch.dict(os.environ, {"MAX_SEARCH_QUERIES": "4", "QUERY_SEED": "13"}):
            queries = _build_queries(profile)
        self.assertEqual(len(queries), 4)

    def test_high_priority_candidates_favoured(self):
        # With 20 terms and 3 templates (60 candidates), window = min(60, 2*10) = 20.
        # All selected queries must come from the first 20 candidates (first template).
        profile = _profile_with_many_terms(20)
        first_template_queries = set(_build_candidate_queries(profile)[:20])
        for seed in range(20):
            with patch.dict(os.environ, {"MAX_SEARCH_QUERIES": "2", "QUERY_SEED": str(seed)}):
                queries = _build_queries(profile)
            for q in queries:
                self.assertIn(q, first_template_queries,
                              f"seed={seed}: {q!r} not in priority window")

    def test_log_includes_seed_label(self):
        import io
        profile = _profile_with_many_terms(5)
        buf = io.StringIO()
        with patch.dict(os.environ, {"MAX_SEARCH_QUERIES": "2", "QUERY_SEED": "99"}):
            with patch("sys.stdout", buf):
                _build_queries(profile)
        self.assertIn("QUERY_SEED=99", buf.getvalue())

    def test_log_includes_candidate_and_selected_count(self):
        import io
        profile = _profile_with_many_terms(5)
        buf = io.StringIO()
        with patch.dict(os.environ, {"MAX_SEARCH_QUERIES": "2", "QUERY_SEED": "0"}):
            with patch("sys.stdout", buf):
                _build_queries(profile)
        output = buf.getvalue()
        self.assertIn("Candidate queries:", output)
        self.assertIn("cap=2", output)


# ---------------------------------------------------------------------------
# 4. Inspiration message wording — conditional on inspiration existing
# ---------------------------------------------------------------------------

class TestInspirationMessageWording(unittest.TestCase):

    def test_no_inspiration_message_when_no_inspiration(self):
        # Stale post has Poor opportunity — no inspiration section
        post = _make_web_post(age_hours=250)
        scored = score_posts([post], profile=_minimal_profile())
        with_replies = generate_replies(scored)
        lines = _build_best_3(with_replies, has_inspiration=False)
        content = "\n".join(lines)
        self.assertIn("No suitable reply opportunities found today", content)
        self.assertNotIn("Save for Inspiration", content)

    def test_inspiration_message_shown_when_inspiration_exists(self):
        post = _make_web_post(age_hours=250)
        scored = score_posts([post], profile=_minimal_profile())
        with_replies = generate_replies(scored)
        lines = _build_best_3(with_replies, has_inspiration=True)
        content = "\n".join(lines)
        self.assertIn("Save for Inspiration", content)

    def test_build_markdown_no_inspiration_ref_when_empty(self):
        post = _make_web_post(age_hours=250)
        scored = score_posts([post], profile=_minimal_profile())
        with_replies = generate_replies(scored)
        from src.post_generator import generate_posts
        sched = generate_posts(0)
        md = build_markdown("Signal Shift", with_replies, sched, mode="Tavily Search")
        # Stale post → no inspiration section → no cross-reference in Best 3 block
        self.assertNotIn(
            "Check the Save for Inspiration section below",
            md.split("## Post Scoring")[0]   # only check the Best 3 block
        )

    def test_build_markdown_has_inspiration_ref_when_section_exists(self):
        # Old+good-fit post → inspiration section IS present
        post = _make_web_post(age_hours=96, fit_text="noise clarity signal overload")
        scored = score_posts([post], profile=_minimal_profile())
        with_replies = generate_replies(scored)
        inspiration = _build_inspiration(with_replies)
        if inspiration:  # only assert if the inspiration section is non-empty
            from src.post_generator import generate_posts
            sched = generate_posts(0)
            md = build_markdown("Signal Shift", with_replies, sched, mode="Tavily Search")
            best3_block = md.split("## Post Scoring")[0]
            self.assertIn("Save for Inspiration", best3_block)

    def test_html_no_inspiration_suffix_when_no_inspiration(self):
        post = _make_web_post(age_hours=250)
        scored = score_posts([post], profile=_minimal_profile())
        with_replies = generate_replies(scored)
        from src.post_generator import generate_posts
        sched = generate_posts(0)
        html = render_digest_html("Signal Shift", with_replies, sched, mode="Tavily Search")
        # No inspiration section → the no-opportunities message should NOT mention it
        self.assertNotIn("Save for Inspiration section below", html)
        self.assertIn("No suitable reply opportunities found today", html)


# ---------------------------------------------------------------------------
# 5. Mock mode unchanged
# ---------------------------------------------------------------------------

class TestMockModeUnchangedM46(unittest.TestCase):

    def test_mock_posts_score_correctly(self):
        from mock_data.posts import MOCK_POSTS
        scored = score_posts(MOCK_POSTS)
        self.assertEqual(scored[0]["score"], "Strong fit")
        self.assertEqual(scored[6]["score"], "Avoid")

    def test_mock_best3_still_finds_opportunities(self):
        from mock_data.posts import MOCK_POSTS
        scored = score_posts(MOCK_POSTS)
        with_replies = generate_replies(scored)
        lines = _build_best_3(with_replies)
        content = "\n".join(lines)
        self.assertNotIn("No suitable reply", content)

    def test_mock_has_no_inspiration_section(self):
        from mock_data.posts import MOCK_POSTS
        scored = score_posts(MOCK_POSTS)
        with_replies = generate_replies(scored)
        lines = _build_inspiration(with_replies)
        self.assertEqual(lines, [])

    def test_mock_build_markdown_no_check_manually(self):
        from mock_data.posts import MOCK_POSTS
        from src.post_generator import generate_posts
        scored = score_posts(MOCK_POSTS)
        with_replies = generate_replies(scored)
        sched = generate_posts(0)
        md = build_markdown("Signal Shift", with_replies, sched, mode="Mock")
        self.assertNotIn("manually before posting", md)


if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(__import__("__main__"))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
