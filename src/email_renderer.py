import html as _html
from datetime import date as _date

from src.digest import _SCORE_ORDER, _OPP_ORDER

# Maps discovery_source values to human-readable provider labels.
# Add new web search providers here — source notes update automatically.
_WEB_SEARCH_LABELS = {
    "brave_search":  "Brave Search",
    "tavily_search": "Tavily Search",
}

_FIT_BADGE = {
    "Strong fit":  ("✅ Strong fit",  "#d1fae5", "#065f46"),
    "Decent fit":  ("🟡 Decent fit",  "#fef3c7", "#92400e"),
    "Weak fit":    ("🔸 Weak fit",    "#fee2e2", "#991b1b"),
    "Avoid":       ("🚫 Avoid",       "#f3f4f6", "#6b7280"),
}

_OPP_BADGE = {
    "High opportunity":   ("🎯 High",   "#dbeafe", "#1e40af"),
    "Medium opportunity": ("⚡ Medium", "#ede9fe", "#5b21b6"),
    "Low opportunity":    ("⏳ Low",    "#f3f4f6", "#6b7280"),
    "Poor opportunity":   ("❌ Poor",   "#fee2e2", "#991b1b"),
}

_VIS_BADGE = {
    "Strong visibility":  ("Strong visibility",  "#e0f2fe", "#0369a1"),
    "Decent visibility":  ("Decent visibility",  "#f3f4f6", "#6b7280"),
    "Low visibility":     ("Low visibility",     "#f3f4f6", "#9ca3af"),
    "Unknown visibility": ("Unknown visibility", "#fef3c7", "#92400e"),
}


def _esc(text):
    return _html.escape(str(text))


def _badge(label, bg, color):
    return (
        f'<span style="display:inline-block;background:{bg};color:{color};'
        f'padding:4px 10px;border-radius:4px;font-size:12px;font-weight:600;'
        f'white-space:nowrap;margin-right:5px;margin-bottom:4px;">{_esc(label)}</span>'
    )


def _get_best3(posts_with_replies):
    eligible = [
        p for p in posts_with_replies
        if p["score"] in ("Strong fit", "Decent fit")
        and p["opportunity"] in ("High opportunity", "Medium opportunity")
    ]
    return sorted(
        eligible,
        key=lambda p: (_SCORE_ORDER.index(p["score"]), _OPP_ORDER.index(p["opportunity"])),
    )[:3]


def _mel_recommendation(best3, posts_schedule):
    founder_needed = posts_schedule["founder"]["needed"]
    product_needed = posts_schedule["product"]["needed"]

    if not best3:
        rec = "No strong reply opportunities today."
    else:
        top = best3[0]
        rec = f"Best move: reply to {top['author']}."
        if len(best3) > 1:
            second = best3[1]
            media_type = (second.get("media") or {}).get("type", "")
            if "quote" in media_type.lower():
                rec += f" Consider quote reposting {second['author']} for a stronger founder take."

    if not founder_needed and not product_needed:
        rec += " No original posts needed today."
    elif founder_needed and product_needed:
        rec += " Original posts recommended for both accounts."
    elif founder_needed:
        rec += " Founder post recommended today."
    elif product_needed:
        rec += " Product post recommended today."

    return rec


def _html_media_block(media):
    if not media:
        return ""

    media_type = media.get("type", "No media")
    lh = "font-size:12px;line-height:1.4;"
    rows = [
        f'<p style="margin:0 0 4px;{lh}font-weight:700;color:#374151;">'
        f'Media: {_esc(media_type)}</p>'
    ]

    if media_type == "Optional GIF":
        idea = media.get("idea", "")
        use_if = media.get("use_if", "")
        skip_if = media.get("skip_if", "")
        if idea:
            rows.append(f'<p style="margin:0 0 2px;{lh}color:#555;">Idea: {_esc(idea)}</p>')
        if use_if:
            rows.append(f'<p style="margin:0 0 2px;{lh}color:#555;">Use: {_esc(use_if)}</p>')
        if skip_if:
            rows.append(f'<p style="margin:0;{lh}color:#888;">Skip: {_esc(skip_if)}</p>')

    elif media_type == "Quote repost":
        use_if = media.get("use_if", "")
        skip_if = media.get("skip_if", "")
        if use_if:
            rows.append(f'<p style="margin:0 0 2px;{lh}color:#555;">Use: {_esc(use_if)}</p>')
        if skip_if:
            rows.append(f'<p style="margin:0;{lh}color:#888;">Skip: {_esc(skip_if)}</p>')

    elif media_type == "No media":
        reason = media.get("reason", "")
        if reason:
            rows.append(f'<p style="margin:0;{lh}color:#888;">Reason: {_esc(reason)}</p>')

    inner = "".join(rows)
    return f"""
      <table width="100%" cellpadding="0" cellspacing="0" style="margin:12px 0 0;">
        <tr>
          <td style="background:#f8fafc;border:1px solid #e8edf2;border-radius:5px;padding:8px 11px;">
            {inner}
          </td>
        </tr>
      </table>"""


