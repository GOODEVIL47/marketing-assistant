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


def _compute_visibility(post):
    age = post.get("age_hours", 9999)
    likes = post.get("likes", 0)
    reply_count = post.get("reply_count", 0)

    if age <= 24 and (likes >= 50 or reply_count >= 15):
        return "Strong visibility"
    if age <= 72 and (likes >= 20 or reply_count >= 5):
        return "Decent visibility"
    return "Low visibility"


def _score_opportunity(post, fit_score, visibility):
    age = post.get("age_hours", 9999)
    likes = post.get("likes", 0)
    reply_count = post.get("reply_count", 0)

    # Avoid: always Poor regardless of reach
    if fit_score == "Avoid":
        return (
            "Poor opportunity",
            "Content type is on the avoid list — no engagement regardless of timing or reach.",
        )

    # Weak fit: call out the visibility vs strategic opportunity gap explicitly
    if fit_score == "Weak fit":
        if visibility == "Strong visibility":
            return (
                "Low opportunity",
                f"Visibility is strong — {likes:,} likes, {reply_count} replies, {int(age)}h old. "
                "But the fit is poor — the audience here is misaligned with Signal Shift. "
                "High reach doesn't translate to a useful reply opportunity when the fit isn't there.",
            )
        if visibility == "Decent visibility":
            return (
                "Poor opportunity",
                f"Fit is weak and visibility is moderate ({likes:,} likes, {int(age)}h old). "
                "Not worth the brand exposure here.",
            )
        return (
            "Poor opportunity",
            "Weak fit and minimal visibility. Nothing to gain from engaging.",
        )

    # Strong or Decent fit — evaluate on timing and engagement
    if age > 8760:
        return "Poor opportunity", "Post is over a year old — the reply window is long gone."

    dead = likes < 10 and reply_count < 3
    if dead:
        return (
            "Poor opportunity",
            "Post has minimal engagement — a reply would get no visibility.",
        )

    crowded = reply_count >= 500

    if visibility == "Strong visibility":
        if crowded:
            return (
                "Medium opportunity",
                f"Good fit but the thread is crowded — {reply_count} replies means your reply may get buried. "
                "Worth doing only if the take is sharp and specific enough to stand out.",
            )
        if age <= 8:
            return (
                "High opportunity",
                f"Strong fit and prime timing — {int(age)}h old, {likes:,} likes, {reply_count} replies. "
                "Reply window is wide open.",
            )
        return (
            "High opportunity",
            f"Strong fit with good timing — {int(age)}h old, {likes:,} likes, {reply_count} replies. "
            "Still well within the reply window.",
        )

    if visibility == "Decent visibility":
        if age > 48:
            days = int(age) // 24
            return (
                "Low opportunity",
                f"Post is {days}d old — the reply window is closing. "
                "Good content but timing has passed. Save the thought for a future original post.",
            )
        if fit_score == "Strong fit":
            return (
                "Medium opportunity",
                f"Strong fit but engagement is moderate — {int(age)}h old, {likes:,} likes, {reply_count} replies. "
                "Still worth a reply if you have something real to add.",
            )
        return (
            "Medium opportunity",
            f"Decent fit and moderate visibility — {int(age)}h old, {likes:,} likes, {reply_count} replies. "
            "Light engagement but recent enough to get eyes on it.",
        )

    # Low visibility
    if age > 48:
        days = int(age) // 24
        return (
            "Low opportunity",
            f"Post is {days}d old with minimal recent activity. "
            "Reply would get very little visibility at this point.",
        )
    return (
        "Low opportunity",
        f"Light engagement — {likes:,} likes, {reply_count} replies. "
        "A reply might not get much visibility even with a strong take.",
    )


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
        visibility = _compute_visibility(post)
        opportunity, opp_reason = _score_opportunity(post, fit_score, visibility)
        action = _suggested_action(fit_score, opportunity, post.get("reply_count", 0))
        eng_summary = _engagement_summary(post)

        results.append({
            **post,
            **fit_data,
            "visibility": visibility,
            "opportunity": opportunity,
            "opportunity_reason": opp_reason,
            "engagement_summary": eng_summary,
            "suggested_action": action,
        })
    return results
