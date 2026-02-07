"""
Firecrawl client for fetching and processing web content.

Provides async URL scraping with retry logic, URL validation,
and graceful error handling.
"""

import asyncio
import html
import logging
import os
import re
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)

# Firecrawl configuration
FIRECRAWL_URL = os.getenv("FIRECRAWL_URL", "http://localhost:3002")
FIRECRAWL_TIMEOUT = int(os.getenv("FIRECRAWL_TIMEOUT", "30"))
FIRECRAWL_MAX_RETRIES = int(os.getenv("FIRECRAWL_MAX_RETRIES", "3"))
FIRECRAWL_MAX_CONTENT_LENGTH = int(os.getenv("FIRECRAWL_MAX_CONTENT_LENGTH", "10000"))

# Domains to skip (social media, login pages, etc.)
SKIP_DOMAINS = {
    # Social media
    "twitter.com",
    "x.com",
    "facebook.com",
    "instagram.com",
    "linkedin.com",
    "tiktok.com",
    "reddit.com",
    "threads.net",
    # Video platforms
    "youtube.com",
    "youtu.be",
    "vimeo.com",
    "twitch.tv",
    # Auth/login
    "accounts.google.com",
    "login.microsoftonline.com",
    "auth0.com",
    # Other
    "mailto:",
    "tel:",
    "javascript:",
}

# File extensions to skip
SKIP_EXTENSIONS = {
    ".pdf",
    ".zip",
    ".tar",
    ".gz",
    ".rar",
    ".exe",
    ".dmg",
    ".pkg",
    ".deb",
    ".rpm",
    ".mp3",
    ".mp4",
    ".avi",
    ".mov",
    ".wav",
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".svg",
    ".ico",
    ".webp",
}


@dataclass
class ScrapeResult:
    """Result of a URL scrape operation."""

    url: str
    success: bool
    content: Optional[str] = None
    title: Optional[str] = None
    error: Optional[str] = None
    status_code: Optional[int] = None


def should_skip_url(url: str) -> tuple[bool, str]:
    """
    Check if a URL should be skipped.

    Returns:
        Tuple of (should_skip, reason)
    """
    # Check for empty or invalid URLs
    if not url or not url.strip():
        return True, "empty_url"

    url_lower = url.lower()

    # Check for non-http schemes
    if not url_lower.startswith(("http://", "https://")):
        return True, "invalid_scheme"

    # Parse the URL
    try:
        parsed = urlparse(url)
    except Exception:
        return True, "parse_error"

    # Check domain against skip list
    domain = parsed.netloc.lower()
    for skip_domain in SKIP_DOMAINS:
        if skip_domain in domain:
            return True, f"skipped_domain:{skip_domain}"

    # Check file extension
    path_lower = parsed.path.lower()
    for ext in SKIP_EXTENSIONS:
        if path_lower.endswith(ext):
            return True, f"skipped_extension:{ext}"

    return False, ""


def extract_urls_from_text(text: str) -> list[str]:
    """
    Extract URLs from text content.

    Handles HN-style HTML entity encoding (e.g. &#x2F; for /) by
    decoding entities before running the regex.

    Args:
        text: Text that may contain URLs (plain text or HTML)

    Returns:
        List of unique, cleaned URLs
    """
    # Decode HTML entities first (HN encodes / as &#x2F; and ' as &#x27;)
    decoded_text = html.unescape(text)

    # URL regex pattern
    url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
    urls = re.findall(url_pattern, decoded_text)

    # Clean and deduplicate
    cleaned_urls = []
    seen = set()

    for url in urls:
        # Remove trailing punctuation
        url = url.rstrip(".,;:!?)'\"")

        # Skip if already seen
        if url in seen:
            continue
        seen.add(url)

        # Skip if should be filtered
        should_skip, _ = should_skip_url(url)
        if not should_skip:
            cleaned_urls.append(url)

    return cleaned_urls