def _html_replies_block(post):
    best_reply = post.get("best_reply") or {}
    best_style = best_reply.get("style", "")
    best_text = best_reply.get("text", "")
    all_replies = post.get("replies") or []
    other_replies = [r for r in all_replies if r.get("style") != best_style]

    if not best_text:
        return ""

    # Recommended reply
    recommended = f"""
      <table width="100%" cellpadding="0" cellspacing="0">
        <tr>
          <td style="background:#f0f4f8;border-left:3px solid #1a2e4a;
                     border-radius:0 4px 4px 0;padding:10px 12px;">
            <p style="margin:0 0 5px;font-size:11px;color:#1a2e4a;
                       text-transform:uppercase;letter-spacing:0.6px;font-weight:700;">
              &#x2705; Recommended &mdash; {_esc(best_style)}
            </p>
            <p style="margin:0;font-size:13px;color:#1a2e4a;line-height:1.5;">
              &ldquo;{_esc(best_text)}&rdquo;
            </p>
          </td>
        </tr>
      </table>"""

    # Other options
    other_html = ""
    if other_replies:
        items = ""
        for i, reply in enumerate(other_replies):
            bottom_margin = "8px" if i < len(other_replies) - 1 else "0"
            items += (
                f'<p style="margin:0 0 3px;font-size:12px;font-weight:700;color:#374151;">'
                f'{_esc(reply.get("style", ""))}</p>'
                f'<p style="margin:0 0 {bottom_margin};font-size:12px;color:#555;line-height:1.5;">'
                f'&ldquo;{_esc(reply.get("text", ""))}&rdquo;</p>'
            )
        other_html = f"""
      <p style="margin:12px 0 7px;font-size:11px;color:#888;
                 text-transform:uppercase;letter-spacing:0.6px;font-weight:700;">
        Other options
      </p>
      {items}"""

    return recommended + other_html


def _html_post_card(rank, post):
    author = post["author"]
    handle = author.lstrip("@")
    post_url = post.get("post_url") or f"https://x.com/{handle}"
    profile_url = post.get("author_profile_url") or f"https://x.com/{handle}"

    fit_label, fit_bg, fit_color = _FIT_BADGE.get(
        post["score"], (post["score"], "#f3f4f6", "#374151")
    )
    opp_label, opp_bg, opp_color = _OPP_BADGE.get(
        post["opportunity"], (post["opportunity"], "#f3f4f6", "#374151")
    )
    vis_label, vis_bg, vis_color = _VIS_BADGE.get(
        post["visibility"], (post["visibility"], "#f3f4f6", "#374151")
    )

    eng = _esc(post.get("engagement_summary", ""))
    age_label = post.get("age_label") or ""
    account = _esc(post.get("reply_account", ""))

    _provider_label = _WEB_SEARCH_LABELS.get(post.get("discovery_source", ""), "")
    source_note = (
        '<p style="margin:0 0 8px;font-size:11px;color:#92400e;'
        'font-style:italic;line-height:1.4;">'
        f'&#x1F50D; Found via {_esc(_provider_label)} &mdash; '
        'check engagement manually before replying.'
        '</p>'
    ) if _provider_label else ""

    replies_block = _html_replies_block(post)
    media_block = _html_media_block(post.get("media"))

    return f"""
    <table width="100%" cellpadding="0" cellspacing="0"
           style="background:#ffffff;border:1px solid #e0e6ed;border-radius:8px;
                  margin-bottom:20px;">
      <tr>
        <td style="padding:16px 18px;">

          <p style="margin:0 0 8px;font-size:15px;font-weight:700;
                    color:#1a2e4a;line-height:1.3;">
            {rank}. {_esc(author)}
          </p>

          <p style="margin:0 0 10px;line-height:1.9;">
            {_badge(fit_label, fit_bg, fit_color)}{_badge(vis_label, vis_bg, vis_color)}{_badge(opp_label, opp_bg, opp_color)}
          </p>

          <p style="margin:0 0 8px;color:#888;font-size:12px;">{eng}</p>
          {f'<p style="margin:0 0 8px;font-size:11px;color:#6b7280;">{_esc(age_label)}</p>' if age_label else ""}
          {source_note}

          <p style="margin:0 0 12px;font-size:12px;color:#444;">
            <strong>Reply from:</strong> {account}
          </p>

          {replies_block}
          {media_block}

          <table width="100%" cellpadding="0" cellspacing="0" style="margin:14px 0 0;">
            <tr>
              <td width="50%" style="padding-right:6px;">
                <a href="{_esc(post_url)}"
                   style="display:block;background:#1a2e4a;color:#ffffff;
                          text-decoration:none;padding:8px 10px;border-radius:5px;
                          font-size:12px;font-weight:600;text-align:center;">
                  Open post &#x2197;
                </a>
              </td>
              <td width="50%">
                <a href="{_esc(profile_url)}"
                   style="display:block;background:#f0f2f5;color:#374151;
                          text-decoration:none;padding:8px 10px;border-radius:5px;
                          font-size:12px;text-align:center;">
                  View profile
                </a>
              </td>
            </tr>
          </table>

        </td>
      </tr>
    </table>"""


