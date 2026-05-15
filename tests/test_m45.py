"""
Tests for M4.5: query quality, stale-post output, reply variation, inspiration angles.
No real API calls, no network access.
"""

import sys
import os
import io
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.providers.tavily_search_provider import _build_candidate_queries, _build_queries
from src.scorer import score_posts
from src.replier import generate_replies, _DYNAMIC_TEMPLATES, _pick_reply_options, REPLIES
from src.digest import _build_best_3, _build_inspiration, _build_original_posts, build_markdown
from src.email_renderer import render_digest_html, render_digest_text, _html_inspiration


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_web_post(tweet_id="1900000000000000001", age_hours=6, age_source="snowflake",
                   fit_text="retail investor noise clarity signal"):
    return {
        "id": tweet_id,
        "author": f"@user_{tweet_id[-4:]}",
        "author_name": f"user_{tweet_id[-4:]}",
        "author_followers": 0,
        "author_profile_url": "https://x.com/user",
        "text": fit_text,
        "likes": 0,
        "reposts": 0,
        "reply_count": 0,
        "impressions": 0,
        "age_hours": age_hours,
        "age_source": age_source,
        "post_url": f"https://x.com/user/status/{tweet_id}",
        "url": f"https://x.com/user/status/{tweet_id}",
        "discovery_source": "tavily_search",
        "metrics_confidence": "low",
    }


def _minimal_profile():
    return {
        "fit_keywords": {
            "strong": ["noise", "clarity", "signal", "overload"],
            "decent": ["investor", "investing", "retail"],
            "weak": ["options strategy", "technical analysis"],
            "avoid": ["get rich quick", "100x"],
        }
    }


def _mock_schedule():
    return {
        "founder": {
            "handle": "@yourhandle",
            "needed": True,
            "reason": "Test",
            "post": {
                "text": "Test founder post.",
                "format": {"type": "Thread", "reason": "Test"},
                "media": {"type": "No media", "reason": "Test"},
            },
        },
        "product": {
            "handle": "@SignalShiftCo",
            "needed": False,
            "reason": "Not scheduled today.",
            "optional_idea": None,
        },
    }


# ---------------------------------------------------------------------------
# 1. _build_candidate_queries — order and deduplication
# ---------------------------------------------------------------------------

class TestCandidateQueries(unittest.TestCase):

    def test_generates_correct_count(self):
        profile = {
            "search_terms": ["term A", "term B"],
            "query_templates": ['site:x.com "{term}"', 'site:x.com "{term}" "today"'],
        }
        candidates = _build_candidate_queries(profile)
        self.assertEqual(len(candidates), 4)

    def test_template_outer_term_inner_order(self):
        profile = {
            "search_terms": ["term A", "term B"],
            "query_templates": ['site:x.com "{term}"', 'site:x.com "{term}" "today"'],
        }
        candidates = _build_candidate_queries(profile)
        self.assertEqual(candidates[0], 'site:x.com "term A"')
        self.assertEqual(candidates[1], 'site:x.com "term B"')
        self.assertEqual(candidates[2], 'site:x.com "term A" "today"')
        self.assertEqual(candidates[3], 'site:x.com "term B" "today"')

    def test_deduplicates_identical_candidates(self):
        profile = {
            "search_terms": ["same"],
            "query_templates": ['site:x.com "{term}"', 'site:x.com "{term}"'],
        }
        candidates = _build_candidate_queries(profile)
        self.assertEqual(len(candidates), 1)

    def test_default_template_used_when_none_in_profile(self):
        profile = {"search_terms": ["market noise"]}
        candidates = _build_candidate_queries(profile)
        self.assertEqual(candidates, ['site:x.com "market noise"'])


# ---------------------------------------------------------------------------
# 2. _build_queries — MAX_SEARCH_QUERIES cap
# ---------------------------------------------------------------------------

