"""
M4.18 — Final Tavily Optimization & Freeze: tests

Covers:
- New hard-avoid keywords (stock-pick promo language)
- _is_stock_recommendation() soft-signal detection
- OwenCarter-style post downgrade (Avoid or Low, not Medium)
- Thin ticker-only / ticker+vague-language posts: no context-aware reply
- ChrisQuelch-style analytical post: contextual reply still generated
- PhotonCap/LPTH rich-context post: contextual reply preserved (regression guard)
- CounterPointTR broadcast downgrade preserved (regression guard)
- Loose query expansion (no double-quotes, >= 25 queries)
- mel_search_digest.yml final Tavily defaults
- Tavily honesty note in digest output
"""

import re
import unittest
import yaml

from src.scorer import _is_stock_recommendation, score_posts
from src.replier import _build_contextual_reply, _extract_post_context, generate_replies
from src.digest import _build_best_3


# ---------------------------------------------------------------------------
# Minimal fixtures
# ---------------------------------------------------------------------------

def _base_post(**overrides):
    defaults = {
        "id": "9000000000000000001",
        "author": "@testuser",
        "text": "test post text",
        "combined_text_for_scoring": "test post text",
        "age_hours": 10.0,
        "age_source": "x_api",
        "likes": 0,
        "reposts": 0,
        "reply_count": 0,
        "impressions": 0,
        "metrics_confidence": "low",
        "discovery_source": "tavily_search",
        "post_url": "https://x.com/testuser/status/9000000000000000001",
    }
    defaults.update(overrides)
    return defaults


def _minimal_profile():
    return {
        "fit_keywords": {
            "strong": [
                "overwhelmed", "noise", "clarity", "chasing", "confused",
                "don't understand", "makes no sense", "story stock",
                "overpriced", "nothing changed", "thesis unchanged",
            ],
            "decent": ["framework", "process", "financial media"],
            "weak": ["rsi", "macd", "moving average", "technical analysis"],
            "avoid": [
                "100x", "moon", "gem", "next 10x", "get rich", "guaranteed",
                "link in bio", "screenshot this", "thank me later",
                "signal group", "join my discord", "free webinar", "paid group",
                "buy this", "insider", "pump", "webinar",
                "today's recommendation", "this is free money",
                "easy trade", "loaded the boat", "backing up the truck", "10-bagger",
            ],
            "market_context_required": [
                "stock", "stocks", "market", "markets", "investing",
                "investor", "investors", "earnings", "$", "trading",
            ],
            "off_topic": ["football club", "rugby club"],
            "out_of_scope_market": ["rupee", "INR", "India", "Nifty", "FTSE"],
        },
        "handles": {"founder": "@yourhandle", "product": "@yourhandle"},
        "us_scope_keywords": ["S&P", "Nasdaq", "NYSE", "earnings", "$", "US stocks"],
    }


# ---------------------------------------------------------------------------
# TestPromoAvoidKeywords
# ---------------------------------------------------------------------------

class TestPromoAvoidKeywords(unittest.TestCase):

    def _post_with(self, text):
        return _base_post(
            text=text,
            combined_text_for_scoring=text,
            age_hours=5.0,
        )

    def _score(self, text):
        posts = [self._post_with(text)]
        scored = score_posts(posts, profile=_minimal_profile())
        return scored[0]

    def test_todays_recommendation_is_avoid(self):
        result = self._score("$NVDA — today's recommendation from our team. Strong buy.")
        self.assertEqual(result["score"], "Avoid")
        self.assertEqual(result["reply_account"], "Do not reply")

    def test_this_is_free_money_is_avoid(self):
        result = self._score("$TSLA is up 12%. This is free money, don't overthink it.")
        self.assertEqual(result["score"], "Avoid")

    def test_easy_trade_is_avoid(self):
        result = self._score("$PLTR looks like an easy trade here, just buy the breakout.")
        self.assertEqual(result["score"], "Avoid")

    def test_loaded_the_boat_is_avoid(self):
        result = self._score("Loaded the boat on $META today. Earnings beat was massive.")
        self.assertEqual(result["score"], "Avoid")

    def test_backing_up_the_truck_is_avoid(self):
        result = self._score("Backing up the truck on $NVDA. AI supercycle is real.")
        self.assertEqual(result["score"], "Avoid")

    def test_ten_bagger_is_avoid(self):
        result = self._score("$AMD could be a 10-bagger from here if AI spending holds.")
        self.assertEqual(result["score"], "Avoid")


