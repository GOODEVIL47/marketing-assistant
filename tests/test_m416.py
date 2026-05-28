"""
Tests for M4.16: Contextual Reply Quality + Better Best 3 Gate.

Covers:
- _is_broadcast_post() detection
- Broadcast post downgrade to Low opportunity in score_posts()
- _extract_post_context() — ticker, pct, driver extraction
- _build_contextual_reply() — context-aware reply generation
- Context injection in generate_replies()
- Mock mode unchanged

No real API calls or network access.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.scorer import _is_broadcast_post, score_posts
from src.replier import (
    _build_contextual_reply,
    _extract_post_context,
    generate_replies,
)


# ---------------------------------------------------------------------------
# Post fixtures for the three manual-review examples
# ---------------------------------------------------------------------------

def _base_post(**overrides):
    post = {
        "id": "1900000000000001001",
        "author": "@test",
        "author_name": "test",
        "author_followers": 0,
        "author_profile_url": "https://x.com/test",
        "likes": 0, "reposts": 0, "reply_count": 0, "impressions": 0,
        "age_hours": 6,
        "age_source": "snowflake",
        "post_url": "https://x.com/test/status/1900000000000001001",
        "url": "https://x.com/test/status/1900000000000001001",
        "discovery_source": "tavily_search",
        "metrics_confidence": "low",
    }
    post.update(overrides)
    return post


# Example A — broadcast NVDA research post (should be downgraded, not Best 3)
_NVDA_BROADCAST_TEXT = (
    "NVIDIA announced a new Taiwan Taipei headquarters expansion. "
    "The company opens its latest AI data center campus as part of GTC 2026. "
    "Retail investors tracking $NVDA noise around the AI expansion news. "
    "Taiwan semiconductor partnership confirmed."
)

def _nvda_broadcast_post():
    return _base_post(
        id="1900000000000001001",
        text=_NVDA_BROADCAST_TEXT,
        combined_text_for_scoring=_NVDA_BROADCAST_TEXT,
    )


# Example B — PhotonCap LPTH reaction post (should be reply opportunity with
#              contextual reply mentioning $LPTH, +8.4%, onshoring/defense)
_LPTH_TEXT = (
    "Nasdaq 100 was down today, $LPTH up +8.4%, near 52-week highs. "
    "Loss-making IR optics company. Market may be buying scarce U.S.-based "
    "optical capacity in a defense supply chain moving away from Chinese germanium. "
    "Onshoring premium or overpriced story stock?"
)

def _lpth_post():
    return _base_post(
        id="1900000000000001002",
        text=_LPTH_TEXT,
        combined_text_for_scoring=_LPTH_TEXT,
    )


# Example C — XFAB structural thesis post (should get contextual reply with
#              photonics / CHIPS Act / $XFAB / $NVDA)
_XFAB_TEXT = (
    "$XFAB discussed by Reuters and Bloomberg. Structural thesis: "
    "800 VDC power semis with $NVDA exposure. $NOK photonics evaluations "
    "ongoing. CHIPS Act semiconductor sovereignty implications. "
    "Thesis unchanged despite stock movement."
)

def _xfab_post():
    return _base_post(
        id="1900000000000001003",
        text=_XFAB_TEXT,
        combined_text_for_scoring=_XFAB_TEXT,
    )


def _minimal_profile():
    return {
        "fit_keywords": {
            "strong": ["noise", "clarity", "signal", "overload", "overwhelmed",
                       "thesis", "retail investor", "confused", "chasing",
                       "story stock", "overpriced"],
            "decent": ["investor", "investing", "market takes", "stock reaction",
                       "volatility", "framework"],
            "weak": ["RSI", "MACD", "day trading", "technical analysis"],
            "avoid": ["get rich quick", "100x", "moon", "XRP"],
            "market_context_required": ["stock", "market", "investing", "investor",
                                        "earnings", "$", "nasdaq"],
            "us_scope_market": ["$", "earnings", "nasdaq", "s&p", "fed",
                                "premarket", "after hours", "us stocks"],
            "out_of_scope_market": [],
            "off_topic": [],
        }
    }


# ---------------------------------------------------------------------------
# 1. _is_broadcast_post() — unit tests
# ---------------------------------------------------------------------------

class TestBroadcastDetection(unittest.TestCase):

    def test_announcement_post_without_hook_is_broadcast(self):
        text = (
            "NVIDIA announced new Taipei AI headquarters. "
            "Company opens its latest data center. "
            "Taiwan semiconductor partnership confirmed."
        )
        self.assertTrue(_is_broadcast_post(text))

    def test_announcement_with_question_mark_is_not_broadcast(self):
        text = (
            "NVIDIA announced Taipei HQ expansion. "
            "Does this change the $NVDA thesis for retail investors?"
        )
        self.assertFalse(_is_broadcast_post(text))

    def test_announcement_with_why_is_not_broadcast(self):
        text = "NVIDIA opens Taipei headquarters. Why is the stock down on this news?"
        self.assertFalse(_is_broadcast_post(text))

    def test_announcement_with_confused_is_not_broadcast(self):
        text = "NVIDIA announces new HQ. Retail investors confused by the reaction."
        self.assertFalse(_is_broadcast_post(text))

    def test_thread_notation_without_hook_is_broadcast(self):
        text = "1/5 NVIDIA AI data center expansion in Taiwan. GTC 2026 highlights."
        self.assertTrue(_is_broadcast_post(text))

    def test_thread_notation_with_question_is_not_broadcast(self):
        text = "1/5 NVIDIA AI expansion. What does this mean for the thesis?"
        self.assertFalse(_is_broadcast_post(text))

    def test_personal_reaction_post_is_not_broadcast(self):
        text = (
            "$LPTH up +8.4% while Nasdaq 100 is down. "
            "Onshoring premium or overpriced story stock?"
        )
        self.assertFalse(_is_broadcast_post(text))

    def test_thesis_unchanged_reaction_is_not_broadcast(self):
        text = (
            "$NVDA sold off but thesis unchanged. "
            "Nothing changed fundamentally — market is noise."
        )
        self.assertFalse(_is_broadcast_post(text))

    def test_story_stock_mention_prevents_broadcast(self):
        text = (
            "NVIDIA announced expansion. $LPTH story stock move. "
            "Retail investors watching supply chain."
        )
        self.assertFalse(_is_broadcast_post(text))

    def test_generic_investor_post_without_announcement_is_not_broadcast(self):
        text = (
            "Retail investors overwhelmed by market noise this week. "
            "Hard to separate signal from signal."
        )
        self.assertFalse(_is_broadcast_post(text))

    def test_empty_text_is_not_broadcast(self):
        self.assertFalse(_is_broadcast_post(""))

    def test_per_reuters_triggers_broadcast(self):
        text = "Per Reuters, $NVDA opens new facility. No major thesis change noted."
        self.assertTrue(_is_broadcast_post(text))

    def test_per_reuters_with_confusion_is_not_broadcast(self):
        text = "Per Reuters, $NVDA opens new facility. Why is the stock confused here?"
        self.assertFalse(_is_broadcast_post(text))


# ---------------------------------------------------------------------------
# 2. Broadcast opportunity downgrade in score_posts()
# ---------------------------------------------------------------------------

class TestBroadcastDowngrade(unittest.TestCase):

    def test_broadcast_post_downgraded_to_low_opportunity(self):
        # Example A: NVDA broadcast announcement — should be downgraded
        post = _nvda_broadcast_post()
        profile = _minimal_profile()
        scored = score_posts([post], profile=profile)
        s = scored[0]
        # Must be Strong or Decent fit (has "retail investor" + "noise" + "$NVDA")
        self.assertIn(s["score"], ("Strong fit", "Decent fit"),
                      "Broadcast post should score well on fit")
        self.assertEqual(
            s["opportunity"], "Low opportunity",
            f"Broadcast post should be downgraded to Low. Got: {s['opportunity']}"
        )
        self.assertIn("broadcast", s["opportunity_reason"].lower())

    def test_broadcast_downgrade_reason_mentions_discussion_hook(self):
        post = _nvda_broadcast_post()
        scored = score_posts([post], profile=_minimal_profile())
        self.assertIn("broadcast", scored[0]["opportunity_reason"].lower())

    def test_reaction_post_not_downgraded(self):
        # Example B: LPTH reaction post — should stay at Medium
        post = _lpth_post()
        profile = _minimal_profile()
        scored = score_posts([post], profile=profile)
        s = scored[0]
        self.assertNotEqual(
            s["opportunity"], "Low opportunity",
            "LPTH reaction post should not be downgraded as broadcast"
        )

    def test_xfab_thesis_post_not_downgraded(self):
        # Example C: XFAB structural thesis post — not a broadcast
        post = _xfab_post()
        scored = score_posts([post], profile=_minimal_profile())
        s = scored[0]
        # "thesis unchanged" in text → discussion hook → not broadcast
        self.assertNotEqual(
            s["opportunity"], "Low opportunity",
            "XFAB thesis post should not be downgraded as broadcast"
        )

    def test_mock_posts_unaffected_by_broadcast_detection(self):
        # Mock posts use integer IDs — never routed through dynamic scoring
        from mock_data.posts import MOCK_POSTS
        scored = score_posts(MOCK_POSTS)
        self.assertEqual(scored[0]["score"], "Strong fit")
        self.assertEqual(scored[6]["score"], "Avoid")

    def test_broadcast_check_only_applies_to_web_search_posts(self):
        # A post with metrics_confidence != "low" is not a web-search post —
        # broadcast check should not apply (it only fires at Unknown visibility).
        post = _nvda_broadcast_post()
        post["metrics_confidence"] = "high"
        post["likes"] = 100
        post["reply_count"] = 20
        scored = score_posts([post], profile=_minimal_profile())
        # With real engagement, opportunity should be High/Medium, not Low from broadcast
        self.assertNotEqual(
            scored[0]["opportunity"], "Low opportunity",
            "Broadcast check should not downgrade posts with real engagement metrics"
        )


# ---------------------------------------------------------------------------
# 3. _extract_post_context() — unit tests
# ---------------------------------------------------------------------------

class TestExtractPostContext(unittest.TestCase):

    def test_extracts_tickers(self):
        post = _lpth_post()
        ctx = _extract_post_context(post)
        self.assertIn("$LPTH", ctx["tickers"])

    def test_extracts_multiple_tickers(self):
        post = _xfab_post()
        ctx = _extract_post_context(post)
        self.assertIn("$XFAB", ctx["tickers"])
        self.assertIn("$NVDA", ctx["tickers"])

    def test_extracts_pct_change(self):
        post = _lpth_post()
        ctx = _extract_post_context(post)
        self.assertTrue(
            any("8.4" in p for p in ctx["pct_changes"]),
            f"Expected +8.4% in pct_changes, got {ctx['pct_changes']}"
        )

    def test_extracts_driver_onshoring(self):
        post = _lpth_post()
        ctx = _extract_post_context(post)
        self.assertIn("onshoring", ctx["drivers"])

    def test_extracts_driver_defense(self):
        post = _lpth_post()
        ctx = _extract_post_context(post)
        self.assertIn("defense", ctx["drivers"])

    def test_extracts_driver_photonics(self):
        post = _xfab_post()
        ctx = _extract_post_context(post)
        self.assertIn("photonics", ctx["drivers"])

    def test_extracts_driver_chips_act(self):
        post = _xfab_post()
        ctx = _extract_post_context(post)
        self.assertIn("chips act", ctx["drivers"])

    def test_no_tickers_for_generic_post(self):
        post = _base_post(
            id="1900000000000001099",
            text="Retail investors overwhelmed by market noise this week.",
            combined_text_for_scoring="Retail investors overwhelmed by market noise.",
        )
        ctx = _extract_post_context(post)
        self.assertEqual(ctx["tickers"], [])

    def test_uses_combined_text_for_scoring(self):
        # combined_text_for_scoring has the ticker; display text does not
        post = _base_post(
            id="1900000000000001098",
            text="Stock moved a lot today for some reason.",
            combined_text_for_scoring="Stock moved. $LPTH up +8.4% on defense supply chain.",
        )
        ctx = _extract_post_context(post)
        self.assertIn("$LPTH", ctx["tickers"])
        self.assertIn("defense", ctx["drivers"])

    def test_caps_tickers_at_three(self):
        post = _base_post(
            id="1900000000000001097",
            text="$NVDA $TSLA $AAPL $MSFT $GOOG all moving today.",
            combined_text_for_scoring="$NVDA $TSLA $AAPL $MSFT $GOOG all moving today.",
        )
        ctx = _extract_post_context(post)
        self.assertLessEqual(len(ctx["tickers"]), 3)


# ---------------------------------------------------------------------------
# 4. _build_contextual_reply() — unit tests
# ---------------------------------------------------------------------------

class TestBuildContextualReply(unittest.TestCase):

    def test_returns_none_for_empty_context(self):
        ctx = {"tickers": [], "pct_changes": [], "drivers": []}
        self.assertIsNone(_build_contextual_reply(ctx))

    def test_returns_none_for_no_tickers(self):
        ctx = {"tickers": [], "pct_changes": ["+8.4%"], "drivers": ["onshoring"]}
        self.assertIsNone(_build_contextual_reply(ctx))

    def test_reply_mentions_ticker(self):
        ctx = {"tickers": ["$LPTH"], "pct_changes": ["+8.4%"], "drivers": ["onshoring"]}
        reply = _build_contextual_reply(ctx)
        self.assertIsNotNone(reply)
        self.assertIn("$LPTH", reply)

    def test_reply_mentions_pct_change(self):
        ctx = {"tickers": ["$LPTH"], "pct_changes": ["+8.4%"], "drivers": ["onshoring"]}
        reply = _build_contextual_reply(ctx)
        self.assertIn("8.4", reply)

    def test_reply_mentions_driver(self):
        ctx = {"tickers": ["$LPTH"], "pct_changes": ["+8.4%"], "drivers": ["onshoring"]}
        reply = _build_contextual_reply(ctx)
        self.assertIn("onshoring", reply)

    def test_reply_with_tickers_and_drivers_only(self):
        ctx = {"tickers": ["$XFAB"], "pct_changes": [], "drivers": ["photonics"]}
        reply = _build_contextual_reply(ctx)
        self.assertIsNotNone(reply)
        self.assertIn("$XFAB", reply)
        self.assertIn("photonics", reply)

    def test_reply_with_tickers_and_pct_only(self):
        ctx = {"tickers": ["$NVDA"], "pct_changes": ["-3.2%"], "drivers": []}
        reply = _build_contextual_reply(ctx)
        self.assertIsNotNone(reply)
        self.assertIn("$NVDA", reply)
        self.assertIn("3.2", reply)

    def test_reply_with_tickers_only(self):
        ctx = {"tickers": ["$AMD"], "pct_changes": [], "drivers": []}
        reply = _build_contextual_reply(ctx)
        self.assertIsNotNone(reply)
        self.assertIn("$AMD", reply)

    def test_reply_uses_up_to_two_tickers(self):
        ctx = {"tickers": ["$XFAB", "$NVDA", "$NOK"], "pct_changes": [], "drivers": ["photonics"]}
        reply = _build_contextual_reply(ctx)
        # Should mention at least the first ticker
        self.assertIn("$XFAB", reply)

    def test_reply_is_string(self):
        ctx = {"tickers": ["$LPTH"], "pct_changes": ["+8.4%"], "drivers": ["defense"]}
        reply = _build_contextual_reply(ctx)
        self.assertIsInstance(reply, str)

    def test_reply_does_not_contain_financial_advice(self):
        ctx = {"tickers": ["$LPTH"], "pct_changes": ["+8.4%"], "drivers": ["onshoring"]}
        reply = _build_contextual_reply(ctx)
        forbidden = ["buy", "sell", "hold", "invest", "price target", "recommend"]
        for word in forbidden:
            self.assertNotIn(word, reply.lower(), f"Reply contains '{word}'")


# ---------------------------------------------------------------------------
# 5. Context injection in generate_replies()
# ---------------------------------------------------------------------------

class TestGenerateRepliesContextInjection(unittest.TestCase):

    def _score_and_reply(self, post):
        profile = _minimal_profile()
        scored = score_posts([post], profile=profile)
        return generate_replies(scored)[0]

    def test_lpth_reply_mentions_ticker_or_driver(self):
        result = self._score_and_reply(_lpth_post())
        all_texts = " ".join(opt["text"] for opt in result.get("replies", []))
        has_context = (
            "$LPTH" in all_texts
            or "onshoring" in all_texts
            or "defense" in all_texts
            or "8.4" in all_texts
            or "germanium" in all_texts
        )
        self.assertTrue(
            has_context,
            f"Expected a contextual reply for LPTH post. Got: {all_texts[:300]}"
        )

    def test_xfab_reply_mentions_ticker_or_driver(self):
        result = self._score_and_reply(_xfab_post())
        all_texts = " ".join(opt["text"] for opt in result.get("replies", []))
        has_context = (
            "$XFAB" in all_texts
            or "photonics" in all_texts
            or "chips act" in all_texts.lower()
            or "power semis" in all_texts.lower()
        )
        self.assertTrue(
            has_context,
            f"Expected a contextual reply for XFAB post. Got: {all_texts[:300]}"
        )

    def test_generic_post_no_context_injection(self):
        # A broad post with no tickers should not have context injection
        post = _base_post(
            id="1900000000000001099",
            text="Retail investors overwhelmed by market noise this week.",
            combined_text_for_scoring="Retail investors overwhelmed by market noise.",
        )
        result = self._score_and_reply(post)
        all_texts = " ".join(opt["text"] for opt in result.get("replies", []))
        # No C — Context-aware style option should be present
        styles = [opt.get("style", "") for opt in result.get("replies", [])]
        self.assertNotIn(
            "C — Context-aware", styles,
            "Generic post should not get context injection"
        )

    def test_context_aware_option_replaces_c(self):
        result = self._score_and_reply(_lpth_post())
        styles = [opt.get("style", "") for opt in result.get("replies", [])]
        self.assertIn(
            "C — Context-aware", styles,
            f"Expected C — Context-aware option for LPTH post. Styles: {styles}"
        )

    def test_mock_posts_replies_unchanged(self):
        from mock_data.posts import MOCK_POSTS
        scored = score_posts(MOCK_POSTS)
        with_replies = generate_replies(scored)
        # Mock post 1 (integer ID) should have the hardcoded replies unchanged
        post1 = next(p for p in with_replies if p["id"] == 1)
        self.assertIn("earnings week", post1["replies"][0]["text"].lower())

    def test_reply_count_unchanged_with_context_injection(self):
        # Context injection replaces C, not adds; total options count stays the same
        result = self._score_and_reply(_lpth_post())
        if result.get("replies"):
            self.assertEqual(len(result["replies"]), 3)

    def test_broadcast_post_has_no_reply_in_best3_action(self):
        # Broadcast post downgraded to Low → suggested_action = Save for inspiration
        post = _nvda_broadcast_post()
        scored = score_posts([post], profile=_minimal_profile())
        self.assertEqual(scored[0]["suggested_action"], "Save for inspiration")


# ---------------------------------------------------------------------------
# 6. Mock mode unchanged
# ---------------------------------------------------------------------------

class TestM416MockUnchanged(unittest.TestCase):

    def test_mock_posts_score_correctly(self):
        from mock_data.posts import MOCK_POSTS
        scored = score_posts(MOCK_POSTS)
        self.assertEqual(scored[0]["score"], "Strong fit")
        self.assertEqual(scored[6]["score"], "Avoid")

    def test_mock_reply_text_unchanged(self):
        from mock_data.posts import MOCK_POSTS
        scored = score_posts(MOCK_POSTS)
        with_replies = generate_replies(scored)
        post1 = next(p for p in with_replies if p["id"] == 1)
        expected_a = "Earnings week is just the financial media's quarterly excuse"
        self.assertIn(expected_a, post1["replies"][0]["text"])

    def test_mock_build_markdown_unchanged(self):
        from mock_data.posts import MOCK_POSTS
        from src.digest import build_markdown
        from src.post_generator import generate_posts
        scored = score_posts(MOCK_POSTS)
        with_replies = generate_replies(scored)
        sched = generate_posts(0)
        md = build_markdown("Signal Shift", with_replies, sched, mode="Mock")
        self.assertNotIn("manually before posting", md)
        self.assertIn("Signal Shift", md)


if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(__import__("__main__"))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