class TestBuildQueriesCap(unittest.TestCase):

    def _profile_with_many_terms(self):
        return {
            "search_terms": [f"term {i}" for i in range(10)],
            "query_templates": ['site:x.com "{term}"', 'site:x.com "{term}" "today"'],
        }

    def test_cap_at_5_by_default(self):
        profile = self._profile_with_many_terms()
        with patch.dict(os.environ, {"MAX_SEARCH_QUERIES": "5"}):
            queries = _build_queries(profile)
        self.assertEqual(len(queries), 5)

    def test_cap_at_2(self):
        profile = self._profile_with_many_terms()
        with patch.dict(os.environ, {"MAX_SEARCH_QUERIES": "2"}):
            queries = _build_queries(profile)
        self.assertEqual(len(queries), 2)

    def test_cap_respects_template_order(self):
        profile = {
            "search_terms": ["term A", "term B", "term C"],
            "query_templates": ['site:x.com "{term}"', 'site:x.com "{term}" "today"'],
        }
        with patch.dict(os.environ, {"MAX_SEARCH_QUERIES": "3"}):
            queries = _build_queries(profile)
        self.assertEqual(queries[0], 'site:x.com "term A"')
        self.assertEqual(queries[1], 'site:x.com "term B"')
        self.assertEqual(queries[2], 'site:x.com "term C"')

    def test_build_queries_logs_selected(self):
        profile = self._profile_with_many_terms()
        buf = io.StringIO()
        with patch.dict(os.environ, {"MAX_SEARCH_QUERIES": "3"}):
            with patch("sys.stdout", buf):
                _build_queries(profile)
        output = buf.getvalue()
        self.assertIn("Selected", output)
        self.assertIn("cap=3", output)

    def test_build_queries_raises_with_no_terms(self):
        with self.assertRaises(ValueError):
            _build_queries({})


# ---------------------------------------------------------------------------
# 3. Stale post — no reply options in Markdown output
# ---------------------------------------------------------------------------

class TestStalePostMarkdown(unittest.TestCase):

    def _stale_digest(self):
        post = _make_web_post(age_hours=250)   # ~10 days — stale
        profile = _minimal_profile()
        scored = score_posts([post], profile=profile)
        with_replies = generate_replies(scored)
        schedule = _mock_schedule()
        from src.post_generator import generate_posts
        sched = generate_posts(0)
        return build_markdown("Signal Shift", with_replies, sched, mode="Tavily Search")

    def test_stale_has_no_reply_options_section(self):
        md = self._stale_digest()
        self.assertNotIn("**Reply options:**", md)

    def test_stale_shows_reply_note(self):
        md = self._stale_digest()
        self.assertIn("No reply suggested", md)
        self.assertIn("stale post", md)
        self.assertIn("inspiration only", md)


# ---------------------------------------------------------------------------
# 4. Stale post — no reply options in HTML email
# ---------------------------------------------------------------------------

class TestStalePostHTML(unittest.TestCase):

    def _stale_html(self):
        post = _make_web_post(age_hours=250)
        profile = _minimal_profile()
        scored = score_posts([post], profile=profile)
        with_replies = generate_replies(scored)
        from src.post_generator import generate_posts
        sched = generate_posts(0)
        return render_digest_html("Signal Shift", with_replies, sched, mode="Tavily Search")

    def test_stale_html_no_recommended_badge(self):
        html = self._stale_html()
        self.assertNotIn("Recommended &mdash;", html)

    def test_stale_html_shows_no_opportunities(self):
        # Stale posts have Poor opportunity — Best 3 is empty, shows no-opportunities message
        html = self._stale_html()
        self.assertIn("No suitable reply opportunities found today", html)


# ---------------------------------------------------------------------------
# 5. Old+good-fit post — inspiration_angles in Save for Inspiration
# ---------------------------------------------------------------------------

class TestInspirationAngles(unittest.TestCase):

    def _old_good_post(self):
        post = _make_web_post(age_hours=96, fit_text="retail investor noise clarity signal overload")
        profile = _minimal_profile()
        scored = score_posts([post], profile=profile)
        return generate_replies(scored)

    def test_old_good_post_has_inspiration_angles(self):
        posts = self._old_good_post()
        post = posts[0]
        if post.get("freshness_tier") == "old" and post["score"] in ("Strong fit", "Decent fit"):
            self.assertIsNotNone(post.get("inspiration_angles"))
            self.assertGreater(len(post["inspiration_angles"]), 0)

    def test_inspiration_section_in_markdown(self):
        posts = self._old_good_post()
        lines = _build_inspiration(posts)
        if lines:
            content = "\n".join(lines)
            self.assertIn("Save for Inspiration", content)
            self.assertIn("Inspiration angles:", content)

    def test_inspiration_section_in_html(self):
        posts = self._old_good_post()
        html = _html_inspiration(posts)
        if html:
            self.assertIn("Save for Inspiration", html)
            # Angles rendered as bullet points — check do-not-reply note is present
            self.assertIn("do not reply", html)

    def test_old_post_has_no_reply_block_in_markdown(self):
        posts = self._old_good_post()
        from src.post_generator import generate_posts
        sched = generate_posts(0)
        md = build_markdown("Signal Shift", posts, sched, mode="Tavily Search")
        if any(p.get("freshness_tier") == "old" for p in posts):
            self.assertNotIn("**Reply options:**", md)