# ---------------------------------------------------------------------------
# TestIsStockRecommendation
# ---------------------------------------------------------------------------

class TestIsStockRecommendation(unittest.TestCase):

    def test_zero_signals_false(self):
        self.assertFalse(_is_stock_recommendation("Just a normal post about market noise."))

    def test_one_signal_false(self):
        self.assertFalse(_is_stock_recommendation(
            "Our conviction on $NVDA remains strong given the AI thesis."
        ))

    def test_two_signals_true(self):
        self.assertTrue(_is_stock_recommendation(
            "Our price target remains $150. Stay patient and let the market do the work."
        ))

    def test_owen_carter_style_true(self):
        body = (
            "Target price remains unchanged at $85. Short-term market fluctuations do not "
            "change our long-term thesis unchanged. Stay patient and let the market do the work. "
            "Biggest winners come to those who wait. Stock up +22.59% this quarter."
        )
        self.assertTrue(_is_stock_recommendation(body))

    def test_maintain_our_and_stay_patient_true(self):
        self.assertTrue(_is_stock_recommendation(
            "We maintain our $200 target on $TSLA. Stay patient — this is a multi-year play."
        ))

    def test_analytical_post_not_triggered(self):
        self.assertFalse(_is_stock_recommendation(
            "$NVDA up +8% today. Earnings came in above consensus. "
            "Revenue beat by 12%, margins expanded. Is this AI capex pull-forward or durable?"
        ))


# ---------------------------------------------------------------------------
# TestOwenCarterDowngrade
# ---------------------------------------------------------------------------

class TestOwenCarterDowngrade(unittest.TestCase):

    def _scored_post(self):
        body = (
            "$NVDA — target price remains unchanged at $180. "
            "Stay patient and let the market do the work. "
            "Our biggest winners always come from conviction. "
            "Exceptional investors ignore short-term noise. Stock up +22.59%."
        )
        post = _base_post(
            id="oc_001",
            text=body,
            combined_text_for_scoring=body,
            age_hours=6.0,
        )
        scored = score_posts([post], profile=_minimal_profile())
        return scored[0]

    def test_not_medium_opportunity(self):
        result = self._scored_post()
        self.assertNotEqual(result["opportunity"], "Medium opportunity")

    def test_is_avoid_or_low(self):
        result = self._scored_post()
        self.assertIn(result["opportunity"], ("Low opportunity", "Poor opportunity"))

    def test_score_is_avoid_or_not_top_lead(self):
        result = self._scored_post()
        # Either hard Avoid (if "today's recommendation" triggered) or
        # downgraded by stock-recommendation gate
        self.assertNotIn(result["opportunity"], ("High opportunity", "Medium opportunity"))

    def test_no_context_aware_reply(self):
        result = self._scored_post()
        with_replies = generate_replies([result])
        post = with_replies[0]
        best = post.get("best_reply") or {}
        style = best.get("style", "")
        self.assertNotIn("Context-aware", style)


# ---------------------------------------------------------------------------
# TestThinTickerPosts
# ---------------------------------------------------------------------------

