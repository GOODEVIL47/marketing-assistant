import os
from datetime import date

from src.replier import (
    _detect_reply_theme,
    _INSPIRATION_ANGLES,
    _INSPIRATION_FORMAT_HINTS,
    _has_market_signal,
)

_SCORE_ORDER = ["Strong fit", "Decent fit", "Weak fit", "Avoid"]
_OPP_ORDER = ["High opportunity", "Medium opportunity", "Low opportunity", "Poor opportunity"]

_NEWS_ORG_PATTERNS = frozenset([
    "news", "finance", "marketwatch", "yahoofinance", "benzinga", "kitco",
    "bloomberg", "cnbc", "reuters", "wsj", "economist", "seekingalpha",
    "thestreet", "zerohedge", "barrons", "investopedia", "motleyfool",
])

_LOW_QUALITY_TEXT_SIGNALS = frozenset([
    "read more", "read the full", "newsletter", "webinar", "join our",
    "click here", "subscribe", "follow for",
])


def _source_quality_score(post):
    """Lower score = higher quality (human post). Higher = news/promo account."""
    score = 0
    author = (post.get("author") or "").lower().lstrip("@")
    text = (post.get("text") or "").lower()
    if any(p in author for p in _NEWS_ORG_PATTERNS):
        score += 3
    if "http" in text:
        score += 1
    if any(s in text for s in _LOW_QUALITY_TEXT_SIGNALS):
        score += 2
    return score


def _fit_emoji(score):
    return {"Strong fit": "✅", "Decent fit": "🟡", "Weak fit": "🔸", "Avoid": "🚫"}.get(score, "❓")


def _opp_emoji(opp):
    return {
        "High opportunity": "🎯",
        "Medium opportunity": "⚡",
        "Low opportunity": "⏳",
        "Poor opportunity": "❌",
    }.get(opp, "")


def _render_media_block(media, lines):
    """Append compact media guidance lines to an existing list."""
    if not media:
        return
    media_type = media.get("type", "No media")
    lines.append(f"**Media/GIF:** {media_type}")
    if media.get("idea"):
        lines.append(f"**Media idea:** {media['idea']}")
    if media.get("use_if"):
        lines.append(f"**Use media if:** {media['use_if']}")
    if media.get("skip_if"):
        lines.append(f"**Skip media if:** {media['skip_if']}")
    if media.get("reason"):
        lines.append(f"**Reason:** *{media['reason']}*")


# ── M4.19 output contract helpers ──────────────────────────────────────────

_REPLY_DEFAULT_MEDIA = {
    "type": "No media",
    "reason": "Clean text reply — the point lands without a visual.",
}

_FOUNDER_DEFAULT_MEDIA = {
    "type": "No media",
    "reason": "Let the words do the work.",
}

_PRODUCT_DEFAULT_MEDIA = {
    "type": "Simple branded image",
    "idea": "clean Signal Shift text card or plain-English brief mockup",
    "use_if": "you want more feed presence without adding hype",
    "skip_if": "the copy is strong enough as text or the visual would feel salesy",
    "reason": "Product posts usually work best with clean branded visuals, not meme GIFs.",
}

_MEDIA_FALLBACKS = {
    "No media": {
        "reason": "Clean text post — the copy works without a visual.",
    },
    "Optional GIF": {
        "idea": "calm/analytical moment — chart, notebook, or focused work",
        "use_if": "the copy has a casual or self-aware tone",
        "skip_if": "the post is analytical or the copy already lands as text",
    },
    "Simple branded image": {
        "idea": "plain-text card with the key line from the post",
        "use_if": "you want more feed presence without adding hype",
        "skip_if": "the copy is strong enough as text or the visual would feel salesy",
    },
    "Screenshot-style graphic": {
        "idea": "screenshot-style text card with the key stat or quote",
        "use_if": "the data point or quote is visually striking",
        "skip_if": "the raw text is clear enough on its own",
    },
    "Text card": {
        "idea": "clean text card — white background, brand font, key line only",
        "use_if": "you want the key point to stand alone visually",
        "skip_if": "the thread text is self-sufficient",
    },
    "Simple text card": {
        "idea": "clean text card with the key line in large, readable type",
        "use_if": "you want the key point to stand alone visually",
        "skip_if": "the thread text is self-sufficient",
    },
    "Product mockup": {
        "idea": "brief mockup or interface screenshot showing the relevant feature",
        "use_if": "the post ties directly to a Signal Shift feature or workflow",
        "skip_if": "the context is conceptual and product placement would feel forced",
    },
}

