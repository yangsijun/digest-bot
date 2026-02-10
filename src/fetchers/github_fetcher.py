"""GitHub Trending fetcher using OSS Insight API with scraping fallback."""

import logging
from typing import Dict, List

from bs4 import BeautifulSoup

from src.fetchers.base_fetcher import BaseFetcher, FetchError

logger = logging.getLogger("digest_bot")

OSSINSIGHT_API_URL = "https://api.ossinsight.io/v1/trends/repos"
GITHUB_TRENDING_URL = "https://github.com/trending"


class GitHubFetcher(BaseFetcher):
    """Fetches trending repositories from GitHub."""

    @property
    def source_name(self) -> str:
        return "github"

    async def fetch(self, limit: int = 10) -> List[Dict]:
        try:
            return await self._fetch_from_api(limit)
        except (FetchError, Exception) as e:
            logger.warning(f"[{self.source_name}] API failed, trying scraping: {e}")
            return await self._fetch_from_scraping(limit)

    async def _fetch_from_api(self, limit: int) -> List[Dict]:
        url = f"{OSSINSIGHT_API_URL}?period=past_week&language=All"

        data = await self._get_json(url)

        rows = data.get("data", {}).get("rows", [])
        if not rows:
            raise FetchError("API returned no rows", self.source_name)

        items = []
        for repo in rows[:limit]:
            item = self._parse_api_repo(repo)
            if item:
                items.append(item)

        logger.info(
            f"[{self.source_name}] Fetched {len(items)} items from OSS Insight API"
        )
        return items

    def _parse_api_repo(self, repo: Dict) -> Dict:
        repo_name = repo.get("repo_name", "")
        description = repo.get("description", "")
        language = repo.get("primary_language", "")
        stars = repo.get("stars", "0")
        url = f"https://github.com/{repo_name}"

        content_parts = []
        if description:
            content_parts.append(description)
        if language:
            content_parts.append(f"Language: {language}")
        if stars and str(stars) != "0":
            content_parts.append(f"Stars: {stars}")

        return self._create_item(
            url=url,
            title=repo_name,
            content=" | ".join(content_parts) if content_parts else None,
        )

    async def _fetch_from_scraping(self, limit: int) -> List[Dict]:
        """Fallback: scrape GitHub trending page."""
        html = await self._get_text(GITHUB_TRENDING_URL)
        soup = BeautifulSoup(html, "html.parser")

        items = []
        repo_rows = soup.select("article.Box-row")

        for row in repo_rows[:limit]:
            item = self._parse_scraped_repo(row)
            if item:
                items.append(item)

        logger.info(f"[{self.source_name}] Fetched {len(items)} items from scraping")
        return items

    def _parse_scraped_repo(self, row) -> Dict:
        """Parse repository data from scraped HTML."""
        title_link = row.select_one("h2 a")
        if not title_link:
            return None

        href = title_link.get("href", "").strip()
        repo_name = href.lstrip("/")
        url = f"https://github.com{href}"

        description_elem = row.select_one("p")
        description = description_elem.get_text(strip=True) if description_elem else ""

        language_elem = row.select_one("[itemprop='programmingLanguage']")
        language = language_elem.get_text(strip=True) if language_elem else ""

        stars_elem = row.select_one("a[href$='/stargazers']")
        stars = stars_elem.get_text(strip=True) if stars_elem else ""

        content_parts = []
        if description:
            content_parts.append(description)
        if language:
            content_parts.append(f"Language: {language}")
        if stars:
            content_parts.append(f"Stars: {stars}")

        return self._create_item(
            url=url,
            title=repo_name,
            content=" | ".join(content_parts) if content_parts else None,
        )
