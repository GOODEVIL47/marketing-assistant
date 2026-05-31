"""
M4.17 — tests for src/providers/x_provider.py

All network calls are mocked via unittest.mock.patch on requests.get.
No X_BEARER_TOKEN required. No real API calls are made.
"""

import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta

import requests

from src.providers.x_provider import (
    _parse_age_hours,
    _build_query,
    _normalize_post,
    get_posts,
    get_posting_history,
)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

def _tweet(
    id="1234567890",
    text="Test tweet text",
    author_id="111",
    created_at="2026-05-31T10:00:00Z",
    like_count=5,
    retweet_count=2,
    reply_count=1,
    quote_count=0,
    impression_count=100,
    conversation_id="1234567890",
    referenced_tweets=None,
    lang="en",
):
    t = {
        "id": id,
        "text": text,
        "author_id": author_id,
        "created_at": created_at,
        "public_metrics": {
            "like_count": like_count,
            "retweet_count": retweet_count,
            "reply_count": reply_count,
            "quote_count": quote_count,
            "impression_count": impression_count,
        },
        "conversation_id": conversation_id,
        "lang": lang,
    }
    if referenced_tweets is not None:
        t["referenced_tweets"] = referenced_tweets
    return t


def _user(id="111", username="testhandle", name="Test User", followers=500):
    return {
        "id": id,
        "username": username,
        "name": name,
        "public_metrics": {"followers_count": followers},
    }


def _mock_search_response(tweets, users):
    return {"data": tweets, "includes": {"users": users}}


