FIT_SCORES = {
    1: {
        "score": "Strong fit",
        "reason": (
            "This post captures exactly the overwhelmed retail investor Signal Shift is built for. "
            "The author isn't chasing alpha — they want to understand what's happening. "
            "'Just want to understand what's actually happening without the noise' is essentially "
            "the product's value prop in the user's own words. High relevance, low risk."
        ),
        "reply_account": "Founder",
    },
    2: {
        "score": "Strong fit",
        "reason": (
            "Bias recognition is a core part of what Signal Shift surfaces in every brief. "
            "This post hits the exact tension the product addresses: having an idea "
            "but not knowing whether your own head is getting in the way. "
            "Thoughtful audience, good opportunity to add real perspective."
        ),
        "reply_account": "Either",
    },
    3: {
        "score": "Decent fit",
        "reason": (
            "The 'more data isn't the answer' angle aligns with Signal Shift's positioning. "
            "But the post is broad — it's not specifically about emotional investing or acting on noise. "
            "There's a real opening here, though a reply needs to add something rather than just agree."
        ),
        "reply_account": "Founder",
    },
    4: {
        "score": "Decent fit",
        "reason": (
            "Reducing reactive behavior is adjacent to what Signal Shift helps with. "
            "The author is describing a behavioral shift without having a clear tool behind it. "
            "A founder reply that acknowledges the insight without pushing the product feels natural here."
        ),
        "reply_account": "Either",
    },
    5: {
        "score": "Weak fit",
        "reason": (
            "Technical analysis setups are outside Signal Shift's lane. The audience here is likely "
            "active traders optimizing entry/exit timing — not someone trying to slow down and think clearly. "
            "Replying risks misaligning the brand with trading-tool culture."
        ),
        "reply_account": "Do not reply",
    },
    6: {
        "score": "Weak fit",
        "reason": (
            "Stock pick content with hype framing. The audience may overlap with retail investors "
            "but the energy is the opposite of Signal Shift's voice. "
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
            "This is exactly the kind of post Signal Shift helps people step back from. "
            "No reply, no engagement — this post is the problem, not an opportunity."
        ),
        "reply_account": "Do not reply",
    },
}


def _engagement_summary(post):
    age = post.get("age_hours", 0)
    if age < 1:
        age_str = "< 1h old"
    elif age < 24:
        age_str = f"{int(age)}h old"
    else:
        days = int(age) // 24
        rem = int(age) % 24
        age_str = f"{days}d {rem}h old" if rem else f"{days}d old"

    likes = post.get("likes", 0)
    reply_count = post.get("reply_count", 0)
    reposts = post.get("reposts", 0)
    return f"{likes:,} likes · {reply_count} replies · {reposts} reposts · {age_str}"


def _score_opportunity(post, fit_score):
    if fit_score == "Avoid":
        return (
            "Poor opportunity",
            "Content type is on the avoid list — no engagement regardless of timing.",
        )

    age = post.get("age_hours", 9999)
    likes = post.get("likes", 0)
    reply_count = post.get("reply_count", 0)

    if age > 8760:
        return "Poor opportunity", "Post is over a year old — the window is long gone."

    # Age points
    if 1 <= age <= 8:
        age_pts = 3
        age_note = f"{int(age)}h old — prime reply window"
    elif age <= 24:
        age_pts = 2
        age_note = f"{int(age)}h old — still a good window"
    elif age <= 48:
        age_pts = 1
        age_note = f"{int(age)}h old — getting stale"
    else:
        days = int(age) // 24
        age_pts = 0
        age_note = f"{days}d old — window has closed"

    # Engagement points
    dead = likes < 10 and reply_count < 3
    crowded = reply_count >= 500

    if dead:
        eng_pts = 0
        eng_note = "minimal engagement — reply would get no visibility"
    elif crowded:
        eng_pts = 1
        eng_note = f"{likes:,} likes · {reply_count} replies — crowded thread, high competition"
    elif 10 <= reply_count <= 150 and 50 <= likes <= 2000:
        eng_pts = 3
        eng_note = f"{likes:,} likes · {reply_count} replies — sweet spot engagement"
    elif likes >= 30 or reply_count >= 5:
        eng_pts = 2
        eng_note = f"{likes:,} likes · {reply_count} replies — decent engagement"
    else:
        eng_pts = 1
        eng_note = f"{likes:,} likes · {reply_count} replies — light but alive"

    total = age_pts + eng_pts

    # Weak fit caps at Low opportunity max
    if fit_score == "Weak fit":
        total = min(total, 2)

    reason = f"{age_note}. {eng_note}."

    if total >= 5:
        return "High opportunity", reason
    elif total >= 3:
        return "Medium opportunity", reason
    elif total >= 1:
        return "Low opportunity", reason
    else:
        return "Poor opportunity", reason


def _suggested_action(fit_score, opportunity, reply_count):
    if fit_score in ("Avoid", "Weak fit"):
        return "Do not engage"
    if opportunity in ("High opportunity", "Medium opportunity"):
        if reply_count >= 500:
            return "Reply (crowded — high competition)"
        return "Reply"
    if opportunity == "Low opportunity":
        return "Save for inspiration"
    return "Do not engage"


def score_posts(posts):
    results = []
    for post in posts:
        post_id = post["id"]
        fit_data = FIT_SCORES.get(post_id, {
            "score": "Weak fit",
            "reason": "No scoring data available for this post.",
            "reply_account": "Do not reply",
        })
        fit_score = fit_data["score"]
        opportunity, opp_reason = _score_opportunity(post, fit_score)
        action = _suggested_action(fit_score, opportunity, post.get("reply_count", 0))
        eng_summary = _engagement_summary(post)

        results.append({
            **post,
            **fit_data,
            "opportunity": opportunity,
            "opportunity_reason": opp_reason,
            "engagement_summary": eng_summary,
            "suggested_action": action,
        })
    return results
