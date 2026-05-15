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

_TWITTER_EPOCH_MS = 1288834974657  # Twitter epoch: 2010-11-04 01:42:54 UTC

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


_DEFAULT_QUERY_TEMPLATES = ['site:x.com "{term}"']


def _build_candidate_queries(profile):
    """
    Generate an ordered candidate query list from profile search_terms and
    query_templates. Templates are iterated first (outer loop) so all terms
    for template 1 appear before any terms for template 2, preserving the
    priority intent: base quote searches before time-qualified variants.
    Duplicates are suppressed.
    """
    terms = profile.get("search_terms", [])
    templates = profile.get("query_templates", _DEFAULT_QUERY_TEMPLATES)
    seen = set()
    candidates = []
    for template in templates:
        for term in terms:
            q = template.replace("{term}", term)
            if q not in seen:
                seen.add(q)
                candidates.append(q)
    return candidates


def _query_seed():
    """
    Return (seed_int, seed_label) for deterministic daily query rotation.
    QUERY_SEED env var overrides the date — useful for testing different
    query selections without waiting for a new calendar day.
    """
    seed_str = os.environ.get("QUERY_SEED", "").strip()
    if seed_str:
        try:
            return int(seed_str), f"QUERY_SEED={seed_str}"
        except ValueError:
            print(f"[Tavily] QUERY_SEED={seed_str!r} is not an integer — using date seed instead.")
    today = datetime.now(timezone.utc).date()
    return today.toordinal(), f"date={today.isoformat()}"


def _select_queries(candidates, max_q, seed):
    """
    Select max_q queries from candidates using seed-based rotation within
    a priority window (top max_q * 10 candidates).

    High-priority queries (lower index) are always in the window so they
    are favoured. The seed offsets the start position within that window
    so each day selects a different slice — same seed always produces the
    same selected queries.
    """
    if not candidates:
        return []
    if len(candidates) <= max_q:
        return list(candidates)
    window_size = min(len(candidates), max_q * 10)
    offset = seed % window_size
    window = candidates[:window_size]
    rotated = window[offset:] + window[:offset]
    return rotated[:max_q]


def _build_bucket_queries(buckets, max_q, seed):
    """
    Select up to max_q queries from query_buckets with diversified allocation.

    Allocation: base = max_q // n_buckets per bucket; remainder distributed
    to the earliest buckets. If max_q < n_buckets, first max_q buckets each
    receive 1 query and the rest are skipped.

    Within each bucket the seed (plus a per-bucket offset) rotates the start
    position so different days pick different queries from each bucket.

    Returns [(bucket_name, query_string), ...], length <= max_q.
    """
    active = [(name, qs) for name, qs in buckets.items() if qs]
    n = len(active)
    if n == 0:
        return []

    if max_q <= n:
        # 1 query from each of the first max_q buckets
        alloc = [(name, qs, 1) for name, qs in active[:max_q]]
    else:
        base = max_q // n
        remainder = max_q % n
        alloc = [
            (name, qs, base + (1 if i < remainder else 0))
            for i, (name, qs) in enumerate(active)
        ]

    selected = []
    for i, (bucket_name, bucket_queries, count) in enumerate(alloc):
        n_q = len(bucket_queries)
        offset = (seed + i) % n_q
        rotated = bucket_queries[offset:] + bucket_queries[:offset]
        for q in rotated[:count]:
            selected.append((bucket_name, q))

    return selected[:max_q]


