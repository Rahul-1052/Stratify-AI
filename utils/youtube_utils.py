import os
import requests
import streamlit as st


YOUTUBE_API_URL = "https://www.googleapis.com/youtube/v3/videos"


def load_youtube_api_key() -> str | None:
    try:
        key = st.secrets["YOUTUBE_API_KEY"]
        if key and str(key).strip():
            return str(key).strip()
    except Exception:
        pass

    key = os.getenv("YOUTUBE_API_KEY")
    if key and str(key).strip():
        return str(key).strip()

    return None


def get_video_details(video_id: str):
    """
    Returns:
        (video_data, debug_info)

    video_data: dict | None
    debug_info: dict
    """
    api_key = load_youtube_api_key()

    debug = {
        "ok": False,
        "stage": "init",
        "video_id": video_id,
    }

    if not api_key:
        debug.update({
            "stage": "missing_api_key",
            "message": "YOUTUBE_API_KEY was not found in st.secrets or environment variables."
        })
        return None, debug

    params = {
        "part": "snippet,statistics",
        "id": video_id,
        "key": api_key,
    }

    try:
        debug["stage"] = "requesting_youtube_api"

        response = requests.get(YOUTUBE_API_URL, params=params, timeout=20)

        debug["http_status"] = response.status_code
        debug["request_url"] = response.url

        # Try JSON first
        try:
            payload = response.json()
        except Exception:
            payload = None

        # Non-200 response
        if response.status_code != 200:
            debug.update({
                "stage": "http_error",
                "message": "YouTube API returned a non-200 response.",
                "response_json": payload,
                "response_text_preview": response.text[:500],
            })
            return None, debug

        # Empty or malformed response
        if not isinstance(payload, dict):
            debug.update({
                "stage": "invalid_json",
                "message": "YouTube API response was not valid JSON.",
                "response_text_preview": response.text[:500],
            })
            return None, debug

        items = payload.get("items", [])
        if not items:
            debug.update({
                "stage": "empty_items",
                "message": "YouTube API returned 200 but no video items.",
                "response_json": payload,
            })
            return None, debug

        item = items[0]
        snippet = item.get("snippet", {})
        stats = item.get("statistics", {})

        video_data = {
            "title": snippet.get("title", "Unknown Title"),
            "channel": snippet.get("channelTitle", "Unknown Channel"),
            "published_at": snippet.get("publishedAt", ""),
            "thumbnail": (
                snippet.get("thumbnails", {}).get("high", {}).get("url")
                or snippet.get("thumbnails", {}).get("medium", {}).get("url")
                or snippet.get("thumbnails", {}).get("default", {}).get("url", "")
            ),
            "views": int(stats.get("viewCount", 0)),
            "likes": int(stats.get("likeCount", 0)),
            "comments": int(stats.get("commentCount", 0)),
        }

        debug.update({
            "ok": True,
            "stage": "success",
            "message": "Video metadata fetched successfully.",
        })
        return video_data, debug

    except requests.Timeout:
        debug.update({
            "stage": "timeout",
            "message": "Timed out while calling YouTube API.",
        })
        return None, debug

    except requests.RequestException as e:
        debug.update({
            "stage": "request_exception",
            "message": str(e),
        })
        return None, debug

    except Exception as e:
        debug.update({
            "stage": "unexpected_exception",
            "message": str(e),
        })
        return None, debug