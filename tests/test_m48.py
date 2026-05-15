"""
Tests for M4.8: domain relevance guardrails and US equities scope filters.
No real API calls, no network access.
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import yaml
from src.providers.tavily_search_provider import _build_candidate_queries
from src.scorer import score_posts, _score_fit_dynamic
from src.replier import generate_replies
from src.digest import _build_best_3, _build_inspiration


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_profile():
    yaml_path = os.path.join(os.path.dirname(__file__), "..", "profiles", "signal_shift.yaml")
    with open(yaml_path) as f:
        return yaml.safe_load(f)


def _make_web_post(text, tweet_id="1900000000000000001", age_hours=6):
    return {
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


def _score(text, age_hours=6, tweet_id="1900000000000000001"):
    post = _make_web_post(text, tweet_id=tweet_id, age_hours=age_hours)
    profile = _load_profile()
    return score_posts([post], profile=profile)[0]


def _fit(text):
    post = _make_web_post(text)
    profile = _load_profile()
    return _score_fit_dynamic(post, profile)["score"]


# ---------------------------------------------------------------------------
# 1. Off-topic rejection — sports/entertainment without market context
# ---------------------------------------------------------------------------

class TestOffTopicRejection(unittest.TestCase):

    def test_football_club_no_market_context_is_weak(self):
        result = _fit(
            "The football club signed a new striker this week — squad depth is looking better"
        )
        self.assertEqual(result, "Weak fit")

    def test_rugby_club_with_fit_keywords_is_weak(self):
        # "signal", "noise" are strong keywords but rugby club + no market context → Weak
        result = _fit(
            "Rugby club performance this season has been really noisy — hard to separate signal from noise"
        )
        self.assertEqual(result, "Weak fit")

    def test_esports_no_market_context_is_weak(self):
        result = _fit(
            "esports tournament noise this week is overwhelming the schedule"
        )
        self.assertEqual(result, "Weak fit")

    def test_cricket_match_no_market_context_is_weak(self):
        result = _fit(
            "The cricket match result today was confusing — what changed in the lineup?"
        )
        self.assertEqual(result, "Weak fit")

    def test_off_topic_reason_mentions_off_topic(self):
        post = _make_web_post("football club noise this season makes no sense")
        profile = _load_profile()
        fit = _score_fit_dynamic(post, profile)
        self.assertIn("off-topic", fit["reason"].lower())

    def test_off_topic_out_of_scope_false(self):
        post = _make_web_post(
            "football club signed a player — squad depth signals are confusing"
        )
        profile = _load_profile()
        fit = _score_fit_dynamic(post, profile)
        self.assertFalse(fit["out_of_scope"])


# ---------------------------------------------------------------------------
# 2. Domain relevance gate — fit keywords without market context → Weak
# ---------------------------------------------------------------------------

class TestDomainRelevanceGate(unittest.TestCase):

    def test_generic_noise_no_market_context_is_weak(self):
        # "noise" is a strong-fit keyword, but no market context → Weak
        result = _fit("There's so much noise in my life right now — hard to think clearly")
        self.assertEqual(result, "Weak fit")

    def test_clarity_without_market_context_is_weak(self):
        result = _fit("I need more clarity on this decision — too many takes from everyone")
        self.assertEqual(result, "Weak fit")

    def test_overload_without_market_context_is_weak(self):
        result = _fit("Information overload is real — I can't keep up with everything")
        self.assertEqual(result, "Weak fit")

    def test_overwhelmed_without_market_context_is_weak(self):
        result = _fit("I feel overwhelmed by all the noise — need some clarity here")
        self.assertEqual(result, "Weak fit")

    def test_domain_relevance_reason_mentions_context(self):
        post = _make_web_post("I feel overwhelmed by all the noise — need some clarity")
        profile = _load_profile()
        fit = _score_fit_dynamic(post, profile)
        self.assertIn("context", fit["reason"].lower())

    def test_noise_with_market_keyword_still_qualifies(self):
        # "market" present → has_market_context=True → Strong/Decent
        result = _fit(
            "There's so much market noise right now — hard to think clearly as a retail investor"
        )
        self.assertIn(result, ("Strong fit", "Decent fit"))

    def test_overwhelmed_with_stock_context_qualifies(self):
        result = _fit(
            "Completely overwhelmed by all the noise this earnings week — "
            "stocks moving and I can't tell why"
        )
        self.assertIn(result, ("Strong fit", "Decent fit"))


# ---------------------------------------------------------------------------
# 3. Out-of-scope market detection
# ---------------------------------------------------------------------------

class TestOutOfScopeMarketDetection(unittest.TestCase):

    def test_rupee_post_is_out_of_scope(self):
        post = _make_web_post(
            "Overwhelmed by all the rupee volatility this week — "
            "Indian market noise is real for retail investors"
        )
        profile = _load_profile()
        fit = _score_fit_dynamic(post, profile)
        self.assertTrue(fit["out_of_scope"])

    def test_nifty_post_is_out_of_scope(self):
        post = _make_web_post(
            "Nifty is moving but I can't separate signal from noise — "
            "retail investor confusion is real"
        )
        profile = _load_profile()
        fit = _score_fit_dynamic(post, profile)
        self.assertTrue(fit["out_of_scope"])

    def test_sensex_post_is_out_of_scope(self):
        post = _make_web_post(
            "Sensex dropped hard today — overwhelmed by the market noise around this move"
        )
        profile = _load_profile()
        fit = _score_fit_dynamic(post, profile)
        self.assertTrue(fit["out_of_scope"])

    def test_ftse_post_is_out_of_scope(self):
        post = _make_web_post(
            "FTSE is confusing me this week — too much noise in the UK market"
        )
        profile = _load_profile()
        fit = _score_fit_dynamic(post, profile)
        self.assertTrue(fit["out_of_scope"])

    def test_us_earnings_post_is_not_out_of_scope(self):
        post = _make_web_post(
            "Earnings this week are exhausting — stock moved but thesis feels unchanged"
        )
        profile = _load_profile()
        fit = _score_fit_dynamic(post, profile)
        self.assertFalse(fit["out_of_scope"])

    def test_out_of_scope_still_gets_fit_score(self):
        # out_of_scope posts still have a fit score — they are NOT Avoid
        post = _make_web_post(
            "Overwhelmed by Nifty noise — retail investors are confused about this market move"
        )
        profile = _load_profile()
        fit = _score_fit_dynamic(post, profile)
        self.assertIn(fit["score"], ("Strong fit", "Decent fit"))
        self.assertTrue(fit["out_of_scope"])

    def test_out_of_scope_posts_have_out_of_scope_key(self):
        post = _make_web_post("Sensex confusion overwhelming for retail investors today")
        profile = _load_profile()
        fit = _score_fit_dynamic(post, profile)
        self.assertIn("out_of_scope", fit)


# ---------------------------------------------------------------------------
# 4. Out-of-scope → Low opportunity (not in Best 3)
# ---------------------------------------------------------------------------

class TestOutOfScopeOpportunity(unittest.TestCase):

    def test_rupee_post_not_medium_opportunity(self):
        scored = _score(
            "Overwhelmed by all the rupee volatility this week — "
            "Indian market noise is exhausting for retail investors",
            age_hours=6
        )
        self.assertNotEqual(scored["opportunity"], "Medium opportunity")
        self.assertNotEqual(scored["opportunity"], "High opportunity")

    def test_nifty_post_is_low_opportunity(self):
        scored = _score(
            "Nifty moving but I can't separate signal from noise — "
            "retail investor confusion is real",
            age_hours=4
        )
        self.assertEqual(scored["opportunity"], "Low opportunity")

    def test_nifty_out_of_scope_flag_in_scored_post(self):
        scored = _score(
            "Nifty signal vs noise debate — overwhelmed retail investor here",
            age_hours=3
        )
        self.assertTrue(scored["out_of_scope"])

    def test_sensex_opportunity_reason_mentions_scope(self):
        scored = _score(
            "Sensex reaction confusing — retail investors overwhelmed by market noise today",
            age_hours=5
        )
        self.assertIn("scope", scored["opportunity_reason"].lower())

    def test_out_of_scope_post_not_in_best3(self):
        post = _make_web_post(
            "Nifty signal vs noise — retail investors overwhelmed by market moves this week",
            age_hours=6
        )
        profile = _load_profile()
        scored = score_posts([post], profile=profile)
        with_replies = generate_replies(scored)
        lines = _build_best_3(with_replies)
        content = "\n".join(lines)
        self.assertIn("No strong reply opportunities today", content)

    def test_us_earnings_still_medium_opportunity(self):
        # Fresh US post with strong fit → Medium opportunity (not downgraded)
        scored = _score(
            "Completely overwhelmed by market noise. Earnings reaction makes no sense. "
            "Hard to separate signal from noise this week.",
            age_hours=6
        )
        self.assertEqual(scored["opportunity"], "Medium opportunity")


# ---------------------------------------------------------------------------
# 5. US equities good posts still qualify
# ---------------------------------------------------------------------------

class TestUSEquitiesGoodPosts(unittest.TestCase):

    def test_us_earnings_confusion_strong_or_decent(self):
        scored = _score(
            "Stock moved 15% after earnings and I still can't figure out what changed. "
            "Thesis still feels valid but the market reaction makes no sense."
        )
        self.assertIn(scored["score"], ("Strong fit", "Decent fit"))

    def test_fomo_chasing_with_stocks(self):
        scored = _score(
            "Tried not to chase this stock but the FOMO got me. "
            "Need to slow down before I act on hot tips — information overload is real."
        )
        self.assertIn(scored["score"], ("Strong fit", "Decent fit"))

    def test_nvda_ticker_post_qualifies(self):
        scored = _score(
            "$NVDA move is confusing me — overwhelmed by the noise and conflicting takes. "
            "Not sure what actually changed for retail investors here."
        )
        self.assertIn(scored["score"], ("Strong fit", "Decent fit"))

    def test_nvda_not_out_of_scope(self):
        scored = _score(
            "$NVDA earnings reaction is making no sense — retail investor confusion here"
        )
        self.assertFalse(scored["out_of_scope"])

    def test_retail_overwhelm_not_out_of_scope(self):
        scored = _score(
            "Retail investors are overwhelmed by market noise this earnings week. "
            "Hard to know what matters."
        )
        self.assertFalse(scored["out_of_scope"])

    def test_sp500_post_qualifies(self):
        scored = _score(
            "S&P is confusing me this week — too much noise, not enough signal. "
            "Information overload for retail investors is real."
        )
        self.assertIn(scored["score"], ("Strong fit", "Decent fit"))


# ---------------------------------------------------------------------------
# 6. Replier out-of-scope branch handling
# ---------------------------------------------------------------------------

class TestReplierOutOfScope(unittest.TestCase):

    def test_fresh_out_of_scope_post_has_scope_reply_note(self):
        post = _make_web_post(
            "Nifty is moving but retail investors are overwhelmed by the noise — "
            "signal is hard to find",
            age_hours=6
        )
        profile = _load_profile()
        scored = score_posts([post], profile=profile)
        with_replies = generate_replies(scored)
        self.assertIsNotNone(with_replies[0]["reply_note"])
        self.assertIn("scope", with_replies[0]["reply_note"].lower())

    def test_fresh_out_of_scope_has_no_reply_options(self):
        post = _make_web_post(
            "Sensex drop this week has retail investors overwhelmed — too much market noise",
            age_hours=4
        )
        profile = _load_profile()
        scored = score_posts([post], profile=profile)
        with_replies = generate_replies(scored)
        self.assertEqual(with_replies[0]["replies"], [])

    def test_old_out_of_scope_has_scope_label_in_inspiration_angles(self):
        post = _make_web_post(
            "Nifty retail investors are overwhelmed by market noise — "
            "hard to separate signal from noise",
            age_hours=96,
            tweet_id="1800000000000000001"
        )
        profile = _load_profile()
        scored = score_posts([post], profile=profile)
        with_replies = generate_replies(scored)
        angles = with_replies[0].get("inspiration_angles")
        self.assertIsNotNone(angles)
        self.assertTrue(
            any("scope" in a.lower() for a in angles),
            "inspiration_angles for old out-of-scope post should include scope label"
        )

    def test_us_post_has_no_scope_reply_note(self):
        post = _make_web_post(
            "Overwhelmed by market noise this earnings week — "
            "retail investor information overload is real",
            age_hours=6
        )
        profile = _load_profile()
        scored = score_posts([post], profile=profile)
        with_replies = generate_replies(scored)
        self.assertIsNone(with_replies[0]["reply_note"])


# ---------------------------------------------------------------------------
# 7. Save for Inspiration filtering
# ---------------------------------------------------------------------------

class TestInspirationFiltering(unittest.TestCase):

    def test_sports_post_not_in_inspiration(self):
        # Weak fit → never appears in inspiration
        post = _make_web_post(
            "football club noise this season is overwhelming — squad depth signals are confusing",
            age_hours=96
        )
        profile = _load_profile()
        scored = score_posts([post], profile=profile)
        with_replies = generate_replies(scored)
        lines = _build_inspiration(with_replies)
        self.assertEqual(lines, [])

    def test_old_out_of_scope_post_in_inspiration(self):
        # Old investing post about Nifty → in inspiration with scope label
        post = _make_web_post(
            "Nifty retail investors are overwhelmed by market noise — "
            "hard to separate signal from noise",
            age_hours=96,
            tweet_id="1800000000000000001"
        )
        profile = _load_profile()
        scored = score_posts([post], profile=profile)
        with_replies = generate_replies(scored)
        lines = _build_inspiration(with_replies)
        self.assertGreater(len(lines), 0)
        content = "\n".join(lines)
        self.assertIn("scope", content.lower())

    def test_us_old_post_in_inspiration_without_scope_label(self):
        # Old US investing post → inspiration without scope label
        post = _make_web_post(
            "Stock moved hard after earnings and I can't figure out if my thesis changed. "
            "Too much market noise this week.",
            age_hours=96,
            tweet_id="1700000000000000001"
        )
        profile = _load_profile()
        scored = score_posts([post], profile=profile)
        with_replies = generate_replies(scored)
        angles = with_replies[0].get("inspiration_angles") or []
        # Should have inspiration angles, none of which should be a scope label
        if angles:
            self.assertFalse(
                any("scope" in a.lower() for a in angles),
                "US post inspiration_angles should not include scope label"
            )


# ---------------------------------------------------------------------------
# 8. Backward compatibility — profile without market_context_required
# ---------------------------------------------------------------------------

class TestMinimalProfileCompatibility(unittest.TestCase):

    def _minimal_profile(self):
        return {
            "fit_keywords": {
                "strong": ["noise", "clarity", "signal", "overload"],
                "decent": ["investor", "investing", "retail"],
                "weak": ["technical analysis"],
                "avoid": ["100x"],
            }
        }

    def test_noise_without_context_section_still_scores(self):
        # No market_context_required → guard fires True → noise qualifies as usual
        post = _make_web_post("There's so much noise right now — need some clarity")
        profile = self._minimal_profile()
        fit = _score_fit_dynamic(post, profile)
        self.assertIn(fit["score"], ("Strong fit", "Decent fit"))

    def test_minimal_profile_no_out_of_scope_crash(self):
        # No out_of_scope_market section → out_of_scope=False, no crash
        post = _make_web_post("Nifty confusion overwhelming for investors today")
        profile = self._minimal_profile()
        fit = _score_fit_dynamic(post, profile)
        self.assertFalse(fit["out_of_scope"])

    def test_score_posts_with_minimal_profile_has_out_of_scope(self):
        post = _make_web_post("Overwhelmed by market noise. Information overload is real.")
        profile = self._minimal_profile()
        results = score_posts([post], profile=profile)
        self.assertEqual(len(results), 1)
        self.assertIn("out_of_scope", results[0])
        self.assertFalse(results[0]["out_of_scope"])


# ---------------------------------------------------------------------------
# 9. Mock mode unchanged
# ---------------------------------------------------------------------------

class TestMockModeUnchangedM48(unittest.TestCase):

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
            self.assertIn("out_of_scope", post)
            self.assertFalse(post["out_of_scope"])

    def test_mock_best3_still_finds_opportunities(self):
        from mock_data.posts import MOCK_POSTS
        scored = score_posts(MOCK_POSTS)
        with_replies = generate_replies(scored)
        lines = _build_best_3(with_replies)
        content = "\n".join(lines)
        self.assertNotIn("No suitable reply", content)


# ---------------------------------------------------------------------------
# 10. Query rotation unchanged
# ---------------------------------------------------------------------------

class TestQueryRotationUnchangedM48(unittest.TestCase):

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

    def test_new_fit_keyword_sections_dont_break_query_building(self):
        # market_context_required, off_topic, out_of_scope_market are in fit_keywords —
        # _build_candidate_queries uses search_terms + query_templates, not fit_keywords
        profile = _load_profile()
        candidates = _build_candidate_queries(profile)
        # Should still generate candidates without crash
        self.assertGreaterEqual(len(candidates), 20)


if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(__import__("__main__"))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
