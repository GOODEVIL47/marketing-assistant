FOUNDER_POST = {
    "account": "Founder",
    "text": (
        "Most people don't need a smarter stock screen. "
        "They need a way to check whether they're thinking clearly before they act. "
        "Those are different problems — and almost nothing is built for the second one."
    ),
    "format": {
        "type": "Short paragraph",
        "reason": (
            "Reads like a real observation, not a pitch. "
            "Three sentences that build on each other without needing a list or a hook."
        ),
    },
    "media": {
        "type": "No media",
        "reason": (
            "A standalone thought like this lands better on its own. "
            "Adding an image risks making it feel like a campaign instead of a genuine take."
        ),
    },
}

PRODUCT_POST = {
    "account": "@SignalShiftCo",
    "text": (
        "Signal Shift doesn't tell you what to do.\n\n"
        "It gives you a plain-English breakdown of the thesis: where the bias is, "
        "what the real risk is, what would need to be true, what would break it.\n\n"
        "Before you decide anything."
    ),
    "format": {
        "type": "2-3 line structure",
        "reason": (
            "Each block lands on its own on X. "
            "The structure lets the product explain itself without reading like a sales script."
        ),
    },
    "media": {
        "type": "Simple branded image",
        "reason": (
            "A clean visual gives this post presence in the feed. "
            "Works well for product posts that need a little visual weight without overselling."
        ),
    },
}


def generate_posts():
    return FOUNDER_POST, PRODUCT_POST
