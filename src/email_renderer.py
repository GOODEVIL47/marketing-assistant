import html as _html
from datetime import date as _date

from src.digest import (
    _SCORE_ORDER,
    _OPP_ORDER,
    _categorize_rejected,
    _normalize_format_label,
    _format_reason_for,
    _manual_review_note,
    _fill_media_fallbacks,
    _FORMAT_LABEL_MAP,
    _display_account,
)

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
        f'Media/GIF: {_esc(media_type)}</p>'
    ]
    if media.get("idea"):
        rows.append(f'<p style="margin:0 0 2px;{lh}color:#555;">Media idea: {_esc(media["idea"])}</p>')
    if media.get("use_if"):
        rows.append(f'<p style="margin:0 0 2px;{lh}color:#555;">Use media if: {_esc(media["use_if"])}</p>')
    if media.get("skip_if"):
        rows.append(f'<p style="margin:0 0 2px;{lh}color:#888;">Skip media if: {_esc(media["skip_if"])}</p>')
    if media.get("reason"):
        rows.append(f'<p style="margin:0;{lh}color:#888;font-style:italic;">{_esc(media["reason"])}</p>')

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
    if not best_style and all_replies:
        other_replies = all_replies

    if not best_text:
        return ""

    fmt_label = _esc(_normalize_format_label(best_style))
    fmt_reason = _esc(_format_reason_for(best_style))
    account = _esc(_display_account(post.get("reply_account", "")))
    note = _manual_review_note(post)
    lh = "font-size:11px;line-height:1.4;"

    meta_rows = (
        f'<p style="margin:6px 0 2px;{lh}color:#555;">Why this format: {fmt_reason}</p>'
        f'<p style="margin:0 0 2px;{lh}color:#555;">Account: {account}</p>'
    )
    if note:
        meta_rows += (
            f'<p style="margin:0;{lh}color:#92400e;font-style:italic;">'
            f'&#x26A0; {_esc(note)}</p>'
        )

    recommended = f"""
      <table width="100%" cellpadding="0" cellspacing="0">
        <tr>
          <td style="background:#f0f4f8;border-left:3px solid #1a2e4a;
                     border-radius:0 4px 4px 0;padding:10px 12px;">
            <p style="margin:0 0 5px;font-size:11px;color:#1a2e4a;
                       text-transform:uppercase;letter-spacing:0.6px;font-weight:700;">
              &#x2705; Recommended format: {fmt_label}
            </p>
            <p style="margin:0;font-size:13px;color:#1a2e4a;line-height:1.5;">
              &ldquo;{_esc(best_text)}&rdquo;
            </p>
            {meta_rows}
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

    _provider_label = _WEB_SEARCH_LABELS.get(post.get("discovery_source", ""), "")
    _eng_raw = post.get("engagement_summary", "")
    _web_suffix = " · found via web search"
    _needs_web_suffix = bool(_provider_label) and _web_suffix not in _eng_raw
    eng = _esc(_eng_raw + (_web_suffix if _needs_web_suffix else ""))
    age_label = post.get("age_label") or ""

    reply_note = post.get("reply_note")
    inspiration_angles = post.get("inspiration_angles")
    if reply_note:
        replies_block = (
            f'<p style="margin:12px 0 0;font-size:12px;color:#92400e;font-style:italic;">'
            f'&#x26A0; {_esc(reply_note)}</p>'
        )
        media_block = ""
    elif inspiration_angles:
        angles_html = "".join(
            f'<p style="margin:0 0 4px;font-size:12px;color:#374151;">&#x2022; {_esc(a)}</p>'
            for a in inspiration_angles
        )
        replies_block = (
            '<p style="margin:12px 0 5px;font-size:11px;font-weight:700;color:#6b7280;'
            'text-transform:uppercase;letter-spacing:0.6px;">Inspiration angles — do not reply</p>'
            + angles_html
        )
        media_block = ""
    else:
        replies_block = _html_replies_block(post)
        raw_media = post.get("media") or {"type": "No media", "reason": "Clean text reply — the point lands without a visual."}
        media_block = _html_media_block(raw_media)

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


def _html_inspiration(posts_with_replies):
    inspiration = [
        p for p in posts_with_replies
        if p["score"] in ("Strong fit", "Decent fit")
        and p.get("metrics_confidence") == "low"
        and p.get("freshness_tier") == "old"
        and p.get("inspiration_angles")
    ]
    if not inspiration:
        return ""

    items = ""
    for post in inspiration:
        angles = post.get("inspiration_angles") or []
        angles_html = "".join(
            f'<p style="margin:0 0 3px;font-size:11px;color:#374151;">&#x2022; {_esc(a)}</p>'
            for a in angles
        )
        post_url = _esc(post.get("post_url", "#"))
        items += (
            f'<p style="margin:0 0 3px;font-size:12px;font-weight:700;color:#1a2e4a;">'
            f'{_esc(post["author"])} &mdash; {_esc(post["score"])}</p>'
            f'<p style="margin:0 0 4px;font-size:11px;color:#6b7280;font-style:italic;">'
            f'&ldquo;{_esc(post["text"][:120])}{"..." if len(post["text"]) > 120 else ""}&rdquo;</p>'
            + angles_html
            + f'<p style="margin:0 0 12px;font-size:11px;">'
            f'<a href="{post_url}" style="color:#1a2e4a;">View post &#x2197;</a></p>'
        )

    return f"""
  <!-- ── Save for Inspiration ── -->
  <tr><td style="background:#ffffff;border-left:1px solid #e0e6ed;
                 border-right:1px solid #e0e6ed;padding:0 22px;">
    <hr style="border:none;border-top:1px solid #e8edf2;margin:0;">
  </td></tr>
  <tr><td style="background:#ffffff;border-left:1px solid #e0e6ed;
                 border-right:1px solid #e0e6ed;padding:16px 22px 10px;">
    <p style="margin:0 0 8px;font-size:14px;font-weight:700;color:#1a2e4a;">
      Save for Inspiration
    </p>
    <p style="margin:0 0 12px;font-size:11px;color:#6b7280;">
      Good fit but outside the reply window. Use as ideas for original posts &mdash; do not reply.
    </p>
    {items}
  </td></tr>"""


def _html_rejected_summary(posts_with_replies):
    """Compact HTML section summarising posts not selected, with category counts and 3 examples."""
    cats = _categorize_rejected(posts_with_replies)
    total = sum(len(v) for v in cats.values())
    if total == 0:
        return ""

    breakdown_parts = []
    if cats["stale"]:
        breakdown_parts.append(f'Stale (&gt;7d): <strong>{len(cats["stale"])}</strong>')
    if cats["out_of_scope"]:
        breakdown_parts.append(f'Out of scope: <strong>{len(cats["out_of_scope"])}</strong>')
    if cats["avoid"]:
        breakdown_parts.append(f'Avoid: <strong>{len(cats["avoid"])}</strong>')
    if cats["weak"]:
        breakdown_parts.append(f'Weak fit: <strong>{len(cats["weak"])}</strong>')
    if cats["other"]:
        breakdown_parts.append(f'Other: <strong>{len(cats["other"])}</strong>')
    breakdown_html = " &middot; ".join(breakdown_parts)

    examples = []
    for cat_name in ("avoid", "weak", "stale", "out_of_scope", "other"):
        for post in cats[cat_name]:
            if len(examples) >= 3:
                break
            examples.append(post)
        if len(examples) >= 3:
            break

    examples_html = ""
    if examples:
        items_html = ""
        for post in examples:
            raw = post.get("text", "")
            snippet = raw[:80] + ("..." if len(raw) > 80 else "")
            items_html += (
                f'<p style="margin:0 0 3px;font-size:11px;color:#6b7280;">'
                f'<strong>{_esc(post["author"])}</strong> ({_esc(post["score"])}): '
                f'&ldquo;{_esc(snippet)}&rdquo;</p>'
            )
        examples_html = (
            '<p style="margin:8px 0 4px;font-size:11px;font-weight:700;color:#374151;">'
            'Examples:</p>'
            + items_html
        )

    return f"""
  <!-- ── Rejected Summary ── -->
  <tr><td style="background:#ffffff;border-left:1px solid #e0e6ed;
                 border-right:1px solid #e0e6ed;padding:0 22px;">
    <hr style="border:none;border-top:1px solid #e8edf2;margin:0;">
  </td></tr>
  <tr><td style="background:#f8fafc;border-left:1px solid #e0e6ed;
                 border-right:1px solid #e0e6ed;padding:12px 22px 14px;">
    <p style="margin:0 0 4px;font-size:12px;font-weight:700;color:#6b7280;">
      Rejected Posts &mdash; {total} not selected
    </p>
    <p style="margin:0 0 6px;font-size:11px;color:#9ca3af;">{breakdown_html}</p>
    {examples_html}
  </td></tr>"""


def _html_original_posts(posts_schedule, mode="Mock"):
    lh = "font-size:11px;line-height:1.4;"
    parts = []
    for role in ("founder", "product"):
        data = posts_schedule[role]
        handle = _esc(data["handle"])
        if data["needed"]:
            post = data["post"]
            fmt_obj = post.get("format") or {}
            fmt_label = _esc(_FORMAT_LABEL_MAP.get(fmt_obj.get("type", ""), fmt_obj.get("type", "N/A")))
            fmt_reason = _esc(fmt_obj.get("reason", ""))
            med = _fill_media_fallbacks(post.get("media") or {}, role=role)
            text = post.get("text", "").replace("\n\n", " ").replace("\n", " ")
            check_note = (
                f'<p style="margin:4px 0 0;{lh}color:#92400e;font-style:italic;">'
                f'&#x26A0; Check {handle} manually before posting '
                f'(posting history unavailable in {_esc(mode)} mode).</p>'
                if mode != "Mock" else ""
            )
            media_block = _html_media_block(med)
            why_row = (
                f'<p style="margin:4px 0 0;{lh}color:#555;">Why this format: {fmt_reason}</p>'
                if fmt_reason else ""
            )
            parts.append(
                f'<p style="margin:0 0 5px;font-size:12px;font-weight:700;color:#1a2e4a;">'
                f'{role.title()} ({handle}) &mdash; Recommended today</p>'
                f'<p style="margin:0 0 3px;{lh}font-weight:600;color:#374151;">Recommended format: {fmt_label}</p>'
                f'<p style="margin:0 0 5px;font-size:12px;color:#444;line-height:1.5;'
                f'font-style:italic;">&ldquo;{_esc(text)}&rdquo;</p>'
                + media_block
                + why_row
                + f'<p style="margin:4px 0 0;{lh}color:#555;">Account: {handle}</p>'
                + check_note
                + '<p style="margin:0 0 14px;"></p>'
            )
        else:
            reason = _esc(data.get("reason", "Not scheduled today."))
            idea = data.get("optional_idea")
            block = (
                f'<p style="margin:0 0 3px;font-size:12px;font-weight:600;color:#888;">'
                f'{role.title()} ({handle}) &mdash; Not needed today</p>'
                f'<p style="margin:0 0 6px;font-size:11px;color:#aaa;line-height:1.5;">'
                f'{reason}</p>'
            )
            if idea:
                idea_fmt = idea.get("format") or {}
                idea_label = _esc(_FORMAT_LABEL_MAP.get(idea_fmt.get("type", ""), idea_fmt.get("type", "N/A")))
                idea_med = _fill_media_fallbacks(idea.get("media") or {}, role=role)
                idea_text = idea.get("text", "").replace("\n\n", " ").replace("\n", " ")
                idea_why = _esc(idea_fmt.get("reason", ""))
                _raw_note = idea.get("note", "Optional idea")
                idea_note = _esc(
                    _raw_note if _raw_note.lower().startswith("optional idea")
                    else f"Optional idea — {_raw_note}"
                )
                idea_media_block = _html_media_block(idea_med)
                why_row = (
                    f'<p style="margin:4px 0 0;{lh}color:#555;">Why this format: {idea_why}</p>'
                    if idea_why else ""
                )
                block += (
                    f'<p style="margin:0 0 3px;{lh}font-weight:600;color:#6b7280;">'
                    f'{idea_note}</p>'
                    f'<p style="margin:0 0 3px;{lh}font-weight:600;color:#374151;">Recommended format: {idea_label}</p>'
                    f'<p style="margin:0 0 5px;font-size:12px;color:#444;line-height:1.5;font-style:italic;">'
                    f'&ldquo;{_esc(idea_text)}&rdquo;</p>'
                    + idea_media_block
                    + why_row
                    + f'<p style="margin:4px 0 0;{lh}color:#555;">Account: {handle}</p>'
                )
            block += '<p style="margin:0 0 14px;"></p>'
            parts.append(block)
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
    inspiration_html = _html_inspiration(posts_with_replies)

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
        no_opp_suffix = (
            " Check the Save for Inspiration section below."
            if inspiration_html.strip() else ""
        )
        cards = (
            f'<p style="color:#888;font-size:14px;">'
            f'No suitable reply opportunities found today.{no_opp_suffix}</p>'
        )

    original_posts_html = _html_original_posts(posts_schedule, mode=mode)
    rejected_summary_html = _html_rejected_summary(posts_with_replies)

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

  {inspiration_html}

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

  {rejected_summary_html}

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
            ]
            if _src_label:
                lines.append(f"   [{_src_label}] Check engagement manually before replying.")
            lines.append("")

            if best_style:
                lines.append(f"   Recommended format: {_normalize_format_label(best_style)}")
            if best_text:
                lines += [
                    f"   Recommended copy:",
                    f'   "{best_text}"',
                ]

            media = post.get("media") or {"type": "No media", "reason": "Clean text reply — the point lands without a visual."}
            lines.append(f"   Media/GIF: {media.get('type', 'No media')}")
            if media.get("idea"):
                lines.append(f"   Media idea: {media['idea']}")
            if media.get("use_if"):
                lines.append(f"   Use media if: {media['use_if']}")
            if media.get("skip_if"):
                lines.append(f"   Skip media if: {media['skip_if']}")
            if media.get("reason"):
                lines.append(f"   Reason: {media['reason']}")

            if best_style:
                lines.append(f"   Why this format: {_format_reason_for(best_style)}")
            lines.append(f"   Account: {_display_account(post.get('reply_account', ''))}")
            note = _manual_review_note(post)
            if note:
                lines.append(f"   Manual review note: {note}")

            if other_replies:
                lines += ["", "   Other options:"]
                for reply in other_replies:
                    lines += [
                        f"   {reply.get('style', '')}:",
                        f'   "{reply.get("text", "")}"',
                        "",
                    ]

            lines += [
                "",
                f"   Open post:    {post_url}",
                f"   View profile: {profile_url}",
                "",
            ]

    inspiration = [
        p for p in posts_with_replies
        if p["score"] in ("Strong fit", "Decent fit")
        and p.get("metrics_confidence") == "low"
        and p.get("freshness_tier") == "old"
        and p.get("inspiration_angles")
    ]
    if inspiration:
        lines += [
            "-" * 52,
            "",
            "SAVE FOR INSPIRATION",
            "Good fit but outside reply window. Use as ideas for original posts — do not reply.",
            "",
        ]
        for post in inspiration:
            lines.append(f"{post['author']} — {post['score']}")
            lines.append(f'"{post["text"][:120]}{"..." if len(post["text"]) > 120 else ""}"')
            for angle in (post.get("inspiration_angles") or []):
                lines.append(f"  • {angle}")
            post_url = post.get("post_url", "")
            if post_url:
                lines.append(f"  {post_url}")
            lines.append("")

    lines += [
        "-" * 52,
        "",
        "ORIGINAL POSTS",
    ]

    for role in ("founder", "product"):
        data = posts_schedule[role]
        handle = data["handle"]
        if data["needed"]:
            post = data["post"]
            fmt_obj = post.get("format") or {}
            fmt_label = _FORMAT_LABEL_MAP.get(fmt_obj.get("type", ""), fmt_obj.get("type", "N/A"))
            fmt_reason = fmt_obj.get("reason", "")
            med = _fill_media_fallbacks(post.get("media") or {}, role=role)
            lines.append(f"{role.title()} ({handle}): Recommended today")
            lines.append(f"  Recommended format: {fmt_label}")
            lines.append(f'  "{post["text"]}"')
            lines.append(f"  Media/GIF: {med.get('type', 'No media')}")
            if med.get("idea"):
                lines.append(f"  Media idea: {med['idea']}")
            if med.get("use_if"):
                lines.append(f"  Use media if: {med['use_if']}")
            if med.get("skip_if"):
                lines.append(f"  Skip media if: {med['skip_if']}")
            if med.get("reason"):
                lines.append(f"  Reason: {med['reason']}")
            if fmt_reason:
                lines.append(f"  Why this format: {fmt_reason}")
            lines.append(f"  Account: {handle}")
            if mode != "Mock":
                lines.append(
                    f"  Manual review note: Check {handle} manually before posting "
                    f"(posting history unavailable in {mode} mode)."
                )
        else:
            lines.append(f"{role.title()} ({handle}): Not needed today")

    cats = _categorize_rejected(posts_with_replies)
    total_rejected = sum(len(v) for v in cats.values())
    if total_rejected > 0:
        breakdown = []
        if cats["stale"]:
            breakdown.append(f"Stale (>7d): {len(cats['stale'])}")
        if cats["out_of_scope"]:
            breakdown.append(f"Out of scope: {len(cats['out_of_scope'])}")
        if cats["avoid"]:
            breakdown.append(f"Avoid: {len(cats['avoid'])}")
        if cats["weak"]:
            breakdown.append(f"Weak fit: {len(cats['weak'])}")
        if cats["other"]:
            breakdown.append(f"Other: {len(cats['other'])}")
        lines += [
            "",
            "-" * 52,
            "",
            f"REJECTED POSTS — {total_rejected} not selected",
            " · ".join(breakdown),
        ]

    footer = (
        "Full detailed digest (all posts, all reply options) available in the GitHub Actions artifact."
        if mode == "Mock"
        else "Full digest with all scoring details saved locally."
    )
    lines += ["", footer]

    return "\n".join(lines)
