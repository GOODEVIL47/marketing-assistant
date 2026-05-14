#!/usr/bin/env python3
"""
Marketing Assistant — Brave Search Discovery Mode

Discovers relevant X posts using Brave's web search API — no X API billing,
no scraping, no login. Posts are found via site:x.com search queries built
from the profile's search_terms, scored with dynamic keyword-based fit logic,
and assembled into the standard Mel digest.

SAFETY: Read-only. Nothing is posted, liked, followed, or replied to.
        Reply suggestions are for manual review only.
        Engagement metrics are unavailable — verify before replying.

Why Brave Search instead of the X API:
  The X API requires a paid plan for any meaningful search volume.
  Brave Search's free/indie tier allows limited discovery without X billing.
  See README for limitations and credit usage.

Environment variables:
    BRAVE_SEARCH_API_KEY    (required)
    MAX_SEARCH_QUERIES=5    (optional, default 5)
    MAX_RESULTS_PER_QUERY=5 (optional, default 5)
    SEND_EMAIL=false        (optional, same as other modes)

Usage:
    python run_brave.py
    SEND_EMAIL=true python run_brave.py
"""

import os
import yaml
from datetime import date

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # set env vars directly if preferred

from src.providers import brave_search_provider
from src.scorer import score_posts
from src.replier import generate_replies
from src.post_generator import generate_posts
from src.digest import save_digest, _SCORE_ORDER, _OPP_ORDER
from src.email_renderer import render_digest_html, render_digest_text
from src.email_sender import send_digest

_MODE = "Brave Search"


def load_profile(profile_path):
    with open(profile_path) as f:
        return yaml.safe_load(f)


def print_summary(posts_with_replies, posts_schedule, filepath):
    print("\n" + "=" * 60)
    print("  SIGNAL SHIFT — BRAVE SEARCH DIGEST (Mel)")
    print("=" * 60)

    fit_counts = {}
    opp_counts = {}
    for post in posts_with_replies:
        fit_counts[post["score"]] = fit_counts.get(post["score"], 0) + 1
        opp_counts[post["opportunity"]] = opp_counts.get(post["opportunity"], 0) + 1

    print("\nFit scores:")
    for label in ("Strong fit", "Decent fit", "Weak fit", "Avoid"):
        print(f"  {label}: {fit_counts.get(label, 0)}")

    print("\nOpportunity scores:")
    for label in ("High opportunity", "Medium opportunity", "Low opportunity", "Poor opportunity"):
        print(f"  {label}: {opp_counts.get(label, 0)}")

    best3 = [
        p for p in posts_with_replies
        if p["score"] in ("Strong fit", "Decent fit")
        and p["opportunity"] in ("High opportunity", "Medium opportunity")
    ]
    print(f"\nToday's Best 3 ({len(best3)} post(s) qualify):")
    for post in sorted(
        best3,
        key=lambda p: (_SCORE_ORDER.index(p["score"]), _OPP_ORDER.index(p["opportunity"])),
    )[:3]:
        print(f"  {post['author']} — {post['score']} · {post['opportunity']}")
        print(f"    {post.get('engagement_summary', '')}")

    print("\nOriginal posts today:")
    for role in ("founder", "product"):
        s = posts_schedule[role]
        status = "Recommended" if s["needed"] else "Not needed (optional idea included)"
        print(f"  {role.title()} ({s['handle']}): {status}")

    print(f"\nDigest saved to:\n  {filepath}")
    print("=" * 60 + "\n")


def main():
    profile_path = os.path.join("profiles", "signal_shift.yaml")
    profile = load_profile(profile_path)

    print(f"[Brave] Running Brave Search discovery mode for: {profile['name']}")
    print("[Brave] SAFETY: read-only. Nothing will be posted, liked, or followed.")
    print("[Brave] Note: engagement metrics unavailable. Verify manually before replying.")
    print()

    try:
        posts = brave_search_provider.get_posts(profile)
    except EnvironmentError as exc:
        print(f"\n{exc}\n")
        return

    if not posts:
        print(
            "[Brave] No X posts found. Try adjusting search_terms in profiles/signal_shift.yaml, "
            "or check that BRAVE_SEARCH_API_KEY is valid."
        )
        return

    posting_history = brave_search_provider.get_posting_history(profile)

    scored = score_posts(posts, profile=profile)
    with_replies = generate_replies(scored)
    posts_schedule = generate_posts(date.today().weekday(), posting_history=posting_history)

    filepath = save_digest(profile["name"], with_replies, posts_schedule, mode=_MODE)
    print_summary(with_replies, posts_schedule, filepath)

    today = date.today().isoformat()
    subject = f"Mel's Daily Marketing Digest — {today} (Brave Search)"
    html_body = render_digest_html(profile["name"], with_replies, posts_schedule, mode=_MODE)
    text_body = render_digest_text(profile["name"], with_replies, posts_schedule, mode=_MODE)

    send_email = os.getenv("SEND_EMAIL", "false").strip().lower() == "true"
    if not send_email:
        print("\n--- Email plain-text preview ---")
        print(text_body)
        print("--- End preview ---\n")

    send_digest(subject, html_body, text_body)


if __name__ == "__main__":
    main()
