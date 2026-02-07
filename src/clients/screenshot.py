"""
Screenshot client for capturing project URL screenshots using Playwright.

Uses Playwright directly as a local library (no external service).
Captures full-page JPEG screenshots and generates thumbnails via Pillow.
"""

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


class ScreenshotError(Exception):
    """Exception raised when screenshot capture fails."""

    pass


async def capture_screenshot(
    url: str,
    width: int = 1280,
    height: int = 800,
    quality: int = 80,
    timeout: int = 30000,
) -> bytes:
    """
    Capture a screenshot of a URL using headless Chromium.

    Args:
        url: The URL to screenshot.
        width: Viewport width in pixels.
        height: Viewport height in pixels.
        quality: JPEG quality (1-100).
        timeout: Navigation timeout in milliseconds.

    Returns:
        Raw JPEG image bytes.

    Raises:
        ScreenshotError: If screenshot capture fails.
    """
    from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(viewport={"width": width, "height": height})

            try:
                await page.goto(url, wait_until="networkidle", timeout=timeout)
            except PlaywrightTimeout:
                logger.warning(f"Timeout navigating to {url}, taking screenshot anyway")

            image_bytes = await page.screenshot(type="jpeg", quality=quality)
            await browser.close()
            return image_bytes

    except PlaywrightTimeout:
        raise ScreenshotError(f"Timeout capturing screenshot for {url}")
    except Exception as e:
        raise ScreenshotError(f"Failed to capture screenshot for {url}: {e}")


def save_screenshot_to_disk(
    image_bytes: bytes,
    project_id: int,
    media_dir: str = "/app/media",
) -> str:
    """
    Save screenshot JPEG and generate a thumbnail.

    Args:
        image_bytes: Raw JPEG image bytes from capture_screenshot.
        project_id: The project ID (used for filename).
        media_dir: Base media directory.

    Returns:
        Relative path to the full screenshot (e.g. "screenshots/123.jpg").

    Raises:
        ScreenshotError: If saving fails.
    """
    from PIL import Image
    import io

    try:
        screenshots_dir = Path(media_dir) / "screenshots"
        screenshots_dir.mkdir(parents=True, exist_ok=True)

        # Save full screenshot
        full_path = screenshots_dir / f"{project_id}.jpg"
        full_path.write_bytes(image_bytes)
        logger.info(f"Saved full screenshot to {full_path}")

        # Generate thumbnail (320x200)
        thumb_path = screenshots_dir / f"{project_id}_thumb.jpg"
        img = Image.open(io.BytesIO(image_bytes))
        img.thumbnail((320, 200))
        img.save(thumb_path, "JPEG", quality=80)
        logger.info(f"Saved thumbnail to {thumb_path}")

        return f"screenshots/{project_id}.jpg"

    except Exception as e:
        raise ScreenshotError(
            f"Failed to save screenshot for project {project_id}: {e}"
        )
