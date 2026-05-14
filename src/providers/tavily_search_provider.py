"""
Read-only Tavily Search API provider for X post discovery.

Discovers recent X posts using Tavily's web search API without calling
the X API, scraping, logging into X, or requiring a paid subscription.

Tavily's free tier (no credit card) allows a limited number of API calls
per month — enough for daily discovery sessions.

SAFETY CONSTRAINTS — enforced here, never change without explicit user approval:
  - Read-only. No writes, no posts, no likes, no follows, no DMs.
  - Does not call the X API. Does not log into X. Does not scrape X pages.
  - Does not use browser automation.
  - Does not auto-post or auto-reply.
  - TAVILY_API_KEY is never printed in logs (it goes in the POST body).

Limitations:
  - Engagement metrics (likes, replies, reposts) are unavailable.
  - Results may not be as fresh as the X API.
  - Snippets may be truncated. Verify post quality before replying.
  - discovery_source="tavily_search" and metrics_confidence="low" are set
    on every post so downstream scoring and rendering flag uncertainty.
"""

import os
import re
from datetime import datetime, timezone

import requests

_TAVILY_API_URL = "https://api.tavily.com/search"
_X_STATUS_RE = re.compile(
    r"https?://(?:www\.)?(?:x\.com|twitter\.com)/([^/?#\s]+)/status/(\d+)",
    re.IGNORECASE,
)
_RESERVED_HANDLES = frozenset({
    "i", "explore", "home", "search", "settings", "notifications",
    "messages", "lists", "bookmarks", "hashtag",
})


def _api_key():
    key = os.environ.get("TAVILY_API_KEY", "").strip()
    if not key:
        raise EnvironmentError(
            "[Tavily] TAVILY_API_KEY is not set. "
            "Sign up at app.tavily.com for a free API key (no credit card required). "
            "Add it to your .env file or as a GitHub Secret. "
            "Run 'python run_mock.py' to use mock mode without any API key."
        )
    return key


def _build_queries(profile):
    search_terms = profile.get("search_terms", [])
    if not search_terms:
        raise ValueError(
            "[Tavily] No search_terms found in profile YAML. "
            "Add a 'search_terms' list to profiles/signal_shift.yaml."
        )
    max_q = int(os.environ.get("MAX_SEARCH_QUERIES", "5"))
    return [f'site:x.com "{term}"' for term in search_terms[:max_q]]


def _post(query, max_results):
    """Single POST to Tavily Search API. Returns parsed JSON or None."""
    # Key goes in the request body — never in headers or logs.
    try:
        key = _api_key()
    except EnvironmentError:
        raise

    payload = {
        "api_key": key,
        "query": query,
        "max_results": max_results,
        "search_depth": "basic",
    }

    try:
        resp = requests.post(_TAVILY_API_URL, json=payload, timeout=15)
    except requests.RequestException as exc:
        print(f"[Tavily] Network error: {exc}")
        return None

    if resp.status_code == 200:
        return resp.json()
    if resp.status_code in (401, 403):
        print(
            f"[Tavily] Auth error {resp.status_code}. "
            "Check that TAVILY_API_KEY is valid and active."
        )
        return None
    if resp.status_code == 429:
        retry_after = resp.headers.get("Retry-After", "unknown")
        print(f"[Tavily] Rate limited. Retry-After: {retry_after}s. Skipping this query.")
        return None
    print(f"[Tavily] Unexpected status {resp.status_code} for query: {query!r}")
    return None


def _parse_age_hours(published_date):
    """
    Parse Tavily's published_date (ISO 8601) to age in hours.
    Falls back to 48.0 if absent or unparseable.
    """
    if not published_date:
        return 48.0
    try:
        dt = datetime.fromisoformat(published_date.replace("Z", "+00:00"))
        delta = datetime.now(timezone.utc) - dt
        return round(max(delta.total_seconds(), 0) / 3600, 1)
    except Exception:
        return 48.0