def _html_original_posts(posts_schedule):
    parts = []
    for role in ("founder", "product"):
        data = posts_schedule[role]
        handle = _esc(data["handle"])
        if data["needed"]:
            post = data["post"]
            fmt = _esc((post.get("format") or {}).get("type", ""))
            med = _esc((post.get("media") or {}).get("type", "No media"))
            text = post.get("text", "").replace("\n\n", " ").replace("\n", " ")
            parts.append(
                f'<p style="margin:0 0 5px;font-size:12px;font-weight:700;color:#1a2e4a;">'
                f'{role.title()} ({handle}) &mdash; Recommended today</p>'
                f'<p style="margin:0 0 5px;font-size:12px;color:#444;line-height:1.5;'
                f'font-style:italic;">&ldquo;{_esc(text)}&rdquo;</p>'
                f'<p style="margin:0 0 14px;font-size:11px;color:#888;">'
                f'Format: {fmt} &nbsp;&middot;&nbsp; Media: {med}</p>'
            )
        else:
            reason = _esc(data.get("reason", "Not scheduled today."))
            parts.append(
                f'<p style="margin:0 0 3px;font-size:12px;font-weight:600;color:#888;">'
                f'{role.title()} ({handle}) &mdash; Not needed today</p>'
                f'<p style="margin:0 0 14px;font-size:11px;color:#aaa;line-height:1.5;">'
                f'{reason}</p>'
            )
    return "".join(parts)


def render_digest_html(profile_name, posts_with_replies, posts_schedule, mode="Mock"):
    today = _date.today().isoformat()
    best3 = _get_best3(posts_with_replies)

    high_count = sum(
        1 for p in posts_with_replies
        if p["opportunity"] == "High opportunity"
        and p["score"] in ("Strong fit", "Decent fit")
    )
    med_count = sum(
        1 for p in posts_with_replies
        if p["opportunity"] == "Medium opportunity"
        and p["score"] in ("Strong fit", "Decent fit")
    )

    founder_ok = posts_schedule["founder"]["needed"]
    product_ok = posts_schedule["product"]["needed"]
    founder_val = '<span style="color:#4ade80;font-weight:700;">Recommended</span>' if founder_ok else "Not needed"
    product_val = '<span style="color:#4ade80;font-weight:700;">Recommended</span>' if product_ok else "Not needed"

    recommendation = _esc(_mel_recommendation(best3, posts_schedule))

    if best3:
        count_note = ""
        if len(best3) < 3:
            noun = "opportunity" if len(best3) == 1 else "opportunities"
            count_note = (
                f'<p style="margin:0 0 12px;font-size:12px;color:#92400e;font-style:italic;">'
                f'Only {len(best3)} suitable reply {noun} found today.</p>'
            )
        cards = count_note + "".join(_html_post_card(i + 1, p) for i, p in enumerate(best3))
    else:
        cards = '<p style="color:#888;font-size:14px;">No suitable reply opportunities found today. Check the full digest for inspiration posts.</p>'

    original_posts_html = _html_original_posts(posts_schedule)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>Mel&apos;s Daily Digest &mdash; {today}</title>