class TestThinTickerPosts(unittest.TestCase):

    def test_ticker_only_no_contextual_reply(self):
        context = {"tickers": ["$ONDS"], "pct_changes": [], "drivers": []}
        result = _build_contextual_reply(context)
        self.assertIsNone(result)

    def test_ticker_plus_pct_no_driver_no_contextual_reply(self):
        context = {"tickers": ["$ONDS"], "pct_changes": ["+22.59%"], "drivers": []}
        result = _build_contextual_reply(context)
        self.assertIsNone(result)

    def test_ticker_plus_vague_language_no_contextual_reply(self):
        post = _base_post(
            text="$ONDS is moving today. Interesting price action.",
            combined_text_for_scoring="$ONDS is moving today. Interesting price action.",
        )
        context = _extract_post_context(post)
        result = _build_contextual_reply(context)
        self.assertIsNone(result)

    def test_thin_post_scoring_not_medium(self):
        post = _base_post(
            text="$ONDS is moving today. Stocks price action.",
            combined_text_for_scoring="$ONDS is moving today. Stocks price action.",
            age_hours=5.0,
        )
        scored = score_posts([post], profile=_minimal_profile())
        self.assertNotEqual(scored[0]["opportunity"], "Medium opportunity")

    def test_thin_post_with_fit_keyword_no_context_aware_reply(self):
        # Has fit keyword ("confused") so may score Decent, but no driver → no contextual reply
        post = _base_post(
            text="I'm confused why $ONDS is moving today. Stocks doing weird things.",
            combined_text_for_scoring="I'm confused why $ONDS is moving today. Stocks doing weird things.",
            age_hours=5.0,
        )
        context = _extract_post_context(post)
        result = _build_contextual_reply(context)
        self.assertIsNone(result)


# ---------------------------------------------------------------------------
# TestChrisQuelchContextualReply
# ---------------------------------------------------------------------------

class TestChrisQuelchContextualReply(unittest.TestCase):

    def _quelch_post(self):
        text = (
            "$NVDA up +28% since earnings. EPS growth >30%, revenue beat massive. "
            "But is this AI capex hype or durable earnings power? "
            "Confused why retail keeps chasing narrative over numbers."
        )
        return _base_post(
            text=text,
            combined_text_for_scoring=text,
            age_hours=8.0,
        )

    def test_quelch_has_drivers(self):
        post = self._quelch_post()
        context = _extract_post_context(post)
        self.assertTrue(len(context["drivers"]) >= 1, f"Expected drivers, got: {context['drivers']}")

    def test_quelch_contextual_reply_generated(self):
        post = self._quelch_post()
        context = _extract_post_context(post)
        result = _build_contextual_reply(context)
        self.assertIsNotNone(result, "Expected contextual reply for ChrisQuelch post")

    def test_quelch_not_downgraded(self):
        post = self._quelch_post()
        scored = score_posts([post], profile=_minimal_profile())
        self.assertIn(scored[0]["score"], ("Strong fit", "Decent fit"))


# ---------------------------------------------------------------------------
# TestPhotoNCapContextualReply (regression guard from M4.16)
# ---------------------------------------------------------------------------

class TestPhotoNCapContextualReply(unittest.TestCase):

    def _lpth_post(self):
        title = 'PhotonCap on X: "$LPTH up +8.4%, near 52-week highs. Loss-making IR optics."'
        content = (
            "Market may be buying scarce U.S.-based optical capacity in a defense supply "
            "chain moving away from Chinese germanium. "
            "Onshoring premium or overpriced story stock? "
            "Around $50M FY26 nine-month revenue, around $1B market cap."
        )
        return _base_post(
            id="1900000000000001004",
            text="$LPTH up +8.4%, near 52-week highs. Loss-making IR optics.",
            combined_text_for_scoring=f"{title} {content}",
            age_hours=10.0,
        )

    def test_lpth_has_tickers_and_drivers(self):
        post = self._lpth_post()
        context = _extract_post_context(post)
        self.assertIn("$LPTH", context["tickers"])
        self.assertTrue(len(context["drivers"]) >= 1)

    def test_lpth_contextual_reply_is_recommended(self):
        post = self._lpth_post()
        scored = score_posts([post], profile=_minimal_profile())
        with_replies = generate_replies(scored)
        post_out = with_replies[0]
        best = post_out.get("best_reply") or {}
        self.assertIn("Context-aware", best.get("style", ""),
                      f"Expected context-aware best reply, got: {best}")


