# Mock post replies — keyed by integer ID (1–8). Never change these.
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
            "idea": "overwhelmed trader / too many browser tabs / 'information overload' reaction",
            "use_if": "the reply feels casual or the original post has a self-aware, relatable tone",
            "skip_if": "the thread turns serious or the reply already lands cleanly as text",
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
            "use_if": "you want to turn this into a bigger founder take on how Signal Shift helps with this",
            "skip_if": "you only have 2 minutes and just want to leave a quick reply",
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
            "reason": "The reply is punchy enough on its own — adding media would dilute it rather than help.",
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
            "idea": "someone turning off a TV / 'finally' relief reaction / unplugging gif",
            "use_if": "you have time to make the reply feel warm and relatable",
            "skip_if": "the post is 2+ days old — probably not worth the extra effort at this stage",
        },
        "best_option_index": 1,
    },
}


# ---------------------------------------------------------------------------
# Dynamic reply templates — used for real X posts (string tweet IDs).
# Keyed by theme name. Theme is detected from post text; falls back to
# generic_strong / generic_decent based on fit score.
#
# Rules applied to every reply in this table:
#   - no financial advice, no buy/sell/hold language
#   - no hype, no "this stock will move"
#   - no forced Signal Shift mentions
#   - human, calm, founder-led voice
#   - no repetitive line-break formatting
# ---------------------------------------------------------------------------
_DYNAMIC_TEMPLATES = {
    "noise_overwhelm": {
        "options": [
            {
                "style": "A — Short and clean",
                "text": (
                    "Most of what hits your feed today won't matter by Friday. "
                    "The hard part is knowing which part."
                ),
            },
            {
                "style": "B — Casual paragraph",
                "text": (
                    "The noise isn't random — most of it is designed to feel urgent. "
                    "The actual signal is usually slower and quieter than any of it. "
                    "Hard to find when you're in the middle of it."
                ),
            },
            {
                "style": "C — Sharper take",
                "text": (
                    "Useful information rarely announces itself with a headline. "
                    "Most of what feels like signal in the moment is just well-packaged noise — "
                    "and the urgency is the packaging, not the content."
                ),
            },
        ],
        "best_option_index": 1,
        "options_b": [
            {
                "style": "A — Short and clean",
                "text": "The loudest signals in markets are usually the least useful ones.",
            },
            {
                "style": "B — Casual paragraph",
                "text": (
                    "Most of what trends on investing Twitter has a half-life of about 48 hours. "
                    "The information worth actually knowing rarely shows up as a headline."
                ),
            },
            {
                "style": "C — Sharper take",
                "text": (
                    "There's a real skill in knowing when more information is just noise "
                    "with better packaging. Hard to develop when you're inside the feed."
                ),
            },
        ],
        "best_option_index_b": 1,
        "media": {
            "type": "Optional GIF",
            "reason": (
                "Relatable overwhelm energy — a GIF can land if the original post "
                "has a self-aware, exasperated tone."
            ),
            "idea": "overwhelmed / too many browser tabs / information overload reaction",
            "use_if": "the reply feels casual and the original post has a relatable, exasperated tone",
            "skip_if": "the thread has turned serious or the reply already lands cleanly as text",
        },
    },
    "bias_emotional": {
        "options": [
            {
                "style": "A — Short and clean",
                "text": "Confidence and correctness feel identical from the inside.",
            },
            {
                "style": "B — Casual paragraph",
                "text": (
                    "The moment your reasoning sounds like a closing argument — "
                    "picking what fits, dismissing what doesn't — "
                    "that's usually the time to pause, not act. "
                    "Hard to catch in real time though."
                ),
            },
            {
                "style": "C — Sharper take",
                "text": (
                    "Bias doesn't announce itself. It shows up as certainty. "
                    "The useful question isn't 'do I have the data' — "
                    "it's 'what would actually change my mind here?'"
                ),
            },
        ],
        "best_option_index": 2,
        "options_b": [
            {
                "style": "A — Short and clean",
                "text": "Conviction and correctness feel identical from the inside.",
            },
            {
                "style": "B — Casual paragraph",
                "text": (
                    "One useful test: could you explain the bear case as convincingly as the bull case? "
                    "If not, the thesis probably has gaps you've been filling in emotionally."
                ),
            },
            {
                "style": "C — Sharper take",
                "text": (
                    "The gap between 'I've thought about this a lot' and 'I've thought about this clearly' "
                    "is bigger than it looks — and the first can feel exactly like the second."
                ),
            },
        ],
        "best_option_index_b": 2,
        "media": {
            "type": "Quote repost",
            "reason": (
                "The original post is strong enough to anchor a bigger founder take "
                "on decision-making and bias."
            ),
            "use_if": "you want to build on this into a larger thread or founder take",
            "skip_if": "you only have a minute and just want to leave a quick reply",
        },
    },
    "clarity_signal": {
        "options": [
            {
                "style": "A — Short and clean",
                "text": "A clear question beats more data almost every time.",
            },
            {
                "style": "B — Casual paragraph",
                "text": (
                    "'What would need to be true for this to work?' is more useful "
                    "than any amount of additional research. "
                    "It forces you to be specific about what you actually believe — "
                    "instead of just reading until you feel ready."
                ),
            },
            {
                "style": "C — Sharper take",
                "text": (
                    "Most analysis is just reading more takes until a position feels defensible. "
                    "That's not the same as understanding it. "
                    "The difference shows up when something unexpected happens."
                ),
            },
        ],
        "best_option_index": 1,
        "options_b": [
            {
                "style": "A — Short and clean",
                "text": "The right question matters more than the right answer.",
            },
            {
                "style": "B — Casual paragraph",
                "text": (
                    "Clarity usually comes from getting more specific about what you're actually "
                    "trying to figure out — not from reading more takes on it."
                ),
            },
            {
                "style": "C — Sharper take",
                "text": (
                    "Most serious investors spend more time defining the question than answering it. "
                    "Most people do it the other way around."
                ),
            },
        ],
        "best_option_index_b": 1,
        "media": {
            "type": "No media",
            "reason": "These replies land better as clean text — adding media would dilute the point.",
        },
    },
    "reactive_slow_down": {
        "options": [
            {
                "style": "A — Short and clean",
                "text": (
                    "Less reactive is almost always the better move. "
                    "Most platforms aren't built to help with that part."
                ),
            },
            {
                "style": "B — Casual paragraph",
                "text": (
                    "There's a difference between staying informed and constantly reacting "
                    "to what just happened. "
                    "Most financial media is optimized for the second one — "
                    "the engagement model depends on it."
                ),
            },
            {
                "style": "C — Sharper take",
                "text": (
                    "Reactivity isn't a character flaw — it's what most tools are designed to produce. "
                    "The goal of keeping you engaged and the goal of helping you make better decisions "
                    "point in almost opposite directions."
                ),
            },
        ],
        "best_option_index": 1,
        "options_b": [
            {
                "style": "A — Short and clean",
                "text": "The urge to react is not the same as the need to act.",
            },
            {
                "style": "B — Casual paragraph",
                "text": (
                    "Most of what financial media calls 'new information' is existing information "
                    "with fresh packaging and a tighter deadline on your attention."
                ),
            },
            {
                "style": "C — Sharper take",
                "text": (
                    "Keeping you engaged and helping you make better decisions are almost perfectly "
                    "opposing incentives for most financial platforms. "
                    "Worth knowing which one your feed is optimized for."
                ),
            },
        ],
        "best_option_index_b": 1,
        "media": {
            "type": "Optional GIF",
            "reason": (
                "Unplugging / relief energy can work if the original post "
                "has a casual, self-aware tone."
            ),
            "idea": "someone turning off a TV / unplugging / 'finally' relief reaction",
            "use_if": "the original post has a light, relatable tone",
            "skip_if": "the reply stands on its own or the thread has turned analytical",
        },
    },
    "data_vs_insight": {
        "options": [
            {
                "style": "A — One-liner",
                "text": "More data, same fog.",
            },
            {
                "style": "B — Casual paragraph",
                "text": (
                    "Most platforms solve 'here's more information' when the actual problem is "
                    "'I don't know what to do with what I already have.' "
                    "Those aren't the same problem — and almost nothing is built for the second one."
                ),
            },
            {
                "style": "C — Sharper take",
                "text": (
                    "Comprehensiveness and usefulness aren't the same thing. "
                    "Most tools optimize for the first because it's measurable. "
                    "The second one is harder to build, and a lot harder to market."
                ),
            },
        ],
        "best_option_index": 0,
        "options_b": [
            {
                "style": "A — One-liner",
                "text": "Information isn't understanding.",
            },
            {
                "style": "B — Casual paragraph",
                "text": (
                    "The bottleneck is almost never more data. "
                    "It's a cleaner framework for deciding what to do with the data you already have."
                ),
            },
            {
                "style": "C — Sharper take",
                "text": (
                    "Being well-informed and being clear are different things. "
                    "More of one doesn't automatically give you more of the other — "
                    "and most platforms are only built for the first."
                ),
            },
        ],
        "best_option_index_b": 0,
        "media": {
            "type": "No media",
            "reason": "Reply A is punchy enough on its own — adding media would dilute it.",
        },
    },
    "generic_strong": {
        "options": [
            {
                "style": "A — Short and clean",
                "text": "This is the part almost no tool is actually built for.",
            },
            {
                "style": "B — Casual paragraph",
                "text": (
                    "The hard part isn't finding more information. "
                    "It's having a clear enough frame to know what to do with what you already have — "
                    "before you act on any of it."
                ),
            },
            {
                "style": "C — Sharper take",
                "text": (
                    "Most of the real work happens before you look at any data — "
                    "knowing what you're trying to answer, and what would actually change your mind. "
                    "That part doesn't get talked about much."
                ),
            },
        ],
        "best_option_index": 1,
        "options_b": [
            {
                "style": "A — Short and clean",
                "text": "The hard part is rarely finding the information — it's knowing what to do with it.",
            },
            {
                "style": "B — Casual paragraph",
                "text": (
                    "Most serious investors spend more time on process than most people realize. "
                    "The research is usually the easier part."
                ),
            },
            {
                "style": "C — Sharper take",
                "text": (
                    "Getting clear on what you're actually trying to decide — before you start researching — "
                    "changes everything about which information ends up being useful."
                ),
            },
        ],
        "best_option_index_b": 2,
        "media": {
            "type": "No media",
            "reason": "Generic fallback reply works better as clean text.",
        },
    },
    "generic_decent": {
        "options": [
            {
                "style": "A — Short and clean",
                "text": "There's more to untangle here than it looks.",
            },
            {
                "style": "B — Casual paragraph",
                "text": (
                    "The framing matters as much as the information. "
                    "Most of the time, the question you're asking is already shaping "
                    "the answer you're going to find — and that part rarely gets examined."
                ),
            },
            {
                "style": "C — Sharper take",
                "text": (
                    "A clear process beats instinct almost every time — "
                    "not because instincts are always wrong, "
                    "but because a process gives you something to learn from when they are."
                ),
            },
        ],
        "best_option_index": 1,
        "options_b": [
            {
                "style": "A — Short and clean",
                "text": "The assumptions you start with shape everything you find.",
            },
            {
                "style": "B — Casual paragraph",
                "text": (
                    "Worth thinking about whether the difficulty here is finding the right information "
                    "or having a clear enough lens to know what to do with it."
                ),
            },
            {
                "style": "C — Sharper take",
                "text": (
                    "Good questions tend to surface faster than good answers. "
                    "Usually the best next move is making the question sharper."
                ),
            },
        ],
        "best_option_index_b": 0,
        "media": {
            "type": "No media",
            "reason": "Generic fallback reply works better as clean text.",
        },
    },
}

