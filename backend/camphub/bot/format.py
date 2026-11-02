"""
Card + strip message design for the Telegram bot.

Delete this module and revert handlers to plain text if the trial look
doesn't stick. All display helpers live here so the visual language is
one place to change or remove.
"""

DIVIDER = "━━━━━━━━━━━━━━━━"


def esc(text) -> str:
    """Escape HTML special chars for Telegram parse_mode=HTML."""
    if text is None:
        return ""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def header(emoji: str, title: str, *meta_lines: str) -> str:
    """
    Standard screen header.

    📚 <b>Today's Lessons</b>
    🎓 Senior · CS · Wednesday
    """
    parts = [f"{emoji} <b>{esc(title)}</b>"]
    for line in meta_lines:
        if line:
            parts.append(esc(line))
    return "\n".join(parts)


def info_card(lead: str, title: str = "", *detail_lines: str, status: str = None) -> str:
    """
    Card whose lead line is plain text (no clock), e.g. contacts / settings.

    ━━━━━━━━━━━━━━━━
    👤 <b>Name</b>
       🪪 Role
       📱 phone
    """
    lines = [DIVIDER]
    if title:
        lines.append(esc(lead))
        lines.append(f"   <b>{esc(title)}</b>")
    else:
        lines.append(f"<b>{esc(lead)}</b>")
    for detail in detail_lines:
        if detail:
            lines.append(f"   {esc(detail)}")
    if status:
        lines.append(f"   {esc(status)}")
    return "\n".join(lines)


def card(time_str: str, title: str, *detail_lines: str, status: str = None) -> str:
    """
    One item card. Status (e.g. reminder) only shown when provided.

    ━━━━━━━━━━━━━━━━
    🕘 <b>09:00–10:30</b>
       Physics 1
       👤 Name · 🚪 206
       ⏰ 15 min before
    """
    lines = [DIVIDER, time_heading(time_str)]
    if title:
        lines.append(f"   <b>{esc(title)}</b>")
    for detail in detail_lines:
        if detail:
            lines.append(f"   {esc(detail)}")
    if status:
        lines.append(f"   {esc(status)}")
    return "\n".join(lines)


def section(emoji: str, title: str) -> str:
    """Inline section label inside a multi-part screen (e.g. My Day)."""
    return f"{emoji} <b>{esc(title)}</b>"


def empty(message: str) -> str:
    """Friendly empty state — one line, no fake card."""
    return f"<i>{esc(message)}</i>"


def compose(header_text: str, *body_parts: str, footer: str = None) -> str:
    """Join header + cards/sections into one HTML message."""
    chunks = [header_text]
    for part in body_parts:
        if part:
            chunks.append(part)
    if footer:
        chunks.append(footer)
    # Trailing divider under the last card looks finished
    text = "\n".join(chunks)
    if body_parts and any(DIVIDER in (p or "") for p in body_parts):
        text += f"\n{DIVIDER}"
    return text


def major_label(major: str) -> str:
    if major == "CS":
        return "Computer Science (CS)"
    if major == "CM":
        return "Communications & Media (CM)"
    return major or "Not set"


def profile_meta(user) -> str:
    """Compact 'Senior · CS' or 'Freshman · CS · CS A · Direct' line."""
    level = getattr(user, "academic_level", None) or "Level?"
    major = getattr(user, "major", None) or "?"
    parts = [f"🎓 {level}", str(major)]
    if level == "Freshman" and major == "CS":
        from .crud import CS_GROUP_LABELS, CS_TRACK_LABELS
        group = CS_GROUP_LABELS.get(getattr(user, "cs_group", None))
        track = CS_TRACK_LABELS.get(getattr(user, "cs_track", None))
        if group:
            parts.append(group)
        if track:
            parts.append(track)
    return " · ".join(parts)


def clock_emoji(time_str: str) -> str:
    """Pick a rough clock emoji from HH:MM (best-effort)."""
    try:
        hour = int(str(time_str).split(":")[0].split("-")[0].strip())
    except (ValueError, IndexError):
        return "🕘"
    # Map to nearest common clock face emoji (Telegram supports these)
    mapping = {
        0: "🕛", 1: "🕐", 2: "🕑", 3: "🕒", 4: "🕓", 5: "🕔",
        6: "🕕", 7: "🕖", 8: "🕗", 9: "🕘", 10: "🕙", 11: "🕚",
        12: "🕛", 13: "🕐", 14: "🕑", 15: "🕒", 16: "🕓", 17: "🕔",
        18: "🕕", 19: "🕖", 20: "🕗", 21: "🕘", 22: "🕙", 23: "🕚",
    }
    return mapping.get(hour % 24, "🕘")


def time_heading(time_str: str) -> str:
    """'🕘 <b>09:00 - 10:30</b>' from a time range string."""
    cleaned = (time_str or "").replace("–", "-").replace("—", "-").strip()
    start = cleaned.split("-")[0].strip() if cleaned else ""
    return f"{clock_emoji(start)} <b>{esc(cleaned)}</b>"


def menu(emoji: str, title: str, hint: str = "Choose an option below:") -> str:
    """Top-level submenu intro shown above an inline keyboard."""
    return header(emoji, title, hint)


def day_label(day: str) -> str:
    """Pinned day heading inside a weekly list."""
    return f"\n📌 <b>{esc(day)}</b>"
