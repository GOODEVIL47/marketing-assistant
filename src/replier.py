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
        "options_c": [
            {
                "style": "A — Question",
                "text": (
                    "What's one thing from the past week that actually changed your thesis? "
                    "Not what got louder — what genuinely changed."
                ),
            },
            {
                "style": "B — Agreement + reframe",
                "text": (
                    "That exact feeling is the signal. "
                    "The moment financial media becomes exhausting, it's usually doing exactly "
                    "what it's designed to do — keeping your attention, not informing you."
                ),
            },
            {
                "style": "C — Key point",
                "text": (
                    "The key distinction isn't more vs. less information. "
                    "It's useful vs. feels urgent. "
                    "Most of the noise falls in the second category."
                ),
            },
        ],
        "best_option_index_c": 2,
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
        "options_c": [
            {
                "style": "A — Question",
                "text": (
                    "What would actually change your mind on this? "
                    "Not make you doubt it — actually change it?"
                ),
            },
            {
                "style": "B — Agreement + reframe",
                "text": (
                    "Totally. And what makes it hard is that the feeling of having thought "
                    "something through carefully is almost indistinguishable from the feeling "
                    "of having rationalized it."
                ),
            },
            {
                "style": "C — Key point",
                "text": (
                    "The meta-skill is noticing when your analysis has stopped looking for "
                    "disconfirming evidence. That's usually when the conviction has outrun the evidence."
                ),
            },
        ],
        "best_option_index_c": 2,
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
        "options_c": [
            {
                "style": "A — Question",
                "text": (
                    "If you had to name one thing you're actually trying to answer — "
                    "not gather more about, but actually answer — what would it be?"
                ),
            },
            {
                "style": "B — Agreement + reframe",
                "text": (
                    "That clarity usually has to precede the research, not emerge from it. "
                    "Otherwise you're just reading until something feels right."
                ),
            },
            {
                "style": "C — Key point",
                "text": (
                    "Best framing test: if something changed the picture completely, would you know it? "
                    "If not, the signal probably isn't specific enough yet."
                ),
            },
        ],
        "best_option_index_c": 1,
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
        "options_c": [
            {
                "style": "A — Question",
                "text": (
                    "What's the default action here — and would you make the same call "
                    "without the price move prompting it?"
                ),
            },
            {
                "style": "B — Agreement + reframe",
                "text": (
                    "Less reactive is the underrated edge. "
                    "Almost every financial incentive — media, platforms, commentary — "
                    "is pointing in the other direction."
                ),
            },
            {
                "style": "C — Key point",
                "text": (
                    "The market prices in action. It doesn't price in patience. "
                    "Which is part of why patience keeps being where the edge is."
                ),
            },
        ],
        "best_option_index_c": 1,
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
        "options_c": [
            {
                "style": "A — Question",
                "text": (
                    "What would you need to believe about this to make a real decision? "
                    "That question tends to cut through a lot faster than another data pull."
                ),
            },
            {
                "style": "B — Agreement + reframe",
                "text": (
                    "Right — and more data often makes it harder, not easier. "
                    "It gives you more things to rationalize with rather than more clarity."
                ),
            },
            {
                "style": "C — Key point",
                "text": (
                    "The gap is almost always at the level of the question, not the data. "
                    "A sharper question makes what you already have useful. "
                    "More data doesn't fix a blurry question."
                ),
            },
        ],
        "best_option_index_c": 2,
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
        "options_c": [
            {
                "style": "A — Question",
                "text": (
                    "What's the actual decision you're trying to make here — "
                    "and what would move the needle on it?"
                ),
            },
            {
                "style": "B — Agreement + reframe",
                "text": (
                    "The underappreciated part: how much of 'doing more research' is just "
                    "delaying a decision that probably doesn't require more information."
                ),
            },
            {
                "style": "C — Key point",
                "text": (
                    "This is the part that rarely gets enough airtime: what the process looks like "
                    "before you look at anything, not after."
                ),
            },
        ],
        "best_option_index_c": 0,
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
        "options_c": [
            {
                "style": "A — Question",
                "text": (
                    "What's the thing that would make this clearer — "
                    "more information, or a sharper question to start from?"
                ),
            },
            {
                "style": "B — Agreement + reframe",
                "text": (
                    "Worth naming — there's a version of gathering more data that is just "
                    "a more sophisticated form of procrastination. "
                    "Doesn't make it wrong, but it's worth knowing which one you're doing."
                ),
            },
            {
                "style": "C — Key point",
                "text": (
                    "The framing matters at least as much as the content. "
                    "What you're looking for shapes what you find."
                ),
            },
        ],
        "best_option_index_c": 2,
        "media": {
            "type": "No media",
            "reason": "Generic fallback reply works better as clean text.",
        },
    },
}