</head>
<body style="margin:0;padding:0;background:#f5f7fa;
             font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;">

<table width="100%" cellpadding="0" cellspacing="0" style="background:#f5f7fa;">
<tr><td align="center" style="padding:18px 10px;">
<table width="100%" cellpadding="0" cellspacing="0" style="max-width:580px;">

  <!-- ── Header ── -->
  <tr><td style="background:#1a2e4a;border-radius:8px 8px 0 0;padding:16px 22px 12px;">
    <p style="margin:0 0 3px;font-size:10px;color:#6b8faf;
               text-transform:uppercase;letter-spacing:1px;font-weight:600;">
      Internal tool &nbsp;&middot;&nbsp; Not for distribution
    </p>
    <h1 style="margin:0 0 4px;font-size:20px;font-weight:700;
               color:#ffffff;line-height:1.2;">
      Mel&apos;s Daily Digest
    </h1>
    <p style="margin:0;font-size:12px;color:#a0b8cc;">
      {_esc(profile_name)} &nbsp;&middot;&nbsp; {today} &nbsp;&middot;&nbsp; {_esc(mode)} mode
    </p>
  </td></tr>

  <!-- ── Quick summary bar ── -->
  <tr><td style="background:#1e3a5f;padding:10px 22px;">
    <table width="100%" cellpadding="0" cellspacing="0">
      <tr>
        <td width="50%" style="color:#a0c4e8;font-size:12px;padding-bottom:4px;">
          &#x1F3AF; High: <strong style="color:#ffffff;">{high_count}</strong>
          &nbsp;&nbsp;&#x26A1; Med: <strong style="color:#ffffff;">{med_count}</strong>
        </td>
        <td width="50%" style="color:#a0c4e8;font-size:12px;padding-bottom:4px;text-align:right;">
          Founder: <strong style="color:#ffffff;">{founder_val}</strong>
        </td>
      </tr>
      <tr>
        <td colspan="2" style="color:#a0c4e8;font-size:12px;">
          Product: <strong style="color:#ffffff;">{product_val}</strong>
        </td>
      </tr>
    </table>
  </td></tr>

  <!-- ── Mel's take ── -->
  <tr><td style="background:#ffffff;border-left:1px solid #e0e6ed;
                 border-right:1px solid #e0e6ed;padding:13px 22px 11px;">
    <p style="margin:0 0 4px;font-size:11px;color:#888;
               text-transform:uppercase;letter-spacing:0.6px;font-weight:700;">
      Mel&apos;s take
    </p>
    <p style="margin:0 0 6px;font-size:13px;color:#2d3748;line-height:1.55;">
      {recommendation}
    </p>
    <p style="margin:0;font-size:11px;color:#9aa8b8;font-style:italic;">
      Pick one. Lightly edit. Post.
    </p>
  </td></tr>

  <!-- ── Divider ── -->
  <tr><td style="background:#ffffff;border-left:1px solid #e0e6ed;
                 border-right:1px solid #e0e6ed;padding:0 22px;">
    <hr style="border:none;border-top:1px solid #e8edf2;margin:0;">
  </td></tr>

  <!-- ── Today's Best 3 ── -->
  <tr><td style="background:#ffffff;border-left:1px solid #e0e6ed;
                 border-right:1px solid #e0e6ed;padding:16px 22px 8px;">
    <p style="margin:0 0 12px;font-size:14px;font-weight:700;color:#1a2e4a;">
      Today&apos;s Best 3
    </p>
    {cards}
  </td></tr>

  <!-- ── Divider ── -->
  <tr><td style="background:#ffffff;border-left:1px solid #e0e6ed;
                 border-right:1px solid #e0e6ed;padding:0 22px;">
    <hr style="border:none;border-top:1px solid #e8edf2;margin:0;">
  </td></tr>

  <!-- ── Original posts ── -->
  <tr><td style="background:#ffffff;border-left:1px solid #e0e6ed;
                 border-right:1px solid #e0e6ed;padding:16px 22px 10px;">
    <p style="margin:0 0 12px;font-size:14px;font-weight:700;color:#1a2e4a;">
      Original Posts
    </p>
    {original_posts_html}
  </td></tr>

  <!-- ── Footer ── -->
  <tr><td style="background:#f0f4f8;border:1px solid #e0e6ed;border-top:none;
                 border-radius:0 0 8px 8px;padding:12px 22px;">
    <p style="margin:0;font-size:11px;color:#999;line-height:1.6;">
      {"Full digest &mdash; all posts, all reply options &mdash; in the GitHub Actions artifact." if mode == "Mock" else "Full digest with all scoring details saved locally."}
    </p>
  </td></tr>

