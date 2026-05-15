"""
Tests for M4.9: Tavily combined-text scoring and US equities scope preference.
No real API calls, no network access.
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import yaml
from src.providers.tavily_search_provider import _normalize, _build_candidate_queries
from src.scorer import score_posts, _score_fit_dynamic, _has_us_scope
from src.replier import generate_replies
from src.digest import _build_best_3


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_profile():
    yaml_path = os.path.join(os.path.dirname(__file__), "..", "profiles", "signal_shift.yaml")
    with open(yaml_path) as f:
        return yaml.safe_load(f)


def _make_web_post(text, tweet_id="1900000000000000001", age_hours=6, combined=None):
    post = {
        "id": tweet_id,
        "author": "@test_user",
        "author_name": "test_user",
        "author_followers": 0,
        "author_profile_url": "https://x.com/test_user",
        "text": text,
        "likes": 0, "reposts": 0, "reply_count": 0, "impressions": 0,
        "age_hours": age_hours,
        "age_source": "snowflake",
        "post_url": f"https://x.com/test_user/status/{tweet_id}",
        "url": f"https://x.com/test_user/status/{tweet_id}",
        "discovery_source": "tavily_search",
        "metrics_confidence": "low",
    }
    if combined is not None:
        post["combined_text_for_scoring"] = combined
    return post


def _score(text, age_hours=6, tweet_id="1900000000000000001", combined=None):
    post = _make_web_post(text, tweet_id=tweet_id, age_hours=age_hours, combined=combined)
    profile = _load_profile()
    return score_posts([post], profile=profile)[0]


def _fit(text, combined=None):
    post = _make_web_post(text, combined=combined)
    profile = _load_profile()
    return _score_fit_dynamic(post, profile)


# ---------------------------------------------------------------------------
# 1. _normalize builds combined_text_for_scoring from title + content
# ---------------------------------------------------------------------------

class TestNormalizeCombinedText(unittest.TestCase):

    def test_combined_text_field_present(self):
        post = _normalize(
            "https://x.com/testuser/status/1900000000000000001",
            "testuser on X: 'Market noise is real this week'",
            "The market has been very noisy — retail investors are overwhelmed",
            "2025-05-15T10:00:00Z",
        )
        self.assertIsNotNone(post)
        self.assertIn("combined_text_for_scoring", post)

    def test_combined_text_includes_title(self):
        post = _normalize(
            "https://x.com/testuser/status/1900000000000000001",
            "testuser on X: 'Rupee hit hard by Modi policy'",
            "retail investors are overwhelmed by market noise",
            "2025-05-15T10:00:00Z",
        )
        self.assertIsNotNone(post)
        self.assertIn("Rupee", post["combined_text_for_scoring"])
        self.assertIn("Modi", post["combined_text_for_scoring"])

    def test_combined_text_includes_content(self):
        post = _normalize(
            "https://x.com/testuser/status/1900000000000000001",
            "testuser on X: 'Market noise this week'",
            "India macro context: rupee weakened as the Sensex dropped",
            "2025-05-15T10:00:00Z",
        )
        self.assertIsNotNone(post)
        self.assertIn("rupee", post["combined_text_for_scoring"])
        self.assertIn("Sensex", post["combined_text_for_scoring"])

    def test_combined_text_handles_none_content(self):
        post = _normalize(
            "https://x.com/testuser/status/1900000000000000001",
            "testuser on X: 'Market noise this week'",
            None,
            "2025-05-15T10:00:00Z",
        )
        self.assertIsNotNone(post)
        self.assertIn("combined_text_for_scoring", post)
        self.assertIsInstance(post["combined_text_for_scoring"], str)

    def test_combined_text_handles_none_title(self):
        post = _normalize(
            "https://x.com/testuser/status/1900000000000000001",
            None,
            "Retail investors overwhelmed by market noise",
            "2025-05-15T10:00:00Z",
        )
        self.assertIsNotNone(post)
        self.assertIn("combined_text_for_scoring", post)
        self.assertIn("retail investors", post["combined_text_for_scoring"].lower())

    def test_display_text_still_uses_clean_extraction(self):
        # The "text" field should still be the extracted tweet text, not raw combined
        post = _normalize(
            "https://x.com/testuser/status/1900000000000000001",
            "testuser on X: \"Market noise is overwhelming\"",
            "India rupee Modi: broader context here",
            "2025-05-15T10:00:00Z",
        )
        self.assertIsNotNone(post)
        # Display text should be clean (extracted tweet text)
        self.assertNotIn("testuser on X:", post["text"])
        # But combined should have raw context
        self.assertIn("India", post["combined_text_for_scoring"])


# ---------------------------------------------------------------------------
# 2. Scorer uses combined_text_for_scoring for out-of-scope detection
# ---------------------------------------------------------------------------

class TestScorerUsesCombinedText(unittest.TestCase):

    def test_out_of_scope_detected_from_combined_text(self):
        # Display text looks generic, but combined text reveals India/rupee context
        profile = _load_profile()
        post = _make_web_post(
            "The market is very noisy this week — retail investors are overwhelmed",
            combined="India rupee Modi: the market is very noisy this week — retail investors are overwhelmed",
        )
        fit = _score_fit_dynamic(post, profile)
        self.assertTrue(fit["out_of_scope"])

    def test_nifty_in_combined_text_triggers_out_of_scope(self):
        profile = _load_profile()
        post = _make_web_post(
            "Retail investors overwhelmed by market noise this week",
            combined="Nifty drops: retail investors overwhelmed by market noise this week",
        )
        fit = _score_fit_dynamic(post, profile)
        self.assertTrue(fit["out_of_scope"])

    def test_combined_text_takes_precedence_over_display_text(self):
        # Display text has no out-of-scope terms; combined text does
        profile = _load_profile()
        post = _make_web_post(
            "Earnings confusion and market noise — retail investor clarity needed",
        )
        # Without combined text: not out_of_scope
        fit_no_combined = _score_fit_dynamic(post, profile)
        self.assertFalse(fit_no_combined["out_of_scope"])
        # Add combined text with India context
        post["combined_text_for_scoring"] = (
            "India macro: earnings confusion and market noise — retail investor clarity needed"
        )
        fit_with_combined = _score_fit_dynamic(post, profile)
        self.assertTrue(fit_with_combined["out_of_scope"])

    def test_us_post_with_combined_text_not_out_of_scope(self):
        # Combined text with S&P context should not trigger out_of_scope
        profile = _load_profile()
        post = _make_web_post(
            "S&P moving but retail investors are overwhelmed by the noise",
            combined="S&P 500 moves: retail investors are overwhelmed by market noise this earnings week",
        )
        fit = _score_fit_dynamic(post, profile)
        self.assertFalse(fit["out_of_scope"])


# ---------------------------------------------------------------------------
# 3. Expanded out_of_scope terms
# ---------------------------------------------------------------------------

class TestExpandedOutOfScopeTerms(unittest.TestCase):

    def test_india_triggers_out_of_scope(self):
        fit = _fit("India stock market retail investors are overwhelmed by the noise")
        # India in text → out_of_scope via combined/text
        profile = _load_profile()
        post = _make_web_post("India stock market retail investors are overwhelmed by the noise")
        result = _score_fit_dynamic(post, profile)
        self.assertTrue(result["out_of_scope"])

    def test_indian_triggers_out_of_scope(self):
        profile = _load_profile()
        post = _make_web_post(
            "Indian retail investors are overwhelmed by market noise this week"
        )
        result = _score_fit_dynamic(post, profile)
        self.assertTrue(result["out_of_scope"])

    def test_modi_triggers_out_of_scope(self):
        profile = _load_profile()
        post = _make_web_post(
            "Modi's gold policy has retail investors overwhelmed by market confusion"
        )
        result = _score_fit_dynamic(post, profile)
        self.assertTrue(result["out_of_scope"])

    def test_inr_triggers_out_of_scope(self):
        profile = _load_profile()
        post = _make_web_post(
            "INR is weakening — retail investors are confused about the market moves"
        )
        result = _score_fit_dynamic(post, profile)
        self.assertTrue(result["out_of_scope"])

    def test_rbi_triggers_out_of_scope(self):
        profile = _load_profile()
        post = _make_web_post(
            "RBI decision has retail investors overwhelmed by market noise today"
        )
        result = _score_fit_dynamic(post, profile)
        self.assertTrue(result["out_of_scope"])

    def test_hang_seng_triggers_out_of_scope(self):
        profile = _load_profile()
        post = _make_web_post(
            "Hang Seng confusion overwhelming retail investors — too much market noise"
        )
        result = _score_fit_dynamic(post, profile)
        self.assertTrue(result["out_of_scope"])

    def test_forex_triggers_out_of_scope(self):
        profile = _load_profile()
        post = _make_web_post(
            "forex market noise is overwhelming retail investors this week"
        )
        result = _score_fit_dynamic(post, profile)
        self.assertTrue(result["out_of_scope"])


# ---------------------------------------------------------------------------
# 4. India/rupee/Modi in combined text → not Medium opportunity, not in Best 3
# ---------------------------------------------------------------------------

class TestCombinedTextScopeOpportunity(unittest.TestCase):

    def test_india_in_combined_text_not_medium(self):
        # Display text looks like good fit; combined text reveals India context
        scored = _score(
            "Overwhelmed by market noise — retail investors are confused this earnings week",
            combined="India rupee: overwhelmed by market noise — retail investors are confused this earnings week",
            age_hours=6,
        )
        self.assertTrue(scored["out_of_scope"])
        self.assertNotEqual(scored["opportunity"], "Medium opportunity")

    def test_modi_in_combined_text_not_in_best3(self):
        post = _make_web_post(
            "Retail investors overwhelmed by market noise — need clarity on earnings",
            age_hours=6,
            combined="Modi gold appeal: retail investors overwhelmed by market noise — need clarity",
        )
        profile = _load_profile()
        scored = score_posts([post], profile=profile)
        with_replies = generate_replies(scored)
        lines = _build_best_3(with_replies)
        content = "\n".join(lines)
        self.assertIn("No suitable reply opportunities found today", content)

    def test_rupee_in_combined_text_low_opportunity(self):
        scored = _score(
            "Overwhelmed by market noise this week — retail investor confusion is real",
            combined="rupee weakens: overwhelmed by market noise — retail investor confusion is real",
            age_hours=6,
        )
        self.assertEqual(scored["opportunity"], "Low opportunity")
        self.assertTrue(scored["out_of_scope"])

    def test_sensex_in_combined_text_low_opportunity(self):
        scored = _score(
            "Market noise overwhelming — hard to separate signal from noise for investors",
            combined="Sensex drops: market noise overwhelming — hard to separate signal from noise",
            age_hours=6,
        )
        self.assertTrue(scored["out_of_scope"])
        self.assertEqual(scored["opportunity"], "Low opportunity")


# ---------------------------------------------------------------------------
# 5. US scope preference — no US context → capped below Medium
# ---------------------------------------------------------------------------

class TestUScopePreference(unittest.TestCase):

    def test_no_us_scope_generic_investing_capped_at_low(self):
        # Strong fit signals + market context, but no US-specific signals
        scored = _score(
            "Retail investors are overwhelmed by market noise — too much information",
            age_hours=6
        )
        self.assertEqual(scored["opportunity"], "Low opportunity")

    def test_no_us_scope_not_in_best3(self):
        post = _make_web_post(
            "Retail investors are overwhelmed by market noise — too much information",
            age_hours=6
        )
        profile = _load_profile()
        scored_list = score_posts([post], profile=profile)
        with_replies = generate_replies(scored_list)
        lines = _build_best_3(with_replies)
        content = "\n".join(lines)
        self.assertIn("No suitable reply opportunities found today", content)

    def test_has_us_scope_returns_true_for_us_signals(self):
        profile = _load_profile()
        post = _make_web_post(
            "S&P 500 is confusing me this week — retail investor overwhelm is real"
        )
        self.assertTrue(_has_us_scope(post, profile))

    def test_has_us_scope_returns_false_for_generic(self):
        profile = _load_profile()
        post = _make_web_post(
            "Retail investors are overwhelmed by market noise — too much information"
        )
        self.assertFalse(_has_us_scope(post, profile))

    def test_has_us_scope_no_section_defaults_true(self):
        # Profile without us_scope_market → guard returns True (no restriction)
        profile = {"fit_keywords": {"strong": ["noise"]}}
        post = _make_web_post("Too much noise")
        self.assertTrue(_has_us_scope(post, profile))

    def test_us_scope_reason_mentions_us_context(self):
        scored = _score(
            "Retail investors overwhelmed by market noise — information overload",
            age_hours=6
        )
        self.assertIn("US", scored["opportunity_reason"])


# ---------------------------------------------------------------------------
# 6. US-market posts still qualify for Medium opportunity
# ---------------------------------------------------------------------------

class TestUSEquitiesStillMedium(unittest.TestCase):

    def test_earnings_post_is_medium_opportunity(self):
        scored = _score(
            "Completely overwhelmed by market noise this earnings week. "
            "Stock reaction makes no sense — retail investor confusion is real.",
            age_hours=6
        )
        self.assertEqual(scored["opportunity"], "Medium opportunity")

    def test_sp500_post_is_medium_opportunity(self):
        scored = _score(
            "S&P is moving and I can't tell what's driving it — "
            "retail investors overwhelmed by the noise.",
            age_hours=6
        )
        self.assertEqual(scored["opportunity"], "Medium opportunity")

    def test_nvda_ticker_is_medium_opportunity(self):
        scored = _score(
            "$NVDA move after earnings is confusing — "
            "hard to separate signal from noise for retail investors.",
            age_hours=6
        )
        self.assertEqual(scored["opportunity"], "Medium opportunity")

    def test_nasdaq_post_is_medium_opportunity(self):
        scored = _score(
            "Nasdaq volatility this week has retail investors overwhelmed — "
            "hard to find the signal in all this noise.",
            age_hours=6
        )
        self.assertEqual(scored["opportunity"], "Medium opportunity")

    def test_fed_post_is_medium_opportunity(self):
        scored = _score(
            "Fed decision has retail investors overwhelmed — "
            "market noise is at peak right now. Too hard to separate signal.",
            age_hours=6
        )
        self.assertEqual(scored["opportunity"], "Medium opportunity")

    def test_wall_street_post_is_medium_opportunity(self):
        scored = _score(
            "Wall Street is moving and retail investors are completely overwhelmed — "
            "hard to know what matters vs what's noise.",
            age_hours=6
        )
        self.assertEqual(scored["opportunity"], "Medium opportunity")

    def test_us_scope_not_out_of_scope(self):
        scored = _score(
            "$NVDA earnings reaction is making no sense — retail investor confusion here"
        )
        self.assertFalse(scored["out_of_scope"])


# ---------------------------------------------------------------------------
# 7. Mock mode unchanged
# ---------------------------------------------------------------------------

class TestMockModeUnchangedM49(unittest.TestCase):

    def test_mock_posts_score_correctly(self):
        from mock_data.posts import MOCK_POSTS
        scored = score_posts(MOCK_POSTS)
        self.assertEqual(scored[0]["score"], "Strong fit")
        self.assertEqual(scored[6]["score"], "Avoid")

    def test_mock_post_2_still_strong(self):
        from mock_data.posts import MOCK_POSTS
        scored = score_posts(MOCK_POSTS)
        self.assertEqual(scored[1]["score"], "Strong fit")

    def test_mock_post_7_still_avoid(self):
        from mock_data.posts import MOCK_POSTS
        scored = score_posts(MOCK_POSTS)
        self.assertEqual(scored[7]["score"], "Avoid")

    def test_mock_posts_all_have_out_of_scope_false(self):
        from mock_data.posts import MOCK_POSTS
        scored = score_posts(MOCK_POSTS)
        for post in scored:
            self.assertFalse(post.get("out_of_scope", True))

    def test_mock_best3_still_finds_opportunities(self):
        from mock_data.posts import MOCK_POSTS
        scored = score_posts(MOCK_POSTS)
        with_replies = generate_replies(scored)
        lines = _build_best_3(with_replies)
        content = "\n".join(lines)
        self.assertNotIn("No suitable reply", content)


# ---------------------------------------------------------------------------
# 8. Query rotation unchanged
# ---------------------------------------------------------------------------

class TestQueryRotationUnchangedM49(unittest.TestCase):

    def test_candidates_generated_from_profile(self):
        profile = _load_profile()
        candidates = _build_candidate_queries(profile)
        self.assertGreater(len(candidates), 0)

    def test_first_template_fills_first(self):
        profile = _load_profile()
        candidates = _build_candidate_queries(profile)
        for c in candidates[:20]:
            self.assertIn("site:x.com", c)

    def test_no_removed_terms_in_candidates(self):
        profile = _load_profile()
        candidates = _build_candidate_queries(profile)
        removed = [
            "everyone is bullish", "everyone is bearish",
            "stock is ripping", "stock is dumping", "market feels broken",
        ]
        for term in removed:
            for c in candidates:
                self.assertNotIn(term, c)

    def test_us_scope_and_out_of_scope_sections_dont_affect_query_building(self):
        # us_scope_market and out_of_scope_market are fit_keyword subsections —
        # _build_candidate_queries uses search_terms + query_templates only
        profile = _load_profile()
        candidates = _build_candidate_queries(profile)
        self.assertGreaterEqual(len(candidates), 20)


if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(__import__("__main__"))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