def _clean_text(title, content, username):
    """
    Extract the clearest post text from Tavily result fields.
    Tavily often returns X post titles as: 'Username on X: "post text"'
    Prefer content over title when it contains the better excerpt.
    """
    for text in (title, content):
        if not text:
            continue
        lower = text.lower()
        for prefix in (
            f"{username.lower()} on x:",
            "on x:",
            "on twitter:",
            f"@{username.lower()}:",
        ):
            idx = lower.find(prefix)
            if idx != -1:
                extracted = (
                    text[idx + len(prefix):]
                    .strip()
                    .strip('"\'')
                    .strip()
                )
                if len(extracted) > 15:
                    return extracted
    # Prefer content (Tavily's longer excerpt) over title if both present
    return (content or title or "").strip()


def _normalize(url, title, content, published_date):
    """
    Convert a Tavily search result to the standard post dict shape.
    Returns None if the URL is not a valid X/Twitter status URL.
    """
    m = _X_STATUS_RE.match(url)
    if not m:
        return None

    username = m.group(1)
    tweet_id = m.group(2)

    if username.lower() in _RESERVED_HANDLES:
        return None

    author = f"@{username}"
    text = _clean_text(title, content, username)
    age_hours = _parse_age_hours(published_date)
    post_url = f"https://x.com/{username}/status/{tweet_id}"

    return {
        "id": tweet_id,                        # string ID → dynamic reply generation
        "author": author,
        "author_name": username,
        "author_followers": 0,                  # unavailable from web search
        "author_profile_url": f"https://x.com/{username}",
        "text": text,
        "likes": 0,                             # unavailable
        "reposts": 0,                           # unavailable
        "reply_count": 0,                       # unavailable
        "impressions": 0,                       # unavailable
        "age_hours": age_hours,
        "post_url": post_url,
        "url": post_url,
        "discovery_source": "tavily_search",
        "metrics_confidence": "low",
    }


def get_posts(profile):
    """
    Discover recent X posts via Tavily Search API. Read-only.

    Safety: does not call the X API, does not scrape, does not log into X.
    TAVILY_API_KEY is never echoed to logs.
    Engagement metrics are unavailable - marked metrics_confidence=low.
    """
    queries = _build_queries(profile)
    max_results = int(os.environ.get("MAX_RESULTS_PER_QUERY", "5"))

    print(f"[Tavily] Provider: Tavily Search API (read-only, no X API)")
    print(f"[Tavily] Queries to run: {len(queries)} | Results per query: {max_results}")
    print(f"[Tavily] Max API calls this run: {len(queries)}")

    raw_count = 0
    url_count = 0
    seen_ids = set()
    posts = []

    for i, query in enumerate(queries):
        print(f"[Tavily] Query {i + 1}/{len(queries)}: {query}")
        data = _post(query, max_results)
        if not data:
            continue

        results = data.get("results", [])
        raw_count += len(results)

        for result in results:
            post = _normalize(
                result.get("url", ""),
                result.get("title", ""),
                result.get("content", ""),
                result.get("published_date"),
            )
            if post is None:
                continue
            url_count += 1
            if post["id"] in seen_ids:
                print(f"[Tavily] Duplicate tweet ID {post['id']} — skipped")
                continue
            seen_ids.add(post["id"])
            posts.append(post)

    print(f"[Tavily] Raw search results: {raw_count}")
    print(f"[Tavily] X status URLs extracted: {url_count}")
    print(f"[Tavily] After deduplication: {len(posts)} unique post(s)")
    print(f"[Tavily] Scoring {len(posts)} post(s)")
    return posts


def get_posting_history(_profile):
    """
    Posting history is not available in Tavily Search mode.
    Returns conservative defaults — post_generator treats 999h as
    "not posted recently" and applies normal schedule logic.
    Review schedule manually before posting.
    """
    print(
        "[Tavily] Posting history unavailable in Tavily Search mode. "
        "Using defaults — review posting schedule manually."
    )
    return {
        "founder": {
            "last_posted_hours_ago": 999,
            "last_post_note": "unknown (Tavily Search mode — check manually)",
        },
        "product": {
            "last_posted_hours_ago": 999,
            "last_post_note": "unknown (Tavily Search mode — check manually)",
        },
    }
