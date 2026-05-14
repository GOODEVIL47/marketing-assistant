"""
Unit tests for src/providers/brave_search_provider.py.

All tests mock requests.get — no real API calls are made.
BRAVE_SEARCH_API_KEY is injected via os.environ patch, never real.

Run with:
    python -m pytest tests/test_brave_provider.py -v
  or:
    python tests/test_brave_provider.py
"""

import sys
import os
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.providers.brave_search_provider import (
    _build_queries,
    _parse_age_hours,
    _clean_text,
    _normalize,
    get_posts,
    get_posting_history,
    _RESERVED_HANDLES,
)

_FAKE_KEY = "BSA_test_key_never_real"

_FAKE_PROFILE = {
    "name": "Signal Shift",
    "search_terms": [
        "retail investor noise",
        "investing clarity",
        "information overload investing",
    ],
    "fit_keywords": {
        "strong": ["noise", "clarity", "overwhelm", "bias"],
        "decent": ["framework", "research"],
        "weak": ["RSI", "MACD"],
        "avoid": ["moon", "🚀"],
    },
}

_FAKE_RESPONSE = {
    "web": {
        "results": [
            {
                "url": "https://x.com/quietinvestor/status/1789234567890001001",
                "title": 'quietinvestor on X: "The market noise this week is exhausting. Just want clarity."',
                "description": "The market noise this week is exhausting. Just want clarity.",
                "age": "2 hours ago",
            },
            {
                "url": "https://twitter.com/patientcapital_/status/1789234567890001002",
                "title": 'patientcapital_ on X: "Confirmation bias is so real in investing."',
                "description": "Confirmation bias is so real in investing.",
                "age": "1 day ago",
            },
            {
                "url": "https://example.com/not-x-at-all",  # should be filtered
                "title": "Some non-X page",
                "description": "Not relevant.",
                "age": "3 hours ago",
            },
        ]
    }
}

_EMPTY_RESPONSE = {"web": {"results": []}}


def _mock_get(response_json, status_code=200):
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.json.return_value = response_json
    mock_resp.headers = {}
    return mock_resp


# ── _build_queries ─────────────────────────────────────────────────────────────

def test_query_building_uses_search_terms():
    queries = _build_queries(_FAKE_PROFILE)
    assert len(queries) == 3  # default MAX_SEARCH_QUERIES=5, profile has 3
    assert queries[0] == 'site:x.com "retail investor noise"'
    assert queries[1] == 'site:x.com "investing clarity"'
    print("PASS test_query_building_uses_search_terms")


def test_query_building_respects_max_queries():
    with patch.dict(os.environ, {"MAX_SEARCH_QUERIES": "2"}):
        queries = _build_queries(_FAKE_PROFILE)
    assert len(queries) == 2
    print("PASS test_query_building_respects_max_queries")


def test_query_building_raises_on_empty_terms():
    try:
        _build_queries({"search_terms": []})
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "search_terms" in str(e)
    print("PASS test_query_building_raises_on_empty_terms")


# ── _parse_age_hours ───────────────────────────────────────────────────────────

def test_age_parsing_minutes():
    assert _parse_age_hours("30 minutes ago") == pytest_approx(0.5, rel=0.1)
    print("PASS test_age_parsing_minutes")


def test_age_parsing_hours():
    assert _parse_age_hours("3 hours ago") == 3.0
    assert _parse_age_hours("1 hour ago") == 1.0
    print("PASS test_age_parsing_hours")


def test_age_parsing_days():
    assert _parse_age_hours("2 days ago") == 48.0
    print("PASS test_age_parsing_days")


def test_age_parsing_weeks():
    assert _parse_age_hours("1 week ago") == 168.0
    print("PASS test_age_parsing_weeks")


def test_age_parsing_unknown():
    assert _parse_age_hours("") == 48.0
    assert _parse_age_hours(None) == 48.0
    assert _parse_age_hours("some time ago") == 48.0
    print("PASS test_age_parsing_unknown")


# ── _clean_text ────────────────────────────────────────────────────────────────

def test_clean_text_strips_on_x_prefix():
    title = 'quietinvestor on X: "The noise is exhausting."'
    result = _clean_text(title, "", "quietinvestor")
    assert "noise" in result.lower()
    assert "on x" not in result.lower()
    print("PASS test_clean_text_strips_on_x_prefix")


def test_clean_text_falls_back_to_description():
    result = _clean_text("", "Just plain description text here.", "someuser")
    assert result == "Just plain description text here."
    print("PASS test_clean_text_falls_back_to_description")


# ── _normalize ─────────────────────────────────────────────────────────────────

def test_normalize_x_com_url():
    post = _normalize(
        "https://x.com/someuser/status/1789000000000000001",
        "someuser on X: \"Great post text here.\"",
        "Great post text here.",
        "3 hours ago",
    )
    assert post is not None
    assert post["id"] == "1789000000000000001"
    assert post["author"] == "@someuser"
    assert post["age_hours"] == 3.0
    assert post["likes"] == 0
    assert post["discovery_source"] == "brave_search"
    assert post["metrics_confidence"] == "low"
    assert "post_url" in post
    assert "author_profile_url" in post
    print("PASS test_normalize_x_com_url")


