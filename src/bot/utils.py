"""Utility functions for Telegram bot."""


def split_message(text: str, max_len: int = 4000) -> list[str]:
    """Split text into chunks respecting paragraph boundaries.

    Priority: paragraph breaks > newlines > spaces > hard split.
    """
    if not text:
        return []

    if len(text) <= max_len:
        return [text]

    chunks: list[str] = []
    remaining = text

    while remaining:
        if len(remaining) <= max_len:
            chunks.append(remaining)
            break

        chunk = remaining[:max_len]

        para_break = chunk.rfind("\n\n")
        if para_break > 0:
            chunks.append(remaining[:para_break])
            remaining = remaining[para_break + 2 :]
            continue

        newline_break = chunk.rfind("\n")
        if newline_break > 0:
            chunks.append(remaining[:newline_break])
            remaining = remaining[newline_break + 1 :]
            continue

        space_break = chunk.rfind(" ")
        if space_break > 0:
            chunks.append(remaining[:space_break])
            remaining = remaining[space_break + 1 :]
            continue

        chunks.append(remaining[:max_len])
        remaining = remaining[max_len:]

    return chunks
