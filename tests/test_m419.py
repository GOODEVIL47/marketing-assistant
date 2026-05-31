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
    _display_account,
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

    def test_paragraph_bare_maps_to_short_paragraph(self):
        self.assertEqual(_normalize_format_label("Paragraph"), "Short paragraph")

    def test_paragraph_with_prefix_maps_to_short_paragraph(self):
        self.assertEqual(_normalize_format_label("B — Paragraph"), "Short paragraph")

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


# ---------------------------------------------------------------------------
# M4.19c tests
# ---------------------------------------------------------------------------

class TestDisplayAccount(unittest.TestCase):
    """_display_account() maps 'Either' to 'Founder by default'; leaves others unchanged."""

    def test_either_maps_to_founder_by_default(self):
        self.assertEqual(_display_account("Either"), "Founder by default")

    def test_founder_unchanged(self):
        self.assertEqual(_display_account("Founder"), "Founder")

    def test_product_unchanged(self):
        self.assertEqual(_display_account("Product"), "Product")

    def test_empty_string_unchanged(self):
        self.assertEqual(_display_account(""), "")


class TestDisplayAccountInMarkdownDigest(unittest.TestCase):
    """_build_best_3() renders 'Founder by default' when reply_account is 'Either'."""

    def test_either_shows_founder_by_default_in_best3(self):
        post = _base_scored_post(reply_account="Either")
        md = "\n".join(_build_best_3([post]))
        self.assertIn("Founder by default", md)
        self.assertNotIn("**Account:** Either", md)

    def test_either_shows_founder_by_default_in_worth_checking(self):
        post = _low_opp_post(reply_account="Either")
        md = "\n".join(_build_worth_checking([post]))
        self.assertIn("Founder by default", md)
        self.assertNotIn("**Account:** Either", md)


class TestDisplayAccountInPlaintext(unittest.TestCase):
    """render_digest_text() renders 'Founder by default' when reply_account is 'Either'."""

    def test_either_shows_founder_by_default(self):
        posts = [_base_scored_post(reply_account="Either")]
        schedule = _minimal_posts_schedule()
        text = render_digest_text("Signal Shift", posts, schedule, mode="Mock")
        self.assertIn("Founder by default", text)
        for line in text.splitlines():
            if "Account:" in line:
                self.assertNotIn("Either", line)


class TestDisplayAccountInHTML(unittest.TestCase):
    """render_digest_html() renders 'Founder by default' when reply_account is 'Either'."""

    def test_either_shows_founder_by_default_in_html(self):
        posts = [_base_scored_post(reply_account="Either")]
        schedule = _minimal_posts_schedule()
        html = render_digest_html("Signal Shift", posts, schedule, mode="Mock")
        self.assertIn("Founder by default", html)


class TestNoDuplicateTavilyWarningInHTMLCard(unittest.TestCase):
    """HTML email: source_note paragraph is gone from the card; only the replies block note remains."""

    def setUp(self):
        posts = [_tavily_post()]
        schedule = _minimal_posts_schedule()
        self.html = render_digest_html("Signal Shift", posts, schedule, mode="Mock")

    def test_found_via_web_search_in_engagement_line(self):
        self.assertIn("found via web search", self.html)

    def test_no_standalone_found_via_tavily_search_paragraph(self):
        # The old "Found via Tavily Search" source_note p-tag should be gone.
        # The signal "Found via Tavily" (capital F, full phrase) was the duplicate.
        self.assertNotIn("Found via Tavily Search", self.html)

    def test_manual_review_note_still_present_in_html(self):
        # HTML renders the Tavily note inline (with ⚠ symbol) rather than a "Manual review note:" label
        self.assertIn("Tavily search result", self.html)
        self.assertIn("verify post is live", self.html)