_FORMAT_LABEL_MAP = {
    "Short and clean": "One-liner",
    "One-liner": "One-liner",
    "Casual paragraph": "Short paragraph",
    "Short paragraph": "Short paragraph",
    "Agreement + reframe": "Short paragraph",
    "Question": "Question",
    "Question/reframe": "Question",
    "Sharper take": "Sharper take",
    "Key point": "Short paragraph",
    "Context-aware": "Context-aware paragraph",
    "2-3 line structure": "Three-liner",
    "Three-liner": "Three-liner",
    "Mini-thread": "Mini-thread",
    "Short paragraph — sharper take": "Sharper take",
}

_FORMAT_REASONS = {
    "One-liner": "Short and punchy — lands the point in one sentence without adding noise.",
    "Short paragraph": "Conversational — shows the reasoning without lecturing; sounds like a founder, not an analyst.",
    "Sharper take": "Direct reframe — redirects reactive thinking toward a clear decision question.",
    "Question": "Invites reflection — asks rather than tells; lets the reader connect the dots.",
    "Three-liner": "Structured turn — sets the tension, shifts the frame, lands the takeaway.",
    "Mini-thread": "Multi-part — for when the point needs space across a few connected steps.",
    "Context-aware paragraph": "Tied directly to the specific ticker or driver — maximally relevant to this post.",
}


def _normalize_format_label(style_name):
    """Strip letter prefix (e.g. 'B — ') and map to a clean display label."""
    key = style_name.split(" — ", 1)[-1] if " — " in style_name else style_name
    return _FORMAT_LABEL_MAP.get(key, key)


def _format_reason_for(style_name):
    label = _normalize_format_label(style_name)
    return _FORMAT_REASONS.get(label, label)


def _manual_review_note(post):
    if post.get("discovery_source") == "tavily_search":
        return "Tavily search result — verify post is live and engagement is real before replying."
    return ""


def _fill_media_fallbacks(med, role=None):
    """Return med with missing fields filled from _MEDIA_FALLBACKS.
    If med is empty/None, returns a role-appropriate default so the media block is never blank.
    role: 'founder' or 'product' (lowercase); used only when med is empty.
    """
    if not med:
        return _PRODUCT_DEFAULT_MEDIA if (role or "").lower() == "product" else _FOUNDER_DEFAULT_MEDIA
    media_type = med.get("type", "No media")
    fallback = _MEDIA_FALLBACKS.get(media_type, {})
    result = dict(med)
    for key, val in fallback.items():
        if not result.get(key):
            result[key] = val
    return result


def _build_best_3(posts_with_replies, has_inspiration=False, worth_checking_count=0):
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

    if any(p.get("discovery_source") == "tavily_search" for p in posts_with_replies):
        lines.append(
            "*Tavily web-search mode — verify post text and engagement on X before replying.*"
        )
        lines.append("")

    if not top3:
        parts = ["No strong reply opportunities today."]
        if worth_checking_count > 0:
            noun = "post" if worth_checking_count == 1 else "posts"
            parts.append(f"{worth_checking_count} borderline {noun} worth checking manually below.")
        if has_inspiration:
            parts.append("Inspiration ideas below.")
        lines.append(f"*{' '.join(parts)}*")
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
        best_style = best.get("style", "")
        best_text = best.get("text", "")
        media = post.get("media") or _REPLY_DEFAULT_MEDIA
        replies = post.get("replies") or []

        lines.append(f"**{i}. {post['author']}**")
        lines.append(
            f"Fit: {post['score']} {fit_e} · "
            f"Visibility: {post['visibility']} · "
            f"Opportunity: {post['opportunity']} {opp_e}"
        )
        lines.append(f"Engagement: {post['engagement_summary']}")
        if post.get("age_label"):
            lines.append(post["age_label"])
        if post.get("post_url"):
            lines.append(post["post_url"])
        lines.append("")

        if best_style:
            lines.append(f"**Recommended format:** {_normalize_format_label(best_style)}")
        if best_text:
            lines.append("**Recommended copy:**")
            lines.append(f"> {best_text}")
            lines.append("")

        _render_media_block(media, lines)
        lines.append("")

        if best_style:
            lines.append(f"**Why this format:** {_format_reason_for(best_style)}")
        lines.append(f"**Account:** {post['reply_account']}")
        note = _manual_review_note(post)
        if note:
            lines.append(f"**Manual review note:** {note}")
        lines.append("")

        other_replies = [r for r in replies if r.get("style") != best_style]
        if not best_style and replies:
            other_replies = replies
        if other_replies:
            lines.append("**Other options:**")
            lines.append("")
            for reply in other_replies:
                lines.append(f"**{reply['style']}**")
                lines.append(f"> {reply['text']}")
                lines.append("")

    return lines


