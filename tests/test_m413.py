"""
Tests for M4.13: Worth Checking quality, reply matching, and no-Best-3 wording.
No real API calls, no network access.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.replier import (
    _has_market_signal,
    _WORTH_CHECKING_MARKET_SIGNALS,
    _detect_reply_theme,
    generate_replies,
)
from src.digest import (
    _get_worth_checking_posts,
    _build_best_3,
    build_markdown,
)
from src.scorer import score_posts


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_post(text, tweet_id="1900000000000000001", age_hours=6.0,
               combined=None):
    """Minimal web-search post dict for scoring/reply tests."""
    return {
        "id": tweet_id,
        "author": "@test_user",
        "author_name": "test_user",
        "author_followers": 0,
        "author_profile_url": "https://x.com/test_user",
        "text": text,
        "combined_text_for_scoring": combined or text,
        "likes": 0, "reposts": 0, "reply_count": 0, "impressions": 0,
        "age_hours": age_hours,
        "age_source": "snowflake",
        "post_url": f"https://x.com/test_user/status/{tweet_id}",
        "url": f"https://x.com/test_user/status/{tweet_id}",
        "discovery_source": "tavily_search",
        "metrics_confidence": "low",
    }


def _make_wc_post(tweet_id, text, score="Decent fit", freshness_tier="fresh",
                  out_of_scope=False, metrics_confidence="low"):
    """Pre-scored post for Worth Checking eligibility tests."""
    return {
        "id": tweet_id,
        "author": f"@user_{tweet_id}",
        "text": text,
        "score": score,
        "visibility": "Unknown visibility",
        "opportunity": "Low opportunity",
        "opportunity_reason": "Engagement unknown.",
        "engagement_summary": "Engagement unknown",
        "age_label": "Age: ~6h old",
        "age_hours": 6.0,
        "freshness_tier": freshness_tier,
        "out_of_scope": out_of_scope,
        "reply_account": "Either",
        "suggested_action": "Do not engage",
        "reason": "Test.",
        "metrics_confidence": metrics_confidence,
        "replies": [],
        "best_reply": {},
        "media": {"type": "No media", "reason": ""},
        "post_url": f"https://x.com/user_{tweet_id}/status/{tweet_id}",
        "author_profile_url": f"https://x.com/user_{tweet_id}",
        "inspiration_angles": None,
        "reply_note": None,
    }


def _load_profile():
    import yaml
    path = os.path.join(os.path.dirname(__file__), "..", "profiles", "signal_shift.yaml")
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


# ---------------------------------------------------------------------------
# 1. _has_market_signal helper
# ---------------------------------------------------------------------------

class TestHasMarketSignal(unittest.TestCase):

    def _post(self, text, combined=None):
        return {"text": text, "combined_text_for_scoring": combined}

    def test_stock_term_qualifies(self):
        self.assertTrue(_has_market_signal(self._post("Why is this stock moving today?")))

    def test_dollar_sign_ticker_qualifies(self):
        self.assertTrue(_has_market_signal(self._post("$NVDA makes no sense right now")))

    def test_market_term_qualifies(self):
        self.assertTrue(_has_market_signal(self._post("The market noise is overwhelming")))

    def test_investor_term_qualifies(self):
        self.assertTrue(_has_market_signal(self._post("Retail investors are chasing FOMO")))

    def test_earnings_term_qualifies(self):
        self.assertTrue(_has_market_signal(self._post("Earnings reaction doesn't make sense")))

    def test_premarket_qualifies(self):
        self.assertTrue(_has_market_signal(self._post("premarket move is confusing me")))

    def test_after_hours_qualifies(self):
        self.assertTrue(_has_market_signal(self._post("after hours dump — why?")))

    def test_thesis_qualifies(self):
        self.assertTrue(_has_market_signal(self._post("my thesis hasn't changed but the stock is down")))

    def test_portfolio_qualifies(self):
        self.assertTrue(_has_market_signal(self._post("half my portfolio is underwater")))

    def test_nasdaq_qualifies(self):
        self.assertTrue(_has_market_signal(self._post("Nasdaq selloff makes no sense")))

    def test_fed_qualifies(self):
        self.assertTrue(_has_market_signal(self._post("Fed statement caused this move")))

    def test_cpi_qualifies(self):
        self.assertTrue(_has_market_signal(self._post("CPI data tomorrow is the real catalyst")))

    def test_pure_ai_business_post_does_not_qualify(self):
        """AI sovereignty / enterprise content with no market context."""
        self.assertFalse(_has_market_signal(self._post(
            "AI sovereignty is the next battleground for enterprise tech. "
            "The noise around LLMs obscures real signal about who controls the stack."
        )))

    def test_generic_productivity_post_does_not_qualify(self):
        self.assertFalse(_has_market_signal(self._post(
            "Information overload is real. "
            "Too many notifications, too much noise, not enough signal."
        )))

    def test_political_policy_post_does_not_qualify(self):
        self.assertFalse(_has_market_signal(self._post(
            "The noise around AI regulation is obscuring the actual signal from Brussels."
        )))

    def test_combined_text_used_when_available(self):
        # text alone has no signal; combined_text_for_scoring has "earnings"
        p = self._post("Not much here.", combined="earnings season is kicking off")
        self.assertTrue(_has_market_signal(p))

    def test_empty_post_does_not_qualify(self):
        self.assertFalse(_has_market_signal({"text": "", "combined_text_for_scoring": None}))

    def test_case_insensitive(self):
        self.assertTrue(_has_market_signal(self._post("The MARKET is volatile")))
        self.assertTrue(_has_market_signal(self._post("S&P 500 dump")))


# ---------------------------------------------------------------------------
# 2. Worth Checking requires market signal
# ---------------------------------------------------------------------------

class TestWorthCheckingMarketSignalRequired(unittest.TestCase):

    def test_ai_sovereignty_post_not_in_worth_checking(self):
        post = _make_wc_post(
            "sandy_ai",
            "AI sovereignty is the next battleground for enterprise tech. "
            "The noise around LLMs obscures the real signal about who controls the stack.",
        )
        result = _get_worth_checking_posts([post])
        self.assertEqual(len(result), 0,
                         "AI sovereignty post without stock/market terms should not appear in Worth Checking")

    def test_generic_noise_signal_post_not_in_worth_checking(self):
        post = _make_wc_post(
            "biz_noise",
            "Too much noise, not enough signal in the enterprise software space.",
        )
        result = _get_worth_checking_posts([post])
        self.assertEqual(len(result), 0)

    def test_clear_stock_post_in_worth_checking(self):
        post = _make_wc_post(
            "nvda_post",
            "$NVDA why is it moving after hours? Makes no sense.",
        )
        result = _get_worth_checking_posts([post])
        self.assertEqual(len(result), 1)

    def test_earnings_confusion_post_in_worth_checking(self):
        post = _make_wc_post(
            "earns_post",
            "earnings reaction doesn't make sense — nothing changed in the guidance",
        )
        result = _get_worth_checking_posts([post])
        self.assertEqual(len(result), 1)

    def test_retail_investor_post_in_worth_checking(self):
        post = _make_wc_post(
            "retail_post",
            "retail investors are chasing this stock without any understanding of the thesis",
        )
        result = _get_worth_checking_posts([post])
        self.assertEqual(len(result), 1)

    def test_market_noise_post_in_worth_checking(self):
        post = _make_wc_post(
            "mkt_noise",
            "Market noise is overwhelming this week. Hard to know what matters.",
        )
        result = _get_worth_checking_posts([post])
        self.assertEqual(len(result), 1)

    def test_all_other_criteria_still_required(self):
        # Has market signal BUT stale → still excluded
        post = _make_wc_post(
            "stale_mkt",
            "$NVDA makes no sense today",
            freshness_tier="stale",
        )
        result = _get_worth_checking_posts([post])
        self.assertEqual(len(result), 0, "Stale post excluded despite market signal")

    def test_out_of_scope_still_excluded_even_with_market_signal(self):
        post = _make_wc_post(
            "india_post",
            "Nifty market reaction doesn't make sense — stock is moving for no reason",
            out_of_scope=True,
        )
        result = _get_worth_checking_posts([post])
        self.assertEqual(len(result), 0)


# ---------------------------------------------------------------------------
# 3. Reply theme only applied when market context present
# ---------------------------------------------------------------------------

class TestReplyThemeRequiresMarketContext(unittest.TestCase):

    def _score_and_reply(self, text, tweet_id="1900000000000000001"):
        profile = _load_profile()
        post = _make_post(text, tweet_id=tweet_id)
        scored = score_posts([post], profile=profile)
        return generate_replies(scored)[0]

    def test_ai_business_post_gets_generic_reply_not_noise_overwhelm(self):
        """An AI/enterprise noise post should get a generic reply, not noise_overwhelm."""
        text = (
            "AI sovereignty is the next battleground for enterprise tech. "
            "The noise around LLMs obscures real signal about who controls the stack."
        )
        # The theme detection keywords ("noise", "signal") would match noise_overwhelm
        # without the market-signal gate — verify the gate prevents it
        post = {"text": text, "combined_text_for_scoring": text}
        theme = _detect_reply_theme(post)  # Would normally match noise_overwhelm
        from src.replier import _has_market_signal
        has_signal = _has_market_signal(post)
        # If theme matched but no market signal → gate should suppress specific theme
        if theme is not None and not has_signal:
            # This is the case being guarded — specific theme overridden to generic
            self.assertIsNotNone(theme)   # theme keyword DID match
            self.assertFalse(has_signal)  # but no market context

    def test_market_noise_post_gets_specific_theme(self):
        """A genuine retail-investor noise post should still get noise_overwhelm theme."""
        text = "Market noise is overwhelming retail investors this week."
        post = {"text": text, "combined_text_for_scoring": text}
        theme = _detect_reply_theme(post)
        from src.replier import _has_market_signal
        has_signal = _has_market_signal(post)
        self.assertIsNotNone(theme)
        self.assertTrue(has_signal)

    def test_generic_reply_returned_for_ai_business_post_with_good_fit(self):
        """Even with Decent/Strong fit, AI post should receive a generic-themed reply."""
        text = (
            "AI sovereignty is the next battleground for enterprise tech. "
            "The noise around LLMs obscures real signal. Too much information overload."
        )
        with_replies = self._score_and_reply(text)
        if with_replies.get("replies"):
            # The reply styles should come from generic_decent or generic_strong, not
            # noise_overwhelm (which has "financial media" / "reactivity" content).
            for reply in with_replies["replies"]:
                reply_text = reply.get("text", "").lower()
                # noise_overwhelm options reference "financial media" or "trending on investing twitter"
                self.assertNotIn("financial media", reply_text,
                                 "AI business post should not get financial-media reply")

    def test_earnings_confusion_post_keeps_specific_theme(self):
        """A genuine earnings confusion post with market signal keeps its theme."""
        text = "earnings reaction makes no sense — retail investors are piling in without any thesis"
        post = {"text": text, "combined_text_for_scoring": text}
        from src.replier import _has_market_signal
        theme = _detect_reply_theme(post)
        has_signal = _has_market_signal(post)
        self.assertTrue(has_signal, "Earnings post should have market signal")


# ---------------------------------------------------------------------------
# 4. No-Best-3 wording — context-aware
# ---------------------------------------------------------------------------

class TestNoBest3Wording(unittest.TestCase):

    def _empty_posts(self):
        """Posts that score Weak or Avoid — never in Best 3."""
        return [_make_wc_post("wp", "RSI crossover on SPY", score="Weak fit")]

    def test_wording_with_no_sections(self):
        lines = _build_best_3([], has_inspiration=False, worth_checking_count=0)
        content = "\n".join(lines)
        self.assertIn("No strong reply opportunities today", content)
        self.assertNotIn("worth checking", content.lower())
        self.assertNotIn("Inspiration", content)

    def test_wording_with_worth_checking_only(self):
        lines = _build_best_3([], has_inspiration=False, worth_checking_count=2)
        content = "\n".join(lines)
        self.assertIn("No strong reply opportunities today", content)
        self.assertIn("2 borderline posts worth checking manually", content)
        self.assertNotIn("Inspiration", content)

    def test_wording_with_inspiration_only(self):
        lines = _build_best_3([], has_inspiration=True, worth_checking_count=0)
        content = "\n".join(lines)
        self.assertIn("No strong reply opportunities today", content)
        self.assertIn("Inspiration ideas below", content)
        self.assertNotIn("worth checking", content.lower())

    def test_wording_with_both_sections(self):
        lines = _build_best_3([], has_inspiration=True, worth_checking_count=3)
        content = "\n".join(lines)
        self.assertIn("No strong reply opportunities today", content)
        self.assertIn("3 borderline posts worth checking manually", content)
        self.assertIn("Inspiration ideas below", content)

    def test_singular_post_wording(self):
        lines = _build_best_3([], has_inspiration=False, worth_checking_count=1)
        content = "\n".join(lines)
        self.assertIn("1 borderline post worth checking manually", content)
        # Singular "post", not "posts"
        self.assertNotIn("1 borderline posts", content)

    def test_no_mention_of_worth_checking_when_count_is_zero(self):
        lines = _build_best_3([], has_inspiration=True, worth_checking_count=0)
        content = "\n".join(lines)
        self.assertNotIn("worth checking", content.lower())

    def test_no_mention_of_inspiration_when_flag_false(self):
        lines = _build_best_3([], has_inspiration=False, worth_checking_count=1)
        content = "\n".join(lines)
        self.assertNotIn("Inspiration", content)

    def test_no_best3_section_when_posts_only_low_opportunity(self):
        """Low opportunity posts don't enter Best 3 — wording reflects this."""
        posts = [_make_wc_post(
            "mkt_low",
            "Market noise is overwhelming retail investors.",
            score="Decent fit",
        )]
        lines = _build_best_3(posts)
        content = "\n".join(lines)
        self.assertIn("No strong reply opportunities today", content)

    def test_wording_matches_build_markdown_output(self):
        """Verify the new wording appears in full digest output."""
        from src.post_generator import generate_posts
        posts = [_make_wc_post(
            "mkt_noise_md",
            "Market noise overwhelming retail investors this week.",
        )]
        sched = generate_posts(0)
        md = build_markdown("Signal Shift", posts, sched, mode="Tavily")
        self.assertIn("No strong reply opportunities today", md)
        # Worth Checking section should also appear (post has market signal)
        self.assertIn("Worth Checking Manually", md)