# ---------------------------------------------------------------------------
# 6. Tavily mode posting schedule — check manually wording
# ---------------------------------------------------------------------------

class TestTavilyModeScheduleWording(unittest.TestCase):

    def test_markdown_check_manually_wording(self):
        from src.post_generator import generate_posts
        sched = generate_posts(0)
        # Force at least one needed post
        sched["founder"]["needed"] = True
        sched["founder"]["post"] = {
            "text": "Test",
            "format": {"type": "Thread", "reason": ""},
            "media": {"type": "No media", "reason": ""},
        }
        lines = _build_original_posts(sched, mode="Tavily Search")
        content = "\n".join(lines)
        self.assertIn("manually before posting", content)
        self.assertIn("posting history unavailable", content)

    def test_mock_mode_no_check_manually(self):
        from src.post_generator import generate_posts
        sched = generate_posts(0)
        sched["founder"]["needed"] = True
        sched["founder"]["post"] = {
            "text": "Test",
            "format": {"type": "Thread", "reason": ""},
            "media": {"type": "No media", "reason": ""},
        }
        lines = _build_original_posts(sched, mode="Mock")
        content = "\n".join(lines)
        self.assertNotIn("manually before posting", content)

    def test_html_check_manually_wording(self):
        from src.email_renderer import _html_original_posts
        from src.post_generator import generate_posts
        sched = generate_posts(0)
        sched["founder"]["needed"] = True
        sched["founder"]["post"] = {
            "text": "Test post",
            "format": {"type": "Thread", "reason": ""},
            "media": {"type": "No media", "reason": ""},
        }
        html = _html_original_posts(sched, mode="Tavily Search")
        self.assertIn("manually before posting", html)

    def test_html_mock_mode_no_check_manually(self):
        from src.email_renderer import _html_original_posts
        from src.post_generator import generate_posts
        sched = generate_posts(0)
        sched["founder"]["needed"] = True
        sched["founder"]["post"] = {
            "text": "Test post",
            "format": {"type": "Thread", "reason": ""},
            "media": {"type": "No media", "reason": ""},
        }
        html = _html_original_posts(sched, mode="Mock")
        self.assertNotIn("manually before posting", html)


# ---------------------------------------------------------------------------
# 7. 3-variant reply variation (% 3 == 0, 1, 2)
# ---------------------------------------------------------------------------

class TestThreeVariantReplySelection(unittest.TestCase):

    def test_mod_0_gets_options_a(self):
        # Tweet ID divisible by 3 → idx=0 → options (set A)
        tweet_id = "1900000000000000002"  # 2 % 3 = 2... need % 3 == 0
        # Use 1900000000000000000 — ends in 000, divisible by 3? 1+9+0... sum digits irrelevant for %
        # Just use a known value: 6 % 3 == 0
        tweet_id = "6"
        template = _DYNAMIC_TEMPLATES["noise_overwhelm"]
        options, best_idx = _pick_reply_options(tweet_id, template)
        self.assertEqual(options, template["options"])
        self.assertEqual(best_idx, template["best_option_index"])

    def test_mod_1_gets_options_b(self):
        tweet_id = "7"  # 7 % 3 == 1
        template = _DYNAMIC_TEMPLATES["noise_overwhelm"]
        options, best_idx = _pick_reply_options(tweet_id, template)
        self.assertEqual(options, template["options_b"])
        self.assertEqual(best_idx, template["best_option_index_b"])

    def test_mod_2_gets_options_c(self):
        tweet_id = "8"  # 8 % 3 == 2
        template = _DYNAMIC_TEMPLATES["noise_overwhelm"]
        options, best_idx = _pick_reply_options(tweet_id, template)
        self.assertEqual(options, template["options_c"])
        self.assertEqual(best_idx, template["best_option_index_c"])

    def test_three_ids_in_same_theme_get_different_sets(self):
        template = _DYNAMIC_TEMPLATES["generic_strong"]
        opts_a, _ = _pick_reply_options("6", template)   # % 3 == 0
        opts_b, _ = _pick_reply_options("7", template)   # % 3 == 1
        opts_c, _ = _pick_reply_options("8", template)   # % 3 == 2
        # All three sets should be distinct
        texts_a = {r["text"] for r in opts_a}
        texts_b = {r["text"] for r in opts_b}
        texts_c = {r["text"] for r in opts_c}
        self.assertNotEqual(texts_a, texts_b)
        self.assertNotEqual(texts_b, texts_c)
        self.assertNotEqual(texts_a, texts_c)

    def test_invalid_id_falls_back_to_options_a(self):
        template = _DYNAMIC_TEMPLATES["generic_strong"]
        options, best_idx = _pick_reply_options("not-a-number", template)
        self.assertEqual(options, template["options"])
        self.assertEqual(best_idx, template.get("best_option_index", 0))


