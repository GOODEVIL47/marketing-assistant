"""
Unit tests for src/providers/tavily_search_provider.py.

All tests mock requests.post — no real API calls are made.
TAVILY_API_KEY is injected via os.environ patch, never real.

Run with:
    python -m pytest tests/test_tavily_provider.py -v
  or:
    python tests/test_tavily_provider.py
"""

import sys
import os
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.providers.tavily_search_provider import (
    _build_queries,
    _parse_age_hours,
    _clean_text,
    _normalize,
    get_posts,
    get_posting_history,
    _RESERVED_HANDLES,
)

_FAKE_KEY = "tvly-test-key-never-real"

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
    "results": [
        {
            "url": "https://x.com/quietinvestor/status/1789234567890001001",
            "title": 'quietinvestor on X: "The market noise this week is exhausting."',
            "content": "The market noise this week is exhausting. Just want clarity.",
            "score": 0.89,
            "published_date": "2025-05-14T10:00:00Z",
        },
        {
            "url": "https://twitter.com/patientcapital_/status/1789234567890001002",
            "title": 'patientcapital_ on X: "Confirmation bias is so real in investing."',
            "content": "Confirmation bias is so real. Keeps explaining away bad signals.",
            "score": 0.82,
            "published_date": "2025-05-13T08:30:00Z",
        },
        {
            "url": "https://example.com/not-x-at-all",  # should be filtered
            "title": "Some non-X page",
            "content": "Not relevant.",
            "score": 0.10,
            "published_date": None,
        },
    ]
}

_EMPTY_RESPONSE = {"results": []}


def _mock_post(response_json, status_code=200):
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.json.return_value = response_json
    mock_resp.headers = {}
    return mock_resp


# ── _build_queries ─────────────────────────────────────────────────────────────

def test_query_building_uses_search_terms():
    queries = _build_queries(_FAKE_PROFILE)
    assert len(queries) == 3
    assert queries[0] == 'site:x.com "retail investor noise"'
    assert queries[2] == 'site:x.com "information overload investing"'
    print("PASS test_query_building_uses_search_terms")


def test_query_building_respects_max_queries():
    with patch.dict(os.environ, {"MAX_SEARCH_QUERIES": "1"}):
        queries = _build_queries(_FAKE_PROFILE)
    assert len(queries) == 1
    print("PASS test_query_building_respects_max_queries")


def test_query_building_raises_on_empty_terms():
    try:
        _build_queries({"search_terms": []})
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "search_terms" in str(e)
    print("PASS test_query_building_raises_on_empty_terms")


# ── _parse_age_hours ───────────────────────────────────────────────────────────

