import re
import requests
from urllib.parse import urlparse, parse_qs


YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"


def extract_video_id(url: str) -> str | None:
    if not url:
        return None

    url = url.strip()

    if re.fullmatch(r"[A-Za-z0-9_-]{11}", url):
        return url

    try:
        parsed = urlparse(url)

        if parsed.hostname in ["youtu.be"]:
            return parsed.path.lstrip("/").split("?")[0]

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


def extract_channel_hint(channel_input: str) -> str | None:
    """
    Accepts:
    - channel URL
    - @handle
    - channel ID
    - plain channel name
    """
    if not channel_input:
        return None

    text = channel_input.strip()

    if text.startswith("@"):
        return text

    if re.fullmatch(r"UC[A-Za-z0-9_-]{22}", text):
        return text

    try:
        parsed = urlparse(text)
        path = parsed.path.strip("/")

        if "/@" in text or path.startswith("@"):
            return path.split("/")[0]

        if path.startswith("channel/"):
            return path.split("channel/")[1].split("/")[0]

        if path.startswith("c/"):
            return path.split("c/")[1].split("/")[0]

        if path.startswith("user/"):
            return path.split("user/")[1].split("/")[0]

        if path:
            return path.split("/")[0]
    except Exception:
        pass

    return text


def _youtube_get(endpoint: str, params: dict, youtube_api_key: str) -> dict:
    if not youtube_api_key:
        return {"ok": False, "error": "Missing YOUTUBE_API_KEY."}

    params["key"] = youtube_api_key

    try:
        response = requests.get(
            f"{YOUTUBE_API_BASE}/{endpoint}",
            params=params,
            timeout=20
        )

        if response.status_code != 200:
            return {
                "ok": False,
                "error": f"YouTube API returned {response.status_code}.",
                "details": response.text
            }

        return {"ok": True, "data": response.json()}

    except requests.RequestException as e:
        return {
            "ok": False,
            "error": f"Network error while calling YouTube API: {str(e)}"
        }


def fetch_video_metadata(video_id: str, youtube_api_key: str) -> dict:
    result = fetch_multiple_video_metadata([video_id], youtube_api_key)

    if not result.get("ok"):
        return result

    videos = result.get("videos", [])

    if not videos:
        return {
            "ok": False,
            "error": "No video found for this ID."
        }

    return videos[0]


def fetch_multiple_video_metadata(video_ids: list[str], youtube_api_key: str) -> dict:
    video_ids = [vid for vid in video_ids if vid]

    if not video_ids:
        return {
            "ok": False,
            "error": "No video IDs provided.",
            "videos": []
        }

    params = {
        "part": "snippet,statistics,contentDetails",
        "id": ",".join(video_ids[:50])
    }

    result = _youtube_get("videos", params, youtube_api_key)

    if not result.get("ok"):
        return result

    items = result.get("data", {}).get("items", [])
    videos = []

    for item in items:
        snippet = item.get("snippet", {})
        stats = item.get("statistics", {})

        views = int(stats.get("viewCount", 0))
        likes = int(stats.get("likeCount", 0))
        comments = int(stats.get("commentCount", 0))

        engagement_rate = round(((likes + comments) / views) * 100, 2) if views > 0 else 0.0

        videos.append({
            "ok": True,
            "video_id": item.get("id"),
            "title": snippet.get("title", "Unknown Title"),
            "description": snippet.get("description", ""),
            "channel": snippet.get("channelTitle", "Unknown Channel"),
            "channel_id": snippet.get("channelId", ""),
            "published_at": snippet.get("publishedAt", ""),
            "thumbnail": snippet.get("thumbnails", {}).get("high", {}).get("url", ""),
            "views": views,
            "likes": likes,
            "comments": comments,
            "engagement_rate": engagement_rate
        })

    return {
        "ok": True,
        "videos": videos
    }


