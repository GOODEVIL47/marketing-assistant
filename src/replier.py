REPLIES = {
    1: {
        "options": [
            {
                "style": "A — Short and clean",
                "text": (
                    "Earnings week is just the financial media's quarterly excuse to max out the volume. "
                    "Most of it won't change your actual thesis."
                ),
            },
            {
                "style": "B — Casual paragraph",
                "text": (
                    "It's not even the numbers that are tiring. "
                    "It's the 48 hours of takes that follow — most of which are just reactions to other reactions. "
                    "Hard to find what actually changed in all that."
                ),
            },
            {
                "style": "C — Sharper take",
                "text": (
                    "Hot take: most earnings 'surprises' aren't surprising if you'd already mapped out "
                    "the range of outcomes beforehand. "
                    "The surprise is usually that people hadn't done that part."
                ),
            },
        ],
        "media": {
            "type": "Optional GIF",
            "reason": (
                "The post is relatable and a little exasperated — earnings week stress is universally felt. "
                "An 'overwhelmed' GIF could work here, but text alone is fine. Skip if unsure."
            ),
        },
        "best_option_index": 1,
    },
    2: {
        "options": [
            {
                "style": "A — One-liner",
                "text": "By the time you see it clearly, you've usually already acted on it.",
            },
            {
                "style": "B — Casual paragraph",
                "text": (
                    "The tricky part is that bias doesn't feel like bias. It feels like conviction. "
                    "Same internal sensation, completely different reliability."
                ),
            },
            {
                "style": "C — Sharper take",
                "text": (
                    "You can usually tell it's kicked in when your reasoning starts sounding like a closing argument — "
                    "dismissing everything that disagrees, explaining away the bad signals. "
                    "That's the moment to pause, not push harder."
                ),
            },
        ],
        "media": {
            "type": "Quote repost",
            "reason": (
                "The original post is strong enough to anchor a bigger founder take. "
                "A quote repost with reply C lets the original do the setup while the reply adds real weight."
            ),
        },
        "best_option_index": 2,
    },
    3: {
        "options": [
            {
                "style": "A — One-liner",
                "text": "More dashboards, same fog.",
            },
            {
                "style": "B — Casual paragraph",
                "text": (
                    "Most platforms solve 'here's more information' when the actual problem is "
                    "'I don't know what to do with what I already have.' Not the same problem."
                ),
            },
            {
                "style": "C — Sharper take",
                "text": (
                    "The thing most investing tools optimize for is comprehensiveness. Not usefulness. "
                    "Those aren't the same thing, and the gap between them is where most people get stuck."
                ),
            },
        ],
        "media": {
            "type": "No media",
            "reason": (
                "The topic is conceptual and the one-liner is punchy on its own. "
                "Adding media here would dilute it rather than help."
            ),
        },
        "best_option_index": 0,
    },
    4: {
        "options": [
            {
                "style": "A — One-liner",
                "text": "Less reactive is underrated.",
            },
            {
                "style": "B — Casual paragraph",
                "text": (
                    "Probably not a coincidence. Most financial media is built to make you feel like "
                    "something is happening right now that needs your attention. "
                    "That pressure is kind of the product."
                ),
            },
            {
                "style": "C — Sharper take",
                "text": (
                    "Financial media isn't designed to help you think clearly. "
                    "It's designed to keep you engaged. "
                    "Those two goals are almost perfectly opposed."
                ),
            },
        ],
        "media": {
            "type": "Optional GIF",
            "reason": (
                "The 'finally turned off the TV' energy is casual and relatable. "
                "A GIF could work, but this post is 2+ days old — probably not worth it at this stage."
            ),
        },
        "best_option_index": 1,
    },
}


def generate_replies(scored_posts):
    results = []
    for post in scored_posts:
        if post["score"] in ("Strong fit", "Decent fit"):
            post_data = REPLIES.get(post["id"], {})
            options = post_data.get("options", [])
            media = post_data.get("media", {"type": "No media", "reason": "No media suggested."})
            best_idx = post_data.get("best_option_index", 0)
            best_reply = options[best_idx] if options else None
            results.append({**post, "replies": options, "media": media, "best_reply": best_reply})
        else:
            results.append({**post, "replies": [], "media": None, "best_reply": None})
    return results
