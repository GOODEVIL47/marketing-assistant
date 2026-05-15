"""
Tests for M4.7: tightened search terms, improved fit/avoid scoring, quality guardrails.
No real API calls, no network access.
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import yaml
from src.providers.tavily_search_provider import _build_candidate_queries
from src.scorer import score_posts, _score_fit_dynamic


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
# 1. Removed / deprioritized bad search terms
# ---------------------------------------------------------------------------

class TestRemovedBadSearchTerms(unittest.TestCase):

    def _search_terms(self):
        return _load_profile().get("search_terms", [])

    def test_everyone_is_bullish_not_in_search_terms(self):
        terms = self._search_terms()
        self.assertNotIn("everyone is bullish", terms)

    def test_everyone_is_bearish_not_in_search_terms(self):
        terms = self._search_terms()
        self.assertNotIn("everyone is bearish", terms)

    def test_stock_is_ripping_not_in_search_terms(self):
        terms = self._search_terms()
        self.assertNotIn("stock is ripping", terms)

    def test_stock_is_dumping_not_in_search_terms(self):
        terms = self._search_terms()
        self.assertNotIn("stock is dumping", terms)

    def test_market_feels_broken_not_in_search_terms(self):
        terms = self._search_terms()
        self.assertNotIn("market feels broken", terms)


# ---------------------------------------------------------------------------
# 2. Better search terms present
# ---------------------------------------------------------------------------

class TestBetterSearchTerms(unittest.TestCase):

    def _search_terms(self):
        return _load_profile().get("search_terms", [])

    def test_earnings_week_is_exhausting_present(self):
        self.assertIn("earnings week is exhausting", self._search_terms())

    def test_not_sure_what_changed_present(self):
        self.assertIn("not sure what changed", self._search_terms())

    def test_hard_to_separate_signal_from_noise_present(self):
        self.assertIn("hard to separate signal from noise", self._search_terms())

    def test_retail_investors_overwhelmed_present(self):
        self.assertIn("retail investors overwhelmed", self._search_terms())

    def test_investing_information_overload_present(self):
        self.assertIn("investing information overload", self._search_terms())

    def test_still_has_20_search_terms(self):
        self.assertEqual(len(self._search_terms()), 20)

    def test_candidates_generated_from_new_terms(self):
        profile = _load_profile()
        candidates = _build_candidate_queries(profile)
        # At least 20 candidates with first template (one per term)
        self.assertGreaterEqual(len(candidates), 20)
        # First candidate uses first term and first template
        self.assertIn("earnings week is exhausting", candidates[0])


# ---------------------------------------------------------------------------
# 3. "everyone is bullish/bearish" style posts → Avoid
# ---------------------------------------------------------------------------

class TestSentimentBaitScoring(unittest.TestCase):

    def test_everyone_is_bullish_scores_avoid(self):
        result = _fit("Everyone is bullish on tech stocks right now")
        self.assertEqual(result, "Avoid")

    def test_everyone_is_bearish_scores_avoid(self):
        result = _fit("Everyone is bearish on the market after today's drop")
        self.assertEqual(result, "Avoid")

    def test_fear_is_spreading_scores_avoid(self):
        result = _fit("Fear is spreading across retail investors as the market falls")
        self.assertEqual(result, "Avoid")

    def test_highest_level_since_scores_avoid(self):
        result = _fit("VIX is at its highest level since March 2020 — what comes next?")
        self.assertEqual(result, "Avoid")

    def test_avoid_overrides_noise_keyword(self):
        # "noise" is a strong fit keyword but "everyone is bullish" is avoid
        result = _fit("Everyone is bullish but I'm trying to filter out the noise")
        self.assertEqual(result, "Avoid")

    def test_avoid_overrides_retail_investor_keyword(self):
        result = _fit("Everyone is bearish and retail investors are scared")
        self.assertEqual(result, "Avoid")


# ---------------------------------------------------------------------------
# 4. "smart money" style posts → Avoid
# ---------------------------------------------------------------------------

class TestSmartMoneyScoring(unittest.TestCase):

    def test_smart_money_is_watching_scores_avoid(self):
        result = _fit("Smart money is watching this sector closely right now")
        self.assertEqual(result, "Avoid")

    def test_smart_money_with_noise_scores_avoid(self):
        # "noise" is strong fit but "smart money" is avoid
        result = _fit("Smart money sees through the noise — retail investors don't")
        self.assertEqual(result, "Avoid")

    def test_smart_money_reason_mentions_sentiment(self):
        post = _make_web_post("Smart money is watching this stock very closely")
        profile = _load_profile()
        fit = _score_fit_dynamic(post, profile)
        self.assertIn("smart money", fit["reason"].lower())


# ---------------------------------------------------------------------------
# 5. XRP / Web3 / crypto-only posts → Avoid
# ---------------------------------------------------------------------------

class TestCryptoPostScoring(unittest.TestCase):

    def test_xrp_scores_avoid(self):
        result = _fit("XRP is about to break out — smart move to accumulate now")
        self.assertEqual(result, "Avoid")

    def test_web3_scores_avoid(self):
        result = _fit("Web3 is the future of finance — retail investors are missing out")
        self.assertEqual(result, "Avoid")

    def test_memecoin_scores_avoid(self):
        result = _fit("This memecoin is going 100x — load up before launch")
        self.assertEqual(result, "Avoid")

    def test_altcoin_scores_avoid(self):
        result = _fit("Best altcoin picks for this bull run — thread below")
        self.assertEqual(result, "Avoid")

    def test_meme_coin_space_scores_avoid(self):
        result = _fit("The meme coin market is showing unusual volume today")
        self.assertEqual(result, "Avoid")

    def test_crypto_avoid_overrides_clarity_keyword(self):
        result = _fit("XRP brings clarity to cross-border payments for retail investors")
        self.assertEqual(result, "Avoid")


# ---------------------------------------------------------------------------
# 6. Promotional posts with fit keywords → Avoid (not Strong)
# ---------------------------------------------------------------------------

class TestPromotionalPostScoring(unittest.TestCase):

    def test_link_in_bio_scores_avoid(self):
        result = _fit("Cut through the market noise with our free signal service — link in bio")
        self.assertEqual(result, "Avoid")

    def test_join_my_discord_scores_avoid(self):
        result = _fit("I share clarity signals every day — join my discord for free picks")
        self.assertEqual(result, "Avoid")

    def test_free_webinar_scores_avoid(self):
        result = _fit("Learn to separate signal from noise — free webinar this Friday")
        self.assertEqual(result, "Avoid")

    def test_screenshot_this_scores_avoid(self):
        result = _fit("Screenshot this: markets are about to move — you'll thank me later")
        self.assertEqual(result, "Avoid")

    def test_paid_group_scores_avoid(self):
        result = _fit("Join my paid group — I post signals when retail investors are confused")
        self.assertEqual(result, "Avoid")

    def test_100x_scores_avoid(self):
        result = _fit("This stock could be a 100x — retail investors are sleeping on it")
        self.assertEqual(result, "Avoid")


# ---------------------------------------------------------------------------
# 7. High-quality retail overwhelm posts → Strong/Decent
# ---------------------------------------------------------------------------

class TestGoodPostsStillQualify(unittest.TestCase):

    def test_retail_overwhelm_strong_fit(self):
        scored = _score(
            "I'm completely overwhelmed by all the market noise this earnings week. "
            "Every analyst has a different take and I genuinely don't know what to believe."
        )
        self.assertIn(scored["score"], ("Strong fit", "Decent fit"))

    def test_earnings_confusion_strong_fit(self):
        scored = _score(
            "Stock moved 12% after earnings and I still can't figure out if the thesis changed. "
            "Too much information, too little clarity."
        )
        self.assertIn(scored["score"], ("Strong fit", "Decent fit"))

    def test_chasing_fomo_decent_or_strong(self):
        scored = _score(
            "Tried not to chase this stock but the FOMO got me. "
            "Need to slow down and think before I act."
        )
        self.assertIn(scored["score"], ("Strong fit", "Decent fit"))

    def test_signal_noise_confusion_strong(self):
        scored = _score(
            "Hard to separate signal from noise when every piece of financial media "
            "is telling me something different."
        )
        self.assertIn(scored["score"], ("Strong fit", "Decent fit"))

    def test_investing_thesis_change_decent_or_strong(self):
        scored = _score(
            "My investing thesis changed after this earnings call but I'm not sure if "
            "that's the right reaction or just an emotional response."
        )
        self.assertIn(scored["score"], ("Strong fit", "Decent fit"))

    def test_high_quality_post_is_not_avoid(self):
        scored = _score(
            "Retail investors are overwhelmed by data but starved for actual insight. "
            "More dashboards is not the answer."
        )
        self.assertNotEqual(scored["score"], "Avoid")

    def test_fresh_good_post_is_medium_opportunity(self):
        scored = _score(
            "Completely overwhelmed by market noise. Information overload is real.",
            age_hours=6
        )
        self.assertEqual(scored["opportunity"], "Medium opportunity")


# ---------------------------------------------------------------------------
# 8. Avoid keywords override strong keyword matches
# ---------------------------------------------------------------------------

class TestAvoidOverridesStrong(unittest.TestCase):

    def test_moon_with_retail_investor_is_avoid(self):
        result = _fit("Retail investor? Don't miss this — going to the moon 🚀")
        self.assertEqual(result, "Avoid")

    def test_pump_with_noise_is_avoid(self):
        result = _fit("Ignore the noise — this is a legitimate pump, not hype")
        self.assertEqual(result, "Avoid")

    def test_guaranteed_with_clarity_is_avoid(self):
        result = _fit("Guaranteed clarity on where the market is headed — my signals are always right")
        self.assertEqual(result, "Avoid")

    def test_gem_with_thesis_is_avoid(self):
        result = _fit("My investing thesis: this altcoin is a hidden gem — 100x incoming")
        self.assertEqual(result, "Avoid")


# ---------------------------------------------------------------------------
# 9. Weak TA keywords block strong promotions
# ---------------------------------------------------------------------------

class TestWeakTABlocking(unittest.TestCase):

    def test_rsi_with_clarity_is_weak(self):
        result = _fit("RSI is giving a clarity signal — buy the dip")
        self.assertEqual(result, "Weak fit")

    def test_macd_with_signal_is_weak(self):
        result = _fit("MACD signal just crossed — great entry point for retail investors")
        self.assertEqual(result, "Weak fit")

    def test_technical_analysis_with_noise_is_weak(self):
        result = _fit("Technical analysis cuts through the noise — here's my chart setup")
        self.assertEqual(result, "Weak fit")


# ---------------------------------------------------------------------------
# 10. Mock mode unchanged
# ---------------------------------------------------------------------------

class TestMockModeUnchangedM47(unittest.TestCase):

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


# ---------------------------------------------------------------------------
# 11. Query rotation unchanged
# ---------------------------------------------------------------------------

class TestQueryRotationUnchangedM47(unittest.TestCase):

    def test_candidates_generated_from_profile(self):
        profile = _load_profile()
        candidates = _build_candidate_queries(profile)
        self.assertGreater(len(candidates), 0)

    def test_first_template_fills_first(self):
        profile = _load_profile()
        candidates = _build_candidate_queries(profile)
        # First 20 candidates should all use the first template
        first_template = profile["query_templates"][0]
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
                self.assertNotIn(term, c, f"Removed term '{term}' still appears in candidates")


if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(__import__("__main__"))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