# Keyword lists for theme detection — order matters, checked top-to-bottom.
_THEME_KEYWORDS = [
    ("noise_overwhelm",   ["noise", "overwhelm", "too much", "exhausting", "overload", "firehose", "drowning"]),
    ("bias_emotional",    ["bias", "emotional", "conviction", "confirmation", "panic", "fear", "gut feeling", "irrational"]),
    ("reactive_slow_down",["reactive", "slow down", "impulsive", "panic sold", "chasing", "fomo", "jumped in"]),
    ("data_vs_insight",   ["dashboard", "more data", "more information", "another tool", "screener", "research rabbit"]),
    ("clarity_signal",    ["clarity", "signal", "clear", "thesis", "what would need", "understand"]),
]


def _pick_reply_options(tweet_id, template):
    """
    Select A/B/C options from a template, rotating between the primary set and
    the 'options_b' alternate set based on the tweet ID. Posts with different IDs
    that share the same theme get different wording. Mock posts are never routed here.
    """
    try:
        use_b = int(tweet_id) % 2 == 1
    except (ValueError, TypeError):
        use_b = False

    if use_b and "options_b" in template:
        return template["options_b"], template.get("best_option_index_b", 0)
    return template["options"], template.get("best_option_index", 0)


def _detect_reply_theme(post):
    text = post.get("text", "").lower()
    for theme, keywords in _THEME_KEYWORDS:
        if any(kw in text for kw in keywords):
            return theme
    return None


def generate_replies(scored_posts):
    results = []
    for post in scored_posts:
        if post["score"] in ("Strong fit", "Decent fit"):
            post_id = post["id"]
            if isinstance(post_id, int):
                # Mock post — use hardcoded replies (IDs 1–8); never change this path.
                post_data = REPLIES.get(post_id, {})
                options = post_data.get("options", [])
                media = post_data.get("media", {"type": "No media", "reason": "No media suggested."})
                best_idx = post_data.get("best_option_index", 0)
                best_reply = options[best_idx] if options else None
            else:
                # Real X post — detect theme from post text, fall back to generic.
                theme = _detect_reply_theme(post)
                if theme is None:
                    theme = "generic_strong" if post["score"] == "Strong fit" else "generic_decent"
                template = _DYNAMIC_TEMPLATES[theme]
                options, best_idx = _pick_reply_options(post_id, template)
                media = template["media"]
                best_reply = options[best_idx]
            results.append({**post, "replies": options, "media": media, "best_reply": best_reply})
        else:
            results.append({**post, "replies": [], "media": None, "best_reply": None})
    return results