def _mock_resp(status_code=200, json_data=None, headers=None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    resp.headers = headers or {}
    return resp


# ---------------------------------------------------------------------------
# TestParseAgeHours
# ---------------------------------------------------------------------------

class TestParseAgeHours(unittest.TestCase):

    def test_valid_z_suffix(self):
        now_utc = datetime.now(timezone.utc)
        two_hours_ago = (now_utc - timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
        age = _parse_age_hours(two_hours_ago)
        self.assertAlmostEqual(age, 2.0, delta=0.1)

    def test_valid_offset_suffix(self):
        now_utc = datetime.now(timezone.utc)
        five_hours_ago = (now_utc - timedelta(hours=5)).isoformat()
        age = _parse_age_hours(five_hours_ago)
        self.assertAlmostEqual(age, 5.0, delta=0.1)

    def test_malformed_string_returns_999(self):
        age = _parse_age_hours("not-a-date")
        self.assertEqual(age, 999.0)

    def test_empty_string_returns_999(self):
        age = _parse_age_hours("")
        self.assertEqual(age, 999.0)

    def test_future_date_returns_small_non_negative(self):
        now_utc = datetime.now(timezone.utc)
        future = (now_utc + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        age = _parse_age_hours(future)
        # delta is negative → total_seconds negative → age is negative or 0
        self.assertLessEqual(age, 0.2)


# ---------------------------------------------------------------------------
# TestBuildQuery
# ---------------------------------------------------------------------------

class TestBuildQuery(unittest.TestCase):

    def test_or_joins_terms(self):
        profile = {"search_terms": ["retail confusion", "market noise"]}
        q = _build_query(profile)
        self.assertIn('"retail confusion"', q)
        self.assertIn('"market noise"', q)
        self.assertIn(" OR ", q)

    def test_excludes_retweets_and_replies(self):
        profile = {"search_terms": ["signal shift"]}
        q = _build_query(profile)
        self.assertIn("-is:retweet", q)
        self.assertIn("-is:reply", q)
        self.assertIn("lang:en", q)

    def test_caps_at_five_terms(self):
        terms = [f"term{i}" for i in range(10)]
        profile = {"search_terms": terms}
        q = _build_query(profile)
        # Only first 5 should appear
        for i in range(5):
            self.assertIn(f'"term{i}"', q)
        for i in range(5, 10):
            self.assertNotIn(f'"term{i}"', q)

    def test_raises_on_empty_terms(self):
        with self.assertRaises(ValueError):
            _build_query({"search_terms": []})

    def test_raises_on_missing_search_terms_key(self):
        with self.assertRaises(ValueError):
            _build_query({})


# ---------------------------------------------------------------------------
# TestNormalizePost — happy path (user found)
# ---------------------------------------------------------------------------

class TestNormalizePost(unittest.TestCase):

    def setUp(self):
        self.tweet = _tweet()
        self.users = [_user()]
        self.post = _normalize_post(self.tweet, self.users)

    def test_id(self):
        self.assertEqual(self.post["id"], "1234567890")

    def test_author_at_prefixed(self):
        self.assertEqual(self.post["author"], "@testhandle")

    def test_username_no_at(self):
        self.assertEqual(self.post["username"], "testhandle")

    def test_author_name(self):
        self.assertEqual(self.post["author_name"], "Test User")

    def test_author_followers_not_follower_count(self):
        self.assertEqual(self.post["author_followers"], 500)
        self.assertNotIn("follower_count", self.post)

    def test_canonical_url_format(self):
        self.assertEqual(self.post["url"], "https://x.com/testhandle/status/1234567890")
        self.assertNotIn("/i/web/status/", self.post["url"])

    def test_post_url_equals_url(self):
        self.assertEqual(self.post["post_url"], self.post["url"])

    def test_author_profile_url(self):
        self.assertEqual(self.post["author_profile_url"], "https://x.com/testhandle")

    def test_text(self):
        self.assertEqual(self.post["text"], "Test tweet text")

    def test_combined_text_for_scoring_equals_text(self):
        self.assertEqual(self.post["combined_text_for_scoring"], self.post["text"])

    def test_created_at_passed_through(self):
        self.assertEqual(self.post["created_at"], "2026-05-31T10:00:00Z")

    def test_age_source_is_x_api(self):
        self.assertEqual(self.post["age_source"], "x_api")

    def test_discovery_source_is_x_api(self):
        self.assertEqual(self.post["discovery_source"], "x_api")

    def test_metrics_confidence_absent(self):
        self.assertNotIn("metrics_confidence", self.post)

    def test_likes(self):
        self.assertEqual(self.post["likes"], 5)

    def test_reposts_not_retweet_count(self):
        self.assertEqual(self.post["reposts"], 2)
        self.assertNotIn("retweet_count", self.post)

    def test_reply_count(self):
        self.assertEqual(self.post["reply_count"], 1)

    def test_quote_count(self):
        self.assertEqual(self.post["quote_count"], 0)

    def test_impressions_not_impression_count(self):
        self.assertEqual(self.post["impressions"], 100)
        self.assertNotIn("impression_count", self.post)

    def test_conversation_id(self):
        self.assertEqual(self.post["conversation_id"], "1234567890")

    def test_referenced_tweets_default_empty_list(self):
        self.assertEqual(self.post["referenced_tweets"], [])

    def test_referenced_tweets_present_when_set(self):
        rt = [{"type": "quoted", "id": "999"}]
        tweet = _tweet(referenced_tweets=rt)
        post = _normalize_post(tweet, self.users)
        self.assertEqual(post["referenced_tweets"], rt)

    def test_lang(self):
        self.assertEqual(self.post["lang"], "en")


# ---------------------------------------------------------------------------
# TestNormalizePostMissingUser — fallback when no user lookup available
# ---------------------------------------------------------------------------

class TestNormalizePostMissingUser(unittest.TestCase):

    def _post_no_user(self, includes_users=None):
        return _normalize_post(_tweet(id="9999", author_id="999"), includes_users)

    def test_empty_includes_users_author_unknown(self):
        post = self._post_no_user(includes_users=[])
        self.assertEqual(post["author"], "@unknown")

    def test_empty_includes_users_username_empty(self):
        post = self._post_no_user(includes_users=[])
        self.assertEqual(post["username"], "")

    def test_none_includes_users_author_unknown(self):
        post = self._post_no_user(includes_users=None)
        self.assertEqual(post["author"], "@unknown")

    def test_author_not_in_list_author_unknown(self):
        other_user = _user(id="different_id", username="someone")
        post = self._post_no_user(includes_users=[other_user])
        self.assertEqual(post["author"], "@unknown")

    def test_fallback_url_uses_i_web_status(self):
        post = self._post_no_user(includes_users=[])
        self.assertEqual(post["url"], "https://x.com/i/web/status/9999")

    def test_fallback_post_url_equals_url(self):
        post = self._post_no_user(includes_users=[])
        self.assertEqual(post["post_url"], post["url"])

    def test_fallback_author_profile_url_empty(self):
        post = self._post_no_user(includes_users=[])
        self.assertEqual(post["author_profile_url"], "")

    def test_no_fake_user_prefix_in_author(self):
        post = self._post_no_user(includes_users=[])
        self.assertNotIn("user_", post["author"])

    def test_no_fake_user_prefix_in_url(self):
        post = self._post_no_user(includes_users=[])
        self.assertNotIn("user_", post["url"])

    def test_other_fields_still_present(self):
        post = self._post_no_user(includes_users=[])
        for field in ("id", "text", "likes", "age_hours", "discovery_source", "age_source"):
            self.assertIn(field, post)


# ---------------------------------------------------------------------------
# TestGetPosts — mocked 200 response
# ---------------------------------------------------------------------------

class TestGetPosts(unittest.TestCase):

    def _profile(self):
        return {"search_terms": ["retail confusion", "market noise"]}

    @patch("src.providers.x_provider.requests.get")
    @patch.dict("os.environ", {"X_BEARER_TOKEN": "fake-token"})
    def test_returns_correct_post_count(self, mock_get):
        tweets = [_tweet(id=str(i), author_id="111") for i in range(3)]
        users = [_user()]
        mock_get.return_value = _mock_resp(200, _mock_search_response(tweets, users))

        posts = get_posts(self._profile())
        self.assertEqual(len(posts), 3)

    @patch("src.providers.x_provider.requests.get")
    @patch.dict("os.environ", {"X_BEARER_TOKEN": "fake-token"})
    def test_first_post_schema_valid(self, mock_get):
        tweets = [_tweet()]
        users = [_user()]
        mock_get.return_value = _mock_resp(200, _mock_search_response(tweets, users))

        posts = get_posts(self._profile())
        post = posts[0]

        self.assertEqual(post["author"], "@testhandle")
        self.assertEqual(post["username"], "testhandle")
        self.assertEqual(post["discovery_source"], "x_api")
        self.assertEqual(post["age_source"], "x_api")
        self.assertIn("author_followers", post)
        self.assertNotIn("follower_count", post)
        self.assertNotIn("metrics_confidence", post)

    @patch("src.providers.x_provider.requests.get")
    @patch.dict("os.environ", {"X_BEARER_TOKEN": "fake-token"})
    def test_empty_data_returns_empty_list(self, mock_get):
        mock_get.return_value = _mock_resp(200, {"data": [], "includes": {"users": []}})
        posts = get_posts(self._profile())
        self.assertEqual(posts, [])

    @patch("src.providers.x_provider.requests.get")
    @patch.dict("os.environ", {"X_BEARER_TOKEN": "fake-token"})
    def test_no_data_key_returns_empty_list(self, mock_get):
        mock_get.return_value = _mock_resp(200, {})
        posts = get_posts(self._profile())
        self.assertEqual(posts, [])


# ---------------------------------------------------------------------------
# TestGetPostsErrorHandling
# ---------------------------------------------------------------------------

class TestGetPostsErrorHandling(unittest.TestCase):

    def _profile(self):
        return {"search_terms": ["signal clarity"]}

    @patch("src.providers.x_provider.requests.get")
    @patch.dict("os.environ", {"X_BEARER_TOKEN": "fake-token"})
    def test_401_returns_empty_list(self, mock_get):
        mock_get.return_value = _mock_resp(401)
        self.assertEqual(get_posts(self._profile()), [])

    @patch("src.providers.x_provider.requests.get")
    @patch.dict("os.environ", {"X_BEARER_TOKEN": "fake-token"})
    def test_403_returns_empty_list(self, mock_get):
        mock_get.return_value = _mock_resp(403)
        self.assertEqual(get_posts(self._profile()), [])

    @patch("src.providers.x_provider.requests.get")
    @patch.dict("os.environ", {"X_BEARER_TOKEN": "fake-token"})
    def test_429_returns_empty_list(self, mock_get):
        mock_get.return_value = _mock_resp(429, headers={"x-rate-limit-reset": "9999999999"})
        self.assertEqual(get_posts(self._profile()), [])

    @patch("src.providers.x_provider.time.sleep")
    @patch("src.providers.x_provider.requests.get")
    @patch.dict("os.environ", {"X_BEARER_TOKEN": "fake-token"})
    def test_500_retries_once_then_returns_empty(self, mock_get, mock_sleep):
        mock_get.return_value = _mock_resp(503)
        result = get_posts(self._profile())
        self.assertEqual(result, [])
        self.assertEqual(mock_get.call_count, 2)

    @patch("src.providers.x_provider.time.sleep")
    @patch("src.providers.x_provider.requests.get")
    @patch.dict("os.environ", {"X_BEARER_TOKEN": "fake-token"})
    def test_network_exception_returns_empty(self, mock_get, mock_sleep):
        mock_get.side_effect = requests.RequestException("connection refused")
        self.assertEqual(get_posts(self._profile()), [])

    def test_missing_token_raises_env_error(self):
        import os
        os.environ.pop("X_BEARER_TOKEN", None)
        with self.assertRaises(EnvironmentError):
            get_posts(self._profile())


# ---------------------------------------------------------------------------
# TestGetPostingHistory
# ---------------------------------------------------------------------------

class TestGetPostingHistory(unittest.TestCase):

    def _profile(self, founder="signalfounder", product="signalproduct"):
        return {"handles": {"founder": f"@{founder}", "product": f"@{product}"}}

    def test_yourhandle_skipped(self):
        profile = {"handles": {"founder": "@yourhandle", "product": "@yourhandle"}}
        result = get_posting_history(profile)
        self.assertEqual(result["founder"]["last_posted_hours_ago"], 999)
        self.assertEqual(result["product"]["last_posted_hours_ago"], 999)

    def test_empty_handle_skipped(self):
        profile = {"handles": {"founder": "", "product": ""}}
        result = get_posting_history(profile)
        self.assertEqual(result["founder"]["last_posted_hours_ago"], 999)

    @patch("src.providers.x_provider.time.sleep")
    @patch("src.providers.x_provider.requests.get")
    @patch.dict("os.environ", {"X_BEARER_TOKEN": "fake-token"})
    def test_user_lookup_failure_uses_fallback(self, mock_get, mock_sleep):
        mock_get.return_value = _mock_resp(404)
        result = get_posting_history(self._profile())
        for key in ("founder", "product"):
            self.assertEqual(result[key]["last_posted_hours_ago"], 999)

    @patch("src.providers.x_provider.time.sleep")
    @patch("src.providers.x_provider.requests.get")
    @patch.dict("os.environ", {"X_BEARER_TOKEN": "fake-token"})
    def test_recent_tweet_age_decoded(self, mock_get, mock_sleep):
        now_utc = datetime.now(timezone.utc)
        three_hours_ago = (now_utc - timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M:%SZ")

        user_resp = _mock_resp(200, {"data": {"id": "u123"}})
        tweets_resp = _mock_resp(200, {"data": [{"id": "t1", "created_at": three_hours_ago}]})
        mock_get.side_effect = [user_resp, tweets_resp, user_resp, tweets_resp]

        result = get_posting_history(self._profile())
        self.assertAlmostEqual(result["founder"]["last_posted_hours_ago"], 3.0, delta=0.2)
        self.assertIn("h ago", result["founder"]["last_post_note"])

    @patch("src.providers.x_provider.time.sleep")
    @patch("src.providers.x_provider.requests.get")
    @patch.dict("os.environ", {"X_BEARER_TOKEN": "fake-token"})
    def test_no_recent_tweets_uses_fallback(self, mock_get, mock_sleep):
        user_resp = _mock_resp(200, {"data": {"id": "u123"}})
        tweets_resp = _mock_resp(200, {"data": []})
        mock_get.side_effect = [user_resp, tweets_resp, user_resp, tweets_resp]

        result = get_posting_history(self._profile())
        self.assertEqual(result["founder"]["last_posted_hours_ago"], 999)


if __name__ == "__main__":
    unittest.main()
