SCORES = {
    1: {
        "score": "Strong fit",
        "reason": (
            "This post captures exactly the overwhelmed retail investor Signal Shift is built for. "
            "The author isn't chasing alpha — they want clarity. The phrase 'just want to understand "
            "what's actually happening without the noise' is essentially Signal Shift's value prop in "
            "the user's own words. High relevance, low risk."
        ),
        "reply_account": "Founder",
    },
    2: {
        "score": "Strong fit",
        "reason": (
            "Bias recognition is a core part of what Signal Shift surfaces in every brief. "
            "This post hits the exact tension the product addresses: the gap between having "
            "an idea and knowing whether your own head is getting in the way. "
            "Thoughtful audience, good opportunity to add perspective."
        ),
        "reply_account": "Either",
    },
    3: {
        "score": "Decent fit",
        "reason": (
            "The 'frameworks over more data' angle aligns well with Signal Shift's positioning. "
            "But the post is broad — it's not specifically about emotional investing or noise. "
            "There's a real opening here, though a reply needs to add something rather than just agree."
        ),
        "reply_account": "Founder",
    },
    4: {
        "score": "Decent fit",
        "reason": (
            "Reducing reactive behavior is adjacent to what Signal Shift helps with. "
            "The author is describing a behavioral shift without a clear tool behind it. "
            "A founder reply that acknowledges the insight without pushing the product feels natural here."
        ),
        "reply_account": "Either",
    },
    5: {
        "score": "Weak fit",
        "reason": (
            "Technical analysis setups are outside Signal Shift's lane. The audience here is likely "
            "active traders optimizing entry/exit timing — not the retail investor trying to slow down "
            "and think clearly. Replying risks misaligning the brand with trading-tool culture."
        ),
        "reply_account": "Do not reply",
    },
    6: {
        "score": "Weak fit",
        "reason": (
            "Stock pick content with hype framing ('screenshot this, thank me later'). The audience "
            "may overlap with retail investors but the energy is the opposite of Signal Shift's voice. "
            "Any reply here would likely be ignored or attract the wrong crowd."
        ),
        "reply_account": "Do not reply",
    },
    7: {
        "score": "Avoid",
        "reason": (
            "Classic get-rich-quick webinar pitch. Associating Signal Shift with this type of content "
            "would damage brand credibility immediately. The voice, the claims, and the audience are "
            "incompatible with what Signal Shift stands for. Hard pass."
        ),
        "reply_account": "Do not reply",
    },
    8: {
        "score": "Avoid",
        "reason": (
            "Unusual options activity speculation with rocket emojis and vague insider framing. "
            "This is exactly the kind of noise Signal Shift is designed to help people step back from. "
            "No reply, no engagement — this post is the problem, not an opportunity."
        ),
        "reply_account": "Do not reply",
    },
}


def score_posts(posts):
    results = []
    for post in posts:
        post_id = post["id"]
        scoring = SCORES.get(post_id, {
            "score": "Weak fit",
            "reason": "No scoring data available for this post.",
            "reply_account": "Do not reply",
        })
        results.append({**post, **scoring})
    return results