def _build_queries(profile):
    max_q = int(os.environ.get("MAX_SEARCH_QUERIES", "5"))
    seed, seed_label = _query_seed()

    buckets = profile.get("query_buckets")
    if buckets:
        selected_pairs = _build_bucket_queries(buckets, max_q, seed)
        if not selected_pairs:
            raise ValueError(
                "[Tavily] query_buckets is present but all buckets are empty. "
                "Add at least one query string to a bucket in profiles/signal_shift.yaml."
            )
        total_in_buckets = sum(len(v) for v in buckets.values() if v)
        print(
            f"[Tavily] Query buckets: {len(buckets)} | "
            f"Total bucket queries: {total_in_buckets} | "
            f"Selected (cap={max_q}): {len(selected_pairs)} | Seed: {seed_label}"
        )
        print(f"[Tavily] Selected queries:")
        idx = 1
        current_bucket = None
        for bucket_name, query in selected_pairs:
            if bucket_name != current_bucket:
                print(f"  {bucket_name}:")
                current_bucket = bucket_name
            print(f"    {idx}. {query}")
            idx += 1
        return [q for _, q in selected_pairs]

    # Legacy path: search_terms + query_templates
    search_terms = profile.get("search_terms", [])
    if not search_terms:
        raise ValueError(
            "[Tavily] No search_terms or query_buckets found in profile YAML. "
            "Add a 'search_terms' list or 'query_buckets' dict to profiles/signal_shift.yaml."
        )
    candidates = _build_candidate_queries(profile)
    selected = _select_queries(candidates, max_q, seed)

    templates = profile.get("query_templates", _DEFAULT_QUERY_TEMPLATES)
    print(f"[Tavily] Query templates available: {len(templates)}")
    print(
        f"[Tavily] Candidate queries: {len(candidates)} | "
        f"Selected (cap={max_q}): {len(selected)} | Seed: {seed_label}"
    )
    for i, q in enumerate(selected, 1):
        print(f"[Tavily]   {i}. {q}")

    return selected


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


def _decode_snowflake(tweet_id):
    """
    Decode creation time from a Twitter/X Snowflake ID.
    Returns (age_hours, age_source). age_source is 'snowflake' on success,
    'unknown' on failure. Pure math — no network calls.
    """
    try:
        tid = int(tweet_id)
        created_ms = (tid >> 22) + _TWITTER_EPOCH_MS
        created_dt = datetime.fromtimestamp(created_ms / 1000, tz=timezone.utc)
        delta = datetime.now(timezone.utc) - created_dt
        age_hours = round(max(delta.total_seconds(), 0) / 3600, 1)
        return age_hours, "snowflake"
    except Exception:
        return None, "unknown"


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
    post_url = f"https://x.com/{username}/status/{tweet_id}"

    # Preserve raw Tavily fields for richer scoring context.
    # Scoring uses this so out-of-scope terms buried in Tavily's title/snippet
    # are caught even when _clean_text() extracts a shorter display text.
    combined_text_for_scoring = " ".join(part for part in [title, content] if part)

    # Prefer Snowflake-decoded age (accurate to the second) over Tavily's
    # published_date (search index lag, may differ by hours or days).
    sf_age, sf_source = _decode_snowflake(tweet_id)
    if sf_source == "snowflake":
        age_hours = sf_age
        age_source = "snowflake"
    elif published_date:
        age_hours = _parse_age_hours(published_date)
        age_source = "tavily"
    else:
        age_hours = None   # truly unknown — do not guess
        age_source = "unknown"

    return {
        "id": tweet_id,                        # string ID → dynamic reply generation
        "author": author,
        "author_name": username,
        "author_followers": 0,                  # unavailable from web search
        "author_profile_url": f"https://x.com/{username}",
        "text": text,
        "combined_text_for_scoring": combined_text_for_scoring,
        "likes": 0,                             # unavailable
        "reposts": 0,                           # unavailable
        "reply_count": 0,                       # unavailable
        "impressions": 0,                       # unavailable
        "age_hours": age_hours,
        "age_source": age_source,
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
    print(f"[Tavily] Provider: Tavily Search API (read-only, no X API)")
    queries = _build_queries(profile)
    max_results = int(os.environ.get("MAX_RESULTS_PER_QUERY", "5"))
    print(f"[Tavily] Results per query: {max_results}")

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
