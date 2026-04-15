import os
import requests
from dotenv import load_dotenv
import os
import streamlit as st

try:
    YOUTUBE_API_KEY = st.secrets["YOUTUBE_API_KEY"]
except:
    YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

load_dotenv()

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")


def get_video_details(video_id: str):
    if not YOUTUBE_API_KEY:
        print("YOUTUBE_API_KEY is missing in .env")
        return None

    url = "https://www.googleapis.com/youtube/v3/videos"
    params = {
        "part": "snippet,statistics",
        "id": video_id,
        "key": YOUTUBE_API_KEY,
    }

    try:
        response = requests.get(url, params=params, timeout=20)
        response.raise_for_status()

        data = response.json()
        items = data.get("items", [])

        if not items:
            return None

        item = items[0]
        snippet = item.get("snippet", {})
        stats = item.get("statistics", {})

        views = int(stats.get("viewCount", 0))
        likes = int(stats.get("likeCount", 0))
        comments = int(stats.get("commentCount", 0))
        engagement_rate = round(((likes + comments) / views) * 100, 2) if views > 0 else 0

        thumbnails = snippet.get("thumbnails", {})
        thumbnail_url = (
            thumbnails.get("high", {}).get("url")
            or thumbnails.get("medium", {}).get("url")
            or thumbnails.get("default", {}).get("url", "")
        )

        return {
            "title": snippet.get("title", ""),
            "views": views,
            "likes": likes,
            "comments": comments,
            "thumbnail": thumbnail_url,
            "channel": snippet.get("channelTitle", ""),
            "published_at": snippet.get("publishedAt", ""),
            "engagement_rate": engagement_rate,
        }

    except requests.exceptions.RequestException as e:
        print(f"YouTube API request failed: {e}")
        return None