# ---------------------------------------------------------------------------
# TestCounterPointTRBroadcastPreserved (regression guard from M4.16b)
# ---------------------------------------------------------------------------

class TestCounterPointTRBroadcastPreserved(unittest.TestCase):

    def test_broadcast_post_downgraded(self):
        # Broadcast post: announces / unveils + no discussion hook → downgrade from Medium.
        # This regression guard confirms the broadcast detection path still fires in M4.18.
        body = (
            "NVIDIA Unveils new AI campus expansion in Taiwan. "
            "The company announces the latest GTC 2026 AI data center partnership. "
            "Retail investors tracking $NVDA noise around the AI expansion. stocks market"
        )
        post = _base_post(
            id="ct_001",
            text=body,
            combined_text_for_scoring=body,
            age_hours=5.0,
        )
        scored = score_posts([post], profile=_minimal_profile())
        result = scored[0]
        self.assertNotEqual(result["opportunity"], "Medium opportunity",
                            "Broadcast post should be downgraded from Medium")


# ---------------------------------------------------------------------------
# TestDriverOnlyReply
# ---------------------------------------------------------------------------

class TestDriverOnlyReply(unittest.TestCase):

    def test_two_generic_drivers_fires(self):
        # "scarcity" and "story stock" — both in _CONTEXT_DRIVERS but not in _STRONG_STRUCTURAL_DRIVERS
        context = {"tickers": [], "pct_changes": [], "drivers": ["scarcity", "story stock"]}
        result = _build_contextual_reply(context)
        self.assertIsNotNone(result)

    def test_one_strong_structural_driver_fires(self):
        context = {"tickers": [], "pct_changes": [], "drivers": ["onshoring"]}
        result = _build_contextual_reply(context)
        self.assertIsNotNone(result)

    def test_one_earnings_driver_fires(self):
        context = {"tickers": [], "pct_changes": [], "drivers": ["earnings"]}
        result = _build_contextual_reply(context)
        self.assertIsNotNone(result)

    def test_one_weak_generic_driver_returns_none(self):
        # "scarcity" alone — not in _STRONG_STRUCTURAL_DRIVERS, only 1 driver → None
        context = {"tickers": [], "pct_changes": [], "drivers": ["scarcity"]}
        result = _build_contextual_reply(context)
        self.assertIsNone(result)

    def test_no_ticker_no_driver_returns_none(self):
        context = {"tickers": [], "pct_changes": [], "drivers": []}
        result = _build_contextual_reply(context)
        self.assertIsNone(result)

    def test_driver_only_reply_contains_driver_word(self):
        context = {"tickers": [], "pct_changes": [], "drivers": ["onshoring"]}
        result = _build_contextual_reply(context)
        self.assertIn("onshoring", result)


# ---------------------------------------------------------------------------
# TestTavilyDigestNote
# ---------------------------------------------------------------------------

class TestTavilyDigestNote(unittest.TestCase):

    def _make_scored_posts(self, discovery_source, count=1):
        posts = []
        for i in range(count):
            posts.append({
                "id": f"ds_{i}",
                "score": "Decent fit",
                "opportunity": "Medium opportunity",
                "text": "test post",
                "author": "@testuser",
                "visibility": "Unknown visibility",
                "age_hours": 5.0,
                "metrics_confidence": "low" if discovery_source == "tavily_search" else None,
                "discovery_source": discovery_source,
                "post_url": f"https://x.com/testuser/status/ds_{i}",
                "opportunity_reason": "Fresh post.",
                "engagement_summary": "Engagement unknown.",
                "suggested_action": "Reply",
                "freshness_tier": "fresh",
                "age_label": "~5h old",
                "out_of_scope": False,
                "best_reply": {"style": "A", "text": "Reply text."},
                "replies": [{"style": "A", "text": "Reply text."}],
                "media": {"type": "No media", "reason": ""},
                "reason": "Good fit.",
                "reply_account": "Either",
            })
        return posts

    def test_tavily_run_includes_note(self):
        posts = self._make_scored_posts("tavily_search", count=1)
        lines = _build_best_3(posts)
        combined = "\n".join(lines)
        self.assertIn("Tavily", combined)
        self.assertIn("verify", combined.lower())

    def test_mock_run_no_tavily_note(self):
        posts = self._make_scored_posts("mock", count=1)
        lines = _build_best_3(posts)
        combined = "\n".join(lines)
        self.assertNotIn("Tavily", combined)