class TestGenericFallbackReplyVoice(unittest.TestCase):
    """Generic fallback replies are finance-native and contain no hype or advice language."""

    _HYPE_TERMS = [
        "buy", "sell", "hold", "invest now", "guaranteed", "explosive", "to the moon",
        "can't miss", "massive returns", "profit", "risk-free",
    ]
    _BUY_SELL_HOLD = {"buy", "sell", "hold"}

    def _get_generic_options_text(self):
        from src.replier import _DYNAMIC_TEMPLATES
        texts = []
        for key in ("generic_strong", "generic_decent"):
            fb = _DYNAMIC_TEMPLATES.get(key, {})
            for group in ("options", "options_b", "options_c"):
                for opt in fb.get(group, []):
                    texts.append(opt.get("text", ""))
        return texts

    def test_no_buy_sell_hold_recommendation(self):
        texts = self._get_generic_options_text()
        self.assertTrue(len(texts) > 0, "Expected generic fallback reply options")
        for text in texts:
            words = set(text.lower().split())
            overlap = words & self._BUY_SELL_HOLD
            self.assertEqual(overlap, set(), f"Found buy/sell/hold in: {text!r}")

    def test_no_hype_language(self):
        texts = self._get_generic_options_text()
        for text in texts:
            lower = text.lower()
            for term in self._HYPE_TERMS:
                if term in self._BUY_SELL_HOLD:
                    continue  # already checked above
                self.assertNotIn(term, lower, f"Found hype term {term!r} in: {text!r}")

    def test_market_context_language_present(self):
        texts = self._get_generic_options_text()
        market_terms = ["thesis", "move", "price", "market", "setup", "investor", "stock"]
        joined = " ".join(texts).lower()
        found = [t for t in market_terms if t in joined]
        self.assertTrue(len(found) >= 3, f"Expected market-context language; found only: {found}")


class TestOptionalIdeaInHTMLOriginalPosts(unittest.TestCase):
    """HTML original posts section renders optional_idea when post is not needed today."""

    def _make_schedule_with_optional_idea(self):
        schedule = _posts_schedule(founder_needed=False)
        schedule["founder"]["reason"] = "Founder already posted today."
        schedule["founder"]["optional_idea"] = {
            "note": "good angle if you have capacity",
            "text": "The market is noisy — here's what actually changed.",
            "format": {
                "type": "One-liner",
                "reason": "Short and punchy.",
            },
            "media": {
                "type": "No media",
                "reason": "Text lands clean.",
            },
        }
        return schedule

    def test_optional_idea_text_shown(self):
        posts = _minimal_posts_with_replies()
        schedule = self._make_schedule_with_optional_idea()
        html = render_digest_html("Signal Shift", posts, schedule, mode="Mock")
        self.assertIn("The market is noisy", html)

    def test_optional_idea_format_shown(self):
        posts = _minimal_posts_with_replies()
        schedule = self._make_schedule_with_optional_idea()
        html = render_digest_html("Signal Shift", posts, schedule, mode="Mock")
        self.assertIn("One-liner", html)

    def test_optional_idea_note_shown(self):
        posts = _minimal_posts_with_replies()
        schedule = self._make_schedule_with_optional_idea()
        html = render_digest_html("Signal Shift", posts, schedule, mode="Mock")
        self.assertIn("good angle if you have capacity", html)

    def test_no_optional_idea_renders_cleanly(self):
        posts = _minimal_posts_with_replies()
        schedule = _posts_schedule(founder_needed=False)
        schedule["founder"]["optional_idea"] = None
        html = render_digest_html("Signal Shift", posts, schedule, mode="Mock")
        # Should not crash and should still contain product content
        self.assertIn("Signal Shift", html)


# ---------------------------------------------------------------------------
# M4.19d tests — duplicate-label cleanup
# ---------------------------------------------------------------------------

