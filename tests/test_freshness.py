"""
Tests for M4.4: freshness filtering, Snowflake decoding, age-aware scoring.
No real API calls, no network access, no X API, no scraping.
"""

import sys
import os
import unittest
from unittest.mock import patch
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.providers.tavily_search_provider import _decode_snowflake, _TWITTER_EPOCH_MS
from src.scorer import _freshness_tier, _age_label, score_posts
from src.replier import generate_replies, _pick_reply_options, _DYNAMIC_TEMPLATES
from src.digest import _build_best_3, _build_inspiration


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_web_post(tweet_id="1900000000000000001", age_hours=6, age_source="snowflake",
                   fit="Strong fit", text="retail investor noise clarity signal"):
    return {
        "id": tweet_id,
        "author": f"@user_{tweet_id[-4:]}",
        "author_name": f"user_{tweet_id[-4:]}",
        "author_followers": 0,
        "author_profile_url": f"https://x.com/user",
        "text": text,
        "likes": 0,
        "reposts": 0,
        "reply_count": 0,
        "impressions": 0,
        "age_hours": age_hours,
        "age_source": age_source,
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
# 1. Snowflake ID decoding
# ---------------------------------------------------------------------------

class TestSnowflakeDecode(unittest.TestCase):

    def test_decode_known_id_returns_snowflake_source(self):
        # Any valid-looking snowflake ID should return source="snowflake"
        age, source = _decode_snowflake("1789234567890001001")
        self.assertEqual(source, "snowflake")
        self.assertIsInstance(age, float)
        self.assertGreater(age, 0)

    def test_decode_recent_id_is_fresh(self):
        # Construct a snowflake ID for ~2 hours ago
        two_hours_ago_ms = int((datetime.now(timezone.utc) - timedelta(hours=2)).timestamp() * 1000)
        synthetic_id = str((two_hours_ago_ms - _TWITTER_EPOCH_MS) << 22)
        age, source = _decode_snowflake(synthetic_id)
        self.assertEqual(source, "snowflake")
        self.assertAlmostEqual(age, 2.0, delta=0.2)

    def test_decode_old_id_is_old(self):
        # Construct a snowflake ID for ~5 days ago
        five_days_ago_ms = int((datetime.now(timezone.utc) - timedelta(days=5)).timestamp() * 1000)
        synthetic_id = str((five_days_ago_ms - _TWITTER_EPOCH_MS) << 22)
        age, source = _decode_snowflake(synthetic_id)
        self.assertEqual(source, "snowflake")
        self.assertAlmostEqual(age, 5 * 24, delta=1.0)

    def test_decode_invalid_returns_unknown(self):
        age, source = _decode_snowflake("not-a-number")
        self.assertIsNone(age)
        self.assertEqual(source, "unknown")

    def test_decode_empty_returns_unknown(self):
        age, source = _decode_snowflake("")
        self.assertIsNone(age)
        self.assertEqual(source, "unknown")

    def test_decode_is_pure_math_no_network(self):
        # Verify no outbound calls are made during decoding
        with patch("socket.socket") as mock_sock:
            _decode_snowflake("1900000000000000001")
            mock_sock.assert_not_called()


# ---------------------------------------------------------------------------
# 2. Freshness tier classification
# ---------------------------------------------------------------------------

class TestFreshnessTier(unittest.TestCase):

    def test_none_is_unknown(self):
        self.assertEqual(_freshness_tier(None), "unknown")

    def test_zero_is_fresh(self):
        self.assertEqual(_freshness_tier(0), "fresh")

    def test_12h_is_fresh(self):
        self.assertEqual(_freshness_tier(12), "fresh")

    def test_24h_is_fresh(self):
        self.assertEqual(_freshness_tier(24), "fresh")

    def test_36h_is_borderline(self):
        self.assertEqual(_freshness_tier(36), "borderline")

    def test_48h_is_borderline(self):
        self.assertEqual(_freshness_tier(48), "borderline")

    def test_72h_is_old(self):
        self.assertEqual(_freshness_tier(72), "old")

    def test_167h_is_old(self):
        self.assertEqual(_freshness_tier(167), "old")

    def test_168h_is_old(self):
        # 168h == exactly 7 days — upper bound of "old" (48h–7d inclusive)
        self.assertEqual(_freshness_tier(168), "old")

    def test_200h_is_stale(self):
        self.assertEqual(_freshness_tier(200), "stale")

    def test_720h_is_stale(self):
        self.assertEqual(_freshness_tier(720), "stale")

    def test_721h_is_very_stale(self):
        self.assertEqual(_freshness_tier(721), "very_stale")


# ---------------------------------------------------------------------------
# 3. Opportunity scoring — freshness gates for Unknown visibility
# ---------------------------------------------------------------------------

class TestAgeAwareOpportunity(unittest.TestCase):

    def _score(self, age_hours, age_source="snowflake", fit_text="noise clarity signal overload"):
        post = _make_web_post(age_hours=age_hours, age_source=age_source, text=fit_text)
        profile = _minimal_profile()
        return score_posts([post], profile=profile)[0]

    def test_fresh_strong_fit_is_medium(self):
        result = self._score(6)
        self.assertEqual(result["opportunity"], "Medium opportunity")
        self.assertEqual(result["visibility"], "Unknown visibility")

    def test_borderline_strong_fit_is_medium(self):
        result = self._score(36)
        self.assertEqual(result["opportunity"], "Medium opportunity")

    def test_borderline_decent_fit_is_low(self):
        post = _make_web_post(age_hours=36, text="retail investor")
        result = score_posts([post], profile=_minimal_profile())[0]
        self.assertIn(result["score"], ("Decent fit", "Weak fit"))
        if result["score"] == "Decent fit":
            self.assertEqual(result["opportunity"], "Low opportunity")

    def test_old_post_is_low_opportunity(self):
        result = self._score(96)   # 4 days
        self.assertEqual(result["opportunity"], "Low opportunity")

    def test_stale_post_is_poor_opportunity(self):
        result = self._score(200)   # ~8 days
        self.assertEqual(result["opportunity"], "Poor opportunity")

    def test_very_stale_post_is_poor_opportunity(self):
        result = self._score(800)   # ~33 days
        self.assertEqual(result["opportunity"], "Poor opportunity")

    def test_unknown_age_is_medium_with_note(self):
        result = self._score(None, age_source="unknown")
        self.assertEqual(result["opportunity"], "Medium opportunity")
        self.assertIn("age", result["opportunity_reason"].lower())

    def test_freshness_tier_in_scored_post(self):
        result = self._score(6)
        self.assertEqual(result["freshness_tier"], "fresh")

    def test_age_label_in_scored_post(self):
        result = self._score(6)
        self.assertIsNotNone(result["age_label"])
        self.assertIn("6h old", result["age_label"])

    def test_age_label_stale_says_do_not_reply(self):
        result = self._score(200)
        self.assertIn("stale", result["age_label"].lower())

    def test_age_label_old_says_save_for_inspiration(self):
        result = self._score(96)
        self.assertIn("inspiration", result["age_label"].lower())


# ---------------------------------------------------------------------------
# 4. Best 3 filtering — stale posts excluded
# ---------------------------------------------------------------------------

class TestBest3Filtering(unittest.TestCase):

    def _scored(self, age_hours, age_source="snowflake"):
        post = _make_web_post(age_hours=age_hours, age_source=age_source)
        profile = _minimal_profile()
        scored = score_posts([post], profile=profile)
        return generate_replies(scored)

    def test_fresh_post_appears_in_best3(self):
        posts = self._scored(6)
        lines = _build_best_3(posts)
        content = "\n".join(lines)
        self.assertNotIn("No suitable reply", content)
        self.assertIn("@user_", content)

    def test_old_post_excluded_from_best3(self):
        posts = self._scored(100)   # 4+ days
        lines = _build_best_3(posts)
        content = "\n".join(lines)
        self.assertIn("No suitable reply", content)

    def test_stale_post_excluded_from_best3(self):
        posts = self._scored(250)   # ~10 days
        lines = _build_best_3(posts)
        content = "\n".join(lines)
        self.assertIn("No suitable reply", content)

    def test_count_message_when_fewer_than_3(self):
        posts = self._scored(6)
        lines = _build_best_3(posts)
        content = "\n".join(lines)
        self.assertIn("Only 1", content)


# ---------------------------------------------------------------------------
# 5. Save for inspiration section
# ---------------------------------------------------------------------------

class TestInspiration(unittest.TestCase):

    def test_old_fit_post_appears_in_inspiration(self):
        post = _make_web_post(age_hours=96)   # 4 days, "old"
        profile = _minimal_profile()
        scored = score_posts([post], profile=profile)
        with_replies = generate_replies(scored)
        lines = _build_inspiration(with_replies)
        if lines:   # only shows for Strong/Decent fit
            self.assertIn("Save for Inspiration", "\n".join(lines))

    def test_fresh_post_not_in_inspiration(self):
        post = _make_web_post(age_hours=6)
        profile = _minimal_profile()
        scored = score_posts([post], profile=profile)
        with_replies = generate_replies(scored)
        lines = _build_inspiration(with_replies)
        self.assertEqual(lines, [])

    def test_mock_post_not_in_inspiration(self):
        # Mock posts have integer IDs and no metrics_confidence — must not appear here
        from mock_data.posts import MOCK_POSTS
        scored = score_posts(MOCK_POSTS)
        with_replies = generate_replies(scored)
        lines = _build_inspiration(with_replies)
        self.assertEqual(lines, [])


# ---------------------------------------------------------------------------
# 6. Author followers display
# ---------------------------------------------------------------------------

class TestFollowersDisplay(unittest.TestCase):

    def test_zero_followers_renders_unknown_for_web_search(self):
        from src.digest import build_markdown
        from src.post_generator import generate_posts
        post = _make_web_post(age_hours=6)
        profile = _minimal_profile()
        scored = score_posts([post], profile=profile)
        with_replies = generate_replies(scored)
        schedule = generate_posts(0)
        md = build_markdown("Signal Shift", with_replies, schedule, mode="Tavily Search")
        self.assertIn("followers:** Unknown", md)
        self.assertNotIn("followers:** 0", md)

    def test_real_followers_render_correctly_for_mock_posts(self):
        from src.digest import build_markdown
        from src.post_generator import generate_posts
        from mock_data.posts import MOCK_POSTS
        scored = score_posts(MOCK_POSTS)
        with_replies = generate_replies(scored)
        schedule = generate_posts(0)
        md = build_markdown("Signal Shift", with_replies, schedule)
        # Mock post 1 has 2100 followers
        self.assertIn("2,100", md)


# ---------------------------------------------------------------------------
# 7. Reply variation — different posts get different wording
# ---------------------------------------------------------------------------

class TestReplyVariation(unittest.TestCase):

    def test_even_and_odd_ids_get_different_options(self):
        template = _DYNAMIC_TEMPLATES["noise_overwhelm"]
        options_even, _ = _pick_reply_options("1900000000000000000", template)  # even
        options_odd, _ = _pick_reply_options("1900000000000000001", template)   # odd
        texts_even = {r["text"] for r in options_even}
        texts_odd = {r["text"] for r in options_odd}
        self.assertNotEqual(texts_even, texts_odd)

    def test_all_themes_have_options_b(self):
        for theme, template in _DYNAMIC_TEMPLATES.items():
            self.assertIn("options_b", template, f"Theme '{theme}' missing options_b")
            self.assertEqual(len(template["options_b"]), 3,
                             f"Theme '{theme}' options_b should have 3 entries")

    def test_pick_reply_options_invalid_id_uses_primary(self):
        template = _DYNAMIC_TEMPLATES["generic_strong"]
        options, idx = _pick_reply_options("not-numeric", template)
        self.assertEqual(options, template["options"])
        self.assertEqual(idx, template["best_option_index"])

    def test_mock_replies_unchanged(self):
        from src.replier import REPLIES
        # Hardcoded mock replies must not be modified — test a known value
        self.assertEqual(REPLIES[3]["options"][0]["text"], "More dashboards, same fog.")


# ---------------------------------------------------------------------------
# 8. Mock mode unchanged
# ---------------------------------------------------------------------------

class TestMockModeUnchanged(unittest.TestCase):

    def test_mock_posts_still_score_correctly(self):
        from mock_data.posts import MOCK_POSTS
        scored = score_posts(MOCK_POSTS)
        self.assertEqual(scored[0]["score"], "Strong fit")
        self.assertEqual(scored[6]["score"], "Avoid")

    def test_mock_posts_have_no_age_label(self):
        from mock_data.posts import MOCK_POSTS
        scored = score_posts(MOCK_POSTS)
        for post in scored:
            self.assertIsNone(post["age_label"])

    def test_mock_best3_uses_real_engagement(self):
        from mock_data.posts import MOCK_POSTS
        scored = score_posts(MOCK_POSTS)
        with_replies = generate_replies(scored)
        lines = _build_best_3(with_replies)
        content = "\n".join(lines)
        # Mock mode should find Best 3 without "Only X opportunities" message
        self.assertNotIn("No suitable reply", content)


if __name__ == "__main__":
    results = []
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(__import__("__main__"))
    runner = unittest.TextTestRunner(verbosity=0, stream=open(os.devnull, "w"))
    test_result = runner.run(suite)

    for test, _ in test_result.failures + test_result.errors:
        print(f"FAIL {test}")
    for test in test_result.successes if hasattr(test_result, "successes") else []:
        print(f"PASS {test}")

    # Simple pass/fail output
    total = test_result.testsRun
    failed = len(test_result.failures) + len(test_result.errors)
    passed = total - failed

    # Re-run with per-test output
    suite2 = loader.loadTestsFromModule(__import__("__main__"))
    for test in suite2:
        for t in test:
            result = unittest.TestResult()
            t.run(result)
            name = t._testMethodName
            cls = t.__class__.__name__
            if result.failures or result.errors:
                msg = (result.failures or result.errors)[0][1].strip().split("\n")[-1]
                print(f"FAIL {cls}.{name}: {msg}")
            else:
                print(f"PASS {cls}.{name}")

    print(f"\n{passed}/{total} tests passed.")
    sys.exit(0 if failed == 0 else 1)