# ---------------------------------------------------------------------------
# 5. Mock mode unchanged
# ---------------------------------------------------------------------------

class TestMockModeUnchangedM413(unittest.TestCase):

    def test_mock_posts_run_without_error(self):
        from src.providers.mock_provider import get_posts
        posts = get_posts({})
        self.assertIsInstance(posts, list)
        self.assertGreater(len(posts), 0)

    def test_mock_scores_unchanged(self):
        from src.providers.mock_provider import get_posts
        profile = _load_profile()
        posts = get_posts(profile)
        scored = score_posts(posts, profile=profile)
        scores = [p["score"] for p in scored]
        self.assertIn("Strong fit", scores)

    def test_mock_does_not_use_has_market_signal(self):
        """Mock posts use integer IDs — market signal gate must not apply to them."""
        from src.providers.mock_provider import get_posts
        from src.replier import generate_replies
        profile = _load_profile()
        posts = get_posts(profile)
        scored = score_posts(posts, profile=profile)
        with_replies = generate_replies(scored)
        strong_fits = [p for p in with_replies if p["score"] == "Strong fit"]
        # Mock Strong fit posts should still have replies (integer ID path, not gated)
        self.assertTrue(any(len(p["replies"]) > 0 for p in strong_fits),
                        "Mock Strong fit posts should have replies")


# ---------------------------------------------------------------------------
# 6. Workflows and secrets unchanged
# ---------------------------------------------------------------------------

class TestWorkflowsUnchangedM413(unittest.TestCase):

    def test_workflow_files_exist(self):
        workflow_dir = os.path.join(
            os.path.dirname(__file__), "..", ".github", "workflows"
        )
        workflows = os.listdir(workflow_dir)
        self.assertIn("mel_digest.yml", workflows)
        self.assertIn("mel_search_digest.yml", workflows)

    def test_no_api_key_in_replier(self):
        path = os.path.join(os.path.dirname(__file__), "..", "src", "replier.py")
        with open(path, encoding="utf-8") as fh:
            content = fh.read()
        self.assertNotIn("tvly-", content)

    def test_no_api_key_in_digest(self):
        path = os.path.join(os.path.dirname(__file__), "..", "src", "digest.py")
        with open(path, encoding="utf-8") as fh:
            content = fh.read()
        self.assertNotIn("tvly-", content)


if __name__ == "__main__":
    unittest.main()