class TestEngagementLineNoDuplicateWebSearch(unittest.TestCase):
    """HTML card engagement line must not repeat 'found via web search'."""

    def _make_tavily_low_confidence_post(self):
        # engagement_summary for low-confidence Tavily posts already embeds
        # "found via web search" via scorer._engagement_summary()
        return _tavily_post(
            metrics_confidence="low",
            engagement_summary="Engagement unknown · found via web search · ~14h old",
        )

    def test_no_duplicate_found_via_web_search(self):
        posts = [self._make_tavily_low_confidence_post()]
        schedule = _minimal_posts_schedule()
        html = render_digest_html("Signal Shift", posts, schedule, mode="Mock")
        # Count occurrences in the engagement paragraph area
        count = html.count("found via web search")
        self.assertEqual(count, 1, f"'found via web search' appeared {count} times, expected 1")

    def test_engagement_line_still_has_web_search_once(self):
        posts = [self._make_tavily_low_confidence_post()]
        schedule = _minimal_posts_schedule()
        html = render_digest_html("Signal Shift", posts, schedule, mode="Mock")
        self.assertIn("found via web search", html)


class TestMarkdownOptionalIdeaNoDoubleLabel(unittest.TestCase):
    """Markdown digest optional idea label must not repeat 'Optional idea'."""

    def _make_schedule_with_production_note(self):
        schedule = _posts_schedule(founder_needed=False)
        schedule["founder"]["optional_idea"] = {
            "note": "Optional idea — save for next scheduled post day",
            "text": "The market is noisy — here's what actually changed.",
            "format": {"type": "One-liner", "reason": "Short and punchy."},
            "media": {"type": "No media", "reason": "Text lands clean."},
        }
        return schedule

    def test_no_double_optional_idea_label(self):
        md = "\n".join(_build_original_posts(
            self._make_schedule_with_production_note(), mode="Mock"
        ))
        self.assertNotIn("Optional idea — Optional idea", md)
        self.assertNotIn("Optional idea (Optional idea", md)

    def test_optional_idea_label_present_once(self):
        md = "\n".join(_build_original_posts(
            self._make_schedule_with_production_note(), mode="Mock"
        ))
        self.assertIn("Optional idea", md)

    def test_custom_note_gets_prefix(self):
        schedule = _posts_schedule(founder_needed=False)
        schedule["founder"]["optional_idea"] = {
            "note": "save for next scheduled post day",
            "text": "The market is noisy.",
            "format": {"type": "One-liner", "reason": "Punchy."},
            "media": None,
        }
        md = "\n".join(_build_original_posts(schedule, mode="Mock"))
        self.assertIn("Optional idea — save for next scheduled post day", md)


class TestHTMLOptionalIdeaNoDoubleLabel(unittest.TestCase):
    """HTML email optional idea label must not repeat 'Optional idea'."""

    def _make_schedule_with_production_note(self):
        schedule = _posts_schedule(founder_needed=False)
        schedule["founder"]["optional_idea"] = {
            "note": "Optional idea — save for next scheduled post day",
            "text": "The market is noisy — here's what actually changed.",
            "format": {"type": "One-liner", "reason": "Short and punchy."},
            "media": {"type": "No media", "reason": "Text lands clean."},
        }
        return schedule

    def test_no_double_optional_idea_in_html(self):
        posts = _minimal_posts_with_replies()
        html = render_digest_html(
            "Signal Shift", posts,
            self._make_schedule_with_production_note(), mode="Mock",
        )
        self.assertNotIn("Optional idea — Optional idea", html)
        self.assertNotIn("Optional idea &mdash; Optional idea", html)

    def test_optional_idea_label_present_in_html(self):
        posts = _minimal_posts_with_replies()
        html = render_digest_html(
            "Signal Shift", posts,
            self._make_schedule_with_production_note(), mode="Mock",
        )
        self.assertIn("Optional idea", html)

    def test_custom_note_gets_prefix_in_html(self):
        schedule = _posts_schedule(founder_needed=False)
        schedule["founder"]["optional_idea"] = {
            "note": "save for next scheduled post day",
            "text": "The market is noisy.",
            "format": {"type": "One-liner", "reason": "Punchy."},
            "media": None,
        }
        posts = _minimal_posts_with_replies()
        html = render_digest_html("Signal Shift", posts, schedule, mode="Mock")
        self.assertIn("Optional idea", html)
        self.assertIn("save for next scheduled post day", html)


if __name__ == "__main__":
    unittest.main()