async def scrape_url(
    url: str,
    max_retries: int = FIRECRAWL_MAX_RETRIES,
    timeout: int = FIRECRAWL_TIMEOUT,
    firecrawl_url: str = FIRECRAWL_URL,
) -> ScrapeResult:
    """
    Scrape a URL using Firecrawl with retry logic.

    Args:
        url: The URL to scrape
        max_retries: Maximum number of retry attempts
        timeout: Request timeout in seconds
        firecrawl_url: Firecrawl service URL

    Returns:
        ScrapeResult with content or error information
    """
    # Check if URL should be skipped
    should_skip, reason = should_skip_url(url)
    if should_skip:
        logger.info(f"⏭️ Skipping URL ({reason}): {url[:60]}...")
        return ScrapeResult(
            url=url,
            success=False,
            error=f"skipped:{reason}",
        )

    logger.info(f"📥 Fetching URL: {url[:60]}...")

    last_error = None

    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    f"{firecrawl_url}/v1/scrape",
                    json={
                        "url": url,
                        "formats": ["markdown"],
                        "onlyMainContent": True,
                        "blockAds": True,
                    },
                )

                if response.status_code == 200:
                    data = response.json()

                    # Extract content
                    content = data.get("data", {}).get("markdown", "")
                    title = data.get("data", {}).get("metadata", {}).get("title", "")

                    # Truncate if too long
                    if len(content) > FIRECRAWL_MAX_CONTENT_LENGTH:
                        content = (
                            content[:FIRECRAWL_MAX_CONTENT_LENGTH]
                            + "\n\n[Content truncated...]"
                        )

                    logger.info(f"✅ Fetched {len(content)} chars from {url[:40]}...")

                    return ScrapeResult(
                        url=url,
                        success=True,
                        content=content,
                        title=title,
                        status_code=response.status_code,
                    )

                else:
                    last_error = f"HTTP {response.status_code}"
                    logger.warning(
                        f"⚠️ Attempt {attempt + 1}/{max_retries} failed for {url[:40]}: {last_error}"
                    )

        except httpx.TimeoutException:
            last_error = "timeout"
            logger.warning(
                f"⚠️ Attempt {attempt + 1}/{max_retries} timed out for {url[:40]}"
            )

        except httpx.ConnectError as e:
            last_error = f"connection_error: {str(e)[:50]}"
            logger.warning(
                f"⚠️ Attempt {attempt + 1}/{max_retries} connection failed for {url[:40]}"
            )

        except Exception as e:
            last_error = f"error: {str(e)[:50]}"
            logger.warning(
                f"⚠️ Attempt {attempt + 1}/{max_retries} failed for {url[:40]}: {e}"
            )

        # Exponential backoff before retry
        if attempt < max_retries - 1:
            wait_time = 2**attempt  # 1, 2, 4 seconds
            logger.info(f"⏳ Waiting {wait_time}s before retry...")
            await asyncio.sleep(wait_time)

    # All retries failed
    logger.error(f"❌ All {max_retries} attempts failed for {url[:40]}: {last_error}")

    return ScrapeResult(
        url=url,
        success=False,
        error=last_error,
    )


async def scrape_urls(
    urls: list[str],
    max_urls: int = 5,
    max_retries: int = FIRECRAWL_MAX_RETRIES,
    timeout: int = FIRECRAWL_TIMEOUT,
    firecrawl_url: str = FIRECRAWL_URL,
) -> list[ScrapeResult]:
    """
    Scrape multiple URLs concurrently.

    Args:
        urls: List of URLs to scrape
        max_urls: Maximum number of URLs to scrape
        max_retries: Maximum retry attempts per URL
        timeout: Request timeout in seconds
        firecrawl_url: Firecrawl service URL

    Returns:
        List of ScrapeResult objects
    """
    # Limit number of URLs
    urls_to_scrape = urls[:max_urls]

    if not urls_to_scrape:
        return []

    logger.info(f"🔗 Scraping {len(urls_to_scrape)} URLs...")

    # Scrape concurrently but with some rate limiting
    results = []
    for url in urls_to_scrape:
        result = await scrape_url(
            url,
            max_retries=max_retries,
            timeout=timeout,
            firecrawl_url=firecrawl_url,
        )
        results.append(result)

        # Small delay between requests to be polite
        if len(urls_to_scrape) > 1:
            await asyncio.sleep(0.5)

    successful = sum(1 for r in results if r.success)
    logger.info(f"📊 Scraped {successful}/{len(results)} URLs successfully")

    return results
