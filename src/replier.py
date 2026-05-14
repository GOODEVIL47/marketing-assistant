REPLIES = {
    1: [
        {
            "style": "A — Short and clean",
            "text": (
                "Earnings week turns up the volume on everything. "
                "The move that helps most: get a clear plain-English summary of what actually changed "
                "before the noise kicks in."
            ),
        },
        {
            "style": "B — Slightly more thoughtful",
            "text": (
                "This is a real thing. The problem isn't that earnings week is complicated — "
                "it's that the coverage optimizes for drama, not clarity. "
                "What helps is separating the actual catalyst from the reaction to the reaction. "
                "Most of the noise is commentary on commentary."
            ),
        },
        {
            "style": "C — Sharper / more opinionated",
            "text": (
                "The exhaustion usually isn't from the earnings themselves. "
                "It's from trying to process 40 takes from people with different time horizons and agendas "
                "as if they all apply to you. They don't. Filter by your actual thesis, not the ticker trending."
            ),
        },
    ],
    2: [
        {
            "style": "A — Short and clean",
            "text": (
                "Bias is the hardest thing to catch in real time. "
                "By the time you recognize it, you've usually already acted on it."
            ),
        },
        {
            "style": "B — Slightly more thoughtful",
            "text": (
                "Most investing mistakes aren't analytical errors — they're bias errors dressed up as analysis. "
                "The conviction felt earned, the reasoning felt solid, "
                "and neither one was actually the driver of the decision."
            ),
        },
        {
            "style": "C — Sharper / more opinionated",
            "text": (
                "The tell is usually when your thesis starts sounding like a closing argument. "
                "You stop weighing evidence and start explaining away anything that disagrees. "
                "That shift is worth noticing — it usually precedes a bad entry."
            ),
        },
    ],
    3: [
        {
            "style": "A — Short and clean",
            "text": (
                "Agreed. More data without a clearer way to reason about it "
                "just produces faster, more confident bad decisions."
            ),
        },
        {
            "style": "B — Slightly more thoughtful",
            "text": (
                "The dashboard problem is real. Most retail investors aren't missing information — "
                "they're missing a way to hold it together into an actual view. "
                "A framework helps you know what matters, not just what exists."
            ),
        },
        {
            "style": "C — Sharper / more opinionated",
            "text": (
                "Data without structure is just noise with a chart on top of it. "
                "The question most tools don't answer is: what does this change about my current view? "
                "That's the framework gap — and it's a big one."
            ),
        },
    ],
    4: [
        {
            "style": "A — Short and clean",
            "text": (
                "Calmer usually is better, even if it doesn't feel like it. "
                "Most market news is designed to create urgency, not clarity."
            ),
        },
        {
            "style": "B — Slightly more thoughtful",
            "text": (
                "Less reactive isn't just a mindset shift — it's a genuine edge for retail investors. "
                "Most of the people trading against you are reacting too. "
                "Slowing down is an underrated strategy."
            ),
        },
        {
            "style": "C — Sharper / more opinionated",
            "text": (
                "Financial news is optimized for engagement, not for helping you make a good decision. "
                "Those two things are almost completely at odds. "
                "Your investing getting calmer after cutting the feed is not a coincidence."
            ),
        },
    ],
}


def generate_replies(scored_posts):
    results = []
    for post in scored_posts:
        if post["score"] in ("Strong fit", "Decent fit"):
            post_replies = REPLIES.get(post["id"], [])
            results.append({**post, "replies": post_replies})
        else:
            results.append({**post, "replies": []})
    return results