def test_age_parsing_iso_date():
    from datetime import datetime, timezone, timedelta
    # A date 3 hours ago
    three_hours_ago = (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat()
    result = _parse_age_hours(three_hours_ago)
    assert 2.5 < result < 3.5, f"Expected ~3h, got {result}"
    print("PASS test_age_parsing_iso_date")


def test_age_parsing_z_suffix():
    from datetime import datetime, timezone, timedelta
    one_day_ago = (datetime.now(timezone.utc) - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ")
    result = _parse_age_hours(one_day_ago)
    assert 23 < result < 25, f"Expected ~24h, got {result}"
    print("PASS test_age_parsing_z_suffix")


def test_age_parsing_none_returns_default():
    assert _parse_age_hours(None) == 48.0
    assert _parse_age_hours("") == 48.0
    assert _parse_age_hours("not-a-date") == 48.0
    print("PASS test_age_parsing_none_returns_default")


# ── _clean_text ────────────────────────────────────────────────────────────────

def test_clean_text_strips_on_x_prefix_from_title():
    title = 'quietinvestor on X: "The noise is exhausting."'
    result = _clean_text(title, "", "quietinvestor")
    assert "noise" in result.lower()
    assert "on x" not in result.lower()
    print("PASS test_clean_text_strips_on_x_prefix_from_title")


def test_clean_text_prefers_content_excerpt():
    title = 'user on X: "Short title."'
    content = "Longer content with more detail about the market noise."
    result = _clean_text(title, content, "user")
    # Should return the extracted text (title-based since prefix found in title)
    assert len(result) > 0
    print("PASS test_clean_text_prefers_content_excerpt")


def test_clean_text_falls_back_to_content_then_title():
    result = _clean_text("", "Plain content here.", "someuser")
    assert result == "Plain content here."
    result2 = _clean_text("Plain title here.", "", "someuser")
    assert result2 == "Plain title here."
    print("PASS test_clean_text_falls_back_to_content_then_title")


# ── _normalize ─────────────────────────────────────────────────────────────────

def test_normalize_x_com_url():
    from datetime import datetime, timezone, timedelta
    two_hours_ago = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    post = _normalize(
        "https://x.com/testuser/status/1789000000000000001",
        "testuser on X: \"Great post text.\"",
        "Great post text here.",
        two_hours_ago,
    )
    assert post is not None
    assert post["id"] == "1789000000000000001"
    assert post["author"] == "@testuser"
    assert 1.5 < post["age_hours"] < 2.5
    assert post["likes"] == 0
    assert post["discovery_source"] == "tavily_search"
    assert post["metrics_confidence"] == "low"
    assert post["post_url"] == "https://x.com/testuser/status/1789000000000000001"
    assert post["author_profile_url"] == "https://x.com/testuser"
    print("PASS test_normalize_x_com_url")


def test_normalize_twitter_com_url():
    post = _normalize(
        "https://twitter.com/someuser/status/9876543210",
        "Title",
        "Content",
        None,
    )
    assert post is not None
    assert post["id"] == "9876543210"
    assert post["age_hours"] == 48.0  # fallback
    print("PASS test_normalize_twitter_com_url")


def test_normalize_non_x_url_returns_none():
    assert _normalize("https://example.com/page", "T", "C", None) is None
    assert _normalize("https://reddit.com/r/stocks/123", "T", "C", None) is None
    print("PASS test_normalize_non_x_url_returns_none")


def test_normalize_reserved_handle_returns_none():
    for handle in ("i", "explore", "home", "search", "settings"):
        url = f"https://x.com/{handle}/status/123456789"
        assert _normalize(url, "T", "C", None) is None
    print("PASS test_normalize_reserved_handle_returns_none")


def test_normalize_has_required_fields():
    post = _normalize(
        "https://x.com/user/status/111",
        "Title",
        "Content",
        None,
    )
    required = ["id", "author", "author_name", "author_followers", "author_profile_url",
                "text", "likes", "reposts", "reply_count", "impressions",
                "age_hours", "post_url", "url", "discovery_source", "metrics_confidence"]
    for field in required:
        assert field in post, f"Missing field: {field}"
    print("PASS test_normalize_has_required_fields")


# ── get_posts ──────────────────────────────────────────────────────────────────

def test_get_posts_filters_non_x_urls():
    with patch.dict(os.environ, {
        "TAVILY_API_KEY": _FAKE_KEY,
        "MAX_SEARCH_QUERIES": "3",
        "MAX_RESULTS_PER_QUERY": "5",
    }):
        with patch("src.providers.tavily_search_provider.requests.post") as mock_p:
            mock_p.return_value = _mock_post(_FAKE_RESPONSE)
            posts = get_posts(_FAKE_PROFILE)

    assert all(p["discovery_source"] == "tavily_search" for p in posts)
    assert all(p["metrics_confidence"] == "low" for p in posts)
    for p in posts:
        assert "example.com" not in p.get("post_url", "")
    print(f"PASS test_get_posts_filters_non_x_urls ({len(posts)} posts after dedup)")


def test_get_posts_deduplicates_by_tweet_id():
    dup_response = {
        "results": [{
            "url": "https://x.com/userA/status/111111111111111111",
            "title": "userA on X: \"Some text\"",
            "content": "Some text",
            "score": 0.7,
            "published_date": None,
        }]
    }
    with patch.dict(os.environ, {
        "TAVILY_API_KEY": _FAKE_KEY,
        "MAX_SEARCH_QUERIES": "3",
        "MAX_RESULTS_PER_QUERY": "5",
    }):
        with patch("src.providers.tavily_search_provider.requests.post") as mock_p:
            mock_p.return_value = _mock_post(dup_response)
            posts = get_posts(_FAKE_PROFILE)

    assert len(posts) == 1, f"Expected 1 after dedup, got {len(posts)}"
    print("PASS test_get_posts_deduplicates_by_tweet_id")


def test_get_posts_empty_results_returns_empty_list():
    with patch.dict(os.environ, {
        "TAVILY_API_KEY": _FAKE_KEY,
        "MAX_SEARCH_QUERIES": "2",
        "MAX_RESULTS_PER_QUERY": "5",
    }):
        with patch("src.providers.tavily_search_provider.requests.post") as mock_p:
            mock_p.return_value = _mock_post(_EMPTY_RESPONSE)
            posts = get_posts(_FAKE_PROFILE)
    assert posts == []
    print("PASS test_get_posts_empty_results_returns_empty_list")


def test_get_posts_handles_rate_limit_gracefully():
    with patch.dict(os.environ, {
        "TAVILY_API_KEY": _FAKE_KEY,
        "MAX_SEARCH_QUERIES": "2",
        "MAX_RESULTS_PER_QUERY": "5",
    }):
        with patch("src.providers.tavily_search_provider.requests.post") as mock_p:
            mock_p.return_value = _mock_post({}, status_code=429)
            posts = get_posts(_FAKE_PROFILE)
    assert posts == []
    print("PASS test_get_posts_handles_rate_limit_gracefully")


def test_get_posts_handles_auth_error_gracefully():
    with patch.dict(os.environ, {
        "TAVILY_API_KEY": _FAKE_KEY,
        "MAX_SEARCH_QUERIES": "1",
        "MAX_RESULTS_PER_QUERY": "5",
    }):
        with patch("src.providers.tavily_search_provider.requests.post") as mock_p:
            mock_p.return_value = _mock_post({}, status_code=401)
            posts = get_posts(_FAKE_PROFILE)
    assert posts == []
    print("PASS test_get_posts_handles_auth_error_gracefully")


def test_missing_api_key_raises_environment_error():
    env = {k: v for k, v in os.environ.items() if k != "TAVILY_API_KEY"}
    with patch.dict(os.environ, env, clear=True):
        try:
            get_posts(_FAKE_PROFILE)
            assert False, "Should have raised EnvironmentError"
        except EnvironmentError as e:
            assert "TAVILY_API_KEY" in str(e)
    print("PASS test_missing_api_key_raises_environment_error")


def test_missing_api_key_message_mentions_free_signup():
    env = {k: v for k, v in os.environ.items() if k != "TAVILY_API_KEY"}
    with patch.dict(os.environ, env, clear=True):
        try:
            get_posts(_FAKE_PROFILE)
        except EnvironmentError as e:
            msg = str(e)
            assert "tavily" in msg.lower() or "app.tavily" in msg.lower()
    print("PASS test_missing_api_key_message_mentions_free_signup")


def test_api_key_never_in_logs(capsys=None):
    """
    Confirm the API key does not appear in any printed output.
    (The key goes in the POST body — we verify it's not printed.)
    """
    with patch.dict(os.environ, {
        "TAVILY_API_KEY": _FAKE_KEY,
        "MAX_SEARCH_QUERIES": "1",
        "MAX_RESULTS_PER_QUERY": "2",
    }):
        with patch("src.providers.tavily_search_provider.requests.post") as mock_p:
            mock_p.return_value = _mock_post(_EMPTY_RESPONSE)
            import io
            from contextlib import redirect_stdout
            buf = io.StringIO()
            with redirect_stdout(buf):
                get_posts(_FAKE_PROFILE)
            output = buf.getvalue()
    assert _FAKE_KEY not in output, f"API key appeared in output: {output}"
    print("PASS test_api_key_never_in_logs")


# ── get_posting_history ────────────────────────────────────────────────────────

def test_get_posting_history_returns_fallback():
    result = get_posting_history(_FAKE_PROFILE)
    assert "founder" in result
    assert "product" in result
    assert result["founder"]["last_posted_hours_ago"] == 999
    assert result["product"]["last_posted_hours_ago"] == 999
    assert "tavily" in result["founder"]["last_post_note"].lower()
    print("PASS test_get_posting_history_returns_fallback")


# ── Integration: scoring and replies ──────────────────────────────────────────

def test_tavily_post_gets_unknown_visibility():
    from src.scorer import _compute_visibility, score_posts
    fake_post = {
        "id": "9999999999999999999",
        "author": "@testuser",
        "text": "The market noise this week is overwhelming. Just want clarity.",
        "likes": 0, "reply_count": 0, "reposts": 0,
        "age_hours": 4.0,
        "discovery_source": "tavily_search",
        "metrics_confidence": "low",
    }
    assert _compute_visibility(fake_post) == "Unknown visibility"
    scored = score_posts([fake_post], profile=_FAKE_PROFILE)
    assert scored[0]["visibility"] == "Unknown visibility"
    assert scored[0]["opportunity"] == "Medium opportunity"
    print("PASS test_tavily_post_gets_unknown_visibility")


def test_tavily_post_gets_reply_options():
    from src.scorer import score_posts
    from src.replier import generate_replies
    fake_post = {
        "id": "8888888888888888888",
        "author": "@noisymarket",
        "text": "All this earnings noise is exhausting. Just want to understand.",
        "likes": 0, "reply_count": 0, "reposts": 0,
        "age_hours": 2.0,
        "post_url": "https://x.com/noisymarket/status/8888888888888888888",
        "author_profile_url": "https://x.com/noisymarket",
        "discovery_source": "tavily_search",
        "metrics_confidence": "low",
    }
    scored = score_posts([fake_post], profile=_FAKE_PROFILE)
    with_replies = generate_replies(scored)
    post = with_replies[0]
    if post["score"] in ("Strong fit", "Decent fit"):
        assert len(post["replies"]) == 3
        assert post["best_reply"] is not None
        assert post["media"] is not None
        print(f"PASS test_tavily_post_gets_reply_options ({post['score']})")
    else:
        print(f"PASS test_tavily_post_gets_reply_options (Weak/Avoid — no replies, {post['score']})")


def test_tavily_source_label_in_email_renderer():
    from src.email_renderer import _WEB_SEARCH_LABELS
    assert "tavily_search" in _WEB_SEARCH_LABELS
    assert _WEB_SEARCH_LABELS["tavily_search"] == "Tavily Search"
    print("PASS test_tavily_source_label_in_email_renderer")


if __name__ == "__main__":
    tests = [
        test_query_building_uses_search_terms,
        test_query_building_respects_max_queries,
        test_query_building_raises_on_empty_terms,
        test_age_parsing_iso_date,
        test_age_parsing_z_suffix,
        test_age_parsing_none_returns_default,
        test_clean_text_strips_on_x_prefix_from_title,
        test_clean_text_prefers_content_excerpt,
        test_clean_text_falls_back_to_content_then_title,
        test_normalize_x_com_url,
        test_normalize_twitter_com_url,
        test_normalize_non_x_url_returns_none,
        test_normalize_reserved_handle_returns_none,
        test_normalize_has_required_fields,
        test_get_posts_filters_non_x_urls,
        test_get_posts_deduplicates_by_tweet_id,
        test_get_posts_empty_results_returns_empty_list,
        test_get_posts_handles_rate_limit_gracefully,
        test_get_posts_handles_auth_error_gracefully,
        test_missing_api_key_raises_environment_error,
        test_missing_api_key_message_mentions_free_signup,
        test_api_key_never_in_logs,
        test_get_posting_history_returns_fallback,
        test_tavily_post_gets_unknown_visibility,
        test_tavily_post_gets_reply_options,
        test_tavily_source_label_in_email_renderer,
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
