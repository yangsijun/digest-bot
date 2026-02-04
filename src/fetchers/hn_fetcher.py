"""Hacker News fetcher using Firebase REST API."""

import asyncio
import logging
from typing import Dict, List, Optional

import aiohttp

from src.fetchers.base_fetcher import BaseFetcher, FetchError

logger = logging.getLogger("digest_bot")

HN_API_BASE = "https://hacker-news.firebaseio.com/v0"
HN_TOP_STORIES_URL = f"{HN_API_BASE}/topstories.json"
HN_ITEM_URL = f"{HN_API_BASE}/item/{{item_id}}.json"


class HNFetcher(BaseFetcher):
    """Fetches top stories from Hacker News using Firebase REST API."""

    @property
    def source_name(self) -> str:
        return "hackernews"

    async def fetch(self, limit: int = 10) -> List[Dict]:
        """Fetch top stories from Hacker News."""
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                story_ids = await self._get_top_story_ids(session, limit)
                stories = await self._fetch_stories(session, story_ids)
                return stories
        except FetchError:
            raise
        except Exception as e:
            logger.error(f"[{self.source_name}] Unexpected error: {e}")
            raise FetchError(f"Unexpected error: {e}", self.source_name, e)

    async def _get_top_story_ids(
        self, session: aiohttp.ClientSession, limit: int
    ) -> List[int]:
        """Fetch list of top story IDs."""
        data = await self._get_json(HN_TOP_STORIES_URL, session)
        return data[:limit]

    async def _fetch_stories(
        self, session: aiohttp.ClientSession, story_ids: List[int]
    ) -> List[Dict]:
        """Fetch story details concurrently with error handling for individual items."""
        tasks = [self._fetch_story(session, story_id) for story_id in story_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        stories = []
        for result in results:
            if isinstance(result, dict):
                stories.append(result)
            elif isinstance(result, Exception):
                logger.warning(
                    f"[{self.source_name}] Failed to fetch a story: {result}"
                )

        return stories

    async def _fetch_story(
        self, session: aiohttp.ClientSession, story_id: int
    ) -> Optional[Dict]:
        """Fetch a single story and convert to standard format."""
        url = HN_ITEM_URL.format(item_id=story_id)
        data = await self._get_json(url, session)

        if not data:
            return None

        title = data.get("title", "")
        story_url = (
            data.get("url") or f"https://news.ycombinator.com/item?id={story_id}"
        )

        return self._create_item(
            url=story_url,
            title=title,
            content=data.get("text"),
        )
