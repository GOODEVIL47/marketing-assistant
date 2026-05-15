import os
from datetime import date

_SCORE_ORDER = ["Strong fit", "Decent fit", "Weak fit", "Avoid"]
_OPP_ORDER = ["High opportunity", "Medium opportunity", "Low opportunity", "Poor opportunity"]


def _fit_emoji(score):
    return {"Strong fit": "✅", "Decent fit": "🟡", "Weak fit": "🔸", "Avoid": "🚫"}.get(score, "❓")


def _opp_emoji(opp):
    return {
        "High opportunity": "🎯",
        "Medium opportunity": "⚡",
        "Low opportunity": "⏳",
        "Poor opportunity": "❌",
    }.get(opp, "")


def _build_best_3(posts_with_replies):
    eligible = [
        p for p in posts_with_replies
        if p["score"] in ("Strong fit", "Decent fit")
        and p["opportunity"] in ("High opportunity", "Medium opportunity")
    ]
    top3 = sorted(
        eligible,
        key=lambda p: (_SCORE_ORDER.index(p["score"]), _OPP_ORDER.index(p["opportunity"])),
    )[:3]

    lines = []
    lines.append("## Today's Best 3")
    lines.append("")

    if not top3:
        lines.append("*No suitable reply opportunities found today.*")
        lines.append("*Check the Save for Inspiration section below for older posts worth referencing.*")
        lines.append("")
        return lines

    count = len(top3)
    if count < 3:
        noun = "opportunity" if count == 1 else "opportunities"
        lines.append(f"*Only {count} suitable reply {noun} found today.*")
        lines.append("")

    for i, post in enumerate(top3, 1):
        fit_e = _fit_emoji(post["score"])
        opp_e = _opp_emoji(post["opportunity"])
        best = post.get("best_reply") or {}
        media = post.get("media") or {}
        reply_text = best.get("text", "N/A")
        lines.append(f"**{i}. {post['author']}**")
        lines.append(
            f"Fit: {post['score']} {fit_e} · "
            f"Visibility: {post['visibility']} · "
            f"Opportunity: {post['opportunity']} {opp_e}"
        )
        lines.append(f"Engagement: {post['engagement_summary']}")
        if post.get("age_label"):
            lines.append(post["age_label"])
        lines.append(f"Reply from: {post['reply_account']} · Action: {post['suggested_action']}")
        lines.append(f"Best reply: *\"{reply_text}\"*")
        lines.append(f"Media: {media.get('type', 'No media')}")
        lines.append("")

    return lines


def _build_inspiration(posts_with_replies):
    """
    Posts that are too old for replies but have good fit — worth keeping as
    content inspiration for original posts.
    """
    inspiration = [
        p for p in posts_with_replies
        if p["score"] in ("Strong fit", "Decent fit")
        and p.get("metrics_confidence") == "low"
        and p.get("freshness_tier") == "old"
        and p.get("inspiration_angles")
    ]
    if not inspiration:
        return []

    lines = ["## Save for Inspiration", ""]
    lines.append(
        "These posts have good fit but are outside the reply window. "
        "Use them as inspiration for original posts — do not reply."
    )
    lines.append("")
    for post in inspiration:
        lines.append(f"- **{post['author']}** · {post['score']} · {post.get('age_label', '')}")
        lines.append(f"  > {post['text'][:120]}{'...' if len(post['text']) > 120 else ''}")
        lines.append(f"  {post.get('post_url', '')}")
        angles = post.get("inspiration_angles") or []
        if angles:
            lines.append("  **Inspiration angles:**")
            for angle in angles:
                lines.append(f"  - {angle}")
        lines.append("")
    return lines


def _build_original_posts(posts_schedule, mode="Mock"):
    lines = []
    lines.append("## Original Posts to Publish")
    lines.append("")

    for role, data in [("Founder", posts_schedule["founder"]), ("Product", posts_schedule["product"])]:
        handle = data.get("handle", role)
        lines.append(f"### {role} Post ({handle})")
        lines.append(f"*{data['reason']}*")
        lines.append("")

        if data["needed"]:
            post = data["post"]
            lines.append(f"> {post['text']}")
            lines.append("")
            fmt = post.get("format") or {}
            med = post.get("media") or {}
            lines.append(f"**Format:** {fmt.get('type', 'N/A')} — *{fmt.get('reason', '')}*")
            lines.append(f"**Media:** {med.get('type', 'No media')} — *{med.get('reason', '')}*")
            if mode != "Mock":
                lines.append(
                    f"*Check {handle} manually before posting "
                    f"(posting history unavailable in {mode} mode).*"
                )
        else:
            lines.append("No original post needed today.")
            lines.append("")
            idea = data.get("optional_idea")
            if idea:
                lines.append(f"**Optional idea ({idea['note']}):**")
                lines.append("")
                lines.append(f"> {idea['text']}")
                lines.append("")
                fmt = idea.get("format") or {}
                med = idea.get("media") or {}
                lines.append(f"**Format:** {fmt.get('type', 'N/A')} — *{fmt.get('reason', '')}*")
                lines.append(f"**Media:** {med.get('type', 'No media')} — *{med.get('reason', '')}*")

        lines.append("")

    return lines


