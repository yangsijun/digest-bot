"""Product Hunt fetcher using GraphQL API with OAuth2 authentication."""

import logging
from typing import Dict, List, Optional

import aiohttp

from src.auth.producthunt import get_access_token
from src.fetchers.base_fetcher import BaseFetcher, FetchError

logger = logging.getLogger("digest_bot")

PRODUCTHUNT_GRAPHQL_URL = "https://api.producthunt.com/v2/api/graphql"

POSTS_QUERY = """
query GetPosts($first: Int!) {
    posts(first: $first, order: VOTES) {
        edges {
            node {
                name
                tagline
                url
                votesCount
            }
        }
    }
}
"""


class ProductHuntFetcher(BaseFetcher):
    """Fetches top posts from Product Hunt using GraphQL API."""

    @property
    def source_name(self) -> str:
        return "producthunt"

    async def fetch(self, limit: int = 10) -> List[Dict]:
        """Fetch top posts from Product Hunt."""
        token = await get_access_token()
        if not token:
            raise FetchError(
                "Failed to get access token. Check PRODUCTHUNT_CLIENT_ID and PRODUCTHUNT_CLIENT_SECRET.",
                self.source_name,
            )

        try:
            data = await self._execute_graphql(token, limit)
            return self._parse_posts(data)
        except FetchError:
            raise
        except Exception as e:
            logger.error(f"[{self.source_name}] Unexpected error: {e}")
            raise FetchError(f"Unexpected error: {e}", self.source_name, e)

    async def _execute_graphql(self, token: str, limit: int) -> Dict:
        """Execute GraphQL query with authentication."""
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        payload = {
            "query": POSTS_QUERY,
            "variables": {"first": limit},
        }

        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            response = await self._request_with_retry(
                session, "POST", PRODUCTHUNT_GRAPHQL_URL, json=payload, headers=headers
            )
            async with response:
                data = await response.json()

        if "errors" in data:
            error_msg = data["errors"][0].get("message", "Unknown GraphQL error")
            raise FetchError(f"GraphQL error: {error_msg}", self.source_name)

        return data

    def _parse_posts(self, data: Dict) -> List[Dict]:
        """Parse GraphQL response into standard format."""
        items = []

        posts_data = data.get("data", {}).get("posts", {})
        edges = posts_data.get("edges", [])

        for edge in edges:
            node = edge.get("node", {})
            item = self._parse_post(node)
            if item:
                items.append(item)

        logger.info(f"[{self.source_name}] Fetched {len(items)} items")
        return items

    def _parse_post(self, node: Dict) -> Optional[Dict]:
        """Parse a single post node."""
        name = node.get("name", "")
        url = node.get("url", "")

        if not name or not url:
            return None

        tagline = node.get("tagline", "")
        votes = node.get("votesCount", 0)

        content_parts = []
        if tagline:
            content_parts.append(tagline)
        if votes:
            content_parts.append(f"Votes: {votes}")

        return self._create_item(
            url=url,
            title=name,
            content=" | ".join(content_parts) if content_parts else None,
        )
