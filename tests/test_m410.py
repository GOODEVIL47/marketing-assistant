"""
Tests for M4.10: Compact Tavily digest output.
No real API calls, no network access.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import yaml
from src.scorer import score_posts, _age_label
from src.digest import (
    build_markdown,
    _build_best_3,
    _build_inspiration,
    _categorize_rejected,
    _build_rejected_summary,
)
from src.email_renderer import render_digest_html, render_digest_text
from src.replier import generate_replies
from src.post_generator import generate_posts


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_profile():
    yaml_path = os.path.join(os.path.dirname(__file__), "..", "profiles", "signal_shift.yaml")
    with open(yaml_path) as f:
        return yaml.safe_load(f)


def _make_web_post(
    text,
    tweet_id="1900000000000000001",
    age_hours=6,
    score=None,
    freshness_tier=None,
    out_of_scope=False,
    opportunity=None,
    inspiration_angles=None,
):
    """Build a pre-scored post dict directly for digest/email tests."""
    post = {
        "id": tweet_id,
        "author": "@test_user",
        "author_name": "test_user",
        "author_followers": 0,
        "author_profile_url": "https://x.com/test_user",
        "text": text,
        "likes": 0,
        "reposts": 0,
        "reply_count": 0,
        "impressions": 0,
        "age_hours": age_hours,
        "age_source": "snowflake",
        "post_url": f"https://x.com/test_user/status/{tweet_id}",
        "url": f"https://x.com/test_user/status/{tweet_id}",
        "discovery_source": "tavily_search",
        "metrics_confidence": "low",
    }
    if score is not None:
        post["score"] = score
    if freshness_tier is not None:
        post["freshness_tier"] = freshness_tier
    if opportunity is not None:
        post["opportunity"] = opportunity
    if out_of_scope:
        post["out_of_scope"] = True
    if inspiration_angles is not None:
        post["inspiration_angles"] = inspiration_angles
    return post


def _score_web_post(text, tweet_id="1900000000000000001", age_hours=6):
    """Score a single web-search post through the full pipeline."""
    post = {
        "id": tweet_id,
        "author": "@test_user",
        "author_name": "test_user",
        "author_followers": 0,
        "author_profile_url": "https://x.com/test_user",
        "text": text,
        "likes": 0,
        "reposts": 0,
        "reply_count": 0,
        "impressions": 0,
        "age_hours": age_hours,
        "age_source": "snowflake",
        "post_url": f"https://x.com/test_user/status/{tweet_id}",
        "url": f"https://x.com/test_user/status/{tweet_id}",
        "discovery_source": "tavily_search",
        "metrics_confidence": "low",
    }
    profile = _load_profile()
    return score_posts([post], profile=profile)[0]


def _make_scored_posts():
    """
    Return a minimal set of pre-scored posts covering all reject categories,
    plus one Best-3-eligible post.
    """
    return [
        # Best 3 eligible: Strong fit, Medium opportunity
        {
            "id": "id_best",
            "author": "@good_user",
            "text": "Overwhelmed by earnings noise this week — retail investor confusion is real",
            "score": "Strong fit",
            "visibility": "Unknown visibility",
            "opportunity": "Medium opportunity",
            "opportunity_reason": "Fresh post, good fit.",
            "engagement_summary": "Engagement unknown",
            "age_label": "Age: 6h old",
            "age_hours": 6,
            "freshness_tier": "fresh",
            "out_of_scope": False,
            "reply_account": "Either",
            "suggested_action": "Reply",
            "reason": "Strong fit signals.",
            "metrics_confidence": "low",
            "replies": [],
            "best_reply": {"style": "Direct", "text": "Great point."},
            "media": {"type": "No media", "reason": ""},
            "post_url": "https://x.com/good_user/status/id_best",
            "author_profile_url": "https://x.com/good_user",
        },
        # Avoid
        {
            "id": "id_avoid",
            "author": "@hype_user",
            "text": "This stock will moon 🚀 — get in now",
            "score": "Avoid",
            "visibility": "Unknown visibility",
            "opportunity": "Poor opportunity",
            "opportunity_reason": "Avoid.",
            "engagement_summary": "Engagement unknown",
            "age_label": None,
            "age_hours": 6,
            "freshness_tier": "fresh",
            "out_of_scope": False,
            "reply_account": "Do not reply",
            "suggested_action": "Do not engage",
            "reason": "Hype content.",
            "metrics_confidence": "low",
            "replies": [],
            "best_reply": {},
            "media": {"type": "No media", "reason": ""},
            "post_url": "https://x.com/hype_user/status/id_avoid",
            "author_profile_url": "https://x.com/hype_user",
        },
        # Weak fit
        {
            "id": "id_weak",
            "author": "@ta_user",
            "text": "RSI crossover looks interesting on this chart",
            "score": "Weak fit",
            "visibility": "Unknown visibility",
            "opportunity": "Poor opportunity",
            "opportunity_reason": "Weak fit.",
            "engagement_summary": "Engagement unknown",
            "age_label": "Age: 6h old — not a reply target",
            "age_hours": 6,
            "freshness_tier": "fresh",
            "out_of_scope": False,
            "reply_account": "Do not reply",
            "suggested_action": "Do not engage",
            "reason": "TA content.",
            "metrics_confidence": "low",
            "replies": [],
            "best_reply": {},
            "media": {"type": "No media", "reason": ""},
            "post_url": "https://x.com/ta_user/status/id_weak",
            "author_profile_url": "https://x.com/ta_user",
        },
        # Stale
        {
            "id": "id_stale",
            "author": "@old_user",
            "text": "Market noise was overwhelming last month",
            "score": "Decent fit",
            "visibility": "Unknown visibility",
            "opportunity": "Poor opportunity",
            "opportunity_reason": "Too old.",
            "engagement_summary": "Engagement unknown",
            "age_label": "Age: 14d old — stale, do not reply",
            "age_hours": 14 * 24,
            "freshness_tier": "stale",
            "out_of_scope": False,
            "reply_account": "Do not reply",
            "suggested_action": "Do not engage",
            "reason": "Stale.",
            "metrics_confidence": "low",
            "replies": [],
            "best_reply": {},
            "media": {"type": "No media", "reason": ""},
            "post_url": "https://x.com/old_user/status/id_stale",
            "author_profile_url": "https://x.com/old_user",
        },
        # Out of scope
        {
            "id": "id_oos",
            "author": "@india_user",
            "text": "Nifty down 3% — retail investors in India are overwhelmed",
            "score": "Decent fit",
            "visibility": "Unknown visibility",
            "opportunity": "Low opportunity",
            "opportunity_reason": "Out of scope.",
            "engagement_summary": "Engagement unknown",
            "age_label": "Age: 6h old — outside current product scope",
            "age_hours": 6,
            "freshness_tier": "fresh",
            "out_of_scope": True,
            "reply_account": "Do not reply",
            "suggested_action": "Do not engage",
            "reason": "Out of scope.",
            "metrics_confidence": "low",
            "replies": [],
            "best_reply": {},
            "media": {"type": "No media", "reason": ""},
            "post_url": "https://x.com/india_user/status/id_oos",
            "author_profile_url": "https://x.com/india_user",
        },
    ]


def _make_posts_schedule():
    return {
        "founder": {
            "handle": "@yourhandle",
            "needed": False,
            "reason": "Already posted today.",
            "post": None,
            "optional_idea": None,
        },
        "product": {
            "handle": "@SignalShiftCo",
            "needed": False,
            "reason": "Already posted today.",
            "post": None,
            "optional_idea": None,
        },
    }


# ---------------------------------------------------------------------------
# 1. _age_label — fit-aware labels
# ---------------------------------------------------------------------------

class TestAgeLabelFitAware(unittest.TestCase):

    def _post(self, age_hours):
        return {
            "age_hours": age_hours,
            "age_source": "snowflake",
        }

    def test_weak_fit_old_is_not_a_reply_target(self):
        label = _age_label(self._post(72), fit_score="Weak fit")
        self.assertIn("not a reply target", label)
        self.assertNotIn("save for inspiration", label)

    def test_avoid_old_is_not_a_reply_target(self):
        label = _age_label(self._post(96), fit_score="Avoid")
        self.assertIn("not a reply target", label)
        self.assertNotIn("save for inspiration", label)

    def test_strong_fit_old_is_save_for_inspiration(self):
        label = _age_label(self._post(72), fit_score="Strong fit")
        self.assertIn("save for inspiration", label)

    def test_decent_fit_old_is_save_for_inspiration(self):
        label = _age_label(self._post(96), fit_score="Decent fit")
        self.assertIn("save for inspiration", label)

    def test_out_of_scope_old_is_outside_scope(self):
        label = _age_label(self._post(72), fit_score="Strong fit", out_of_scope=True)
        self.assertIn("outside current product scope", label)
        self.assertNotIn("save for inspiration", label)

    def test_fresh_post_no_qualifier(self):
        label = _age_label(self._post(6), fit_score="Weak fit")
        self.assertNotIn("not a reply target", label)
        self.assertNotIn("save for inspiration", label)

    def test_stale_post_unchanged(self):
        label = _age_label(self._post(200), fit_score="Weak fit")
        self.assertIn("stale, do not reply", label)

    def test_snowflake_suffix_present(self):
        label = _age_label(self._post(72), fit_score="Strong fit")
        self.assertIn("estimated from X status ID", label)


# ---------------------------------------------------------------------------
# 2. score_posts wires fit_score into age_label
# ---------------------------------------------------------------------------

class TestScorePostsAgeLabelWired(unittest.TestCase):

    def test_weak_fit_post_age_label_not_save_for_inspiration(self):
        scored = _score_web_post("RSI crossover on this chart — entry point looks clean", age_hours=72)
        self.assertEqual(scored["score"], "Weak fit")
        self.assertIsNotNone(scored.get("age_label"))
        self.assertNotIn("save for inspiration", scored["age_label"])
        self.assertIn("not a reply target", scored["age_label"])

    def test_strong_fit_post_age_label_is_save_for_inspiration(self):
        scored = _score_web_post(
            "Overwhelmed by earnings noise this week — retail investor confusion is real.",
            age_hours=72,
        )
        self.assertIn(scored["score"], ("Strong fit", "Decent fit"))
        self.assertIsNotNone(scored.get("age_label"))
        self.assertIn("save for inspiration", scored["age_label"])


# ---------------------------------------------------------------------------
# 3. _categorize_rejected
# ---------------------------------------------------------------------------

class TestCategorizeRejected(unittest.TestCase):

    def test_avoid_post_in_avoid_category(self):
        posts = _make_scored_posts()
        cats = _categorize_rejected(posts)
        authors = [p["author"] for p in cats["avoid"]]
        self.assertIn("@hype_user", authors)

    def test_weak_post_in_weak_category(self):
        posts = _make_scored_posts()
        cats = _categorize_rejected(posts)
        authors = [p["author"] for p in cats["weak"]]
        self.assertIn("@ta_user", authors)

    def test_stale_post_in_stale_category(self):
        posts = _make_scored_posts()
        cats = _categorize_rejected(posts)
        authors = [p["author"] for p in cats["stale"]]
        self.assertIn("@old_user", authors)

    def test_out_of_scope_post_in_oos_category(self):
        posts = _make_scored_posts()
        cats = _categorize_rejected(posts)
        authors = [p["author"] for p in cats["out_of_scope"]]
        self.assertIn("@india_user", authors)

    def test_best3_post_excluded_from_rejected(self):
        posts = _make_scored_posts()
        cats = _categorize_rejected(posts)
        all_rejected = (
            cats["avoid"] + cats["weak"] + cats["stale"] + cats["out_of_scope"] + cats["other"]
        )
        authors = [p["author"] for p in all_rejected]
        self.assertNotIn("@good_user", authors)

    def test_inspiration_post_excluded_from_rejected(self):
        posts = [
            {
                "id": "id_insp",
                "author": "@inspiration_user",
                "text": "Noise in markets is real — retail overwhelm is growing",
                "score": "Strong fit",
                "visibility": "Unknown visibility",
                "opportunity": "Low opportunity",
                "opportunity_reason": "Old post.",
                "engagement_summary": "Engagement unknown",
                "age_label": "Age: 4d old — save for inspiration",
                "age_hours": 96,
                "freshness_tier": "old",
                "out_of_scope": False,
                "reply_account": "Either",
                "suggested_action": "Save for inspiration",
                "reason": "Strong signals.",
                "metrics_confidence": "low",
                "replies": [],
                "best_reply": {},
                "media": {"type": "No media", "reason": ""},
                "post_url": "https://x.com/inspiration_user/status/id_insp",
                "author_profile_url": "https://x.com/inspiration_user",
                "inspiration_angles": ["Write about the noise problem"],
            }
        ]
        cats = _categorize_rejected(posts)
        all_rejected = (
            cats["avoid"] + cats["weak"] + cats["stale"] + cats["out_of_scope"] + cats["other"]
        )
        self.assertEqual(len(all_rejected), 0)

    def test_counts_match_expected(self):
        posts = _make_scored_posts()
        cats = _categorize_rejected(posts)
        self.assertEqual(len(cats["avoid"]), 1)
        self.assertEqual(len(cats["weak"]), 1)
        self.assertEqual(len(cats["stale"]), 1)
        self.assertEqual(len(cats["out_of_scope"]), 1)


# ---------------------------------------------------------------------------
# 4. _build_rejected_summary
# ---------------------------------------------------------------------------

class TestBuildRejectedSummary(unittest.TestCase):

    def test_summary_has_total_count(self):
        posts = _make_scored_posts()
        lines = _build_rejected_summary(posts)
        content = "\n".join(lines)
        self.assertIn("4 posts scanned but not selected", content)

    def test_summary_has_avoid_count(self):
        posts = _make_scored_posts()
        lines = _build_rejected_summary(posts)
        content = "\n".join(lines)
        self.assertIn("Avoid", content)

    def test_summary_has_weak_count(self):
        posts = _make_scored_posts()
        lines = _build_rejected_summary(posts)
        content = "\n".join(lines)
        self.assertIn("Weak fit", content)

    def test_summary_has_stale_count(self):
        posts = _make_scored_posts()
        lines = _build_rejected_summary(posts)
        content = "\n".join(lines)
        self.assertIn("Stale", content)

    def test_summary_has_out_of_scope_count(self):
        posts = _make_scored_posts()
        lines = _build_rejected_summary(posts)
        content = "\n".join(lines)
        self.assertIn("Out of scope", content)

    def test_summary_has_examples_section(self):
        posts = _make_scored_posts()
        lines = _build_rejected_summary(posts)
        content = "\n".join(lines)
        self.assertIn("Examples", content)

    def test_examples_capped_at_3(self):
        posts = _make_scored_posts()
        lines = _build_rejected_summary(posts)
        example_lines = [l for l in lines if l.startswith("- @")]
        self.assertLessEqual(len(example_lines), 3)

    def test_empty_posts_returns_empty_list(self):
        posts = _make_scored_posts()[:1]  # only the Best 3 eligible post
        lines = _build_rejected_summary(posts)
        self.assertEqual(lines, [])

    def test_singular_count_phrasing(self):
        posts = _make_scored_posts()
        cats = _categorize_rejected(posts)
        # Check only the avoid category, by stripping others
        single_post = [p for p in posts if p["id"] == "id_avoid"]
        lines = _build_rejected_summary(single_post)
        content = "\n".join(lines)
        self.assertIn("1 post scanned", content)


# ---------------------------------------------------------------------------
# 5. build_markdown — compact mode (no DIGEST_DEBUG)
# ---------------------------------------------------------------------------

class TestBuildMarkdownCompact(unittest.TestCase):

    def setUp(self):
        os.environ.pop("DIGEST_DEBUG", None)

    def tearDown(self):
        os.environ.pop("DIGEST_DEBUG", None)

    def test_compact_mode_no_full_scoring_section(self):
        posts = _make_scored_posts()
        md = build_markdown("Signal Shift", posts, _make_posts_schedule(), mode="Tavily")
        self.assertNotIn("## Post Scoring & Reply Suggestions", md)

    def test_compact_mode_no_per_post_header_for_rejected(self):
        posts = _make_scored_posts()
        md = build_markdown("Signal Shift", posts, _make_posts_schedule(), mode="Tavily")
        # Rejected posts should not appear as ### Post ... headers
        self.assertNotIn("### Post id_avoid", md)
        self.assertNotIn("### Post id_weak", md)
        self.assertNotIn("### Post id_stale", md)

    def test_compact_mode_has_rejected_summary(self):
        posts = _make_scored_posts()
        md = build_markdown("Signal Shift", posts, _make_posts_schedule(), mode="Tavily")
        self.assertIn("Rejected Posts Summary", md)

    def test_compact_mode_best3_still_present(self):
        posts = _make_scored_posts()
        md = build_markdown("Signal Shift", posts, _make_posts_schedule(), mode="Tavily")
        self.assertIn("## Today's Best 3", md)

    def test_compact_mode_original_posts_still_present(self):
        posts = _make_scored_posts()
        md = build_markdown("Signal Shift", posts, _make_posts_schedule(), mode="Tavily")
        self.assertIn("## Original Posts to Publish", md)


# ---------------------------------------------------------------------------
# 6. build_markdown — debug mode (DIGEST_DEBUG=true)
# ---------------------------------------------------------------------------

class TestBuildMarkdownDebug(unittest.TestCase):

    def setUp(self):
        os.environ["DIGEST_DEBUG"] = "true"

    def tearDown(self):
        os.environ.pop("DIGEST_DEBUG", None)

    def test_debug_mode_includes_full_scoring_section(self):
        posts = _make_scored_posts()
        md = build_markdown("Signal Shift", posts, _make_posts_schedule(), mode="Tavily")
        self.assertIn("## Post Scoring & Reply Suggestions", md)

    def test_debug_mode_includes_all_post_headers(self):
        posts = _make_scored_posts()
        md = build_markdown("Signal Shift", posts, _make_posts_schedule(), mode="Tavily")
        self.assertIn("### Post id_avoid", md)
        self.assertIn("### Post id_weak", md)

    def test_debug_mode_no_rejected_summary(self):
        posts = _make_scored_posts()
        md = build_markdown("Signal Shift", posts, _make_posts_schedule(), mode="Tavily")
        self.assertNotIn("Rejected Posts Summary", md)

    def test_debug_mode_case_insensitive_true(self):
        os.environ["DIGEST_DEBUG"] = "TRUE"
        posts = _make_scored_posts()
        md = build_markdown("Signal Shift", posts, _make_posts_schedule(), mode="Tavily")
        self.assertIn("## Post Scoring & Reply Suggestions", md)


# ---------------------------------------------------------------------------
# 7. _build_inspiration only includes Strong/Decent fit posts
# ---------------------------------------------------------------------------

class TestInspirationExcludesWeakAvoid(unittest.TestCase):

    def _make_old_post(self, tweet_id, author, score):
        return {
            "id": tweet_id,
            "author": author,
            "text": "Some text about market noise and investing",
            "score": score,
            "visibility": "Unknown visibility",
            "opportunity": "Low opportunity",
            "opportunity_reason": "Old post.",
            "engagement_summary": "Engagement unknown",
            "age_label": "Age: 4d old",
            "age_hours": 96,
            "freshness_tier": "old",
            "out_of_scope": False,
            "reply_account": "Do not reply",
            "suggested_action": "Do not engage",
            "reason": "Some reason.",
            "metrics_confidence": "low",
            "replies": [],
            "best_reply": {},
            "media": {"type": "No media", "reason": ""},
            "post_url": f"https://x.com/{author}/status/{tweet_id}",
            "author_profile_url": f"https://x.com/{author}",
            "inspiration_angles": ["An angle for original content"],
        }

    def test_weak_fit_old_post_not_in_inspiration(self):
        posts = [self._make_old_post("id1", "@ta_user", "Weak fit")]
        result = _build_inspiration(posts)
        self.assertEqual(result, [])

    def test_avoid_old_post_not_in_inspiration(self):
        posts = [self._make_old_post("id2", "@hype_user", "Avoid")]
        result = _build_inspiration(posts)
        self.assertEqual(result, [])

    def test_strong_fit_old_post_in_inspiration(self):
        posts = [self._make_old_post("id3", "@good_user", "Strong fit")]
        result = _build_inspiration(posts)
        self.assertNotEqual(result, [])

    def test_decent_fit_old_post_in_inspiration(self):
        posts = [self._make_old_post("id4", "@decent_user", "Decent fit")]
        result = _build_inspiration(posts)
        self.assertNotEqual(result, [])


# ---------------------------------------------------------------------------
# 8. Email HTML includes Rejected Summary, no full rejected blocks
# ---------------------------------------------------------------------------

class TestEmailHtmlRejectedSummary(unittest.TestCase):

    def test_html_email_has_rejected_summary(self):
        posts = _make_scored_posts()
        html = render_digest_html("Signal Shift", posts, _make_posts_schedule(), mode="Tavily")
        self.assertIn("Rejected Posts", html)

    def test_html_email_rejected_summary_has_counts(self):
        posts = _make_scored_posts()
        html = render_digest_html("Signal Shift", posts, _make_posts_schedule(), mode="Tavily")
        self.assertIn("not selected", html)

    def test_html_email_no_full_post_scoring_blocks(self):
        posts = _make_scored_posts()
        html = render_digest_html("Signal Shift", posts, _make_posts_schedule(), mode="Tavily")
        # Full scoring for rejected posts (e.g. "Post Scoring & Reply Suggestions") must NOT appear
        self.assertNotIn("Post Scoring &amp; Reply Suggestions", html)
        self.assertNotIn("Post Scoring & Reply Suggestions", html)

    def test_html_email_still_shows_best3(self):
        posts = _make_scored_posts()
        html = render_digest_html("Signal Shift", posts, _make_posts_schedule(), mode="Tavily")
        self.assertIn("Today&apos;s Best 3", html)

    def test_html_email_rejected_examples_present(self):
        posts = _make_scored_posts()
        html = render_digest_html("Signal Shift", posts, _make_posts_schedule(), mode="Tavily")
        self.assertIn("Examples", html)


# ---------------------------------------------------------------------------
# 9. Email text includes Rejected Summary
# ---------------------------------------------------------------------------

class TestEmailTextRejectedSummary(unittest.TestCase):

    def test_text_email_has_rejected_section(self):
        posts = _make_scored_posts()
        text = render_digest_text("Signal Shift", posts, _make_posts_schedule(), mode="Tavily")
        self.assertIn("REJECTED POSTS", text)

    def test_text_email_has_not_selected_count(self):
        posts = _make_scored_posts()
        text = render_digest_text("Signal Shift", posts, _make_posts_schedule(), mode="Tavily")
        self.assertIn("not selected", text)

    def test_text_email_no_rejected_section_when_none(self):
        # Only the Best 3 eligible post — nothing is rejected
        posts = _make_scored_posts()[:1]
        text = render_digest_text("Signal Shift", posts, _make_posts_schedule(), mode="Tavily")
        self.assertNotIn("REJECTED POSTS", text)


# ---------------------------------------------------------------------------
# 10. Mock mode unchanged
# ---------------------------------------------------------------------------

class TestMockModeUnchangedM410(unittest.TestCase):

    def test_mock_posts_score_correctly(self):
        from mock_data.posts import MOCK_POSTS
        scored = score_posts(MOCK_POSTS)
        self.assertEqual(scored[0]["score"], "Strong fit")
        self.assertEqual(scored[6]["score"], "Avoid")

    def test_mock_digest_still_builds(self):
        from mock_data.posts import MOCK_POSTS
        scored = score_posts(MOCK_POSTS)
        with_replies = generate_replies(scored)
        posts_schedule = generate_posts(0)
        md = build_markdown("Signal Shift", with_replies, posts_schedule, mode="Mock")
        self.assertIn("## Today's Best 3", md)

    def test_mock_email_still_renders(self):
        from mock_data.posts import MOCK_POSTS
        scored = score_posts(MOCK_POSTS)
        with_replies = generate_replies(scored)
        posts_schedule = generate_posts(0)
        html = render_digest_html("Signal Shift", with_replies, posts_schedule, mode="Mock")
        self.assertIn("Mel", html)

    def test_mock_mode_no_debug_section_by_default(self):
        os.environ.pop("DIGEST_DEBUG", None)
        from mock_data.posts import MOCK_POSTS
        scored = score_posts(MOCK_POSTS)
        with_replies = generate_replies(scored)
        posts_schedule = generate_posts(0)
        md = build_markdown("Signal Shift", with_replies, posts_schedule, mode="Mock")
        self.assertNotIn("## Post Scoring & Reply Suggestions", md)


if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(__import__("__main__"))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
