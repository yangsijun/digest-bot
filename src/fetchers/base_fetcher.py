"""Base fetcher abstract class with retry logic and error handling."""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional

import aiohttp

logger = logging.getLogger("digest_bot")

DEFAULT_TIMEOUT = 30
DEFAULT_MAX_RETRIES = 2
DEFAULT_BACKOFF_BASE = 2


class FetchError(Exception):
    """Custom exception for fetch errors."""

    def __init__(
        self, message: str, source: str, original_error: Optional[Exception] = None
    ):
        self.message = message
        self.source = source
        self.original_error = original_error
        super().__init__(f"[{source}] {message}")


class BaseFetcher(ABC):
    """
    Abstract base class for news fetchers.

    Provides common functionality:
    - HTTP requests with aiohttp
    - 30-second timeout
    - Exponential backoff retry (2 attempts)
    - Standardized error handling
    - Logging

    Subclasses must implement:
    - `fetch(limit: int) -> List[Dict]`
    - `source_name` property
    """

    def __init__(
        self,
        timeout: int = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        backoff_base: int = DEFAULT_BACKOFF_BASE,
    ):
        """
        Initialize the fetcher.

        Args:
            timeout: HTTP request timeout in seconds (default: 30)
            max_retries: Maximum number of retry attempts (default: 2)
            backoff_base: Base for exponential backoff in seconds (default: 2)
        """
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.max_retries = max_retries
        self.backoff_base = backoff_base

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Return the name of the data source for logging and tagging."""
        pass

    @abstractmethod
    async def fetch(self, limit: int = 10) -> List[Dict]:
        """
        Fetch news items from the data source.

        Args:
            limit: Maximum number of items to fetch

        Returns:
            List of dicts with keys: url, title, content (optional), source
        """
        pass

    async def _request(
        self,
        method: str,
        url: str,
        session: Optional[aiohttp.ClientSession] = None,
        **kwargs,
    ) -> aiohttp.ClientResponse:
        """
        Make an HTTP request with retry logic.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: Request URL
            session: Optional aiohttp session (creates new one if not provided)
            **kwargs: Additional arguments passed to aiohttp request

        Returns:
            aiohttp.ClientResponse

        Raises:
            FetchError: If all retry attempts fail
        """
        own_session = session is None
        if own_session:
            session = aiohttp.ClientSession(timeout=self.timeout)

        try:
            return await self._request_with_retry(session, method, url, **kwargs)
        finally:
            if own_session:
                await session.close()

    async def _request_with_retry(
        self,
        session: aiohttp.ClientSession,
        method: str,
        url: str,
        **kwargs,
    ) -> aiohttp.ClientResponse:
        """
        Execute request with exponential backoff retry.

        Args:
            session: aiohttp session
            method: HTTP method
            url: Request URL
            **kwargs: Additional request arguments

        Returns:
            aiohttp.ClientResponse

        Raises:
            FetchError: If all retry attempts fail
        """
        last_error = None

        for attempt in range(self.max_retries + 1):
            try:
                if attempt > 0:
                    delay = self.backoff_base**attempt
                    logger.warning(
                        f"[{self.source_name}] Retry attempt {attempt}/{self.max_retries}, "
                        f"waiting {delay}s..."
                    )
                    await asyncio.sleep(delay)

                logger.debug(f"[{self.source_name}] {method} {url}")
                response = await session.request(method, url, **kwargs)

                if response.status >= 400:
                    text = await response.text()
                    raise aiohttp.ClientResponseError(
                        response.request_info,
                        response.history,
                        status=response.status,
                        message=f"HTTP {response.status}: {text[:200]}",
                    )

                return response

            except asyncio.TimeoutError as e:
                last_error = e
                logger.warning(
                    f"[{self.source_name}] Request timeout (attempt {attempt + 1}/{self.max_retries + 1})"
                )

            except aiohttp.ClientError as e:
                last_error = e
                logger.warning(
                    f"[{self.source_name}] Request error (attempt {attempt + 1}/{self.max_retries + 1}): {e}"
                )

        raise FetchError(
            f"Failed after {self.max_retries + 1} attempts",
            self.source_name,
            last_error,
        )

    async def _get_json(
        self,
        url: str,
        session: Optional[aiohttp.ClientSession] = None,
        **kwargs,
    ) -> Dict:
        """
        Make a GET request and return JSON response.

        Args:
            url: Request URL
            session: Optional aiohttp session
            **kwargs: Additional request arguments

        Returns:
            Parsed JSON response as dict

        Raises:
            FetchError: If request fails or response is not valid JSON
        """
        own_session = session is None
        if own_session:
            session = aiohttp.ClientSession(timeout=self.timeout)

        try:
            response = await self._request_with_retry(session, "GET", url, **kwargs)
            async with response:
                return await response.json()
        except Exception as e:
            if isinstance(e, FetchError):
                raise
            raise FetchError(f"Failed to get JSON from {url}", self.source_name, e)
        finally:
            if own_session:
                await session.close()

    async def _get_text(
        self,
        url: str,
        session: Optional[aiohttp.ClientSession] = None,
        **kwargs,
    ) -> str:
        """
        Make a GET request and return text response.

        Args:
            url: Request URL
            session: Optional aiohttp session
            **kwargs: Additional request arguments

        Returns:
            Response text

        Raises:
            FetchError: If request fails
        """
        own_session = session is None
        if own_session:
            session = aiohttp.ClientSession(timeout=self.timeout)

        try:
            response = await self._request_with_retry(session, "GET", url, **kwargs)
            async with response:
                return await response.text()
        except Exception as e:
            if isinstance(e, FetchError):
                raise
            raise FetchError(f"Failed to get text from {url}", self.source_name, e)
        finally:
            if own_session:
                await session.close()

    async def _post_json(
        self,
        url: str,
        json_data: Dict,
        session: Optional[aiohttp.ClientSession] = None,
        **kwargs,
    ) -> Dict:
        """
        Make a POST request with JSON body and return JSON response.

        Args:
            url: Request URL
            json_data: JSON body data
            session: Optional aiohttp session
            **kwargs: Additional request arguments

        Returns:
            Parsed JSON response as dict

        Raises:
            FetchError: If request fails or response is not valid JSON
        """
        own_session = session is None
        if own_session:
            session = aiohttp.ClientSession(timeout=self.timeout)

        try:
            response = await self._request_with_retry(
                session, "POST", url, json=json_data, **kwargs
            )
            async with response:
                return await response.json()
        except Exception as e:
            if isinstance(e, FetchError):
                raise
            raise FetchError(f"Failed to post JSON to {url}", self.source_name, e)
        finally:
            if own_session:
                await session.close()

    def _create_item(
        self,
        url: str,
        title: str,
        content: Optional[str] = None,
    ) -> Dict:
        """
        Create a standardized item dict.

        Args:
            url: Item URL
            title: Item title
            content: Optional item content/description

        Returns:
            Dict with keys: url, title, content, source
        """
        return {
            "url": url,
            "title": title,
            "content": content,
            "source": self.source_name,
        }
