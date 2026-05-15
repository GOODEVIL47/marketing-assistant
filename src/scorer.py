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


def _freshness_tier(age_hours):
    """Classify post age into a freshness tier for opportunity gating."""
    if age_hours is None:
        return "unknown"
    if age_hours <= 24:
        return "fresh"
    if age_hours <= 48:
        return "borderline"
    if age_hours <= 168:   # 7 days
        return "old"
    if age_hours <= 720:   # 30 days
        return "stale"
    return "very_stale"


def _age_label(post):
    """Human-readable age label for display in digest and email."""
    age = post.get("age_hours")
    source = post.get("age_source", "")

    if age is None:
        return "Age: unknown"

    if age < 24:
        label = f"Age: {int(age)}h old"
    elif age < 48:
        label = f"Age: {age / 24:.1f}d old — older but possibly usable"
    elif age < 168:
        label = f"Age: {int(age // 24)}d old — save for inspiration"
    elif age < 720:
        label = f"Age: {int(age // 24)}d old — stale, do not reply"
    else:
        label = f"Age: {int(age // 24)}d old — stale"

    if source == "snowflake":
        label += " (estimated from X status ID)"
    return label


def _engagement_summary(post):
    if post.get("metrics_confidence") == "low":
        age = post.get("age_hours")
        if age is None:
            age_str = "age unknown"
        elif age < 1:
            age_str = "< 1h old"
        elif age < 24:
            age_str = f"~{int(age)}h old"
        else:
            days = int(age) // 24
            rem = int(age) % 24
            age_str = f"~{days}d {rem}h old" if rem else f"~{days}d old"
        return f"Engagement unknown · found via web search · {age_str}"

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
    if post.get("metrics_confidence") == "low":
        return "Unknown visibility"

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

    # Unknown visibility (web search discovery — engagement metrics unavailable).
    # Only reached for Strong or Decent fit (Avoid and Weak fit already returned above).
    # Apply freshness gate: old/stale posts cap at Low/Poor regardless of fit.
    if visibility == "Unknown visibility":
        tier = _freshness_tier(age)
        if tier in ("stale", "very_stale"):
            days = int(age // 24)
            return (
                "Poor opportunity",
                f"Post is {days}d old — too stale to reply to. "
                "Save as inspiration for original content if the topic resonates.",
            )
        if tier == "old":
            days = int(age // 24)
            return (
                "Low opportunity",
                f"Post is {days}d old — outside the ideal reply window. "
                "Engagement metrics unavailable. Save for inspiration rather than replying.",
            )
        if tier == "borderline":
            if fit_score == "Strong fit":
                return (
                    "Medium opportunity",
                    "Post is 1-2 days old — borderline for replies. "
                    "Strong fit may still be worth engaging; verify the post is still active "
                    "and check engagement manually before replying.",
                )
            return (
                "Low opportunity",
                "Post is 1-2 days old with decent but not strong fit. "
                "Engagement metrics unavailable — check if it is still getting traction "
                "before committing to a reply.",
            )
        if tier == "unknown":
            return (
                "Medium opportunity",
                "Post found via web search — age and engagement metrics unavailable. "
                "Verify recency and engagement manually before replying.",
            )
        # fresh (0-24h)
        return (
            "Medium opportunity",
            "Post found via web search — engagement metrics unavailable. "
            "Fit looks good but verify engagement manually before replying.",
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


_AVOID_CRYPTO = frozenset({"xrp", "web3", "memecoin", "meme coin", "altcoin", "crypto pump"})
_AVOID_HYPE = frozenset({"100x", "moon", "gem", "next 10x", "get rich", "guaranteed"})
_AVOID_BAIT = frozenset({
    "link in bio", "screenshot this", "thank me later",
    "signal group", "join my discord", "free webinar", "paid group",
})
_AVOID_SENTIMENT = frozenset({
    "smart money", "everyone is bullish", "everyone is bearish",
    "fear is spreading", "highest level since",
})
_AVOID_TA = frozenset({
    "rsi", "macd", "moving average", "chart pattern", "technical analysis",
    "day trading", "swing trade", "screener", "entry point", "exit point",
    "bull trap", "bear trap",
})


def _avoid_reason(kw):
    kl = kw.lower()
    if kl in _AVOID_CRYPTO or any(t in kl for t in _AVOID_CRYPTO):
        return (
            f"Post contains '{kw}' — crypto-specific content outside Signal Shift's lane. "
            "Engaging could misalign the brand with crypto hype culture."
        )
    if kl in _AVOID_HYPE or any(t in kl for t in _AVOID_HYPE):
        return (
            f"Post contains '{kw}' — hype or get-rich framing. "
            "Incompatible with Signal Shift's calm, plain-English voice."
        )
    if kl in _AVOID_BAIT or any(t in kl for t in _AVOID_BAIT):
        return (
            f"Post contains '{kw}' — promotional or engagement-bait content. "
            "Signal Shift's voice is the opposite of this."
        )
    if kl in _AVOID_SENTIMENT or any(t in kl for t in _AVOID_SENTIMENT):
        return (
            f"Post contains '{kw}' — generic market sentiment bait. "
            "No retail decision-clarity angle. Not worth engaging."
        )
    return (
        f"Post contains '{kw}' — matches an avoid keyword. "
        "Engaging could associate Signal Shift with low-quality content."
    )


def _weak_reason(weak_hits):
    hits_lower = {h.lower() for h in weak_hits}
    if hits_lower & _AVOID_TA:
        return (
            f"Post matches technical-analysis keyword(s): {', '.join(weak_hits[:3])}. "
            "Audience is likely active traders focused on entries/exits — "
            "not retail investors seeking decision clarity."
        )
    return (
        f"Post matches weak-fit keyword(s): {', '.join(weak_hits[:3])}. "
        "Topic is misaligned with Signal Shift's retail-investor clarity positioning."
    )


def _score_fit_dynamic(post, profile):
    """
    Keyword-based fit scoring for real X posts whose IDs are not in FIT_SCORES.
    Uses fit_keywords from the profile YAML. Falls back gracefully if missing.
    Avoid keywords are checked first and override all other signals.
    Weak keywords block strong/decent promotion.
    """
    keywords = profile.get("fit_keywords", {}) if profile else {}
    avoid_kw = keywords.get("avoid", [])
    weak_kw = keywords.get("weak", [])
    decent_kw = keywords.get("decent", [])
    strong_kw = keywords.get("strong", [])

    text_lower = post.get("text", "").lower()

    # Check avoid first — hard stop regardless of any other signals
    for kw in avoid_kw:
        if kw.lower() in text_lower:
            return {
                "score": "Avoid",
                "reason": _avoid_reason(kw),
                "reply_account": "Do not reply",
            }

    # Count signals per tier
    strong_hits = [kw for kw in strong_kw if kw.lower() in text_lower]
    decent_hits = [kw for kw in decent_kw if kw.lower() in text_lower]
    weak_hits = [kw for kw in weak_kw if kw.lower() in text_lower]

    # Weak keywords outweigh positive signals
    if weak_hits:
        return {
            "score": "Weak fit",
            "reason": _weak_reason(weak_hits),
            "reply_account": "Do not reply",
        }

    if len(strong_hits) >= 2:
        return {
            "score": "Strong fit",
            "reason": (
                f"Post hits multiple strong-fit signals: {', '.join(strong_hits[:3])}. "
                "Directly addresses the retail investor overwhelm or clarity gap "
                "Signal Shift is built to solve."
            ),
            "reply_account": "Either",
        }

    if strong_hits:
        return {
            "score": "Decent fit",
            "reason": (
                f"Post hits strong-fit signal '{strong_hits[0]}'. "
                "Relevant angle but a single keyword is not enough to confirm "
                "the retail decision-clarity pain point Signal Shift addresses."
            ),
            "reply_account": "Either",
        }

    if decent_hits:
        return {
            "score": "Decent fit",
            "reason": (
                f"Post matches decent-fit signal(s): {', '.join(decent_hits[:3])}. "
                "Adjacent to Signal Shift's positioning — check whether the post "
                "has a genuine retail investor angle before replying."
            ),
            "reply_account": "Either",
        }

    return {
        "score": "Weak fit",
        "reason": (
            "Post did not match Signal Shift's core fit keywords. "
            "The topic may not address the retail investor overwhelm or "
            "earnings-clarity angle Signal Shift is built around."
        ),
        "reply_account": "Do not reply",
    }


def score_posts(posts, profile=None):
    results = []
    for post in posts:
        post_id = post["id"]
        # Mock posts (integer IDs 1-8) use hardcoded scoring; real posts use dynamic keyword scoring
        fit_data = FIT_SCORES.get(post_id) if isinstance(post_id, int) else None
        if fit_data is None:
            fit_data = _score_fit_dynamic(post, profile)
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
            "freshness_tier": _freshness_tier(post.get("age_hours")),
            "age_label": _age_label(post) if post.get("metrics_confidence") == "low" else None,
        })
    return results
