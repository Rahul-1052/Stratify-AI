import re
import requests
from urllib.parse import urlparse, parse_qs


def extract_video_id(url: str) -> str | None:
    """
    Extract YouTube video ID from various URL formats.
    """
    if not url:
        return None

    url = url.strip()

    # direct 11-char id
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", url):
        return url

    try:
        parsed = urlparse(url)

        if parsed.hostname in ["youtu.be"]:
            return parsed.path.lstrip("/")

        if parsed.hostname in ["www.youtube.com", "youtube.com", "m.youtube.com"]:
            if parsed.path == "/watch":
                return parse_qs(parsed.query).get("v", [None])[0]
            if parsed.path.startswith("/shorts/"):
                return parsed.path.split("/shorts/")[1].split("/")[0]
            if parsed.path.startswith("/embed/"):
                return parsed.path.split("/embed/")[1].split("/")[0]
    except Exception:
        return None

    match = re.search(r"(?:v=|/)([A-Za-z0-9_-]{11})(?:[?&/]|$)", url)
    return match.group(1) if match else None


def fetch_video_metadata(video_id: str, youtube_api_key: str) -> dict:
    """
    Fetch video metadata from YouTube Data API.
    """
    if not youtube_api_key:
        return {
            "ok": False,
            "error": "Missing YOUTUBE_API_KEY."
        }

    endpoint = "https://www.googleapis.com/youtube/v3/videos"
    params = {
        "part": "snippet,statistics",
        "id": video_id,
        "key": youtube_api_key
    }

    try:
        response = requests.get(endpoint, params=params, timeout=20)

        if response.status_code != 200:
            return {
                "ok": False,
                "error": f"YouTube API returned {response.status_code}.",
                "details": response.text
            }

        data = response.json()
        items = data.get("items", [])

        if not items:
            return {
                "ok": False,
                "error": "No video found for this ID."
            }

        item = items[0]
        snippet = item.get("snippet", {})
        stats = item.get("statistics", {})

        views = int(stats.get("viewCount", 0))
        likes = int(stats.get("likeCount", 0))
        comments = int(stats.get("commentCount", 0))

        engagement_rate = round(((likes + comments) / views) * 100, 2) if views > 0 else 0.0

        return {
            "ok": True,
            "video_id": video_id,
            "title": snippet.get("title", "Unknown Title"),
            "description": snippet.get("description", ""),
            "channel": snippet.get("channelTitle", "Unknown Channel"),
            "published_at": snippet.get("publishedAt", ""),
            "thumbnail": snippet.get("thumbnails", {}).get("high", {}).get("url", ""),
            "views": views,
            "likes": likes,
            "comments": comments,
            "engagement_rate": engagement_rate
        }

    except requests.RequestException as e:
        return {
            "ok": False,
            "error": f"Network error while fetching YouTube metadata: {str(e)}"
        }
    except Exception as e:
        return {
            "ok": False,
            "error": f"Unexpected metadata error: {str(e)}"
        }