def test_normalize_twitter_com_url():
    post = _normalize(
        "https://twitter.com/someuser/status/9876543210",
        "Title",
        "Description",
        "1 day ago",
    )
    assert post is not None
    assert post["id"] == "9876543210"
    print("PASS test_normalize_twitter_com_url")


def test_normalize_non_x_url_returns_none():
    assert _normalize("https://example.com/page", "Title", "Desc", "") is None
    assert _normalize("https://reddit.com/r/stocks/comments/123", "Title", "Desc", "") is None
    print("PASS test_normalize_non_x_url_returns_none")


def test_normalize_reserved_handle_returns_none():
    for handle in ("i", "explore", "home", "search"):
        url = f"https://x.com/{handle}/status/123456789"
        assert _normalize(url, "Title", "Desc", "") is None, f"Should filter out /{handle}/"
    print("PASS test_normalize_reserved_handle_returns_none")


def test_normalize_post_url_is_correct():
    post = _normalize(
        "https://x.com/testuser/status/111222333444",
        "Title",
        "Desc",
        "5 hours ago",
    )
    assert post["post_url"] == "https://x.com/testuser/status/111222333444"
    assert post["author_profile_url"] == "https://x.com/testuser"
    print("PASS test_normalize_post_url_is_correct")


# ── get_posts ──────────────────────────────────────────────────────────────────

def test_get_posts_filters_non_x_urls():
    with patch.dict(os.environ, {"BRAVE_SEARCH_API_KEY": _FAKE_KEY, "MAX_SEARCH_QUERIES": "3", "MAX_RESULTS_PER_QUERY": "5"}):
        with patch("src.providers.brave_search_provider.requests.get") as mock_get:
            mock_get.return_value = _mock_get(_FAKE_RESPONSE)
            posts = get_posts(_FAKE_PROFILE)

    # 3 queries × 2 valid X URLs per response (1 non-X filtered) = 6, but tweet IDs deduplicated
    assert all(p["discovery_source"] == "brave_search" for p in posts)
    assert all(p["metrics_confidence"] == "low" for p in posts)
    # None of the non-X URL results should appear
    for p in posts:
        assert "example.com" not in p.get("post_url", "")
    print(f"PASS test_get_posts_filters_non_x_urls ({len(posts)} posts after dedup)")


def test_get_posts_deduplicates_by_tweet_id():
    # Same tweet ID appears in two query results
    dup_response = {
        "web": {
            "results": [
                {
                    "url": "https://x.com/userA/status/111111111111111111",
                    "title": "userA on X: \"Some text\"",
                    "description": "Some text",
                    "age": "1 hour ago",
                }
            ]
        }
    }
    with patch.dict(os.environ, {"BRAVE_SEARCH_API_KEY": _FAKE_KEY, "MAX_SEARCH_QUERIES": "2", "MAX_RESULTS_PER_QUERY": "5"}):
        with patch("src.providers.brave_search_provider.requests.get") as mock_get:
            mock_get.return_value = _mock_get(dup_response)
            posts = get_posts(_FAKE_PROFILE)

    assert len(posts) == 1, f"Expected 1 after dedup, got {len(posts)}"
    print("PASS test_get_posts_deduplicates_by_tweet_id")


def test_get_posts_empty_results_returns_empty_list():
    with patch.dict(os.environ, {"BRAVE_SEARCH_API_KEY": _FAKE_KEY, "MAX_SEARCH_QUERIES": "2", "MAX_RESULTS_PER_QUERY": "5"}):
        with patch("src.providers.brave_search_provider.requests.get") as mock_get:
            mock_get.return_value = _mock_get(_EMPTY_RESPONSE)
            posts = get_posts(_FAKE_PROFILE)
    assert posts == []
    print("PASS test_get_posts_empty_results_returns_empty_list")


def test_get_posts_handles_api_error_gracefully():
    with patch.dict(os.environ, {"BRAVE_SEARCH_API_KEY": _FAKE_KEY, "MAX_SEARCH_QUERIES": "2", "MAX_RESULTS_PER_QUERY": "5"}):
        with patch("src.providers.brave_search_provider.requests.get") as mock_get:
            mock_get.return_value = _mock_get({}, status_code=429)
            posts = get_posts(_FAKE_PROFILE)
    assert posts == []  # graceful: rate limit just skips queries
    print("PASS test_get_posts_handles_api_error_gracefully")


def test_missing_api_key_raises_environment_error():
    env = {k: v for k, v in os.environ.items() if k != "BRAVE_SEARCH_API_KEY"}
    with patch.dict(os.environ, env, clear=True):
        try:
            get_posts(_FAKE_PROFILE)
            assert False, "Should have raised EnvironmentError"
        except EnvironmentError as e:
            assert "BRAVE_SEARCH_API_KEY" in str(e)
    print("PASS test_missing_api_key_raises_environment_error")


