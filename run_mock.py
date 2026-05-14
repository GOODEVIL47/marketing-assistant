#!/usr/bin/env python3
"""
Marketing Assistant — Mock Mode

Runs a full mock daily digest for the Signal Shift product profile.
No API keys required. All data is hardcoded for demonstration.

Usage:
    python run_mock.py
"""

import yaml
import os

from mock_data.posts import MOCK_POSTS
from src.scorer import score_posts
from src.replier import generate_replies
from src.post_generator import generate_posts
from src.digest import save_digest


def load_profile(profile_path):
    with open(profile_path) as f:
        return yaml.safe_load(f)


def print_summary(posts_with_replies, founder_post, product_post, filepath):
    print("\n" + "=" * 60)
    print("  SIGNAL SHIFT — MOCK DAILY DIGEST")
    print("=" * 60)

    score_counts = {}
    for post in posts_with_replies:
        score_counts[post["score"]] = score_counts.get(post["score"], 0) + 1

    print("\nPost scores:")
    for label in ("Strong fit", "Decent fit", "Weak fit", "Avoid"):
        count = score_counts.get(label, 0)
        print(f"  {label}: {count}")

    print("\nPosts with replies generated:")
    for post in posts_with_replies:
        if post["replies"]:
            print(f"  Post {post['id']} ({post['author']}) — {len(post['replies'])} reply options")

    print(f"\nFounder post draft ready ({founder_post['account']})")
    print(f"Product post draft ready ({product_post['account']})")

    print(f"\nDigest saved to:\n  {filepath}")
    print("\n" + "=" * 60 + "\n")


def main():
    profile_path = os.path.join("profiles", "signal_shift.yaml")
    profile = load_profile(profile_path)

    print(f"Running mock mode for: {profile['name']}")

    scored = score_posts(MOCK_POSTS)
    with_replies = generate_replies(scored)
    founder_post, product_post = generate_posts()

    filepath = save_digest(profile["name"], with_replies, founder_post, product_post)
    print_summary(with_replies, founder_post, product_post, filepath)


if __name__ == "__main__":
    main()
