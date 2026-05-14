from datetime import date

_DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
_FOUNDER_DAYS = {0, 2, 4}  # Mon, Wed, Fri
_PRODUCT_DAYS = {1, 3}     # Tue, Thu

# Mock posting history — replace with real tracking in live mode
MOCK_POSTING_HISTORY = {
    "founder": {
        "last_posted_hours_ago": 48,
        "last_post_note": "2 days ago",
    },
    "product": {
        "last_posted_hours_ago": 3,
        "last_post_note": "earlier today (~3h ago)",
    },
}

# Scheduled post content

FOUNDER_POST = {
    "text": (
        "Most people don't need a smarter stock screen. "
        "They need a way to check whether they're thinking clearly before they act. "
        "Those are different problems — and almost nothing is built for the second one."
    ),
    "format": {
        "type": "Short paragraph",
        "reason": "Reads like a real observation, not a pitch. Three sentences that build without needing a list or a hook.",
    },
    "media": {
        "type": "No media",
        "reason": "A standalone thought like this lands better on its own. An image risks making it feel like a campaign.",
    },
}

FOUNDER_IDEA = {
    "note": "Optional idea — save for next scheduled post day",
    "text": (
        "There's a version of 'doing your research' that's just reading more takes "
        "until you feel confident enough to act. "
        "That's not research. That's permission-seeking dressed up as due diligence."
    ),
    "format": {
        "type": "2-3 line structure",
        "reason": "Two lines, the second reframes the first. Standalone thought, no context needed.",
    },
    "media": {
        "type": "No media",
        "reason": "Let the words do the work.",
    },
}

PRODUCT_POST = {
    "text": (
        "Signal Shift doesn't tell you what to do.\n\n"
        "It gives you a plain-English breakdown of the thesis: where the bias is, "
        "what the real risk is, what would need to be true, what would break it.\n\n"
        "Before you decide anything."
    ),
    "format": {
        "type": "2-3 line structure",
        "reason": "Each block lands on its own on X. Lets the product explain itself without reading like a sales script.",
    },
    "media": {
        "type": "Simple branded image",
        "reason": "A clean visual gives this post feed presence without overselling.",
    },
}

PRODUCT_IDEA = {
    "note": "Optional idea — save for next scheduled post day",
    "text": (
        "What does Signal Shift actually do? "
        "It turns the noise around a stock into a plain-English brief: "
        "bias check, key risks, what would need to be true, what would break it. "
        "No signals. No picks. Just a clearer starting point."
    ),
    "format": {
        "type": "Short paragraph",
        "reason": "Explains the product simply in one breath. Easy to scan.",
    },
    "media": {
        "type": "No media",
        "reason": "Save media for posts with a stronger visual hook.",
    },
}


def _next_scheduled_day(weekday, scheduled_days):
    for i in range(1, 8):
        if (weekday + i) % 7 in scheduled_days:
            return _DAY_NAMES[(weekday + i) % 7]
    return "Unknown"


def generate_posts(weekday=None, posting_history=None):
    if weekday is None:
        weekday = date.today().weekday()
    if posting_history is None:
        posting_history = MOCK_POSTING_HISTORY

    day_name = _DAY_NAMES[weekday]
    founder_scheduled = weekday in _FOUNDER_DAYS
    product_scheduled = weekday in _PRODUCT_DAYS

    founder_hist = posting_history.get("founder", {})
    product_hist = posting_history.get("product", {})
    founder_last_h = founder_hist.get("last_posted_hours_ago", 999)
    product_last_h = product_hist.get("last_posted_hours_ago", 999)
    founder_last_note = founder_hist.get("last_post_note", f"~{founder_last_h}h ago")
    product_last_note = product_hist.get("last_post_note", f"~{product_last_h}h ago")

    # Founder schedule
    if founder_last_h < 24:
        founder_needed = False
        founder_reason = (
            f"Already posted {founder_last_note} — no post needed today."
        )
    elif founder_scheduled:
        founder_needed = True
        founder_reason = (
            f"Scheduled Mon / Wed / Fri — today ({day_name}) is a post day. "
            f"Last posted {founder_last_note}."
        )
    else:
        next_day = _next_scheduled_day(weekday, _FOUNDER_DAYS)
        founder_needed = False
        founder_reason = (
            f"Not a scheduled day (Mon / Wed / Fri). Today is {day_name}. "
            f"Last posted {founder_last_note}. Next scheduled: {next_day}."
        )

    # Product schedule
    if product_last_h < 24:
        product_needed = False
        product_reason = (
            f"@SignalShiftCo already posted {product_last_note} — "
            f"skip today even though {day_name} is a scheduled day."
        )
    elif product_scheduled:
        product_needed = True
        product_reason = (
            f"Scheduled Tue / Thu — today ({day_name}) is a post day. "
            f"Last posted {product_last_note}."
        )
    else:
        next_day = _next_scheduled_day(weekday, _PRODUCT_DAYS)
        product_needed = False
        product_reason = (
            f"Not a scheduled day (Tue / Thu). Today is {day_name}. "
            f"Last posted {product_last_note}. Next scheduled: {next_day}."
        )

    return {
        "founder": {
            "needed": founder_needed,
            "handle": "Founder",
            "reason": founder_reason,
            "post": FOUNDER_POST if founder_needed else None,
            "optional_idea": FOUNDER_IDEA if not founder_needed else None,
        },
        "product": {
            "needed": product_needed,
            "handle": "@SignalShiftCo",
            "reason": product_reason,
            "post": PRODUCT_POST if product_needed else None,
            "optional_idea": PRODUCT_IDEA if not product_needed else None,
        },
    }
