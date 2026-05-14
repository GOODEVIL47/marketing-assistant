"""
Smoke tests for dynamic reply generation.

Verifies:
  - Real X posts (string IDs) receive A/B/C reply options and media guidance.
  - Mock posts (integer IDs 1–8) still use hardcoded REPLIES unchanged.
  - Weak/Avoid posts receive no replies regardless of ID type.
  - Each theme produces exactly 3 options with a valid best_reply.
  - No reply text contains forbidden language.

Run with:
    python -m pytest tests/test_real_replies.py -v
  or:
    python tests/test_real_replies.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.replier import generate_replies, REPLIES, _DYNAMIC_TEMPLATES, _detect_reply_theme

_BASE_POST = {
    "author": "@test_user",
    "author_name": "Test User",
    "follower_count": 500,
    "likes": 45,
    "reposts": 5,
    "reply_count": 8,
    "impressions": 1200,
    "age_hours": 4.0,
    "visibility": "Decent visibility",
    "opportunity": "Medium opportunity",
    "opportunity_reason": "Decent fit and moderate visibility.",
    "engagement_summary": "45 likes · 8 replies · 5 reposts · 4h old",
    "suggested_action": "Reply",
    "reply_account": "Founder",
    "reason": "Test post.",
    "url": "https://x.com/i/web/status/1789234567890001999",
}

_FORBIDDEN = [
    "buy", "sell", "hold", "financial advice", "guaranteed", "10x", "moon",
    "🚀", "get rich", "this stock will", "i recommend",
]


def _make_real_post(text, score="Strong fit"):
    return {
        **_BASE_POST,
        "id": "1789234567890001999",
        "text": text,
        "score": score,
    }


def _make_mock_post(post_id, score="Strong fit"):
    return {
        **_BASE_POST,
        "id": post_id,
        "text": "Mock post text.",
        "score": score,
    }


def _check_replies(post, label):
    assert len(post["replies"]) == 3, f"{label}: expected 3 reply options, got {len(post['replies'])}"
    assert post["best_reply"] is not None, f"{label}: best_reply should not be None"
    assert post["media"] is not None, f"{label}: media should not be None"
    styles = [r["style"] for r in post["replies"]]
    assert any("A" in s for s in styles), f"{label}: missing option A"
    assert any("B" in s for s in styles), f"{label}: missing option B"
    assert any("C" in s for s in styles), f"{label}: missing option C"
    for r in post["replies"]:
        text_lower = r["text"].lower()
        for word in _FORBIDDEN:
            assert word not in text_lower, (
                f"{label}: reply contains forbidden term '{word}': {r['text']!r}"
            )


def test_real_post_noise_overwhelm():
    post = _make_real_post("The noise around earnings week is exhausting. Just want clarity.")
    result = generate_replies([post])[0]
    _check_replies(result, "noise_overwhelm real post")
    assert result["media"]["type"] == "Optional GIF"
    print("PASS test_real_post_noise_overwhelm")


def test_real_post_bias_emotional():
    post = _make_real_post("Confirmation bias is so real. I keep explaining away the bad signals.")
    result = generate_replies([post])[0]
    _check_replies(result, "bias_emotional real post")
    assert result["media"]["type"] == "Quote repost"
    print("PASS test_real_post_bias_emotional")


def test_real_post_reactive():
    post = _make_real_post("Stopped being so reactive to every headline. Portfolio stopped moving with the news.")
    result = generate_replies([post])[0]
    _check_replies(result, "reactive_slow_down real post")
    assert result["media"]["type"] == "Optional GIF"
    print("PASS test_real_post_reactive")


def test_real_post_data_vs_insight():
    post = _make_real_post("More dashboards, more data — but still no idea what to do with any of it.")
    result = generate_replies([post])[0]
    _check_replies(result, "data_vs_insight real post")
    assert result["media"]["type"] == "No media"
    print("PASS test_real_post_data_vs_insight")


def test_real_post_generic_strong_fallback():
    post = _make_real_post("Retail investors deserve better tools.", score="Strong fit")
    result = generate_replies([post])[0]
    _check_replies(result, "generic_strong fallback")
    print("PASS test_real_post_generic_strong_fallback")


def test_real_post_generic_decent_fallback():
    post = _make_real_post("Interesting take on market cycles.", score="Decent fit")
    result = generate_replies([post])[0]
    _check_replies(result, "generic_decent fallback")
    print("PASS test_real_post_generic_decent_fallback")


def test_real_post_weak_no_replies():
    post = {**_make_real_post("RSI breakout setup on $XYZ looking bullish."), "score": "Weak fit",
            "opportunity": "Poor opportunity", "suggested_action": "Do not engage"}
    result = generate_replies([post])[0]
    assert result["replies"] == [], "Weak fit real post should get no replies"
    assert result["best_reply"] is None
    print("PASS test_real_post_weak_no_replies")


def test_mock_post_replies_unchanged():
    for post_id in (1, 2, 3, 4):
        score = "Strong fit" if post_id in (1, 2) else "Decent fit"
        post = _make_mock_post(post_id, score=score)
        result = generate_replies([post])[0]
        assert result["replies"] == REPLIES[post_id]["options"], (
            f"Mock post {post_id}: replies should match hardcoded REPLIES unchanged"
        )
        assert result["media"] == REPLIES[post_id]["media"], (
            f"Mock post {post_id}: media should match hardcoded REPLIES unchanged"
        )
    print("PASS test_mock_post_replies_unchanged (IDs 1–4)")


def test_all_templates_no_forbidden_language():
    for theme, template in _DYNAMIC_TEMPLATES.items():
        for option in template["options"]:
            text_lower = option["text"].lower()
            for word in _FORBIDDEN:
                assert word not in text_lower, (
                    f"Template '{theme}' option '{option['style']}' contains "
                    f"forbidden term '{word}': {option['text']!r}"
                )
    print(f"PASS test_all_templates_no_forbidden_language ({len(_DYNAMIC_TEMPLATES)} themes checked)")


def test_best_reply_index_in_range():
    for theme, template in _DYNAMIC_TEMPLATES.items():
        idx = template["best_option_index"]
        assert 0 <= idx < len(template["options"]), (
            f"Template '{theme}' best_option_index {idx} out of range"
        )
    print("PASS test_best_reply_index_in_range")


if __name__ == "__main__":
    tests = [
        test_real_post_noise_overwhelm,
        test_real_post_bias_emotional,
        test_real_post_reactive,
        test_real_post_data_vs_insight,
        test_real_post_generic_strong_fallback,
        test_real_post_generic_decent_fallback,
        test_real_post_weak_no_replies,
        test_mock_post_replies_unchanged,
        test_all_templates_no_forbidden_language,
        test_best_reply_index_in_range,
    ]
    failed = 0
    for t in tests:
        try:
            t()
        except AssertionError as e:
            print(f"FAIL {t.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"ERROR {t.__name__}: {e}")
            failed += 1
    print()
    if failed:
        print(f"{failed}/{len(tests)} test(s) FAILED")
        sys.exit(1)
    else:
        print(f"All {len(tests)} tests passed.")
