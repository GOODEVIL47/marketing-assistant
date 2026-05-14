#!/usr/bin/env python3
"""
Marketing Assistant — Mock Mode

Runs a full mock daily digest for the Signal Shift product profile.
No API keys required for mock mode. Email is optional and off by default.

Usage:
    python run_mock.py                  # digest only
    SEND_EMAIL=true python run_mock.py  # digest + email

Or create a .env file with your settings (see .env.example).
"""

import os
import yaml
from datetime import date

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not required — set env vars directly if preferred

from mock_data.posts import MOCK_POSTS
from src.scorer import score_posts
from src.replier import generate_replies
from src.post_generator import generate_posts
from src.digest import save_digest, _SCORE_ORDER, _OPP_ORDER
from src.email_renderer import render_digest_html, render_digest_text
from src.email_sender import send_digest


def load_profile(profile_path):
    with open(profile_path) as f:
        return yaml.safe_load(f)


def print_summary(posts_with_replies, posts_schedule, filepath):
    print("\n" + "=" * 60)
    print("  SIGNAL SHIFT — MOCK DAILY DIGEST (Mel)")
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

    print(f"Running mock mode for: {profile['name']}")

    scored = score_posts(MOCK_POSTS)
    with_replies = generate_replies(scored)
    posts_schedule = generate_posts(date.today().weekday())

    filepath = save_digest(profile["name"], with_replies, posts_schedule)
    print_summary(with_replies, posts_schedule, filepath)

    today = date.today().isoformat()
    subject = f"Mel's Daily Marketing Digest — {today}"
    html_body = render_digest_html(profile["name"], with_replies, posts_schedule)
    text_body = render_digest_text(profile["name"], with_replies, posts_schedule)

    send_email = os.getenv("SEND_EMAIL", "false").strip().lower() == "true"
    if not send_email:
        print("\n--- Email plain-text preview ---")
        print(text_body)
        print("--- End preview ---\n")

    send_digest(subject, html_body, text_body)


if __name__ == "__main__":
    main()