# ---------------------------------------------------------------------------
# TestLooseQueryExpansion
# ---------------------------------------------------------------------------

class TestLooseQueryExpansion(unittest.TestCase):

    def _load_profile(self):
        with open("profiles/signal_shift.yaml") as f:
            return yaml.safe_load(f)

    def test_loose_discovery_has_25_or_more_queries(self):
        profile = self._load_profile()
        buckets = profile.get("query_buckets", profile.get("search_settings", {}).get("query_buckets", {}))
        loose = buckets.get("loose_discovery", [])
        self.assertGreaterEqual(len(loose), 25,
                                f"Expected >= 25 loose_discovery queries, got {len(loose)}")

    def test_all_loose_queries_have_no_double_quotes(self):
        profile = self._load_profile()
        buckets = profile.get("query_buckets", profile.get("search_settings", {}).get("query_buckets", {}))
        loose = buckets.get("loose_discovery", [])
        for q in loose:
            self.assertNotIn('"', q, f"Loose query contains double-quote: {q!r}")

    def test_avoid_list_has_new_promo_phrases(self):
        profile = self._load_profile()
        avoid = profile.get("fit_keywords", {}).get("avoid", [])
        for phrase in ("today's recommendation", "loaded the boat", "10-bagger"):
            self.assertIn(phrase, avoid, f"Expected '{phrase}' in avoid list")


# ---------------------------------------------------------------------------
# TestWorkflowDefaults
# ---------------------------------------------------------------------------

class TestWorkflowDefaults(unittest.TestCase):

    def _load_workflow(self):
        with open(".github/workflows/mel_search_digest.yml") as f:
            return f.read()

    def test_max_search_queries_default_10(self):
        content = self._load_workflow()
        self.assertIn("MAX_SEARCH_QUERIES", content)
        self.assertIn("|| '10'", content)

    def test_max_results_per_query_default_10(self):
        content = self._load_workflow()
        self.assertIn("MAX_RESULTS_PER_QUERY", content)
        self.assertIn("|| '10'", content)

    def test_tavily_search_depth_default_advanced(self):
        content = self._load_workflow()
        self.assertIn("|| 'advanced'", content)

    def test_tavily_topic_default_general(self):
        content = self._load_workflow()
        self.assertIn("|| 'general'", content)

    def test_tavily_time_range_default_day(self):
        content = self._load_workflow()
        self.assertIn("|| 'day'", content)

    def test_tavily_auto_parameters_default_false(self):
        content = self._load_workflow()
        self.assertIn("|| 'false'", content)

    def test_tavily_query_style_default_loose(self):
        content = self._load_workflow()
        self.assertIn("|| 'loose'", content)

    def test_no_schedule_trigger(self):
        content = self._load_workflow()
        self.assertNotIn("schedule:", content)
        self.assertNotIn("cron:", content)

    def test_no_push_trigger(self):
        content = self._load_workflow()
        # The file should only have workflow_dispatch
        # "push" might appear in artifact name, so check for "push:" specifically
        self.assertNotIn("push:", content)

    def test_workflow_dispatch_present(self):
        content = self._load_workflow()
        self.assertIn("workflow_dispatch", content)

    def test_tavily_days_has_no_default(self):
        content = self._load_workflow()
        # TAVILY_DAYS should NOT have a || fallback
        # Find the TAVILY_DAYS line and confirm no || on it
        for line in content.splitlines():
            if "TAVILY_DAYS" in line and "||" in line:
                self.fail(f"TAVILY_DAYS should have no default fallback, but found: {line.strip()!r}")


if __name__ == "__main__":
    unittest.main()
