"""Fetchers module for news sources."""

from src.fetchers.base_fetcher import BaseFetcher, FetchError
from src.fetchers.geeknews_fetcher import GeekNewsFetcher
from src.fetchers.github_fetcher import GitHubFetcher
from src.fetchers.hn_fetcher import HNFetcher
from src.fetchers.producthunt_fetcher import ProductHuntFetcher

__all__ = [
    "BaseFetcher",
    "FetchError",
    "HNFetcher",
    "GeekNewsFetcher",
    "GitHubFetcher",
    "ProductHuntFetcher",
]