</table>
</td></tr>
</table>

</body>
</html>"""


def render_digest_text(profile_name, posts_with_replies, posts_schedule, mode="Mock"):
    today = _date.today().isoformat()
    best3 = _get_best3(posts_with_replies)

    high_count = sum(
        1 for p in posts_with_replies
        if p["opportunity"] == "High opportunity"
        and p["score"] in ("Strong fit", "Decent fit")
    )
    med_count = sum(
        1 for p in posts_with_replies
        if p["opportunity"] == "Medium opportunity"
        and p["score"] in ("Strong fit", "Decent fit")
    )

    lines = [
        "MEL'S DAILY DIGEST",
        f"{profile_name} · {today} · {mode} mode",
        "=" * 52,
        "",
        "QUICK SUMMARY",
        f"High opportunity replies:   {high_count}",
        f"Medium opportunity replies: {med_count}",
        f"Founder post:  {'Recommended today' if posts_schedule['founder']['needed'] else 'Not needed today'}",
        f"Product post:  {'Recommended today' if posts_schedule['product']['needed'] else 'Not needed today'}",
        "",
        "MEL'S TAKE",
        _mel_recommendation(best3, posts_schedule),
        "Pick one. Lightly edit. Post.",
        "",
        "TODAY'S BEST 3",
        "-" * 52,
        "",
    ]

    if not best3:
        lines.append("No strong reply opportunities found today.")
    else:
        for i, post in enumerate(best3, 1):
            author = post["author"]
            handle = author.lstrip("@")
            post_url = post.get("post_url") or f"https://x.com/{handle}"
            profile_url = post.get("author_profile_url") or f"https://x.com/{handle}"

            best_reply = post.get("best_reply") or {}
            best_style = best_reply.get("style", "")
            best_text = best_reply.get("text", "")
            all_replies = post.get("replies") or []
            other_replies = [r for r in all_replies if r.get("style") != best_style]

            _src_label = _WEB_SEARCH_LABELS.get(post.get("discovery_source", ""), "")
            lines += [
                f"{i}. {author}",
                f"   {post['score']} · {post['visibility']} · {post['opportunity']}",
                f"   {post.get('engagement_summary', '')}",
                f"   Reply from: {post.get('reply_account', '')}",
            ]
            if _src_label:
                lines.append(f"   [{_src_label}] Check engagement manually before replying.")
            lines.append("")

            if best_text:
                lines += [
                    f"   * Recommended — {best_style}:",
                    f'   "{best_text}"',
                ]

            if other_replies:
                lines += ["", "   Other options:"]
                for reply in other_replies:
                    lines += [
                        f"   {reply.get('style', '')}:",
                        f'   "{reply.get("text", "")}"',
                        "",
                    ]

            media = post.get("media") or {}
            media_type = media.get("type", "No media")
            lines.append(f"   Media: {media_type}")
            if media_type == "Optional GIF":
                idea = media.get("idea", "")
                use_if = media.get("use_if", "")
                skip_if = media.get("skip_if", "")
                if idea:
                    lines.append(f"   Idea: {idea}")
                if use_if:
                    lines.append(f"   Use: {use_if}")
                if skip_if:
                    lines.append(f"   Skip: {skip_if}")
            elif media_type == "Quote repost":
                use_if = media.get("use_if", "")
                skip_if = media.get("skip_if", "")
                if use_if:
                    lines.append(f"   Use: {use_if}")
                if skip_if:
                    lines.append(f"   Skip: {skip_if}")
            elif media_type == "No media":
                reason = media.get("reason", "")
                if reason:
                    lines.append(f"   Reason: {reason}")

            lines += [
                "",
                f"   Open post:    {post_url}",
                f"   View profile: {profile_url}",
                "",
            ]

    lines += [
        "-" * 52,
        "",
        "ORIGINAL POSTS",
    ]

    for role in ("founder", "product"):
        data = posts_schedule[role]
        status = "Recommended today" if data["needed"] else "Not needed today"
        lines.append(f"{role.title()} ({data['handle']}): {status}")

    footer = (
        "Full detailed digest (all posts, all reply options) available in the GitHub Actions artifact."
        if mode == "Mock"
        else "Full digest with all scoring details saved locally."
    )
    lines += ["", footer]

    return "\n".join(lines)