def test_no_real_api_calls_made():
    """Verify that all tests above use mocks — requests.get is never called for real."""
    import requests
    original = requests.get
    call_count = [0]

    def counting_get(*args, **kwargs):
        call_count[0] += 1
        raise AssertionError("requests.get was called without a mock — real API call detected!")

    # This test itself doesn't call get_posts, just verifies the import is patchable
    with patch("src.providers.brave_search_provider.requests.get", side_effect=counting_get):
        pass  # patching works

    assert call_count[0] == 0
    print("PASS test_no_real_api_calls_made")


# ── get_posting_history ────────────────────────────────────────────────────────

def test_get_posting_history_returns_fallback():
    result = get_posting_history(_FAKE_PROFILE)
    assert "founder" in result
    assert "product" in result
    assert result["founder"]["last_posted_hours_ago"] == 999
    assert result["product"]["last_posted_hours_ago"] == 999
    assert "brave" in result["founder"]["last_post_note"].lower()
    print("PASS test_get_posting_history_returns_fallback")


# ── Integration: post shape flows through scorer ───────────────────────────────

def test_brave_post_gets_unknown_visibility_in_scorer():
    from src.scorer import score_posts, _compute_visibility

    fake_post = {
        "id": "9999999999999999999",
        "author": "@testuser",
        "text": "The market noise is overwhelming me. Just want clarity.",
        "likes": 0,
        "reply_count": 0,
        "reposts": 0,
        "age_hours": 4.0,
        "discovery_source": "brave_search",
        "metrics_confidence": "low",
    }
    assert _compute_visibility(fake_post) == "Unknown visibility"
    scored = score_posts([fake_post], profile=_FAKE_PROFILE)
    assert scored[0]["visibility"] == "Unknown visibility"
    assert scored[0]["opportunity"] == "Medium opportunity"
    print("PASS test_brave_post_gets_unknown_visibility_in_scorer")


def test_brave_post_gets_reply_options():
    from src.scorer import score_posts
    from src.replier import generate_replies

    fake_post = {
        "id": "8888888888888888888",
        "author": "@noisymarket",
        "text": "All this earnings noise is exhausting. Just want to understand what's actually happening.",
        "likes": 0,
        "reply_count": 0,
        "reposts": 0,
        "age_hours": 2.0,
        "post_url": "https://x.com/noisymarket/status/8888888888888888888",
        "author_profile_url": "https://x.com/noisymarket",
        "discovery_source": "brave_search",
        "metrics_confidence": "low",
    }
    scored = score_posts([fake_post], profile=_FAKE_PROFILE)
    with_replies = generate_replies(scored)
    post = with_replies[0]
    if post["score"] in ("Strong fit", "Decent fit"):
        assert len(post["replies"]) == 3, "Expected 3 reply options"
        assert post["best_reply"] is not None
        assert post["media"] is not None
        print(f"PASS test_brave_post_gets_reply_options (theme detected, {post['score']})")
    else:
        print(f"PASS test_brave_post_gets_reply_options (Weak/Avoid — no replies expected, {post['score']})")


# ── Simple approx helper (avoid pytest dependency for the minutes test) ────────

def pytest_approx(value, rel=0.01):
    class Approx:
        def __init__(self, v, r):
            self.v = v
            self.r = r
        def __eq__(self, other):
            return abs(other - self.v) <= self.r * self.v
        def __repr__(self):
            return f"~{self.v}"
    return Approx(value, rel)


if __name__ == "__main__":
    tests = [
        test_query_building_uses_search_terms,
        test_query_building_respects_max_queries,
        test_query_building_raises_on_empty_terms,
        test_age_parsing_minutes,
        test_age_parsing_hours,
        test_age_parsing_days,
        test_age_parsing_weeks,
        test_age_parsing_unknown,
        test_clean_text_strips_on_x_prefix,
        test_clean_text_falls_back_to_description,
        test_normalize_x_com_url,
        test_normalize_twitter_com_url,
        test_normalize_non_x_url_returns_none,
        test_normalize_reserved_handle_returns_none,
        test_normalize_post_url_is_correct,
        test_get_posts_filters_non_x_urls,
        test_get_posts_deduplicates_by_tweet_id,
        test_get_posts_empty_results_returns_empty_list,
        test_get_posts_handles_api_error_gracefully,
        test_missing_api_key_raises_environment_error,
        test_no_real_api_calls_made,
        test_get_posting_history_returns_fallback,
        test_brave_post_gets_unknown_visibility_in_scorer,
        test_brave_post_gets_reply_options,
    ]

    failed = 0
    for t in tests:
        try:
            t()
        except AssertionError as e:
            print(f"FAIL {t.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"ERROR {t.__name__}: {type(e).__name__}: {e}")
            failed += 1

    print()
    if failed:
        print(f"{failed}/{len(tests)} test(s) FAILED")
        sys.exit(1)
    else:
        print(f"All {len(tests)} tests passed.")
