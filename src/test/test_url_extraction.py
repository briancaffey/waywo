"""Tests for URL extraction from HN comment text."""

import pytest

from src.clients.firecrawl import extract_urls_from_text


@pytest.mark.parametrize(
    "text,expected",
    [
        pytest.param(
            '<a href="https:&#x2F;&#x2F;www.tonediff.com&#x2F;" rel="nofollow">'
            "https:&#x2F;&#x2F;www.tonediff.com&#x2F;</a>",
            ["https://www.tonediff.com/"],
            id="hn_html_entity_encoded_url",
        ),
        pytest.param(
            '<a href="https:&#x2F;&#x2F;www.unlistedjobs.com&#x2F;" rel="nofollow">'
            "https:&#x2F;&#x2F;www.unlistedjobs.com&#x2F;</a>"
            "<p>A different type of job search site.",
            ["https://www.unlistedjobs.com/"],
            id="hn_comment_with_surrounding_text",
        ),
        pytest.param(
            "Check out https://www.example.com/path for more info.",
            ["https://www.example.com/path"],
            id="plain_text_url",
        ),
        pytest.param(
            "I'm working on a cool project with no links.",
            [],
            id="no_urls",
        ),
        pytest.param(
            "Visit https://example.com and also https://example.com again.",
            ["https://example.com"],
            id="deduplication",
        ),
        pytest.param(
            "Check https://example.com/path.",
            ["https://example.com/path"],
            id="trailing_punctuation_stripped",
        ),
        pytest.param(
            "Watch https://www.youtube.com/watch?v=abc123 for a demo.",
            [],
            id="skipped_domains_filtered",
        ),
        pytest.param(
            "I&#x27;m building "
            '<a href="https:&#x2F;&#x2F;myapp.dev" rel="nofollow">'
            "https:&#x2F;&#x2F;myapp.dev</a>",
            ["https://myapp.dev"],
            id="hn_apostrophe_encoding",
        ),
        pytest.param(
            "Visit http://example.com for the demo.",
            ["http://example.com"],
            id="http_url",
        ),
    ],
)
def test_extract_urls_from_text(text, expected):
    """Test URL extraction handles various HN comment formats."""
    urls = extract_urls_from_text(text)
    assert urls == expected


def test_extract_multiple_hn_encoded_urls():
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


def test_extract_url_with_complex_path():
    """URLs with query params and fragments."""
    text = "See https://example.com/path?q=test&page=1#section for details."
    urls = extract_urls_from_text(text)
    assert len(urls) == 1
    assert "https://example.com/path?q=test&page=1#section" in urls[0]