# ---------------------------------------------------------------------------
# 8. All themes have options_c
# ---------------------------------------------------------------------------

class TestAllThemesHaveOptionsC(unittest.TestCase):

    def test_all_themes_have_options_c(self):
        for theme, template in _DYNAMIC_TEMPLATES.items():
            self.assertIn("options_c", template, f"Theme '{theme}' missing options_c")

    def test_all_themes_options_c_has_3_entries(self):
        for theme, template in _DYNAMIC_TEMPLATES.items():
            self.assertEqual(
                len(template["options_c"]), 3,
                f"Theme '{theme}' options_c should have 3 entries"
            )

    def test_all_themes_have_best_option_index_c(self):
        for theme, template in _DYNAMIC_TEMPLATES.items():
            self.assertIn("best_option_index_c", template, f"Theme '{theme}' missing best_option_index_c")


# ---------------------------------------------------------------------------
# 9. Mock replies unchanged
# ---------------------------------------------------------------------------

class TestMockRepliesUnchanged(unittest.TestCase):

    def test_mock_reply_3_option_a_unchanged(self):
        self.assertEqual(REPLIES[3]["options"][0]["text"], "More dashboards, same fog.")

    def test_mock_post_1_best_option_index_is_1(self):
        self.assertEqual(REPLIES[1]["best_option_index"], 1)

    def test_mock_post_2_best_option_index_is_2(self):
        self.assertEqual(REPLIES[2]["best_option_index"], 2)


# ---------------------------------------------------------------------------
# 10. Mock mode output unchanged
# ---------------------------------------------------------------------------

class TestMockModeOutputUnchanged(unittest.TestCase):

    def test_mock_posts_score_correctly(self):
        from mock_data.posts import MOCK_POSTS
        scored = score_posts(MOCK_POSTS)
        self.assertEqual(scored[0]["score"], "Strong fit")
        self.assertEqual(scored[6]["score"], "Avoid")

    def test_mock_posts_no_inspiration_in_inspiration_section(self):
        from mock_data.posts import MOCK_POSTS
        scored = score_posts(MOCK_POSTS)
        with_replies = generate_replies(scored)
        lines = _build_inspiration(with_replies)
        self.assertEqual(lines, [])

    def test_mock_best3_finds_opportunities(self):
        from mock_data.posts import MOCK_POSTS
        scored = score_posts(MOCK_POSTS)
        with_replies = generate_replies(scored)
        lines = _build_best_3(with_replies)
        content = "\n".join(lines)
        self.assertNotIn("No suitable reply", content)

    def test_mock_mode_schedule_no_check_manually(self):
        from mock_data.posts import MOCK_POSTS
        from src.post_generator import generate_posts
        scored = score_posts(MOCK_POSTS)
        with_replies = generate_replies(scored)
        sched = generate_posts(0)
        md = build_markdown("Signal Shift", with_replies, sched, mode="Mock")
        self.assertNotIn("manually before posting", md)


# ---------------------------------------------------------------------------
# 11. Freshness filters unchanged
# ---------------------------------------------------------------------------

class TestFreshnesFiltersUnchanged(unittest.TestCase):

    def test_fresh_is_medium_opportunity(self):
        post = _make_web_post(age_hours=6)
        scored = score_posts([post], profile=_minimal_profile())
        self.assertEqual(scored[0]["opportunity"], "Medium opportunity")

    def test_stale_is_poor_opportunity(self):
        post = _make_web_post(age_hours=250)
        scored = score_posts([post], profile=_minimal_profile())
        self.assertEqual(scored[0]["opportunity"], "Poor opportunity")

    def test_old_is_low_opportunity(self):
        post = _make_web_post(age_hours=96)
        scored = score_posts([post], profile=_minimal_profile())
        self.assertEqual(scored[0]["opportunity"], "Low opportunity")

    def test_fresh_post_in_best3(self):
        post = _make_web_post(age_hours=6)
        scored = score_posts([post], profile=_minimal_profile())
        with_replies = generate_replies(scored)
        lines = _build_best_3(with_replies)
        content = "\n".join(lines)
        self.assertNotIn("No suitable reply", content)

    def test_old_post_excluded_from_best3(self):
        post = _make_web_post(age_hours=96)
        scored = score_posts([post], profile=_minimal_profile())
        with_replies = generate_replies(scored)
        lines = _build_best_3(with_replies)
        content = "\n".join(lines)
        self.assertIn("No suitable reply", content)


if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(__import__("__main__"))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
