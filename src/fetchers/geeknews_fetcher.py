"""GeekNews (news.hada.io) fetcher using RSS feed."""

import logging
from typing import Dict, List

import feedparser

from src.fetchers.base_fetcher import BaseFetcher, FetchError

logger = logging.getLogger("digest_bot")

GEEKNEWS_RSS_URL = "https://news.hada.io/rss/news"


class GeekNewsFetcher(BaseFetcher):
    """Fetches news from GeekNews (news.hada.io) via RSS feed."""

    @property
    def source_name(self) -> str:
        return "geeknews"

    async def fetch(self, limit: int = 10) -> List[Dict]:
        """Fetch news items from GeekNews RSS feed."""
        try:
            rss_content = await self._get_text(GEEKNEWS_RSS_URL)
            feed = feedparser.parse(rss_content)

            if feed.bozo and not feed.entries:
                raise FetchError(
                    f"RSS parse error: {feed.bozo_exception}",
                    self.source_name,
                    feed.bozo_exception if hasattr(feed, "bozo_exception") else None,
                )

            items = []
            for entry in feed.entries[:limit]:
                item = self._parse_entry(entry)
                if item:
                    items.append(item)

            logger.info(f"[{self.source_name}] Fetched {len(items)} items")
            return items

        except FetchError:
            raise
        except Exception as e:
            logger.error(f"[{self.source_name}] Unexpected error: {e}")
            raise FetchError(f"Unexpected error: {e}", self.source_name, e)

    def _parse_entry(self, entry) -> Dict:
        """Parse a single RSS entry into standard format."""
        url = entry.get("link", "")
        title = entry.get("title", "")
        content = entry.get("summary") or entry.get("description")

        return self._create_item(url=url, title=title, content=content)
