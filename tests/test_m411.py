"""
Tests for M4.11: Reply creativity, worth-check output, and inspiration quality.
No real API calls, no network access.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import yaml
from src.scorer import score_posts
from src.replier import (
    generate_replies,
    _pick_reply_options,
    _DYNAMIC_TEMPLATES,
    _INSPIRATION_ANGLES,
    _INSPIRATION_FORMAT_HINTS,
)
from src.digest import (
    build_markdown,
    _build_best_3,
    _build_inspiration,
    _build_worth_checking,
    _get_worth_checking_posts,
    _categorize_rejected,
    _source_quality_score,
)
from src.post_generator import generate_posts


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_profile():
    path = os.path.join(os.path.dirname(__file__), "..", "profiles", "signal_shift.yaml")
    with open(path) as f:
        return yaml.safe_load(f)


def _make_posts_schedule():
    return {
        "founder": {"handle": "@yourhandle", "needed": False, "reason": "Not needed.", "post": None, "optional_idea": None},
        "product": {"handle": "@SignalShiftCo", "needed": False, "reason": "Not needed.", "post": None, "optional_idea": None},
    }


def _make_scored(
    tweet_id, text, score, opportunity, freshness_tier,
    out_of_scope=False, age_hours=6, metrics_confidence="low",
    inspiration_angles=None, replies=None, best_reply=None, media=None,
    age_label=None, author=None,
):
    """Build a pre-scored, pre-replied post dict."""
    return {
        "id": tweet_id,
        "author": author or f"@user_{tweet_id}",
        "text": text,
        "score": score,
        "visibility": "Unknown visibility",
        "opportunity": opportunity,
        "opportunity_reason": "Test reason.",
        "engagement_summary": "Engagement unknown",
        "age_label": age_label,
        "age_hours": age_hours,
        "freshness_tier": freshness_tier,
        "out_of_scope": out_of_scope,
        "reply_account": "Either" if score in ("Strong fit", "Decent fit") else "Do not reply",
        "suggested_action": "Reply" if opportunity in ("High opportunity", "Medium opportunity") else "Do not engage",
        "reason": "Test.",
        "metrics_confidence": metrics_confidence,
        "replies": replies or [],
        "best_reply": best_reply or {},
        "media": media or {"type": "No media", "reason": ""},
        "post_url": f"https://x.com/user_{tweet_id}/status/{tweet_id}",
        "author_profile_url": f"https://x.com/user_{tweet_id}",
        "inspiration_angles": inspiration_angles,
        "reply_note": None,
    }


def _web_post_text(text, tweet_id="1900000000000000001", age_hours=6):
    """Score a web post through the full pipeline and return with replies."""
    post = {
        "id": tweet_id,
        "author": "@test_user",
        "author_name": "test_user",
        "author_followers": 0,
        "author_profile_url": f"https://x.com/test_user",
        "text": text,
        "likes": 0, "reposts": 0, "reply_count": 0, "impressions": 0,
        "age_hours": age_hours,
        "age_source": "snowflake",
        "post_url": f"https://x.com/test_user/status/{tweet_id}",
        "url": f"https://x.com/test_user/status/{tweet_id}",
        "discovery_source": "tavily_search",
        "metrics_confidence": "low",
    }
    profile = _load_profile()
    scored = score_posts([post], profile=profile)
    return generate_replies(scored)[0]


# ---------------------------------------------------------------------------
# 1. Worth Checking — appearance criteria
# ---------------------------------------------------------------------------

class TestWorthCheckingAppears(unittest.TestCase):

    def _decent_low_fresh(self, tweet_id="wc_test"):
        """A fresh Decent fit Low opportunity web-search post."""
        return _make_scored(
            tweet_id, "Retail investors feel overwhelmed by all the market noise",
            score="Decent fit", opportunity="Low opportunity", freshness_tier="fresh",
            age_hours=6, replies=[
                {"style": "A — One-liner", "text": "A."},
                {"style": "B — Para", "text": "B."},
                {"style": "C — Reframe", "text": "C."},
            ],
            best_reply={"style": "A — One-liner", "text": "A."},
            media={"type": "Optional GIF", "idea": "overload", "use_if": "casual", "skip_if": "serious"},
        )

    def test_worth_checking_shows_for_low_opp_fresh_decent_post(self):
        posts = [self._decent_low_fresh()]
        result = _get_worth_checking_posts(posts)
        self.assertEqual(len(result), 1)

    def test_worth_checking_in_markdown_when_no_best3(self):
        posts = [self._decent_low_fresh()]
        md = build_markdown("Signal Shift", posts, _make_posts_schedule(), mode="Tavily")
        self.assertIn("Worth Checking Manually", md)

    def test_worth_checking_shows_post_snippet(self):
        posts = [self._decent_low_fresh()]
        lines = _build_worth_checking(posts)
        content = "\n".join(lines)
        self.assertIn("overwhelmed", content)

    def test_worth_checking_shows_post_url(self):
        posts = [self._decent_low_fresh()]
        lines = _build_worth_checking(posts)
        content = "\n".join(lines)
        self.assertIn("https://x.com", content)

    def test_worth_checking_shows_reply_options(self):
        posts = [self._decent_low_fresh()]
        lines = _build_worth_checking(posts)
        content = "\n".join(lines)
        self.assertIn("Reply options", content)

    def test_worth_checking_shows_media_guidance(self):
        posts = [self._decent_low_fresh()]
        lines = _build_worth_checking(posts)
        content = "\n".join(lines)
        self.assertIn("Media:", content)

    def test_best3_note_mentions_worth_checking_when_empty(self):
        posts = [self._decent_low_fresh()]
        lines = _build_best_3(posts, has_worth_checking=True)
        content = "\n".join(lines)
        self.assertIn("Worth Checking Manually", content)


# ---------------------------------------------------------------------------
# 2. Worth Checking — exclusion criteria
# ---------------------------------------------------------------------------

class TestWorthCheckingExclusions(unittest.TestCase):

    def test_weak_fit_excluded(self):
        posts = [_make_scored("wc_weak", "RSI crossover", "Weak fit", "Poor opportunity", "fresh")]
        self.assertEqual(_get_worth_checking_posts(posts), [])

    def test_avoid_excluded(self):
        posts = [_make_scored("wc_avoid", "Moon rocket 🚀", "Avoid", "Poor opportunity", "fresh")]
        self.assertEqual(_get_worth_checking_posts(posts), [])

    def test_out_of_scope_excluded(self):
        posts = [_make_scored("wc_oos", "Nifty down", "Decent fit", "Low opportunity", "fresh", out_of_scope=True)]
        self.assertEqual(_get_worth_checking_posts(posts), [])

    def test_stale_excluded(self):
        posts = [_make_scored("wc_stale", "Old noise", "Decent fit", "Low opportunity", "stale")]
        self.assertEqual(_get_worth_checking_posts(posts), [])

    def test_old_excluded(self):
        posts = [_make_scored("wc_old", "Week-old post", "Decent fit", "Low opportunity", "old")]
        self.assertEqual(_get_worth_checking_posts(posts), [])

    def test_medium_opportunity_excluded(self):
        # Medium opportunity → should be in Best 3, not Worth Checking
        posts = [_make_scored("wc_med", "Good fit fresh", "Strong fit", "Medium opportunity", "fresh")]
        self.assertEqual(_get_worth_checking_posts(posts), [])

    def test_non_web_excluded(self):
        posts = [_make_scored("wc_mock", "Retail noise", "Decent fit", "Low opportunity", "fresh", metrics_confidence="high")]
        self.assertEqual(_get_worth_checking_posts(posts), [])

    def test_worth_checking_max_3(self):
        posts = [
            _make_scored(f"wc_{i}", "Market noise overwhelm retail investors", "Decent fit", "Low opportunity", "fresh")
            for i in range(6)
        ]
        result = _get_worth_checking_posts(posts)
        self.assertLessEqual(len(result), 3)


# ---------------------------------------------------------------------------
# 3. Today's Best 3 remains strict
# ---------------------------------------------------------------------------

class TestBest3StaysStrict(unittest.TestCase):

    def test_best3_not_force_filled_with_worth_checking_posts(self):
        posts = [
            _make_scored("b3_low", "Retail noise", "Decent fit", "Low opportunity", "fresh")
        ]
        lines = _build_best_3(posts)
        content = "\n".join(lines)
        self.assertIn("No suitable reply opportunities found today", content)

    def test_best3_still_strict_when_worth_checking_present(self):
        posts = [
            _make_scored("b3_low", "Retail noise", "Decent fit", "Low opportunity", "fresh")
        ]
        md = build_markdown("Signal Shift", posts, _make_posts_schedule(), mode="Tavily")
        self.assertIn("No suitable reply opportunities found today", md)
        self.assertIn("Worth Checking Manually", md)


# ---------------------------------------------------------------------------
# 4. Worth Checking posts excluded from Rejected Summary
# ---------------------------------------------------------------------------

class TestWorthCheckingNotInRejected(unittest.TestCase):

    def test_worth_checking_post_not_in_other_bucket(self):
        posts = [
            _make_scored("wc_x", "Market noise overwhelm retail investors", "Decent fit", "Low opportunity", "fresh")
        ]
        cats = _categorize_rejected(posts)
        all_rejected_ids = {
            p["id"] for bucket in cats.values() for p in bucket
        }
        self.assertNotIn("wc_x", all_rejected_ids)


# ---------------------------------------------------------------------------
# 5. Best 3 shows all reply options + media guidance in compact mode
# ---------------------------------------------------------------------------

class TestBest3ReplyOptions(unittest.TestCase):
    def setUp(self):
        os.environ.pop("DIGEST_DEBUG", None)

    def tearDown(self):
        os.environ.pop("DIGEST_DEBUG", None)

    def _best3_post(self):
        return _make_scored(
            "b3_good", "Overwhelmed by earnings noise this week — retail investor confusion.",
            score="Strong fit", opportunity="Medium opportunity", freshness_tier="fresh",
            replies=[
                {"style": "A — One-liner", "text": "One line."},
                {"style": "B — Paragraph", "text": "A longer paragraph."},
                {"style": "C — Reframe", "text": "A question or reframe."},
            ],
            best_reply={"style": "B — Paragraph", "text": "A longer paragraph."},
            media={"type": "Optional GIF", "idea": "overwhelmed trader", "use_if": "casual", "skip_if": "serious"},
        )

    def test_compact_mode_shows_all_reply_options(self):
        posts = [self._best3_post()]
        md = build_markdown("Signal Shift", posts, _make_posts_schedule(), mode="Tavily")
        self.assertIn("A — One-liner", md)
        self.assertIn("B — Paragraph", md)
        self.assertIn("C — Reframe", md)

    def test_compact_mode_shows_media_guidance(self):
        posts = [self._best3_post()]
        md = build_markdown("Signal Shift", posts, _make_posts_schedule(), mode="Tavily")
        self.assertIn("**Media:**", md)

    def test_compact_mode_shows_gif_idea(self):
        posts = [self._best3_post()]
        md = build_markdown("Signal Shift", posts, _make_posts_schedule(), mode="Tavily")
        self.assertIn("Idea:", md)
        self.assertIn("overwhelmed trader", md)

    def test_compact_mode_shows_use_if_skip_if(self):
        posts = [self._best3_post()]
        md = build_markdown("Signal Shift", posts, _make_posts_schedule(), mode="Tavily")
        self.assertIn("Use if:", md)
        self.assertIn("Skip if:", md)

    def test_compact_mode_shows_post_url(self):
        posts = [self._best3_post()]
        md = build_markdown("Signal Shift", posts, _make_posts_schedule(), mode="Tavily")
        self.assertIn("https://x.com/user_b3_good", md)

    def test_compact_mode_marks_recommended_option(self):
        posts = [self._best3_post()]
        md = build_markdown("Signal Shift", posts, _make_posts_schedule(), mode="Tavily")
        self.assertIn("✅", md)


# ---------------------------------------------------------------------------
# 6. Reply variation — theme + hash variation
# ---------------------------------------------------------------------------

class TestReplyVariation(unittest.TestCase):

    def test_pick_reply_options_is_deterministic(self):
        template = _DYNAMIC_TEMPLATES["noise_overwhelm"]
        opts1, idx1 = _pick_reply_options("abc123", "market noise", "noise_overwhelm", template)
        opts2, idx2 = _pick_reply_options("abc123", "market noise", "noise_overwhelm", template)
        self.assertEqual(opts1, opts2)
        self.assertEqual(idx1, idx2)

    def test_same_theme_different_ids_get_variety(self):
        template = _DYNAMIC_TEMPLATES["noise_overwhelm"]
        first_options = set()
        for tid in ["id_alpha", "id_beta", "id_gamma", "id_delta"]:
            opts, _ = _pick_reply_options(tid, "market noise", "noise_overwhelm", template)
            first_options.add(opts[0]["text"])
        self.assertGreater(len(first_options), 1)

    def test_options_d_reachable_for_themes_with_it(self):
        # noise_overwhelm now has options_d — check it's in available sets
        template = _DYNAMIC_TEMPLATES["noise_overwhelm"]
        self.assertIn("options_d", template)
        # Brute-force find an input that selects options_d
        found = False
        for i in range(100):
            opts, _ = _pick_reply_options(str(i), f"text_{i}", "noise_overwhelm", template)
            if opts == template.get("options_d"):
                found = True
                break
        self.assertTrue(found, "options_d set was never selected across 100 varied inputs")

    def test_inspiration_format_hints_present_for_all_themes(self):
        expected_themes = [
            "noise_overwhelm", "bias_emotional", "clarity_signal",
            "reactive_slow_down", "data_vs_insight", "generic_strong", "generic_decent",
        ]
        for theme in expected_themes:
            self.assertIn(theme, _INSPIRATION_FORMAT_HINTS, f"Missing format hint for {theme}")

    def test_inspiration_angles_expanded_to_4(self):
        for theme, angles in _INSPIRATION_ANGLES.items():
            self.assertGreaterEqual(len(angles), 4, f"Theme '{theme}' has fewer than 4 angles")


# ---------------------------------------------------------------------------
# 7. Human voice / witty lines present in templates
# ---------------------------------------------------------------------------

class TestHumanVoiceInTemplates(unittest.TestCase):

    def _all_option_texts(self):
        texts = []
        for template in _DYNAMIC_TEMPLATES.values():
            for key in ("options", "options_b", "options_c", "options_d"):
                for opt in template.get(key, []):
                    texts.append(opt["text"])
        return texts

    def test_witty_noise_line_present(self):
        texts = self._all_option_texts()
        self.assertTrue(
            any("volume wearing a suit" in t or "browser disease" in t or "steering wheel" in t for t in texts),
            "Expected at least one witty noise/overwhelm line in templates"
        )

    def test_witty_candle_line_present(self):
        texts = self._all_option_texts()
        self.assertTrue(
            any("candle" in t or "chart moved" in t or "Not every loud" in t for t in texts),
            "Expected witty candle/thesis line in templates"
        )

    def test_no_forced_product_mentions_in_dynamic_templates(self):
        texts = self._all_option_texts()
        for t in texts:
            self.assertNotIn("Signal Shift", t, "Dynamic templates should not name-drop Signal Shift")


# ---------------------------------------------------------------------------
# 8. Save for Inspiration quality improvements
# ---------------------------------------------------------------------------

class TestInspirationImprovements(unittest.TestCase):

    def _insp_post(self, tweet_id, author, text, score="Strong fit", age_label=None):
        return _make_scored(
            tweet_id, text, score=score, opportunity="Low opportunity",
            freshness_tier="old", age_hours=96,
            inspiration_angles=["Angle one.", "Angle two."],
            age_label=age_label or f"Age: 4d old — save for inspiration",
            author=author,
        )

    def test_inspiration_maxes_at_3_shown(self):
        posts = [self._insp_post(f"insp_{i}", f"@user_{i}", "Overwhelmed by market noise this week.") for i in range(6)]
        lines = _build_inspiration(posts)
        content = "\n".join(lines)
        # Count post entries — each starts with "- **@user_"
        shown = [l for l in lines if l.startswith("- **@user_")]
        self.assertLessEqual(len(shown), 3)

    def test_inspiration_shows_hidden_count_when_more_exist(self):
        posts = [self._insp_post(f"insp_{i}", f"@user_{i}", "Market noise overwhelming this week.") for i in range(5)]
        lines = _build_inspiration(posts)
        content = "\n".join(lines)
        self.assertIn("hidden", content)

    def test_inspiration_no_hidden_note_when_3_or_fewer(self):
        posts = [self._insp_post(f"insp_{i}", f"@user_{i}", "Market noise overwhelming this week.") for i in range(3)]
        lines = _build_inspiration(posts)
        content = "\n".join(lines)
        self.assertNotIn("hidden", content)

    def test_inspiration_deduplicates_angles_across_posts(self):
        # Two posts with same theme — second post should get different angles
        posts = [
            self._insp_post("insp_1", "@user_1", "Overwhelmed by market noise — too much information overload."),
            self._insp_post("insp_2", "@user_2", "Market noise is overwhelming retail investors this week."),
        ]
        lines = _build_inspiration(posts)
        # Collect angle lines
        angle_lines = [l.strip() for l in lines if l.strip().startswith("- ") and "**" not in l]
        # No two identical angle lines
        self.assertEqual(len(angle_lines), len(set(angle_lines)), "Duplicate inspiration angles found across posts")

    def test_inspiration_shows_format_hint(self):
        posts = [self._insp_post("insp_1", "@user_1", "Overwhelmed by market noise — information overload this week.")]
        lines = _build_inspiration(posts)
        content = "\n".join(lines)
        self.assertIn("Format:", content)

    def test_human_post_sorted_before_news_org(self):
        human = self._insp_post("h1", "@retail_investor_joe", "Market noise overwhelming this week.")
        news = self._insp_post("n1", "@MarketWatchNews", "Market noise overwhelming this week.")
        # News org score should be higher (worse), human score lower (better)
        self.assertLess(_source_quality_score(human), _source_quality_score(news))


# ---------------------------------------------------------------------------
# 9. Source quality score heuristics
# ---------------------------------------------------------------------------

class TestSourceQualityScore(unittest.TestCase):

    def _post(self, author, text="Some market post"):
        return {"author": author, "text": text}

    def test_human_account_low_score(self):
        self.assertEqual(_source_quality_score(self._post("@retailinvestor")), 0)

    def test_news_org_high_score(self):
        score = _source_quality_score(self._post("@MarketWatchNews"))
        self.assertGreater(score, 0)

    def test_link_in_text_adds_score(self):
        score = _source_quality_score(self._post("@user", "Check https://link.com for more"))
        self.assertGreater(score, 0)

    def test_promo_text_adds_score(self):
        score = _source_quality_score(self._post("@user", "read more in my newsletter"))
        self.assertGreater(score, 0)

    def test_clean_human_text_zero_score(self):
        score = _source_quality_score(self._post("@just_a_trader", "Market noise is real this week"))
        self.assertEqual(score, 0)


# ---------------------------------------------------------------------------
# 10. Compact digest remains compact; debug mode works
# ---------------------------------------------------------------------------

class TestCompactModeUnchangedM411(unittest.TestCase):

    def setUp(self):
        os.environ.pop("DIGEST_DEBUG", None)

    def tearDown(self):
        os.environ.pop("DIGEST_DEBUG", None)

    def test_compact_no_per_post_scoring_section(self):
        posts = [
            _make_scored("a1", "Hype moon 🚀", "Avoid", "Poor opportunity", "fresh"),
        ]
        md = build_markdown("Signal Shift", posts, _make_posts_schedule(), mode="Tavily")
        self.assertNotIn("## Post Scoring & Reply Suggestions", md)

    def test_debug_mode_restores_scoring_section(self):
        os.environ["DIGEST_DEBUG"] = "true"
        posts = [
            _make_scored("a1", "Hype moon 🚀", "Avoid", "Poor opportunity", "fresh"),
        ]
        md = build_markdown("Signal Shift", posts, _make_posts_schedule(), mode="Tavily")
        self.assertIn("## Post Scoring & Reply Suggestions", md)

    def test_rejected_posts_not_in_worth_checking(self):
        posts = [
            _make_scored("rej1", "RSI crossover", "Weak fit", "Poor opportunity", "fresh"),
            _make_scored("rej2", "Moon 🚀", "Avoid", "Poor opportunity", "fresh"),
        ]
        wc = _get_worth_checking_posts(posts)
        self.assertEqual(wc, [])


# ---------------------------------------------------------------------------
# 11. Mock mode unchanged
# ---------------------------------------------------------------------------

class TestMockModeUnchangedM411(unittest.TestCase):

    def setUp(self):
        os.environ.pop("DIGEST_DEBUG", None)

    def tearDown(self):
        os.environ.pop("DIGEST_DEBUG", None)

    def test_mock_posts_score_correctly(self):
        from mock_data.posts import MOCK_POSTS
        scored = score_posts(MOCK_POSTS)
        self.assertEqual(scored[0]["score"], "Strong fit")
        self.assertEqual(scored[6]["score"], "Avoid")

    def test_mock_replies_still_use_hardcoded_data(self):
        from mock_data.posts import MOCK_POSTS
        scored = score_posts(MOCK_POSTS)
        with_replies = generate_replies(scored)
        # Mock post 1 should use hardcoded reply, not dynamic templates
        self.assertIn("Earnings week", with_replies[0]["replies"][0]["text"])

    def test_mock_digest_builds_without_debug(self):
        from mock_data.posts import MOCK_POSTS
        scored = score_posts(MOCK_POSTS)
        with_replies = generate_replies(scored)
        schedule = generate_posts(0)
        md = build_markdown("Signal Shift", with_replies, schedule, mode="Mock")
        self.assertIn("## Today's Best 3", md)
        self.assertNotIn("## Post Scoring & Reply Suggestions", md)

    def test_mock_digest_best3_shows_reply_options(self):
        from mock_data.posts import MOCK_POSTS
        scored = score_posts(MOCK_POSTS)
        with_replies = generate_replies(scored)
        schedule = generate_posts(0)
        md = build_markdown("Signal Shift", with_replies, schedule, mode="Mock")
        self.assertIn("Reply options:", md)

    def test_mock_best3_shows_media_guidance(self):
        from mock_data.posts import MOCK_POSTS
        scored = score_posts(MOCK_POSTS)
        with_replies = generate_replies(scored)
        schedule = generate_posts(0)
        md = build_markdown("Signal Shift", with_replies, schedule, mode="Mock")
        self.assertIn("**Media:**", md)


if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(__import__("__main__"))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