def _build_inspiration(posts_with_replies):
    """
    Posts that are too old for replies but have good fit — worth keeping as
    content inspiration for original posts.
    Sorted by source quality (human posts first). Max 3 shown; angles de-duped
    across posts to avoid repetition.
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

    inspiration = sorted(inspiration, key=_source_quality_score)
    total = len(inspiration)
    shown = inspiration[:3]
    hidden = total - len(shown)

    lines = ["## Save for Inspiration", ""]
    lines.append(
        "These posts have good fit but are outside the reply window. "
        "Use them as inspiration for original posts — do not reply."
    )
    lines.append("")

    used_angles: set = set()
    for post in shown:
        lines.append(f"- **{post['author']}** · {post['score']} · {post.get('age_label', '')}")
        lines.append(f"  > {post['text'][:120]}{'...' if len(post['text']) > 120 else ''}")
        if post.get("post_url"):
            lines.append(f"  {post['post_url']}")

        theme = _detect_reply_theme(post)
        if theme is None:
            theme = "generic_strong" if post["score"] == "Strong fit" else "generic_decent"
        all_pool = _INSPIRATION_ANGLES.get(theme, [])
        unique_angles = [a for a in all_pool if a not in used_angles][:2]
        if not unique_angles and all_pool:
            unique_angles = all_pool[:1]
        used_angles.update(unique_angles)

        if unique_angles:
            fmt_hint = _INSPIRATION_FORMAT_HINTS.get(theme, "short paragraph")
            lines.append("  **Inspiration angles:**")
            for angle in unique_angles:
                lines.append(f"  - {angle}")
            lines.append(f"  *Format: {fmt_hint}*")
        lines.append("")

    if hidden > 0:
        lines.append(
            f"*+ {hidden} more inspiration item{'s' if hidden != 1 else ''} hidden. "
            "Use DIGEST_DEBUG=true for full detail.*"
        )
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
            fmt = post.get("format") or {}
            med = _fill_media_fallbacks(post.get("media") or {}, role=role.lower())
            fmt_type = _FORMAT_LABEL_MAP.get(fmt.get("type", ""), fmt.get("type", "N/A"))
            fmt_reason = fmt.get("reason", "")
            lines.append(f"**Recommended format:** {fmt_type}")
            lines.append("")
            lines.append("**Recommended copy:**")
            lines.append(f"> {post['text']}")
            lines.append("")
            _render_media_block(med, lines)
            lines.append("")
            if fmt_reason:
                lines.append(f"**Why this format:** {fmt_reason}")
            lines.append(f"**Account:** {handle}")
            if mode != "Mock":
                lines.append(
                    f"**Manual review note:** Check {handle} manually before posting "
                    f"(posting history unavailable in {mode} mode)."
                )
        else:
            lines.append("No original post needed today.")
            lines.append("")
            idea = data.get("optional_idea")
            if idea:
                fmt = idea.get("format") or {}
                med = _fill_media_fallbacks(idea.get("media") or {}, role=role.lower())
                fmt_type = _FORMAT_LABEL_MAP.get(fmt.get("type", ""), fmt.get("type", "N/A"))
                fmt_reason = fmt.get("reason", "")
                lines.append(f"**Optional idea ({idea['note']}):**")
                lines.append("")
                lines.append(f"**Recommended format:** {fmt_type}")
                lines.append("")
                lines.append("**Recommended copy:**")
                lines.append(f"> {idea['text']}")
                lines.append("")
                _render_media_block(med, lines)
                lines.append("")
                if fmt_reason:
                    lines.append(f"**Why this format:** {fmt_reason}")
                lines.append(f"**Account:** {handle}")

        lines.append("")

    return lines


def _get_worth_checking_posts(posts_with_replies):
    """
    Fresh/borderline web-search posts with Decent/Strong fit and Low opportunity
    that missed Best 3 due to unknown engagement. Surfaces them for manual review.
    Excludes: Weak/Avoid, out-of-scope, stale/old posts, Best 3 posts.
    Returns up to 3.
    """
    eligible = [
        p for p in posts_with_replies
        if p["score"] in ("Strong fit", "Decent fit")
        and p["opportunity"] in ("High opportunity", "Medium opportunity")
    ]
    top3_ids = {
        p["id"]
        for p in sorted(
            eligible,
            key=lambda p: (_SCORE_ORDER.index(p["score"]), _OPP_ORDER.index(p["opportunity"])),
        )[:3]
    }
    candidates = []
    for post in posts_with_replies:
        if post["id"] in top3_ids:
            continue
        if post["score"] not in ("Strong fit", "Decent fit"):
            continue
        if post.get("out_of_scope"):
            continue
        tier = post.get("freshness_tier", "unknown")
        if tier in ("stale", "very_stale", "old"):
            continue
        if post.get("opportunity") != "Low opportunity":
            continue
        if post.get("metrics_confidence") != "low":
            continue
        if not _has_market_signal(post):
            continue
        candidates.append(post)
    return candidates[:3]


def _build_worth_checking(posts_with_replies):
    """Compact section for borderline posts worth opening manually."""
    candidates = _get_worth_checking_posts(posts_with_replies)
    if not candidates:
        return []

    lines = ["## Worth Checking Manually", ""]
    lines.append(
        "*These are not strong enough to recommend outright — "
        "but may be worth opening manually if you have time.*"
    )
    lines.append("")

    for i, post in enumerate(candidates, 1):
        fit_e = _fit_emoji(post["score"])
        age_l = post.get("age_label") or ""
        text = post.get("text", "")
        snippet = text[:120] + ("..." if len(text) > 120 else "")
        best = post.get("best_reply") or {}
        best_style = best.get("style", "")
        best_text = best.get("text", "")
        replies = post.get("replies") or []
        media = post.get("media") or _REPLY_DEFAULT_MEDIA

        lines.append(f"**{i}. {post['author']}**")
        lines.append(f"Fit: {post['score']} {fit_e} · Opportunity: Low opportunity ⏳")
        if age_l:
            lines.append(age_l)
        lines.append(f"Engagement: {post.get('engagement_summary', '')}")
        lines.append(f"*\"{snippet}\"*")
        if post.get("post_url"):
            lines.append(post["post_url"])

        opp_reason = post.get("opportunity_reason", "")
        if opp_reason:
            lines.append(f"**Why:** {opp_reason}")
        lines.append("**Reply if:** engagement looks real when you open it.")
        lines.append("**Skip if:** engagement is dead or the thread has moved on.")
        lines.append("")

        if best_style:
            lines.append(f"**Recommended format:** {_normalize_format_label(best_style)}")
        if best_text:
            lines.append("**Recommended copy:**")
            lines.append(f"> {best_text}")
            lines.append("")

        _render_media_block(media, lines)
        lines.append("")

        if best_style:
            lines.append(f"**Why this format:** {_format_reason_for(best_style)}")
        lines.append(f"**Account:** {post['reply_account']}")
        note = _manual_review_note(post)
        if note:
            lines.append(f"**Manual review note:** {note}")
        lines.append("")

        other_replies = [r for r in replies if r.get("style") != best_style]
        if not best_style and replies:
            other_replies = replies
        if other_replies:
            lines.append("**Other options:**")
            lines.append("")
            for reply in other_replies:
                lines.append(f"**{reply['style']}**")
                lines.append(f"> {reply['text']}")
                lines.append("")

        lines.append("---")
        lines.append("")

    return lines


def _categorize_rejected(posts_with_replies):
    """
    Classify posts not selected for Best 3, Worth Checking, or Inspiration
    into reject categories.
    Returns a dict with keys: stale, out_of_scope, avoid, weak, other.
    """
    eligible = [
        p for p in posts_with_replies
        if p["score"] in ("Strong fit", "Decent fit")
        and p["opportunity"] in ("High opportunity", "Medium opportunity")
    ]
    top3_ids = {
        p["id"]
        for p in sorted(
            eligible,
            key=lambda p: (_SCORE_ORDER.index(p["score"]), _OPP_ORDER.index(p["opportunity"])),
        )[:3]
    }
    inspiration_ids = {
        p["id"] for p in posts_with_replies
        if p["score"] in ("Strong fit", "Decent fit")
        and p.get("metrics_confidence") == "low"
        and p.get("freshness_tier") == "old"
        and p.get("inspiration_angles")
    }
    worth_checking_ids = {p["id"] for p in _get_worth_checking_posts(posts_with_replies)}

    stale, out_of_scope, avoid, weak, other = [], [], [], [], []
    for post in posts_with_replies:
        if post["id"] in top3_ids or post["id"] in inspiration_ids or post["id"] in worth_checking_ids:
            continue
        tier = post.get("freshness_tier", "unknown")
        if tier in ("stale", "very_stale"):
            stale.append(post)
        elif post.get("out_of_scope"):
            out_of_scope.append(post)
        elif post["score"] == "Avoid":
            avoid.append(post)
        elif post["score"] == "Weak fit":
            weak.append(post)
        else:
            other.append(post)

    return {
        "stale": stale,
        "out_of_scope": out_of_scope,
        "avoid": avoid,
        "weak": weak,
        "other": other,
    }


def _build_rejected_summary(posts_with_replies):
    """Compact summary of posts not selected, with category breakdown and 3 examples."""
    cats = _categorize_rejected(posts_with_replies)
    total = sum(len(v) for v in cats.values())
    if total == 0:
        return []

    lines = ["## Rejected Posts Summary", ""]
    lines.append(f"**{total} post{'s' if total != 1 else ''} scanned but not selected for replies.**")
    lines.append("")

    breakdown = []
    if cats["stale"]:
        breakdown.append(f"Stale (>7d old): {len(cats['stale'])}")
    if cats["out_of_scope"]:
        breakdown.append(f"Out of scope (non-US market): {len(cats['out_of_scope'])}")
    if cats["avoid"]:
        breakdown.append(f"Avoid (hype/promo/crypto): {len(cats['avoid'])}")
    if cats["weak"]:
        breakdown.append(f"Weak fit (TA/misaligned): {len(cats['weak'])}")
    if cats["other"]:
        breakdown.append(f"Other (low opportunity): {len(cats['other'])}")
    lines.append(" · ".join(breakdown))
    lines.append("")

    examples = []
    for cat_name in ("avoid", "weak", "stale", "out_of_scope", "other"):
        for post in cats[cat_name]:
            if len(examples) >= 3:
                break
            examples.append(post)
        if len(examples) >= 3:
            break

    if examples:
        lines.append("**Examples:**")
        lines.append("")
        for post in examples:
            raw = post.get("text", "")
            snippet = raw[:80] + ("..." if len(raw) > 80 else "")
            lines.append(f"- {post['author']} ({post['score']}): *\"{snippet}\"*")
        lines.append("")

    return lines


def build_markdown(profile_name, posts_with_replies, posts_schedule, mode="Mock"):
    today = date.today().isoformat()
    debug_mode = os.environ.get("DIGEST_DEBUG", "").lower() == "true"
    lines = []

    lines.append(f"# Mel's Daily Digest — {today}")
    lines.append(f"**Product:** {profile_name}")
    lines.append(f"**Mode:** {mode}")
    lines.append("")
    lines.append("---")
    lines.append("")

    inspiration = _build_inspiration(posts_with_replies)
    wc_count = len(_get_worth_checking_posts(posts_with_replies))
    worth_checking = _build_worth_checking(posts_with_replies)
    lines.extend(_build_best_3(
        posts_with_replies,
        has_inspiration=bool(inspiration),
        worth_checking_count=wc_count,
    ))

    if worth_checking:
        lines.append("---")
        lines.append("")
        lines.extend(worth_checking)

    if inspiration:
        lines.append("---")
        lines.append("")
        lines.extend(inspiration)

    lines.append("---")
    lines.append("")

    if debug_mode:
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
    else:
        rejected_summary = _build_rejected_summary(posts_with_replies)
        if rejected_summary:
            lines.extend(rejected_summary)
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
