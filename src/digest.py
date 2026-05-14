import os
from datetime import date


def _score_emoji(score):
    return {
        "Strong fit": "✅",
        "Decent fit": "🟡",
        "Weak fit": "🔸",
        "Avoid": "🚫",
    }.get(score, "❓")


def build_markdown(profile_name, posts_with_replies, founder_post, product_post):
    today = date.today().isoformat()
    lines = []

    lines.append(f"# Marketing Digest — {today}")
    lines.append(f"**Product:** {profile_name}")
    lines.append(f"**Mode:** Mock")
    lines.append("")

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
    lines.append(f"### Product Post ({product_post['account']})")
    lines.append("")
    lines.append(f"> {product_post['text']}")
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