# ---------------------------------------------------------------------------
# Inspiration angles — used for "old" web-search posts in Save for Inspiration.
# Framed as original post ideas, not reply options.
# ---------------------------------------------------------------------------
_INSPIRATION_ANGLES = {
    "noise_overwhelm": [
        "Market noise feels useful because it's urgent. But urgency and usefulness are not the same thing. Worth separating them.",
        "There's a version of research that is just looking for permission to act. Worth checking which one you're doing.",
    ],
    "bias_emotional": [
        "Conviction and clarity feel identical from the inside. That's the problem — and why process matters more than the conclusion you've already reached.",
        "A calm investing process starts by separating what genuinely changed from what merely got louder. They feel the same in the moment.",
    ],
    "clarity_signal": [
        "The question matters more than the data. A sharp question makes what you already have useful. More data doesn't fix a blurry question.",
        "Most research is just reading until a position feels defensible — which isn't the same as understanding it.",
    ],
    "reactive_slow_down": [
        "Less reactive is the underrated edge. Almost every financial incentive — media, platforms, commentary — points in the other direction.",
        "The market prices in action. It doesn't price in patience. Which is part of why patience keeps being where the edge is.",
    ],
    "data_vs_insight": [
        "Information and understanding are not the same thing. Most tools are built for the first. Almost nothing is built for the second.",
        "More data often makes decisions harder, not easier — it gives you more things to rationalize with rather than more clarity.",
    ],
    "generic_strong": [
        "The real work happens before you look at any data — getting clear on what you're trying to answer and what would actually change your mind.",
        "Most serious investors talk about process more than outcomes. That probably isn't a coincidence.",
    ],
    "generic_decent": [
        "The framing matters as much as the information. The question you start with shapes everything you find.",
        "Good questions tend to surface faster than good answers. Making the question sharper is usually the best next move.",
    ],
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
    Select A/B/C options from one of three named variant sets, chosen by
    tweet_id % 3. Posts with different IDs and the same theme get different
    wording. Output is deterministic: same ID always yields the same set.
    Mock posts are never routed here.
    """
    try:
        idx = int(tweet_id) % 3
    except (ValueError, TypeError):
        idx = 0

    sets = [
        ("options",   "best_option_index"),
        ("options_b", "best_option_index_b"),
        ("options_c", "best_option_index_c"),
    ]
    opt_key, best_key = sets[idx]
    options = template.get(opt_key) or template["options"]
    best_idx = template.get(best_key, template.get("best_option_index", 0))
    return options, best_idx


def _get_inspiration_angles(post):
    """Return up to 2 original-post inspiration angles keyed by the post's theme."""
    theme = _detect_reply_theme(post)
    if theme is None:
        theme = "generic_strong" if post.get("score") == "Strong fit" else "generic_decent"
    return _INSPIRATION_ANGLES.get(theme, _INSPIRATION_ANGLES["generic_strong"])[:2]


def _detect_reply_theme(post):
    text = post.get("text", "").lower()
    for theme, keywords in _THEME_KEYWORDS:
        if any(kw in text for kw in keywords):
            return theme
    return None


def generate_replies(scored_posts):
    results = []
    for post in scored_posts:
        post_id = post["id"]
        fit_score = post["score"]
        is_web_search = post.get("metrics_confidence") == "low"
        freshness_tier = post.get("freshness_tier")
        opportunity = post.get("opportunity", "")

        # Web-search posts that are stale or Poor opportunity:
        # show a clear "do not reply" note, no reply options, no inspiration angles.
        if is_web_search and (
            freshness_tier in ("stale", "very_stale")
            or opportunity == "Poor opportunity"
        ):
            results.append({
                **post,
                "replies": [],
                "media": None,
                "best_reply": None,
                "reply_note": "No reply suggested — stale post. Use as inspiration only.",
                "inspiration_angles": None,
            })
            continue

        # Web-search posts that are "old" (48h–7d) with good fit:
        # show inspiration angles instead of reply options.
        if is_web_search and freshness_tier == "old" and fit_score in ("Strong fit", "Decent fit"):
            results.append({
                **post,
                "replies": [],
                "media": None,
                "best_reply": None,
                "reply_note": None,
                "inspiration_angles": _get_inspiration_angles(post),
            })
            continue

        # Fresh/borderline web posts and all mock/real-X posts with good fit:
        # normal reply generation.
        if fit_score in ("Strong fit", "Decent fit"):
            if isinstance(post_id, int):
                # Mock post — use hardcoded replies (IDs 1–8); never change this path.
                post_data = REPLIES.get(post_id, {})
                options = post_data.get("options", [])
                media = post_data.get("media", {"type": "No media", "reason": "No media suggested."})
                best_idx = post_data.get("best_option_index", 0)
                best_reply = options[best_idx] if options else None
            else:
                # Real X post — detect theme, pick variant by tweet ID.
                theme = _detect_reply_theme(post)
                if theme is None:
                    theme = "generic_strong" if fit_score == "Strong fit" else "generic_decent"
                template = _DYNAMIC_TEMPLATES[theme]
                options, best_idx = _pick_reply_options(post_id, template)
                media = template["media"]
                best_reply = options[best_idx]
            results.append({
                **post,
                "replies": options,
                "media": media,
                "best_reply": best_reply,
                "reply_note": None,
                "inspiration_angles": None,
            })
        else:
            results.append({
                **post,
                "replies": [],
                "media": None,
                "best_reply": None,
                "reply_note": None,
                "inspiration_angles": None,
            })
    return results
