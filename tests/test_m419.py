"""
M4.19 — Output Contract Polish: Reply + Original Post Format/Media Guidance

Tests cover:
- _render_media_block() generic field rendering, "Media/GIF:" label
- _fill_media_fallbacks() role-appropriate defaults when med is empty
- _normalize_format_label() strips prefix, maps to clean label
- _format_reason_for() returns non-empty reason for known labels
- _manual_review_note() Tavily vs non-Tavily
- _build_best_3() contract fields; no "Reply from:"; Tavily note; media always present
- _build_worth_checking() contract fields
- _build_original_posts() contract fields; Founder/Product media fallbacks; mode note
- render_digest_text() contract fields
- render_digest_html() contract fields
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.digest import (
    _render_media_block,
    _fill_media_fallbacks,
    _normalize_format_label,
    _format_reason_for,
    _manual_review_note,
    _build_best_3,
    _build_worth_checking,
    _build_original_posts,
)
from src.email_renderer import render_digest_text, render_digest_html


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _base_scored_post(**overrides):
    post = {
        "id": "1000000000000000001",
        "author": "@trader_person",
        "text": "Nasdaq 100 down today, my thesis is unchanged though.",
        "combined_text_for_scoring": "Nasdaq 100 down today, my thesis is unchanged though.",
        "score": "Strong fit",
        "opportunity": "High opportunity",
        "visibility": "Unknown visibility",
        "engagement_summary": "145 likes · 23 reposts · unknown impressions",
        "age_label": "2h ago",
        "post_url": "https://x.com/trader_person/status/1000000000000000001",
        "reply_account": "Founder",
        "suggested_action": "Reply",
        "best_reply": {
            "style": "B — Casual paragraph",
            "text": "The stock moved. Your analysis didn't break.",
        },
        "replies": [
            {"style": "A — One-liner", "text": "Price change != thesis change."},
            {"style": "B — Casual paragraph", "text": "The stock moved. Your analysis didn't break."},
            {"style": "C — Sharper take", "text": "If you bought for the fundamentals, one down day isn't a signal."},
        ],
        "media": {
            "type": "Optional GIF",
            "idea": "overwhelmed trader at multiple screens",
            "use_if": "the post shows emotional/reactive tone",
            "skip_if": "the reply is purely analytical",
        },
        "reason": "Strong fit — trader reacting emotionally to market noise.",
        "opportunity_reason": "High engagement, fresh post, relevant to Signal Shift.",
        "freshness_tier": "fresh",
        "metrics_confidence": "low",
        "discovery_source": "mock",
        "out_of_scope": False,
        "inspiration_angles": None,
        "reply_note": None,
        "author_followers": 0,
    }
    post.update(overrides)
    return post


def _tavily_post(**overrides):
    return _base_scored_post(
        id="1000000000000000002",
        discovery_source="tavily_search",
        **overrides,
    )


def _low_opp_post(**overrides):
    return _base_scored_post(
        id="1000000000000000003",
        score="Decent fit",
        opportunity="Low opportunity",
        metrics_confidence="low",
        freshness_tier="fresh",
        opportunity_reason="Unknown engagement — check manually.",
        **overrides,
    )


def _posts_schedule(
    founder_needed=True,
    founder_media=None,
    founder_has_media_key=True,
    product_needed=True,
    product_media=None,
    product_has_media_key=True,
):
    founder_post = {
        "text": "The stock moved. Your thesis didn't.",
        "format": {"type": "One-liner", "reason": "Short and punchy — lands the point without noise."},
    }
    if founder_has_media_key:
        founder_post["media"] = founder_media  # could be None or a dict

    product_post = {
        "text": "Signal Shift helps you cut through market noise.",
        "format": {"type": "Short paragraph", "reason": "Conversational, sounds like a founder."},
    }
    if product_has_media_key:
        product_post["media"] = product_media  # could be None or a dict

    schedule = {
        "founder": {
            "handle": "Founder",
            "needed": founder_needed,
            "reason": "High market noise today — good time for a clarity take.",
            "post": founder_post if founder_needed else {},
            "optional_idea": None,
        },
        "product": {
            "handle": "Product",
            "needed": product_needed,
            "reason": "Good timing for a product post.",
            "post": product_post if product_needed else {},
            "optional_idea": None,
        },
    }
    return schedule


def _has_market_signal_stub(post):
    return True


# ---------------------------------------------------------------------------
# TestRenderMediaBlock
# ---------------------------------------------------------------------------

class TestMediaGIFLabel(unittest.TestCase):
    """_render_media_block() outputs 'Media/GIF:' not 'Media:'."""

    def _render(self, media):
        lines = []
        _render_media_block(media, lines)
        return "\n".join(lines)

    def test_optional_gif_uses_media_gif_label(self):
        out = self._render({"type": "Optional GIF", "idea": "x", "use_if": "y", "skip_if": "z"})
        self.assertIn("**Media/GIF:** Optional GIF", out)
        self.assertNotIn("**Media:** ", out)

    def test_no_media_uses_media_gif_label(self):
        out = self._render({"type": "No media", "reason": "Clean text."})
        self.assertIn("**Media/GIF:** No media", out)
        self.assertNotIn("**Media:** ", out)

    def test_simple_branded_image_uses_media_gif_label(self):
        out = self._render({"type": "Simple branded image", "idea": "card"})
        self.assertIn("**Media/GIF:** Simple branded image", out)

    def test_empty_media_renders_nothing(self):
        lines = []
        _render_media_block({}, lines)
        self.assertEqual(lines, [])


class TestMediaFieldsGeneric(unittest.TestCase):
    """_render_media_block() shows idea/use_if/skip_if/reason for any type."""

    def _render(self, media):
        lines = []
        _render_media_block(media, lines)
        return "\n".join(lines)

    def test_idea_shown_when_present(self):
        out = self._render({"type": "Optional GIF", "idea": "calm moment"})
        self.assertIn("**Media idea:** calm moment", out)

    def test_use_if_shown_when_present(self):
        out = self._render({"type": "Optional GIF", "use_if": "casual tone"})
        self.assertIn("**Use media if:** casual tone", out)

    def test_skip_if_shown_when_present(self):
        out = self._render({"type": "Optional GIF", "skip_if": "analytical post"})
        self.assertIn("**Skip media if:** analytical post", out)

    def test_reason_shown_for_no_media(self):
        out = self._render({"type": "No media", "reason": "Let the words do the work."})
        self.assertIn("**Reason:**", out)
        self.assertIn("Let the words do the work.", out)

    def test_reason_shown_for_any_type(self):
        out = self._render({"type": "Simple branded image", "reason": "Product post best practice."})
        self.assertIn("**Reason:**", out)

    def test_only_type_shown_when_no_sub_fields(self):
        out = self._render({"type": "Text card"})
        self.assertIn("**Media/GIF:** Text card", out)
        self.assertNotIn("**Media idea:**", out)
        self.assertNotIn("**Use media if:**", out)


# ---------------------------------------------------------------------------
# TestFillMediaFallbacks
# ---------------------------------------------------------------------------

class TestFillMediaFallbacks(unittest.TestCase):

    def test_empty_founder_returns_no_media_default(self):
        result = _fill_media_fallbacks({}, role="founder")
        self.assertEqual(result["type"], "No media")
        self.assertIn("reason", result)
        self.assertTrue(result["reason"])

    def test_none_founder_returns_no_media_default(self):
        result = _fill_media_fallbacks(None, role="founder")
        self.assertEqual(result["type"], "No media")

    def test_empty_product_returns_simple_branded_image(self):
        result = _fill_media_fallbacks({}, role="product")
        self.assertEqual(result["type"], "Simple branded image")
        self.assertIn("idea", result)
        self.assertIn("use_if", result)
        self.assertIn("skip_if", result)
        self.assertIn("reason", result)

    def test_none_product_returns_simple_branded_image(self):
        result = _fill_media_fallbacks(None, role="product")
        self.assertEqual(result["type"], "Simple branded image")

    def test_existing_media_preserved(self):
        med = {"type": "Optional GIF", "idea": "custom idea"}
        result = _fill_media_fallbacks(med, role="founder")
        self.assertEqual(result["idea"], "custom idea")
        self.assertEqual(result["type"], "Optional GIF")

    def test_missing_fields_filled_from_fallbacks(self):
        med = {"type": "Optional GIF"}
        result = _fill_media_fallbacks(med, role="founder")
        self.assertIn("idea", result)
        self.assertIn("use_if", result)
        self.assertIn("skip_if", result)

    def test_simple_branded_image_gets_fallbacks(self):
        med = {"type": "Simple branded image"}
        result = _fill_media_fallbacks(med)
        self.assertIn("idea", result)
        self.assertIn("use_if", result)
        self.assertIn("skip_if", result)

    def test_role_case_insensitive(self):
        result = _fill_media_fallbacks({}, role="Product")
        self.assertEqual(result["type"], "Simple branded image")


# ---------------------------------------------------------------------------
# TestNormalizeFormatLabel
# ---------------------------------------------------------------------------

class TestNormalizeFormatLabel(unittest.TestCase):

    def test_strips_letter_prefix(self):
        self.assertEqual(_normalize_format_label("B — Casual paragraph"), "Short paragraph")

    def test_one_liner_maps_correctly(self):
        self.assertEqual(_normalize_format_label("One-liner"), "One-liner")

    def test_short_and_clean_maps_to_one_liner(self):
        self.assertEqual(_normalize_format_label("Short and clean"), "One-liner")

    def test_two_three_line_structure_maps_to_three_liner(self):
        self.assertEqual(_normalize_format_label("2-3 line structure"), "Three-liner")

    def test_context_aware_maps_to_paragraph(self):
        self.assertEqual(_normalize_format_label("Context-aware"), "Context-aware paragraph")

    def test_context_aware_with_prefix(self):
        self.assertEqual(_normalize_format_label("C — Context-aware"), "Context-aware paragraph")

    def test_unknown_label_returned_as_is(self):
        self.assertEqual(_normalize_format_label("Something new"), "Something new")

    def test_sharper_take(self):
        self.assertEqual(_normalize_format_label("Sharper take"), "Sharper take")


# ---------------------------------------------------------------------------
# TestFormatReasonLookup
# ---------------------------------------------------------------------------

class TestFormatReasonLookup(unittest.TestCase):

    def test_one_liner_returns_reason(self):
        reason = _format_reason_for("One-liner")
        self.assertTrue(reason)
        self.assertNotEqual(reason, "One-liner")

    def test_b_casual_paragraph_returns_reason(self):
        reason = _format_reason_for("B — Casual paragraph")
        self.assertTrue(reason)

    def test_context_aware_returns_reason(self):
        reason = _format_reason_for("C — Context-aware")
        self.assertTrue(reason)
        self.assertNotEqual(reason, "C — Context-aware")

    def test_sharper_take_returns_reason(self):
        reason = _format_reason_for("Sharper take")
        self.assertTrue(reason)

    def test_unknown_style_returns_label_string(self):
        result = _format_reason_for("Brand new style")
        self.assertTrue(result)


# ---------------------------------------------------------------------------
# TestManualReviewNoteHelper
# ---------------------------------------------------------------------------

class TestManualReviewNoteHelper(unittest.TestCase):

    def test_tavily_returns_note(self):
        note = _manual_review_note({"discovery_source": "tavily_search"})
        self.assertTrue(note)
        self.assertIn("Tavily", note)

    def test_x_api_returns_empty(self):
        note = _manual_review_note({"discovery_source": "x_api"})
        self.assertEqual(note, "")

    def test_mock_returns_empty(self):
        note = _manual_review_note({"discovery_source": "mock"})
        self.assertEqual(note, "")

    def test_missing_field_returns_empty(self):
        note = _manual_review_note({})
        self.assertEqual(note, "")


# ---------------------------------------------------------------------------
# TestContractFormatReplyLead (_build_best_3)
# ---------------------------------------------------------------------------

class TestContractFormatReplyLead(unittest.TestCase):

    def setUp(self):
        self.post = _base_scored_post()
        self.md = "\n".join(_build_best_3([self.post]))

    def test_recommended_format_present(self):
        self.assertIn("**Recommended format:**", self.md)

    def test_recommended_copy_present(self):
        self.assertIn("**Recommended copy:**", self.md)

    def test_why_this_format_present(self):
        self.assertIn("**Why this format:**", self.md)

    def test_account_present(self):
        self.assertIn("**Account:** Founder", self.md)

    def test_other_options_present(self):
        self.assertIn("**Other options:**", self.md)

    def test_media_gif_present(self):
        self.assertIn("**Media/GIF:**", self.md)

    def test_media_idea_present(self):
        self.assertIn("**Media idea:**", self.md)


class TestContractNoReplyFromLine(unittest.TestCase):

    def test_no_reply_from_label(self):
        post = _base_scored_post()
        md = "\n".join(_build_best_3([post]))
        self.assertNotIn("Reply from:", md)


class TestManualReviewNoteTavilyInDigest(unittest.TestCase):

    def test_tavily_post_has_manual_review_note(self):
        post = _tavily_post()
        md = "\n".join(_build_best_3([post]))
        self.assertIn("**Manual review note:**", md)
        self.assertIn("Tavily", md)


class TestManualReviewNoteMockAbsent(unittest.TestCase):

    def test_mock_post_has_no_manual_review_note(self):
        post = _base_scored_post(discovery_source="mock")
        md = "\n".join(_build_best_3([post]))
        self.assertNotIn("**Manual review note:**", md)


class TestMediaAlwaysPresentInBest3(unittest.TestCase):

    def test_post_without_media_still_shows_media_gif(self):
        post = _base_scored_post()
        post.pop("media", None)  # remove media entirely
        md = "\n".join(_build_best_3([post]))
        self.assertIn("**Media/GIF:**", md)

    def test_post_with_none_media_still_shows_media_gif(self):
        post = _base_scored_post(media=None)
        md = "\n".join(_build_best_3([post]))
        self.assertIn("**Media/GIF:**", md)


class TestOtherOptionsAbsentWhenOneReply(unittest.TestCase):

    def test_single_reply_no_other_options_section(self):
        post = _base_scored_post()
        post["replies"] = [{"style": "B — Casual paragraph", "text": "The stock moved."}]
        post["best_reply"] = {"style": "B — Casual paragraph", "text": "The stock moved."}
        md = "\n".join(_build_best_3([post]))
        self.assertNotIn("**Other options:**", md)


class TestBestReplyNoneEdgeCase(unittest.TestCase):

    def test_no_best_reply_renders_without_crash(self):
        post = _base_scored_post()
        post["best_reply"] = None
        post["replies"] = []
        md = "\n".join(_build_best_3([post]))
        self.assertIn("**Account:** Founder", md)
        self.assertNotIn("**Recommended format:**", md)


# ---------------------------------------------------------------------------
# TestWorthCheckingContractFormat
# ---------------------------------------------------------------------------

class TestWorthCheckingContractFormat(unittest.TestCase):

    def _make_wc_post(self):
        # Need a post that passes _get_worth_checking_posts filter:
        # score in Strong/Decent, opportunity Low, metrics_confidence low,
        # freshness_tier NOT stale/old, has market signal
        post = _low_opp_post()
        post["text"] = "Nasdaq 100 down today. $AAPL earnings tomorrow. Market confused."
        post["combined_text_for_scoring"] = post["text"]
        return post

    def setUp(self):
        import src.digest as d
        original = d._has_market_signal
        d._has_market_signal = _has_market_signal_stub

        post = self._make_wc_post()
        from src.digest import _get_worth_checking_posts
        eligible = [post] if _get_worth_checking_posts([post]) else [post]
        self.md = "\n".join(_build_worth_checking([post]))

        d._has_market_signal = original

    def test_account_present(self):
        self.assertIn("**Account:**", self.md)

    def test_media_gif_present(self):
        self.assertIn("**Media/GIF:**", self.md)


# ---------------------------------------------------------------------------
# TestOriginalPostContractFormat
# ---------------------------------------------------------------------------

class TestOriginalPostContractFormat(unittest.TestCase):

    def setUp(self):
        schedule = _posts_schedule(
            founder_media={"type": "Optional GIF", "idea": "calm moment", "use_if": "casual tone", "skip_if": "analytical"},
            product_media={"type": "Simple branded image", "reason": "branded"},
        )
        self.md = "\n".join(_build_original_posts(schedule, mode="Mock"))

    def test_recommended_format_present(self):
        self.assertIn("**Recommended format:**", self.md)

    def test_recommended_copy_present(self):
        self.assertIn("**Recommended copy:**", self.md)

    def test_why_this_format_present(self):
        self.assertIn("**Why this format:**", self.md)

    def test_account_present(self):
        self.assertIn("**Account:**", self.md)

    def test_media_gif_present(self):
        self.assertIn("**Media/GIF:**", self.md)


class TestOriginalPostFounderMediaGIF(unittest.TestCase):
    """Founder post with no media dict → shows No media with Reason."""

    def setUp(self):
        schedule = _posts_schedule(
            founder_media=None,
            product_media={"type": "Simple branded image", "reason": "branded"},
        )
        # Build only looking at founder section
        self.md = "\n".join(_build_original_posts(schedule, mode="Mock"))

    def test_founder_shows_no_media_type(self):
        self.assertIn("**Media/GIF:** No media", self.md)

    def test_founder_shows_reason(self):
        self.assertIn("**Reason:**", self.md)


class TestOriginalPostProductMediaFallback(unittest.TestCase):
    """Product post with no media dict → shows Simple branded image with sub-fields."""

    def setUp(self):
        schedule = _posts_schedule(
            founder_media={"type": "No media", "reason": "text only"},
            product_media=None,
        )
        self.md = "\n".join(_build_original_posts(schedule, mode="Mock"))

    def test_product_shows_simple_branded_image(self):
        self.assertIn("**Media/GIF:** Simple branded image", self.md)

    def test_product_shows_media_idea(self):
        self.assertIn("**Media idea:**", self.md)

    def test_product_shows_use_media_if(self):
        self.assertIn("**Use media if:**", self.md)

    def test_product_shows_skip_media_if(self):
        self.assertIn("**Skip media if:**", self.md)


class TestOriginalPostManualReviewNoteMockAbsent(unittest.TestCase):

    def test_mock_mode_no_manually_before_posting(self):
        schedule = _posts_schedule()
        md = "\n".join(_build_original_posts(schedule, mode="Mock"))
        self.assertNotIn("manually before posting", md)


class TestOriginalPostManualReviewNoteNonMock(unittest.TestCase):

    def test_non_mock_shows_manual_review_note(self):
        schedule = _posts_schedule()
        md = "\n".join(_build_original_posts(schedule, mode="Tavily"))
        self.assertIn("**Manual review note:**", md)
        self.assertIn("manually before posting", md)


# ---------------------------------------------------------------------------
# Email renderer tests
# ---------------------------------------------------------------------------

def _minimal_posts_with_replies():
    return [_base_scored_post()]


def _minimal_posts_schedule():
    return _posts_schedule()


class TestPlaintextEmailContractFields(unittest.TestCase):

    def setUp(self):
        posts = _minimal_posts_with_replies()
        schedule = _minimal_posts_schedule()
        self.text = render_digest_text("Signal Shift", posts, schedule, mode="Mock")

    def test_recommended_format_present(self):
        self.assertIn("Recommended format:", self.text)

    def test_media_gif_present(self):
        self.assertIn("Media/GIF:", self.text)

    def test_account_present(self):
        self.assertIn("Account:", self.text)


class TestPlaintextEmailManualReviewNote(unittest.TestCase):

    def test_tavily_post_has_manual_review_note(self):
        posts = [_tavily_post()]
        schedule = _minimal_posts_schedule()
        text = render_digest_text("Signal Shift", posts, schedule, mode="Mock")
        self.assertIn("Manual review note:", text)


class TestPlaintextEmailNoReplyFrom(unittest.TestCase):

    def test_no_standalone_reply_from_line(self):
        posts = _minimal_posts_with_replies()
        schedule = _minimal_posts_schedule()
        text = render_digest_text("Signal Shift", posts, schedule, mode="Mock")
        # "Reply from:" should not appear as a standalone line
        for line in text.splitlines():
            self.assertNotIn("Reply from:", line.strip())


class TestPlaintextEmailOriginalPostsMedia(unittest.TestCase):

    def test_original_posts_have_media_gif(self):
        posts = _minimal_posts_with_replies()
        schedule = _posts_schedule(founder_media=None, product_media=None)
        text = render_digest_text("Signal Shift", posts, schedule, mode="Mock")
        self.assertIn("Media/GIF:", text)
        any_guidance = any(
            field in text
            for field in ("Media idea:", "Use media if:", "Skip media if:", "Reason:")
        )
        self.assertTrue(any_guidance, "Original posts media block should have at least one guidance field")


class TestHTMLEmailContractFields(unittest.TestCase):

    def setUp(self):
        posts = _minimal_posts_with_replies()
        schedule = _minimal_posts_schedule()
        self.html = render_digest_html("Signal Shift", posts, schedule, mode="Mock")

    def test_recommended_format_in_html(self):
        self.assertIn("Recommended format", self.html)

    def test_media_gif_in_html(self):
        self.assertIn("Media/GIF", self.html)

    def test_account_in_html(self):
        self.assertIn("Account:", self.html)

    def test_no_reply_from_in_html(self):
        self.assertNotIn("Reply from:", self.html)


class TestHTMLEmailOriginalPostsContract(unittest.TestCase):

    def test_original_posts_have_media_gif(self):
        posts = _minimal_posts_with_replies()
        schedule = _posts_schedule(founder_media=None, product_media=None)
        html = render_digest_html("Signal Shift", posts, schedule, mode="Mock")
        self.assertIn("Media/GIF", html)
        any_guidance = any(
            field in html
            for field in ("Media idea:", "Use media if:", "Skip media if:", "Reason:")
        )
        self.assertTrue(any_guidance, "Original posts HTML should have at least one media guidance field")

    def test_recommended_format_in_original_posts(self):
        posts = _minimal_posts_with_replies()
        schedule = _minimal_posts_schedule()
        html = render_digest_html("Signal Shift", posts, schedule, mode="Mock")
        self.assertIn("Recommended format", html)


if __name__ == "__main__":
    unittest.main()
