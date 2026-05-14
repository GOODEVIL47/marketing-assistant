FOUNDER_POST = {
    "account": "Founder",
    "text": (
        "The retail investor problem isn't a lack of information. "
        "It's that all the information arrives at the same volume, with the same urgency, "
        "and none of it tells you what actually changed about your thesis. "
        "That gap between data and clarity is what I've been thinking about for a while now."
    ),
}

PRODUCT_POST = {
    "account": "@SignalShiftCo",
    "text": (
        "Before you act on a hot ticker, Signal Shift gives you a plain-English brief: "
        "what the bias looks like, where the real risk is, what would need to be true for this to work, "
        "and what would invalidate it. "
        "Not a signal. Not a trade. Just clarity before you decide."
    ),
}


def generate_posts():
    return FOUNDER_POST, PRODUCT_POST
