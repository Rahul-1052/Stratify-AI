import streamlit as st
import google.generativeai as genai
import re
import requests
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable,
)

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(page_title="Stratify AI", layout="wide")
st.title("Stratify AI")
st.caption("AI-powered YouTube content intelligence")

# =========================
# API KEYS
# =========================
youtube_api_key = ""
gemini_api_key = ""

try:
    youtube_api_key = st.secrets["YOUTUBE_API_KEY"]
except Exception:
    youtube_api_key = ""

try:
    gemini_api_key = st.secrets["GEMINI_API_KEY"]
except Exception:
    gemini_api_key = ""

if not youtube_api_key:
    st.warning("Missing YOUTUBE_API_KEY in secrets.toml")

if not gemini_api_key:
    st.warning("Missing GEMINI_API_KEY in secrets.toml")

model = None
if gemini_api_key:
    try:
        genai.configure(api_key=gemini_api_key)
        model = genai.GenerativeModel("gemini-2.0-flash-001")
    except Exception as e:
        st.error(f"Gemini setup failed: {str(e)}")

# =========================
# HELPERS
# =========================
def extract_video_id(url: str):
    if not url:
        return None

    patterns = [
        r"(?:v=|\/videos\/|embed\/|youtu\.be\/|\/shorts\/)([A-Za-z0-9_-]{11})"
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    if re.fullmatch(r"[A-Za-z0-9_-]{11}", url.strip()):
        return url.strip()

    return None


def safe_int(value, default=0):
    try:
        return int(value)
    except Exception:
        return default


def calculate_engagement(video):
    views = video.get("views", 0)
    likes = video.get("likes", 0)
    comments = video.get("comments", 0)

    if views <= 0:
        return {
            "engagement_rate": 0.0,
            "like_rate": 0.0,
            "comment_rate": 0.0,
        }

    return {
        "engagement_rate": round(((likes + comments) / views) * 100, 2),
        "like_rate": round((likes / views) * 100, 2),
        "comment_rate": round((comments / views) * 100, 2),
    }


# =========================
# YOUTUBE DATA
# =========================
def get_video_data(video_url: str):
    video_id = extract_video_id(video_url)
    if not video_id:
        return {
            "ok": False,
            "message": "Invalid YouTube URL or video ID."
        }

    url = (
        "https://www.googleapis.com/youtube/v3/videos"
        f"?part=snippet,statistics&id={video_id}&key={youtube_api_key}"
    )

    try:
        res = requests.get(url, timeout=20)
    except Exception as e:
        return {
            "ok": False,
            "message": f"Request failed: {str(e)}"
        }

    if res.status_code != 200:
        try:
            error_json = res.json()
        except Exception:
            error_json = {"raw_text": res.text}

        return {
            "ok": False,
            "message": "YouTube API request failed.",
            "status_code": res.status_code,
            "error": error_json,
        }

    try:
        data = res.json()
    except Exception as e:
        return {
            "ok": False,
            "message": f"Could not parse YouTube response: {str(e)}"
        }

    items = data.get("items", [])
    if not items:
        return {
            "ok": False,
            "message": "No video found for this URL."
        }

    item = items[0]
    snippet = item.get("snippet", {})
    statistics = item.get("statistics", {})

    video = {
        "ok": True,
        "video_id": video_id,
        "title": snippet.get("title", ""),
        "description": snippet.get("description", ""),
        "channel": snippet.get("channelTitle", ""),
        "published_at": snippet.get("publishedAt", ""),
        "views": safe_int(statistics.get("viewCount")),
        "likes": safe_int(statistics.get("likeCount")),
        "comments": safe_int(statistics.get("commentCount")),
        "url": video_url,
    }

    video.update(calculate_engagement(video))
    return video


# =========================
# TRANSCRIPT
# =========================
def clean_text(text: str):
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


def get_transcript(video_id: str):
    try:
        api = YouTubeTranscriptApi()
        data = api.fetch(video_id, languages=["en", "en-US", "en-GB"])
        text = " ".join([seg.text for seg in data if getattr(seg, "text", "")])
        text = clean_text(text)

        return {
            "ok": True,
            "text": text[:5000],
            "word_count": len(text.split()),
        }

    except (TranscriptsDisabled, NoTranscriptFound, VideoUnavailable):
        return {
            "ok": False,
            "text": "",
            "word_count": 0,
        }
    except Exception:
        return {
            "ok": False,
            "text": "",
            "word_count": 0,
        }


# =========================
# PROMPTS
# =========================
def build_prompt(video, transcript):
    return f"""
You are a senior YouTube content strategist.

Analyze this YouTube video using:
- title
- description
- transcript
- performance signals

Be specific and practical.
Do not be generic.

Return in exactly this format:

Content Style:
<2-3 sentences>

Target Audience:
<2-3 sentences>

Psychology:
<2-3 sentences>

Why It Performs:
<2-3 sentences>

Improvements:
- <point 1>
- <point 2>
- <point 3>

TITLE:
{video['title']}

DESCRIPTION:
{video['description'][:1500]}

TRANSCRIPT:
{transcript[:5000]}

METRICS:
Views: {video['views']}
Likes: {video['likes']}
Comments: {video['comments']}
Like Rate: {video['like_rate']}%
Comment Rate: {video['comment_rate']}%
Engagement Rate: {video['engagement_rate']}%
""".strip()


def build_comparison_prompt(video_a, transcript_a, ai_a, video_b, transcript_b, ai_b):
    return f"""
You are a senior YouTube content strategist.

Compare these two videos using:
- title
- description
- transcript
- performance metrics
- prior analysis

Return in exactly this format:

Which Video Has Stronger Content Strategy:
<short paragraph>

Video A Strengths:
<short paragraph>

Video B Strengths:
<short paragraph>

Audience Difference:
<short paragraph>

Hook / Psychology Difference:
<short paragraph>

Winner:
<short paragraph>

VIDEO A
Title: {video_a['title']}
Description: {video_a['description'][:1000]}
Transcript: {transcript_a[:2500]}
Views: {video_a['views']}
Likes: {video_a['likes']}
Comments: {video_a['comments']}
Engagement Rate: {video_a['engagement_rate']}%
Analysis:
{ai_a[:2000]}

VIDEO B
Title: {video_b['title']}
Description: {video_b['description'][:1000]}
Transcript: {transcript_b[:2500]}
Views: {video_b['views']}
Likes: {video_b['likes']}
Comments: {video_b['comments']}
Engagement Rate: {video_b['engagement_rate']}%
Analysis:
{ai_b[:2000]}
""".strip()


# =========================
# AI ANALYSIS
# =========================
def analyze(video_url):
    video = get_video_data(video_url)
    if not video.get("ok"):
        return video

    transcript_data = get_transcript(video["video_id"])
    transcript = transcript_data["text"] if transcript_data["ok"] else "Transcript unavailable."

    prompt = build_prompt(video, transcript)

    try:
        if not model:
            return {
                "ok": True,
                "video": video,
                "transcript_ok": transcript_data["ok"],
                "transcript_text": transcript,
                "result": (
                    "Gemini is not connected. Video metadata and transcript were fetched, "
                    "but AI insights are unavailable until a valid Gemini API key is active."
                )
            }

        response = model.generate_content(prompt)
        response_text = getattr(response, "text", "") or "No AI response returned."

        return {
            "ok": True,
            "video": video,
            "transcript_ok": transcript_data["ok"],
            "transcript_text": transcript,
            "result": response_text
        }

    except Exception as e:
        error_text = str(e)

        if "quota" in error_text.lower() or "429" in error_text:
            return {
                "ok": True,
                "video": video,
                "transcript_ok": transcript_data["ok"],
                "transcript_text": transcript,
                "result": (
                    "Gemini quota exceeded for this API key/project.\n\n"
                    "The app successfully fetched the video metadata and transcript, "
                    "but AI insights are temporarily unavailable. "
                    "Please check Gemini quota/billing or try again later."
                )
            }

        return {
            "ok": False,
            "message": f"Gemini analysis failed: {error_text}"
        }


# =========================
# UI
# =========================
tab1, tab2 = st.tabs(["Single Video", "Compare Videos"])

with tab1:
    st.subheader("Single Video Analysis")
    url = st.text_input("Enter YouTube URL")

    if st.button("Analyze"):
        if not url:
            st.error("Please enter a YouTube URL.")
        elif not youtube_api_key:
            st.error("YouTube API key is missing.")
        else:
            with st.spinner("Analyzing video..."):
                result = analyze(url)

            if not result.get("ok"):
                st.error(result.get("message", "Unknown error"))
                if "error" in result:
                    st.json(result["error"])
            else:
                v = result["video"]

                st.subheader("Video Info")
                st.write(f"**Title:** {v['title']}")
                st.write(f"**Channel:** {v['channel']}")
                st.write(f"**Published:** {v['published_at']}")
                st.write(f"**Views:** {v['views']:,}")
                st.write(f"**Likes:** {v['likes']:,}")
                st.write(f"**Comments:** {v['comments']:,}")
                st.write(f"**Like Rate:** {v['like_rate']}%")
                st.write(f"**Comment Rate:** {v['comment_rate']}%")
                st.write(f"**Engagement Rate:** {v['engagement_rate']}%")

                st.subheader("Transcript Status")
                if result["transcript_ok"]:
                    st.success("Transcript loaded")
                    with st.expander("Preview Transcript"):
                        st.write(result["transcript_text"][:3000])
                else:
                    st.warning("Transcript unavailable")

                st.subheader("AI Insights")
                st.markdown(result["result"])


with tab2:
    st.subheader("Compare Two Videos")
    col1, col2 = st.columns(2)

    with col1:
        url_a = st.text_input("Video A URL")

    with col2:
        url_b = st.text_input("Video B URL")

    if st.button("Compare"):
        if not url_a or not url_b:
            st.error("Please enter both video URLs.")
        elif not youtube_api_key:
            st.error("YouTube API key is missing.")
        else:
            with st.spinner("Analyzing both videos..."):
                res_a = analyze(url_a)
                res_b = analyze(url_b)

            if not res_a.get("ok"):
                st.error(f"Video A failed: {res_a.get('message', 'Unknown error')}")
            elif not res_b.get("ok"):
                st.error(f"Video B failed: {res_b.get('message', 'Unknown error')}")
            else:
                st.subheader("Video A")
                st.write(f"**Title:** {res_a['video']['title']}")
                st.write(f"**Engagement Rate:** {res_a['video']['engagement_rate']}%")

                st.subheader("Video B")
                st.write(f"**Title:** {res_b['video']['title']}")
                st.write(f"**Engagement Rate:** {res_b['video']['engagement_rate']}%")

                if not model:
                    st.subheader("Comparison Result")
                    st.warning("Gemini not connected, so AI comparison is unavailable.")
                else:
                    try:
                        compare_prompt = build_comparison_prompt(
                            res_a["video"],
                            res_a["transcript_text"],
                            res_a["result"],
                            res_b["video"],
                            res_b["transcript_text"],
                            res_b["result"],
                        )
                        response = model.generate_content(compare_prompt)
                        compare_text = getattr(response, "text", "") or "No comparison returned."

                        st.subheader("Comparison Result")
                        st.markdown(compare_text)

                    except Exception as e:
                        error_text = str(e)
                        if "quota" in error_text.lower() or "429" in error_text:
                            st.subheader("Comparison Result")
                            st.warning(
                                "Gemini quota exceeded. Individual video data loaded, "
                                "but AI comparison is temporarily unavailable."
                            )
                        else:
                            st.error(f"Comparison failed: {error_text}")