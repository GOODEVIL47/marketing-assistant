"""
Read-only X API v2 provider.

SAFETY CONSTRAINTS — enforced here, never change without explicit user approval:
  - Read-only. No writes, no posts, no likes, no follows, no DMs.
  - Bearer token auth only. Never stores or requests passwords.
  - No auto-posting or auto-replying of any kind.
"""

import os
import time
from datetime import datetime, timezone

import requests

_BASE = "https://api.twitter.com/2"
_MAX_RESULTS = 10  # per search call; X free tier allows up to 10


def _bearer_headers():
    token = os.environ.get("X_BEARER_TOKEN", "").strip()
    if not token:
        raise EnvironmentError(
            "[X] X_BEARER_TOKEN is not set. "
            "Set it in your .env file or as a GitHub Secret. "
            "Run 'python run_mock.py' to use mock mode without a token."
        )
    return {"Authorization": f"Bearer {token}"}


def _get(url, params, label):
    """Single GET with one retry on transient 5xx errors. Never retries auth failures."""
    headers = _bearer_headers()
    for attempt in (1, 2):
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=15)
        except requests.RequestException as exc:
            print(f"[X] Network error on {label} (attempt {attempt}): {exc}")
            if attempt == 2:
                return None
            time.sleep(3)
            continue

        if resp.status_code == 200:
            return resp.json()

        if resp.status_code in (401, 403):
            print(
                f"[X] Auth error {resp.status_code} on {label}. "
                "Check that X_BEARER_TOKEN is valid and has read permissions."
            )
            return None

        if resp.status_code == 429:
            reset = resp.headers.get("x-rate-limit-reset", "unknown")
            print(f"[X] Rate limited on {label}. Resets at Unix time {reset}. Skipping.")
            return None

        if resp.status_code >= 500 and attempt == 1:
            print(f"[X] Server error {resp.status_code} on {label}. Retrying once...")
            time.sleep(3)
            continue

        print(f"[X] Unexpected status {resp.status_code} on {label}.")
        return None

    return None


def _parse_age_hours(created_at_str):
    try:
        created = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
        delta = datetime.now(timezone.utc) - created
        return round(delta.total_seconds() / 3600, 1)
    except Exception:
        return 999.0


def _normalize_post(tweet, includes_users=None):
    """Convert a raw X API v2 tweet object to the standard post dict shape."""
    metrics = tweet.get("public_metrics", {})
    author_id = tweet.get("author_id", "")
    tweet_id = tweet["id"]

    username = ""
    author_name = ""
    follower_count = 0

    if includes_users:
        for user in includes_users:
            if user.get("id") == author_id:
                username = user.get("username", "")
                author_name = user.get("name", "")
                follower_count = user.get("public_metrics", {}).get("followers_count", 0)
                break

    if username:
        author = "@" + username
        url = f"https://x.com/{username}/status/{tweet_id}"
        author_profile_url = f"https://x.com/{username}"
    else:
        author = "@unknown"
        url = f"https://x.com/i/web/status/{tweet_id}"
        author_profile_url = ""

    age_hours = _parse_age_hours(tweet.get("created_at", ""))
    text = tweet.get("text", "")

    return {
        "id": tweet_id,
        "author": author,
        "username": username,
        "author_name": author_name,
        "author_followers": follower_count,
        "author_profile_url": author_profile_url,
        "text": text,
        "combined_text_for_scoring": text,
        "created_at": tweet.get("created_at", ""),
        "age_hours": age_hours,
        "age_source": "x_api",
        "url": url,
        "post_url": url,
        "discovery_source": "x_api",
        "likes": metrics.get("like_count", 0),
        "reposts": metrics.get("retweet_count", 0),
        "reply_count": metrics.get("reply_count", 0),
        "quote_count": metrics.get("quote_count", 0),
        "impressions": metrics.get("impression_count", 0),
        "conversation_id": tweet.get("conversation_id", ""),
        "referenced_tweets": tweet.get("referenced_tweets", []),
        "lang": tweet.get("lang", ""),
    }


def _build_query(profile):
    """Build an X search query from profile search_terms. Excludes retweets."""
    terms = profile.get("search_terms", [])
    if not terms:
        raise ValueError(
            "[X] No search_terms found in profile YAML. "
            "Add a 'search_terms' list to profiles/signal_shift.yaml."
        )
    # OR-join terms, exclude retweets and replies for cleaner signal
    joined = " OR ".join(f'"{t}"' for t in terms[:5])  # X free tier: keep query short
    return f"({joined}) -is:retweet -is:reply lang:en"


def get_posts(profile):
    """Fetch recent X posts matching the profile's search terms. Read-only."""
    query = _build_query(profile)
    print(f"[X] Searching recent posts | query: {query}")

    params = {
        "query": query,
        "max_results": _MAX_RESULTS,
        "tweet.fields": "created_at,public_metrics,author_id,conversation_id,referenced_tweets,lang",
        "expansions": "author_id",
        "user.fields": "username,name,public_metrics",
    }
    data = _get(f"{_BASE}/tweets/search/recent", params, "search/recent")

    if not data:
        print("[X] Search returned no data. Falling back to empty post list.")
        return []

    tweets = data.get("data", [])
    users = data.get("includes", {}).get("users", [])
    print(f"[X] Retrieved {len(tweets)} post(s) from search.")

    posts = [_normalize_post(t, users) for t in tweets]
    return posts


def get_posting_history(profile):
    """
    Fetch the most recent tweet time for founder and product handles.
    Returns the same shape as MOCK_POSTING_HISTORY so post_generator works unchanged.
    Read-only.
    """
    handles = profile.get("handles", {})
    founder_handle = handles.get("founder", "").lstrip("@")
    product_handle = handles.get("product", "").lstrip("@")

    result = {}
    for key, handle in (("founder", founder_handle), ("product", product_handle)):
        if not handle or handle == "yourhandle":
            print(f"[X] Skipping posting history for '{key}' — handle not configured in profile.")
            result[key] = {"last_posted_hours_ago": 999, "last_post_note": "unknown (handle not set)"}
            continue

        user_data = _get(
            f"{_BASE}/users/by/username/{handle}",
            {"user.fields": "id"},
            f"user lookup @{handle}",
        )
        if not user_data or "data" not in user_data:
            print(f"[X] Could not look up @{handle}. Using fallback (assume not posted today).")
            result[key] = {"last_posted_hours_ago": 999, "last_post_note": f"unknown (@{handle} lookup failed)"}
            continue

        user_id = user_data["data"]["id"]
        tweets_data = _get(
            f"{_BASE}/users/{user_id}/tweets",
            {
                "max_results": 5,
                "tweet.fields": "created_at",
                "exclude": "retweets,replies",
            },
            f"recent tweets @{handle}",
        )

        if not tweets_data or not tweets_data.get("data"):
            print(f"[X] No recent tweets found for @{handle}.")
            result[key] = {"last_posted_hours_ago": 999, "last_post_note": f"no recent posts (@{handle})"}
            continue

        most_recent = tweets_data["data"][0]
        age_hours = _parse_age_hours(most_recent.get("created_at", ""))
        age_h = int(age_hours)

        if age_h < 1:
            note = "< 1h ago"
        elif age_h < 24:
            note = f"~{age_h}h ago"
        else:
            days = age_h // 24
            note = f"~{days}d ago"

        print(f"[X] @{handle} last posted: {note}")
        result[key] = {"last_posted_hours_ago": age_hours, "last_post_note": note}

    return result
