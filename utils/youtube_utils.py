import os
import requests
import streamlit as st


try:
    YOUTUBE_API_KEY = st.secrets["YOUTUBE_API_KEY"]
except Exception:
    YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")


def get_video_details(video_id: str):
    if not YOUTUBE_API_KEY:
        print("Missing YOUTUBE_API_KEY")
        return None

    url = "https://www.googleapis.com/youtube/v3/videos"
    params = {
        "part": "snippet,statistics",
        "id": video_id,
        "key": YOUTUBE_API_KEY,
    }

    try:
        response = requests.get(url, params=params, timeout=20)
        print("YouTube status:", response.status_code)
        print("YouTube response:", response.text[:500])

        if response.status_code != 200:
            return None

        data = response.json()

        items = data.get("items", [])
        if not items:
            return None

        item = items[0]
        snippet = item.get("snippet", {})
        stats = item.get("statistics", {})

        return {
            "title": snippet.get("title", "Unknown Title"),
            "channel": snippet.get("channelTitle", "Unknown Channel"),
            "published_at": snippet.get("publishedAt", ""),
            "thumbnail": snippet.get("thumbnails", {}).get("high", {}).get("url", ""),
            "views": int(stats.get("viewCount", 0)),
            "likes": int(stats.get("likeCount", 0)),
            "comments": int(stats.get("commentCount", 0)),
        }

    except Exception as e:
        print("YouTube fetch error:", str(e))
        return None