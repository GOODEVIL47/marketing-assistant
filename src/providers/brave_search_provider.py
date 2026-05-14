"""
Read-only Brave Search API provider for X post discovery.

Discovers recent X posts using Brave's web search API without calling
the X API, scraping, or logging into X. No X billing required.

SAFETY CONSTRAINTS — enforced here, never change without explicit user approval:
  - Read-only. No writes, no posts, no likes, no follows, no DMs.
  - Does not call the X API. Does not log into X. Does not scrape X pages.
  - Does not use browser automation.
  - Does not auto-post or auto-reply.
  - BRAVE_SEARCH_API_KEY is never printed in logs.

Limitations:
  - Engagement metrics (likes, replies, reposts) are unavailable from search results.
  - Results may not be as fresh as the X API.
  - Snippets may be truncated. Verify post quality before replying.
  - discovery_source="brave_search" and metrics_confidence="low" are set on
    every post so downstream scoring and rendering can flag uncertainty.
"""

import os
import re
import time

import requests

_BRAVE_API_URL = "https://api.search.brave.com/res/v1/web/search"
_X_STATUS_RE = re.compile(
    r"https?://(?:www\.)?(?:x\.com|twitter\.com)/([^/?#\s]+)/status/(\d+)",
    re.IGNORECASE,
)
# X path segments that are not real user handles
_RESERVED_HANDLES = frozenset({
    "i", "explore", "home", "search", "settings", "notifications",
    "messages", "lists", "bookmarks", "hashtag",
})


def _api_key():
    key = os.environ.get("BRAVE_SEARCH_API_KEY", "").strip()
    if not key:
        raise EnvironmentError(
            "[Brave] BRAVE_SEARCH_API_KEY is not set. "
            "Add it to your .env file or as a GitHub Secret. "
            "Run 'python run_mock.py' to use mock mode without any API key."
        )
    return key


def _build_queries(profile):
    search_terms = profile.get("search_terms", [])
    if not search_terms:
        raise ValueError(
            "[Brave] No search_terms found in profile YAML. "
            "Add a 'search_terms' list to profiles/signal_shift.yaml."
        )
    max_q = int(os.environ.get("MAX_SEARCH_QUERIES", "5"))
    return [f'site:x.com "{term}"' for term in search_terms[:max_q]]


def _get(query, max_results):
    """Single GET against Brave Search API. Returns parsed JSON or None."""
    try:
        key = _api_key()
    except EnvironmentError:
        raise

    headers = {
        "X-Subscription-Token": key,
        "Accept": "application/json",
    }
    params = {"q": query, "count": max_results}

    try:
        resp = requests.get(_BRAVE_API_URL, headers=headers, params=params, timeout=15)
    except requests.RequestException as exc:
        print(f"[Brave] Network error: {exc}")
        return None

    if resp.status_code == 200:
        return resp.json()
    if resp.status_code in (401, 403):
        print(
            f"[Brave] Auth error {resp.status_code}. "
            "Check that BRAVE_SEARCH_API_KEY is valid and active."
        )
        return None
    if resp.status_code == 429:
        retry_after = resp.headers.get("Retry-After", "unknown")
        print(f"[Brave] Rate limited. Retry-After: {retry_after}s. Skipping this query.")
        return None
    print(f"[Brave] Unexpected status {resp.status_code} for query: {query!r}")
    return None


def _parse_age_hours(age_str):
    """Best-effort parse of Brave's human-readable age strings into hours."""
    if not age_str:
        return 48.0
    s = age_str.lower().strip()
    for pattern, multiplier in [
        (r"(\d+)\s*minute", 1 / 60),
        (r"(\d+)\s*hour",   1.0),
        (r"(\d+)\s*day",    24.0),
        (r"(\d+)\s*week",   7 * 24.0),
        (r"(\d+)\s*month",  30 * 24.0),
    ]:
        m = re.search(pattern, s)
        if m:
            return round(int(m.group(1)) * multiplier, 2)
    return 48.0  # unknown — conservative default


def _clean_text(title, description, username):
    """
    Extract the clearest available post text from Brave search result fields.
    Brave often wraps X post titles as: 'Username on X: "post text here"'
    """
    for text in (title, description):
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
                    .strip("“”\"'")
                    .strip()
                )
                if len(extracted) > 15:
                    return extracted
    return (description or title or "").strip()


def _normalize(url, title, description, age_str):
    """
    Convert a Brave search result to the standard post dict shape.
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
    text = _clean_text(title, description, username)
    age_hours = _parse_age_hours(age_str)
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
        "discovery_source": "brave_search",
        "metrics_confidence": "low",
    }


def get_posts(profile):
    """
    Discover recent X posts via Brave Search API. Read-only.

    Safety: does not call the X API, does not scrape, does not log into X.
    Engagement metrics are unavailable — marked metrics_confidence=low.
    BRAVE_SEARCH_API_KEY is never echoed to logs.
    """
    queries = _build_queries(profile)
    max_results = int(os.environ.get("MAX_RESULTS_PER_QUERY", "5"))

    print(f"[Brave] Provider: Brave Search API (read-only, no X API)")
    print(f"[Brave] Queries to run: {len(queries)} | Results per query: {max_results}")
    print(f"[Brave] Max API calls this run: {len(queries)}")

    raw_count = 0
    url_count = 0
    seen_ids = set()
    posts = []

    for i, query in enumerate(queries):
        print(f"[Brave] Query {i + 1}/{len(queries)}: {query}")
        data = _get(query, max_results)
        if not data:
            continue

        results = data.get("web", {}).get("results", [])
        raw_count += len(results)

        for result in results:
            post = _normalize(
                result.get("url", ""),
                result.get("title", ""),
                result.get("description", ""),
                result.get("age", ""),
            )
            if post is None:
                continue
            url_count += 1
            if post["id"] in seen_ids:
                print(f"[Brave] Duplicate tweet ID {post['id']} — skipped")
                continue
            seen_ids.add(post["id"])
            posts.append(post)

        if i < len(queries) - 1:
            time.sleep(1)  # polite delay between queries

    print(f"[Brave] Raw search results: {raw_count}")
    print(f"[Brave] X status URLs extracted: {url_count}")
    print(f"[Brave] After deduplication: {len(posts)} unique post(s)")
    print(f"[Brave] Scoring {len(posts)} post(s)")
    return posts


def get_posting_history(_profile):
    """
    Posting history is not available in Brave Search mode.
    Returns conservative defaults — post_generator treats 999h as
    "not posted recently" and will apply the normal schedule logic.
    Review schedule manually before posting.
    """
    print(
        "[Brave] Posting history check unavailable in Brave Search mode. "
        "Using defaults — review posting schedule manually."
    )
    return {
        "founder": {
            "last_posted_hours_ago": 999,
            "last_post_note": "unknown (Brave Search mode — check manually)",
        },
        "product": {
            "last_posted_hours_ago": 999,
            "last_post_note": "unknown (Brave Search mode — check manually)",
        },
    }