def build_markdown(profile_name, posts_with_replies, posts_schedule, mode="Mock"):
    today = date.today().isoformat()
    lines = []

    lines.append(f"# Mel's Daily Digest — {today}")
    lines.append(f"**Product:** {profile_name}")
    lines.append(f"**Mode:** {mode}")
    lines.append("")
    lines.append("---")
    lines.append("")

    lines.extend(_build_best_3(posts_with_replies))

    inspiration = _build_inspiration(posts_with_replies)
    if inspiration:
        lines.append("---")
        lines.append("")
        lines.extend(inspiration)

    lines.append("---")
    lines.append("")
    lines.append("## Post Scoring & Reply Suggestions")
    lines.append("")

    for post in posts_with_replies:
        fit_e = _fit_emoji(post["score"])
        opp_e = _opp_emoji(post["opportunity"])
        lines.append(f"### Post {post['id']} — {post['author']}")
        lines.append(f"**Fit:** {post['score']} {fit_e}")
        lines.append(f"**Visibility:** {post['visibility']}")
        lines.append(f"**Opportunity:** {post['opportunity']} {opp_e}")
        lines.append(f"**Engagement:** {post['engagement_summary']}")
        if post.get("age_label"):
            lines.append(f"**{post['age_label']}**")
        _src_labels = {"brave_search": "Brave Search", "tavily_search": "Tavily Search"}
        _src = _src_labels.get(post.get("discovery_source", ""), "")
        if _src:
            lines.append(
                f"**Source:** Found via {_src} — "
                "engagement metrics unavailable. Verify before replying."
            )
        followers = post.get("author_followers", 0)
        followers_str = (
            "Unknown"
            if (followers == 0 and post.get("metrics_confidence") == "low")
            else f"{followers:,}"
        )
        lines.append(f"**Author followers:** {followers_str}")
        post_url = post.get("post_url")
        if post_url:
            lines.append(f"**Post URL:** {post_url}")
        lines.append(f"**Suggested account:** {post['reply_account']}")
        lines.append(f"**Suggested action:** {post['suggested_action']}")
        lines.append("")
        lines.append(f"**Post:** {post['text']}")
        lines.append("")
        lines.append(f"**Why it fits:** {post['reason']}")
        lines.append(f"**Why this is / is not worth engaging:** {post['opportunity_reason']}")
        lines.append("")

        reply_note = post.get("reply_note")
        inspiration_angles = post.get("inspiration_angles")
        if reply_note:
            lines.append(f"*{reply_note}*")
            lines.append("")
        elif inspiration_angles:
            lines.append("**Inspiration angles (do not reply — use for original posts):**")
            lines.append("")
            for angle in inspiration_angles:
                lines.append(f"- {angle}")
            lines.append("")
        elif post["replies"]:
            media = post.get("media") or {}
            lines.append(f"**Media suggestion:** {media.get('type', 'No media')}")
            lines.append(f"*{media.get('reason', '')}*")
            lines.append("")
            lines.append("**Reply options:**")
            lines.append("")
            for reply in post["replies"]:
                lines.append(f"**{reply['style']}**")
                lines.append(f"> {reply['text']}")
                lines.append("")
        else:
            lines.append("*No replies suggested for this post.*")
            lines.append("")

        lines.append("---")
        lines.append("")

    lines.extend(_build_original_posts(posts_schedule, mode=mode))

    return "\n".join(lines)


def save_digest(profile_name, posts_with_replies, posts_schedule, mode="Mock"):
    today = date.today().isoformat()
    output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output")
    os.makedirs(output_dir, exist_ok=True)

    filename = f"daily_digest_{today}.md"
    filepath = os.path.join(output_dir, filename)

    content = build_markdown(profile_name, posts_with_replies, posts_schedule, mode=mode)

    with open(filepath, "w") as f:
        f.write(content)

    return filepath