def resolve_channel(channel_input: str, youtube_api_key: str) -> dict:
    """
    Converts channel URL / handle / channel name into channel_id.
    """
    hint = extract_channel_hint(channel_input)

    if not hint:
        return {
            "ok": False,
            "error": "Invalid channel input."
        }

    if re.fullmatch(r"UC[A-Za-z0-9_-]{22}", hint):
        return fetch_channel_metadata(hint, youtube_api_key)

    search_query = hint

    params = {
        "part": "snippet",
        "q": search_query,
        "type": "channel",
        "maxResults": 1
    }

    result = _youtube_get("search", params, youtube_api_key)

    if not result.get("ok"):
        return result

    items = result.get("data", {}).get("items", [])

    if not items:
        return {
            "ok": False,
            "error": "No channel found."
        }

    channel_id = items[0].get("snippet", {}).get("channelId")

    if not channel_id:
        return {
            "ok": False,
            "error": "Could not resolve channel ID."
        }

    return fetch_channel_metadata(channel_id, youtube_api_key)


def fetch_channel_metadata(channel_id: str, youtube_api_key: str) -> dict:
    params = {
        "part": "snippet,statistics,contentDetails",
        "id": channel_id
    }

    result = _youtube_get("channels", params, youtube_api_key)

    if not result.get("ok"):
        return result

    items = result.get("data", {}).get("items", [])

    if not items:
        return {
            "ok": False,
            "error": "Channel not found."
        }

    item = items[0]
    snippet = item.get("snippet", {})
    stats = item.get("statistics", {})
    content_details = item.get("contentDetails", {})

    return {
        "ok": True,
        "channel_id": channel_id,
        "title": snippet.get("title", "Unknown Channel"),
        "description": snippet.get("description", ""),
        "published_at": snippet.get("publishedAt", ""),
        "thumbnail": snippet.get("thumbnails", {}).get("high", {}).get("url", ""),
        "subscribers": int(stats.get("subscriberCount", 0)) if not stats.get("hiddenSubscriberCount") else 0,
        "total_views": int(stats.get("viewCount", 0)),
        "video_count": int(stats.get("videoCount", 0)),
        "uploads_playlist_id": content_details.get("relatedPlaylists", {}).get("uploads", "")
    }


def fetch_latest_channel_video_ids(channel_id: str, youtube_api_key: str, max_results: int = 10) -> dict:
    channel = fetch_channel_metadata(channel_id, youtube_api_key)

    if not channel.get("ok"):
        return channel

    uploads_playlist_id = channel.get("uploads_playlist_id")

    if not uploads_playlist_id:
        return {
            "ok": False,
            "error": "Could not find channel uploads playlist."
        }

    params = {
        "part": "snippet",
        "playlistId": uploads_playlist_id,
        "maxResults": min(max_results, 25)
    }

    result = _youtube_get("playlistItems", params, youtube_api_key)

    if not result.get("ok"):
        return result

    items = result.get("data", {}).get("items", [])

    video_ids = [
        item.get("snippet", {}).get("resourceId", {}).get("videoId")
        for item in items
        if item.get("snippet", {}).get("resourceId", {}).get("videoId")
    ]

    return {
        "ok": True,
        "video_ids": video_ids
    }


def fetch_channel_latest_videos(channel_input: str, youtube_api_key: str, max_results: int = 10) -> dict:
    channel = resolve_channel(channel_input, youtube_api_key)

    if not channel.get("ok"):
        return channel

    video_id_result = fetch_latest_channel_video_ids(
        channel_id=channel["channel_id"],
        youtube_api_key=youtube_api_key,
        max_results=max_results
    )

    if not video_id_result.get("ok"):
        return video_id_result

    metadata_result = fetch_multiple_video_metadata(
        video_id_result.get("video_ids", []),
        youtube_api_key
    )

    if not metadata_result.get("ok"):
        return metadata_result

    return {
        "ok": True,
        "channel": channel,
        "videos": metadata_result.get("videos", [])
    }