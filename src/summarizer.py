"""Claude CLI summarization for tech news articles."""

import logging
import subprocess
import time

logger = logging.getLogger("digest_bot")

import shutil

_claude_path = shutil.which("claude") or "/home/sijun/.local/bin/claude"

CLAUDE_COMMAND = [
    _claude_path,
    "-p",
    "--model",
    "sonnet",
    "--fallback-model",
    "haiku",
    "--no-session-persistence",
    "--allowedTools",
    "WebFetch",
]

MAX_CONTENT_LENGTH = 10_000
RETRY_DELAYS = (2, 4, 8)

PROMPT_TEMPLATE = (
    "Summarise the following tech news in British English (5-7 sentences).\n"
    "If the provided content is sparse, visit the URL to read the full article.\n"
    "Include:\n"
    "1. Key insights for software developers\n"
    "2. Actionable recommendations\n"
    "3. For difficult vocabulary, add footnotes with definitions\n"
    "\n"
    "Format:\n"
    "## Summary\n"
    "[summary text]\n"
    "\n"
    "## Insights\n"
    "- [insight 1]\n"
    "- [insight 2]\n"
    "\n"
    "## Action Items\n"
    "- [action 1]\n"
    "- [action 2]\n"
    "\n"
    "## Vocabulary\n"
    "- [word]: [definition]\n"
    "\n"
    "Article:\n"
    "Title: {title}\n"
    "URL: {url}\n"
    "Content: {content}\n"
)


def summarize_article(article: dict) -> str:
    """Summarise a tech news article using the Claude CLI."""
    article_data = article or {}

    title = article_data.get("title") or ""
    url = article_data.get("url") or ""
    content = (article_data.get("content") or "")[:MAX_CONTENT_LENGTH]

    prompt = PROMPT_TEMPLATE.format(title=title, url=url, content=content)

    for attempt in range(len(RETRY_DELAYS) + 1):
        try:
            result = subprocess.run(
                CLAUDE_COMMAND,
                input=prompt,
                text=True,
                capture_output=True,
                check=False,
                timeout=120,
            )
            output = result.stdout.strip()
            if result.returncode == 0 and output:
                return output

            if result.returncode != 0:
                stderr = result.stderr.strip() or "no error output"
                logger.warning(
                    "Claude CLI failed (attempt %s/%s) with code %s: %s",
                    attempt + 1,
                    len(RETRY_DELAYS) + 1,
                    result.returncode,
                    stderr,
                )
            else:
                logger.warning(
                    "Claude CLI returned empty output (attempt %s/%s).",
                    attempt + 1,
                    len(RETRY_DELAYS) + 1,
                )
        except Exception as exc:
            logger.warning(
                "Claude CLI call failed (attempt %s/%s): %s",
                attempt + 1,
                len(RETRY_DELAYS) + 1,
                exc,
            )

        if attempt < len(RETRY_DELAYS):
            time.sleep(RETRY_DELAYS[attempt])

    return ""
