"""Product Hunt OAuth2 Client Credentials authentication."""

import asyncio
import logging
import time
from typing import Optional

import aiohttp

from src.config import PRODUCTHUNT_CLIENT_ID, PRODUCTHUNT_CLIENT_SECRET

logger = logging.getLogger("digest_bot")

# Product Hunt OAuth2 token endpoint
PRODUCTHUNT_TOKEN_URL = "https://api.producthunt.com/v2/oauth/token"

# In-memory token cache
_token_cache: dict = {
    "access_token": None,
    "expires_at": 0,
}


async def get_access_token() -> Optional[str]:
    """
    Get a valid Product Hunt API access token.

    Uses OAuth2 Client Credentials flow with automatic token caching and refresh.
    Returns the access token string (without 'Bearer' prefix).

    Returns:
        str: Access token for Product Hunt API, or None if authentication fails

    Raises:
        ValueError: If PRODUCTHUNT_CLIENT_ID or PRODUCTHUNT_CLIENT_SECRET are not set
    """
    # Validate credentials are configured
    if not PRODUCTHUNT_CLIENT_ID or not PRODUCTHUNT_CLIENT_SECRET:
        logger.error(
            "Product Hunt credentials not configured. "
            "Set PRODUCTHUNT_CLIENT_ID and PRODUCTHUNT_CLIENT_SECRET in .env"
        )
        return None

    # Check if cached token is still valid
    current_time = time.time()
    if _token_cache["access_token"] and _token_cache["expires_at"] > current_time:
        logger.debug("Using cached Product Hunt access token")
        return _token_cache["access_token"]

    # Token is expired or doesn't exist, fetch a new one
    logger.debug("Fetching new Product Hunt access token")
    return await _fetch_new_token()


async def _fetch_new_token() -> Optional[str]:
    """
    Fetch a new access token from Product Hunt OAuth2 endpoint.

    Uses Client Credentials grant type to obtain an access token.
    Caches the token with its expiration time for reuse.

    Returns:
        str: Access token, or None if the request fails
    """
    payload = {
        "client_id": PRODUCTHUNT_CLIENT_ID,
        "client_secret": PRODUCTHUNT_CLIENT_SECRET,
        "grant_type": "client_credentials",
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                PRODUCTHUNT_TOKEN_URL,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                if response.status != 200:
                    logger.error(
                        f"Failed to get Product Hunt token: "
                        f"HTTP {response.status} - {await response.text()}"
                    )
                    return None

                data = await response.json()
                access_token = data.get("access_token")
                expires_in = data.get("expires_in", 86400)  # Default 24 hours

                if not access_token:
                    logger.error("No access_token in Product Hunt response")
                    return None

                # Cache the token with expiration time (subtract 60s buffer for safety)
                _token_cache["access_token"] = access_token
                _token_cache["expires_at"] = time.time() + expires_in - 60

                logger.info(
                    f"Successfully obtained Product Hunt access token "
                    f"(expires in {expires_in}s)"
                )
                return access_token

    except asyncio.TimeoutError:
        logger.error("Timeout while fetching Product Hunt access token")
        return None
    except aiohttp.ClientError as e:
        logger.error(f"Network error while fetching Product Hunt token: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error while fetching Product Hunt token: {e}")
        return None


def get_auth_header() -> Optional[dict]:
    """
    Get the Authorization header for Product Hunt API requests.

    This is a synchronous wrapper that runs the async token fetch in a new event loop.
    Use this when you can't use async/await directly.

    Returns:
        dict: Authorization header dict with Bearer token, or None if auth fails

    Example:
        headers = get_auth_header()
        if headers:
            async with session.get(url, headers=headers) as response:
                ...
    """
    try:
        # Try to get or create event loop
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running loop, create a new one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            token = loop.run_until_complete(get_access_token())
            loop.close()
        else:
            # Already in async context, create task
            token = loop.run_until_complete(get_access_token())

        if token:
            return {"Authorization": f"Bearer {token}"}
        return None
    except Exception as e:
        logger.error(f"Error getting auth header: {e}")
        return None
