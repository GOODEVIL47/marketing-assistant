from datetime import date

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

_FOUNDER_DAYS = {0, 2, 4}  # Mon, Wed, Fri
_PRODUCT_DAYS = {1, 3}     # Tue, Thu

_DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def generate_posts(weekday=None):
    if weekday is None:
        weekday = date.today().weekday()

    day_name = _DAY_NAMES[weekday]
    founder_needed = weekday in _FOUNDER_DAYS
    product_needed = weekday in _PRODUCT_DAYS

    return {
        "founder": {
            "needed": founder_needed,
            "handle": "Founder",
            "reason": (
                f"Scheduled Mon / Wed / Fri. Today is {day_name}."
                if not founder_needed
                else f"Scheduled Mon / Wed / Fri — today ({day_name}) is a post day."
            ),
            "post": FOUNDER_POST if founder_needed else None,
            "optional_idea": FOUNDER_IDEA if not founder_needed else None,
        },
        "product": {
            "needed": product_needed,
            "handle": "@SignalShiftCo",
            "reason": (
                f"Scheduled Tue / Thu. Today is {day_name}."
                if not product_needed
                else f"Scheduled Tue / Thu — today ({day_name}) is a post day."
            ),
            "post": PRODUCT_POST if product_needed else None,
            "optional_idea": PRODUCT_IDEA if not product_needed else None,
        },
    }
