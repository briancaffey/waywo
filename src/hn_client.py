import requests

HN_API_BASE = "https://hacker-news.firebaseio.com/v0"


def fetch_item(item_id: int) -> dict | None:
    """
    Fetch a single item from the Hacker News API.

    Args:
        item_id: The HN item ID to fetch.

    Returns:
        The item data as a dict, or None if not found.
    """
    url = f"{HN_API_BASE}/item/{item_id}.json"
    response = requests.get(url, timeout=30)

    if response.status_code != 200:
        return None

    data = response.json()
    if data is None:
        return None

    return data
