import os
from datetime import date

_SCORE_ORDER = ["Strong fit", "Decent fit", "Weak fit", "Avoid"]


def _score_emoji(score):
    return {
        "Strong fit": "✅",
        "Decent fit": "🟡",
        "Weak fit": "🔸",
        "Avoid": "🚫",
    }.get(score, "❓")


def _build_best_3(posts_with_replies):
    eligible = [p for p in posts_with_replies if p["score"] in ("Strong fit", "Decent fit")]
    top3 = sorted(eligible, key=lambda p: _SCORE_ORDER.index(p["score"]))[:3]

    lines = []
    lines.append("## Today's Best 3")
    lines.append("")
    lines.append("Top posts worth engaging with today.")
    lines.append("")

    for i, post in enumerate(top3, 1):
        emoji = _score_emoji(post["score"])
        best = post.get("best_reply") or {}
        media = post.get("media") or {}
        reply_text = best.get("text", "N/A")
        lines.append(f"**{i}. {post['author']} — {post['score']} {emoji}**")
        lines.append(f"Reply from: {post['reply_account']}")
        lines.append(f"Best reply: *\"{reply_text}\"*")
        lines.append(f"Media: {media.get('type', 'No media')}")
        lines.append("")

    return lines


def build_markdown(profile_name, posts_with_replies, founder_post, product_post):
    today = date.today().isoformat()
    lines = []

    lines.append(f"# Marketing Digest — {today}")
    lines.append(f"**Product:** {profile_name}")
    lines.append(f"**Mode:** Mock")
    lines.append("")
    lines.append("---")
    lines.append("")

    lines.extend(_build_best_3(posts_with_replies))

    lines.append("---")
    lines.append("")
    lines.append("## Post Scoring & Reply Suggestions")
    lines.append("")

    for post in posts_with_replies:
        emoji = _score_emoji(post["score"])
        lines.append(f"### Post {post['id']} — {post['score']} {emoji}")
        lines.append(f"**Author:** {post['author']}")
        lines.append(f"**Post:** {post['text']}")
        lines.append("")
        lines.append(f"**Score:** {post['score']}")
        lines.append(f"**Why:** {post['reason']}")
        lines.append(f"**Suggested account:** {post['reply_account']}")
        lines.append("")

        if post["replies"]:
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

    lines.append("## Original Posts to Publish")
    lines.append("")

    lines.append(f"### Founder Post ({founder_post['account']})")
    lines.append("")
    lines.append(f"> {founder_post['text']}")
    lines.append("")
    fmt = founder_post.get("format") or {}
    med = founder_post.get("media") or {}
    lines.append(f"**Format:** {fmt.get('type', 'N/A')} — *{fmt.get('reason', '')}*")
    lines.append(f"**Media:** {med.get('type', 'No media')} — *{med.get('reason', '')}*")
    lines.append("")

    lines.append(f"### Product Post ({product_post['account']})")
    lines.append("")
    lines.append(f"> {product_post['text']}")
    lines.append("")
    fmt = product_post.get("format") or {}
    med = product_post.get("media") or {}
    lines.append(f"**Format:** {fmt.get('type', 'N/A')} — *{fmt.get('reason', '')}*")
    lines.append(f"**Media:** {med.get('type', 'No media')} — *{med.get('reason', '')}*")
    lines.append("")

    return "\n".join(lines)


def save_digest(profile_name, posts_with_replies, founder_post, product_post):
    today = date.today().isoformat()
    output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output")
    os.makedirs(output_dir, exist_ok=True)

    filename = f"daily_digest_{today}.md"
    filepath = os.path.join(output_dir, filename)

    content = build_markdown(profile_name, posts_with_replies, founder_post, product_post)

    with open(filepath, "w") as f:
        f.write(content)

    return filepath
