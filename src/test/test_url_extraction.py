"""Tests for URL extraction from HN comment text."""

import pytest

from src.firecrawl_client import extract_urls_from_text


class TestExtractUrlsFromText:
    """Test extract_urls_from_text handles various HN comment formats."""

    def test_hn_html_entity_encoded_url(self):
        """HN encodes slashes as &#x2F; — must decode before extracting."""
        text = (
            '<a href="https:&#x2F;&#x2F;www.tonediff.com&#x2F;" rel="nofollow">'
            "https:&#x2F;&#x2F;www.tonediff.com&#x2F;</a>"
        )
        urls = extract_urls_from_text(text)
        assert urls == ["https://www.tonediff.com/"]

    def test_hn_comment_with_surrounding_text(self):
        """Real-world HN comment with URL embedded in HTML."""
        text = (
            '<a href="https:&#x2F;&#x2F;www.unlistedjobs.com&#x2F;" rel="nofollow">'
            "https:&#x2F;&#x2F;www.unlistedjobs.com&#x2F;</a>"
            "<p>A different type of job search site."
        )
        urls = extract_urls_from_text(text)
        assert urls == ["https://www.unlistedjobs.com/"]

    def test_multiple_hn_encoded_urls(self):
        """Comment with multiple distinct encoded URLs."""
        text = (
            '<a href="https:&#x2F;&#x2F;example.com" rel="nofollow">'
            "https:&#x2F;&#x2F;example.com</a>"
            "<p>Also check out "
            '<a href="https:&#x2F;&#x2F;github.com&#x2F;user&#x2F;repo" rel="nofollow">'
            "https:&#x2F;&#x2F;github.com&#x2F;user&#x2F;repo</a>"
        )
        urls = extract_urls_from_text(text)
        assert "https://example.com" in urls
        assert "https://github.com/user/repo" in urls
        assert len(urls) == 2

    def test_plain_text_url(self):
        """Plain text URL without any HTML encoding."""
        text = "Check out https://www.example.com/path for more info."
        urls = extract_urls_from_text(text)
        assert urls == ["https://www.example.com/path"]

    def test_no_urls(self):
        """Text with no URLs returns empty list."""
        text = "I'm working on a cool project with no links."
        urls = extract_urls_from_text(text)
        assert urls == []

    def test_deduplication(self):
        """Same URL appearing multiple times is deduplicated."""
        text = (
            "Visit https://example.com and also https://example.com again."
        )
        urls = extract_urls_from_text(text)
        assert urls == ["https://example.com"]

    def test_trailing_punctuation_stripped(self):
        """Trailing punctuation after URL is stripped."""
        text = "Check https://example.com/path."
        urls = extract_urls_from_text(text)
        assert urls == ["https://example.com/path"]

    def test_skipped_domains_filtered(self):
        """YouTube and other skip-listed domains are filtered out."""
        text = "Watch https://www.youtube.com/watch?v=abc123 for a demo."
        urls = extract_urls_from_text(text)
        assert urls == []

    def test_hn_apostrophe_encoding(self):
        """HN also encodes apostrophes as &#x27; — should not break parsing."""
        text = (
            "I&#x27;m building "
            '<a href="https:&#x2F;&#x2F;myapp.dev" rel="nofollow">'
            "https:&#x2F;&#x2F;myapp.dev</a>"
        )
        urls = extract_urls_from_text(text)
        assert urls == ["https://myapp.dev"]

    def test_http_url(self):
        """http:// URLs (not just https) are extracted."""
        text = "Visit http://example.com for the demo."
        urls = extract_urls_from_text(text)
        assert urls == ["http://example.com"]

    def test_url_with_complex_path(self):
        """URLs with query params and fragments."""
        text = "See https://example.com/path?q=test&page=1#section for details."
        urls = extract_urls_from_text(text)
        assert len(urls) == 1
        assert "https://example.com/path?q=test&page=1#section" in urls[0]
