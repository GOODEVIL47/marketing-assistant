#!/usr/bin/env python3
"""
Marketing Assistant — Web Search Discovery Mode

Discovers relevant X posts through a pluggable web search provider.
No X API billing, no scraping, no login.

SAFETY: Read-only. Nothing is posted, liked, followed, or replied to.
        Reply suggestions are for manual review only.
        Engagement metrics are unavailable — verify before replying.

Supported providers (set via SEARCH_PROVIDER env var):
    tavily  — Tavily Search API (default, free tier, no credit card)
    brave   — Brave Search API (requires paid subscription)

Usage:
    python run_search.py
    SEARCH_PROVIDER=brave python run_search.py
    SEND_EMAIL=true python run_search.py

Environment variables:
    SEARCH_PROVIDER=tavily      (default)
    TAVILY_API_KEY              (required for tavily)
    BRAVE_SEARCH_API_KEY        (required for brave)
    MAX_SEARCH_QUERIES=5
    MAX_RESULTS_PER_QUERY=5
    SEND_EMAIL=false
"""

import os
import sys
import yaml
from datetime import date

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from src.scorer import score_posts
from src.replier import generate_replies
from src.post_generator import generate_posts
from src.digest import save_digest, _SCORE_ORDER, _OPP_ORDER
from src.email_renderer import render_digest_html, render_digest_text
from src.email_sender import send_digest

_SUPPORTED_PROVIDERS = {
    "tavily": ("src.providers.tavily_search_provider", "Tavily Search"),
    "brave":  ("src.providers.brave_search_provider",  "Brave Search"),
}


def _load_provider():
    name = os.environ.get("SEARCH_PROVIDER", "tavily").strip().lower()
    if name not in _SUPPORTED_PROVIDERS:
        print(
            f"[Search] Unknown SEARCH_PROVIDER={name!r}. "
            f"Supported: {', '.join(_SUPPORTED_PROVIDERS)}."
        )
        sys.exit(1)
    module_path, label = _SUPPORTED_PROVIDERS[name]
    import importlib
    module = importlib.import_module(module_path)
    return module, label


def load_profile(profile_path):
    with open(profile_path) as f:
        return yaml.safe_load(f)


def print_summary(posts_with_replies, posts_schedule, filepath, provider_label):
    print("\n" + "=" * 60)
    print(f"  SIGNAL SHIFT — {provider_label.upper()} DIGEST (Mel)")
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
    provider, provider_label = _load_provider()

    profile_path = os.path.join("profiles", "signal_shift.yaml")
    profile = load_profile(profile_path)

    print(f"[Search] Provider: {provider_label}")
    print(f"[Search] Product: {profile['name']}")
    print("[Search] SAFETY: read-only. Nothing will be posted, liked, or followed.")
    print("[Search] Note: engagement metrics unavailable. Verify manually before replying.")
    print()

    try:
        posts = provider.get_posts(profile)
    except EnvironmentError as exc:
        print(f"\n{exc}\n")
        return

    if not posts:
        print(
            "[Search] No X posts found. Try adjusting search_terms in "
            "profiles/signal_shift.yaml, or check that your API key is valid."
        )
        return

    posting_history = provider.get_posting_history(profile)

    scored = score_posts(posts, profile=profile)
    with_replies = generate_replies(scored)
    posts_schedule = generate_posts(date.today().weekday(), posting_history=posting_history)

    filepath = save_digest(profile["name"], with_replies, posts_schedule, mode=provider_label)
    print_summary(with_replies, posts_schedule, filepath, provider_label)

    today = date.today().isoformat()
    subject = f"Mel's Daily Marketing Digest — {today} ({provider_label})"
    html_body = render_digest_html(profile["name"], with_replies, posts_schedule, mode=provider_label)
    text_body = render_digest_text(profile["name"], with_replies, posts_schedule, mode=provider_label)

    send_email = os.getenv("SEND_EMAIL", "false").strip().lower() == "true"
    if not send_email:
        print("\n--- Email plain-text preview ---")
        print(text_body)
        print("--- End preview ---\n")

    send_digest(subject, html_body, text_body)


if __name__ == "__main__":
    main()
