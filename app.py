import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re
import json
from datetime import datetime, timezone
from urllib.parse import urlparse, parse_qs
from html import escape
from io import BytesIO
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage

try:
    from youtube_transcript_api import YouTubeTranscriptApi
except Exception:
    YouTubeTranscriptApi = None


# =========================================================
# APP CONFIG
# =========================================================

BASE_DIR = Path(__file__).resolve().parent
ASSET_DIR = BASE_DIR / "assets"


def find_asset(*names):
    """Return the first existing asset path from the assets folder."""
    for name in names:
        path = ASSET_DIR / name
        if path.exists():
            return path
    return None


APP_ICON_PATH = find_asset(
    "stratify_icon.png",
    "logo.png",
    "icon.png",
    "stratify_logo.png"
)

APP_HORIZONTAL_LOGO_PATH = find_asset(
    "stratify_logo_horizontal.png",
    "logo_horizontal.png",
    "stratify_horizontal.png"
)

# Browser tab icon / favicon.
# Using bytes is more reliable on Streamlit Cloud than passing a file path string.
APP_PAGE_ICON = "📊"
if APP_ICON_PATH:
    try:
        APP_PAGE_ICON = APP_ICON_PATH.read_bytes()
    except Exception:
        APP_PAGE_ICON = "📊"

st.set_page_config(
    page_title="Stratify",
    page_icon=APP_PAGE_ICON,
    layout="wide"
)

YOUTUBE_API_KEY = st.secrets.get("YOUTUBE_API_KEY", "")
NVIDIA_API_KEY = st.secrets.get("NVIDIA_API_KEY", "")

YOUTUBE_BASE_URL = "https://www.googleapis.com/youtube/v3"
NVIDIA_URL = "https://integrate.api.nvidia.com/v1/chat/completions"

# =========================================================
# GLOBAL CSS
# =========================================================

st.markdown(
    """
    <style>
    :root {
        --bg: #0b1020;
        --panel: rgba(17, 24, 39, 0.88);
        --panel-soft: rgba(30, 41, 59, 0.72);
        --border: rgba(148, 163, 184, 0.22);
        --text: #f8fafc;
        --muted: #cbd5e1;
        --accent: #38bdf8;
        --accent-2: #22c55e;
    }

    .stApp {
        background:
            radial-gradient(circle at 10% 10%, rgba(14, 165, 233, 0.10), transparent 24%),
            radial-gradient(circle at 90% 16%, rgba(34, 197, 94, 0.08), transparent 28%),
            linear-gradient(135deg, #07111f 0%, #0a1324 52%, #0f172a 100%);
        color: var(--text);
    }

    div[data-testid="stHeader"] {
        background: transparent;
    }

    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
    }

    .main-title {
        font-size: 52px;
        font-weight: 900;
        margin-top: 4px;
        margin-bottom: 6px;
        letter-spacing: -1.4px;
        color: #f8fafc;
        line-height: 1.05;
    }

    .sub-title {
        color: #cbd5e1;
        font-size: 20px;
        margin-bottom: 28px;
    }

    div[data-testid="stTabs"] {
        background: rgba(8, 13, 28, 0.40) !important;
        border-radius: 18px !important;
        padding: 6px 8px 0 8px !important;
        border: 1px solid rgba(148, 163, 184, 0.12) !important;
    }

    div[data-testid="stTabs"] button {
        color: #cbd5e1 !important;
        background: rgba(15, 23, 42, 0.48) !important;
        border-radius: 14px 14px 0 0 !important;
        border: 1px solid rgba(148, 163, 184, 0.14) !important;
        margin-right: 6px !important;
        box-shadow: none !important;
    }

    div[data-testid="stTabs"] button:hover {
        background: rgba(30, 41, 59, 0.72) !important;
        color: #ffffff !important;
    }

    div[data-testid="stTabs"] button[aria-selected="true"] {
        color: #ffffff !important;
        background: linear-gradient(135deg, rgba(15, 23, 42, 0.95), rgba(30, 41, 59, 0.88)) !important;
        border: 1px solid rgba(56, 189, 248, 0.26) !important;
        border-bottom: 3px solid #22c55e !important;
    }

    div[data-testid="stTabs"] [data-baseweb="tab-highlight"] {
        background-color: #22c55e !important;
    }

    .metric-card {
        background: linear-gradient(135deg, rgba(15, 23, 42, 0.98), rgba(30, 41, 59, 0.90));
        padding: 22px;
        border-radius: 18px;
        color: #f8fafc;
        border: 1px solid var(--border);
        box-shadow: 0 10px 30px rgba(0,0,0,0.24);
        margin-bottom: 12px;
        min-height: 120px;
    }

    .metric-card h3 {
        margin: 0;
        font-size: 14px;
        color: #cbd5e1;
        font-weight: 600;
    }

    .metric-card h2 {
        margin: 10px 0 0 0;
        font-size: 30px;
        font-weight: 850;
        color: #ffffff;
    }

    .insight-card, .premium-card {
        background: linear-gradient(135deg, rgba(15, 23, 42, 0.94), rgba(30, 41, 59, 0.78));
        padding: 22px 24px;
        border-radius: 20px;
        border: 1px solid var(--border);
        box-shadow: 0 10px 28px rgba(0,0,0,0.22);
        margin-bottom: 16px;
        color: #f8fafc !important;
    }

    .insight-card h4, .premium-card h4 {
        color: #e0f2fe !important;
        margin-top: 0;
        margin-bottom: 10px;
        font-weight: 800;
        font-size: 18px;
    }

    .insight-card p, .premium-card p {
        color: #e5e7eb !important;
        font-size: 15.5px;
        line-height: 1.7;
        margin: 0;
        white-space: pre-wrap;
    }

    .score-card {
        background: linear-gradient(135deg, rgba(14, 165, 233, 0.22), rgba(34, 197, 94, 0.14));
        border: 1px solid rgba(56, 189, 248, 0.34);
        padding: 24px;
        border-radius: 22px;
        margin-bottom: 16px;
        color: #ffffff !important;
        min-height: 260px;
    }

    .score-card h1, .score-card h2, .score-card div {
        color: #ffffff !important;
    }

    .dna-list-item {
        padding: 16px 18px;
        border: 1px solid rgba(148, 163, 184, 0.18);
        background: rgba(15, 23, 42, 0.70);
        border-radius: 16px;
        margin-bottom: 10px;
        color: #e5e7eb !important;
        line-height: 1.6;
    }

    .small-muted {
        color: #cbd5e1 !important;
        font-size: 14px;
    }

    textarea, input {
        background-color: rgba(15, 23, 42, 0.86) !important;
        color: #f8fafc !important;
        border: 1px solid rgba(148, 163, 184, 0.28) !important;
    }

    label, .stMarkdown, .stText, p, span, h1, h2, h3, h4 {
        color: inherit;
    }

    .stDataFrame, div[data-testid="stDataFrame"] {
        border-radius: 16px;
        overflow: hidden;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# =========================================================
# UTILITY FUNCTIONS
# =========================================================

def safe_int(value):
    try:
        return int(value)
    except Exception:
        return 0


def safe_float(value):
    try:
        return float(value)
    except Exception:
        return 0.0


def format_number(num):
    num = safe_float(num)
    if num >= 1_000_000_000:
        return f"{num / 1_000_000_000:.1f}B"
    if num >= 1_000_000:
        return f"{num / 1_000_000:.1f}M"
    if num >= 1_000:
        return f"{num / 1_000:.1f}K"
    return str(int(num))


def format_date(value):
    try:
        if not value:
            return "Not available"
        clean_value = str(value).replace("Z", "+00:00")
        dt = datetime.fromisoformat(clean_value)
        return dt.strftime("%B %d, %Y")
    except Exception:
        return str(value) if value else "Not available"


def clean_text(text):
    if not text:
        return ""
    text = re.sub(r"<.*?>", "", text)
    text = text.replace("&amp;", "&")
    text = text.replace("&quot;", '"')
    text = text.replace("&#39;", "'")
    return text.strip()


def extract_json(text):
    try:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
    except Exception:
        return None
    return None


def calculate_engagement_rate(likes, comments, views):
    if views <= 0:
        return 0
    return round(((likes + comments) / views) * 100, 2)


def calculate_video_score(views, likes, comments):
    if views <= 0:
        return 0

    like_rate = likes / views
    comment_rate = comments / views
    engagement_rate = (likes + comments) / views

    score = (
        min(like_rate * 1000, 35) +
        min(comment_rate * 4000, 25) +
        min(engagement_rate * 700, 40)
    )

    return round(min(score, 100), 1)


def classify_performance(score):
    if score >= 80:
        return "Excellent"
    if score >= 65:
        return "Strong"
    if score >= 45:
        return "Moderate"
    return "Needs Improvement"


def score_tone(score):
    score = safe_float(score)
    if score >= 80:
        return "Excellent"
    if score >= 65:
        return "Strong"
    if score >= 45:
        return "Moderate"
    return "Needs Improvement"


def get_score_color_hex(value):
    score = safe_float(str(value).replace("/100", "").replace("%", ""))
    if score >= 80:
        return "#15803d"
    if score >= 60:
        return "#b45309"
    return "#b91c1c"


def extract_title_keywords(videos, limit=5):
    if not videos:
        return []

    stopwords = {
        "the", "and", "for", "with", "from", "that", "this", "into", "your", "you",
        "are", "was", "were", "their", "they", "his", "her", "its", "our", "out",
        "how", "why", "what", "when", "where", "best", "top", "official", "video",
        "clips", "clip", "scene", "scenes", "shorts"
    }

    counts = {}
    for video in videos:
        title = str(video.get("title", "")).lower()
        words = re.findall(r"[a-zA-Z][a-zA-Z']+", title)
        for word in words:
            word = word.strip("'").lower()
            if len(word) < 4 or word in stopwords:
                continue
            counts[word] = counts.get(word, 0) + 1

    return [word.title() for word, _ in sorted(counts.items(), key=lambda item: item[1], reverse=True)[:limit]]


def get_top_video_by_score(videos):
    if not videos:
        return None
    try:
        return sorted(videos, key=lambda v: safe_float(v.get("performance_score", 0)), reverse=True)[0]
    except Exception:
        return videos[0]


def get_channel_signal_summary(videos):
    if not videos:
        return {
            "avg_views": 0,
            "avg_engagement": 0,
            "avg_score": 0,
            "top_video": None,
            "keywords": [],
            "uploads_per_week": 0
        }

    df = pd.DataFrame(videos)
    avg_views = safe_float(df["views"].mean()) if "views" in df else 0
    avg_engagement = safe_float(df["engagement_rate"].mean()) if "engagement_rate" in df else 0
    avg_score = safe_float(df["performance_score"].mean()) if "performance_score" in df else 0

    upload_dates = pd.to_datetime(df["published_at"], errors="coerce", utc=True).dropna() if "published_at" in df else []
    if len(upload_dates) >= 2:
        date_span = (upload_dates.max() - upload_dates.min()).days + 1
        uploads_per_week = round(len(upload_dates) / max(date_span / 7, 1), 1)
    else:
        uploads_per_week = 0

    return {
        "avg_views": avg_views,
        "avg_engagement": avg_engagement,
        "avg_score": avg_score,
        "top_video": get_top_video_by_score(videos),
        "keywords": extract_title_keywords(videos),
        "uploads_per_week": uploads_per_week
    }


def build_video_executive_summary(video):
    score = safe_float(video.get("performance_score", 0))
    engagement = safe_float(video.get("engagement_rate", 0))
    views = safe_int(video.get("views", 0))
    title = normalize_text(video.get("title"), "this video")
    channel = normalize_text(video.get("channel_title"), "this channel")

    if views >= 1_000_000 and engagement < 1:
        finding = "This video achieved strong reach, but the engagement rate is low compared with the size of the audience it reached."
        recommendation = "Keep the broad topic appeal, but improve the hook and viewer interaction prompts so more viewers like, comment, or continue watching."
    elif score >= 65:
        finding = "This video shows healthy performance because the audience response is strong relative to its reach."
        recommendation = "Use this video as a repeatable template for future topics, titles, thumbnails, and pacing."
    elif score >= 45:
        finding = "This video has a workable foundation, but the engagement signals suggest the packaging or opening could be sharper."
        recommendation = "Test a clearer title promise, stronger first 15 seconds, and a thumbnail that makes the viewer payoff more obvious."
    else:
        finding = "This video is getting limited interaction relative to its view count, which means the topic may attract clicks without creating enough viewer response."
        recommendation = "Rework the title, thumbnail, and opening structure around a more specific emotional or curiosity-driven promise."

    return [
        f"Video reviewed: {title} from {channel}.",
        f"Performance read: {score}/100 ({score_tone(score)}) with {format_number(views)} views and {engagement}% engagement.",
        f"Key finding: {finding}",
        f"Primary recommendation: {recommendation}"
    ]


def build_channel_executive_summary(channel, scorecard, videos):
    signals = get_channel_signal_summary(videos)
    top_video = signals["top_video"]
    top_title = top_video.get("title") if top_video else "No standout video detected yet"
    keywords = ", ".join(signals["keywords"]) if signals["keywords"] else "not enough title pattern data"

    strengths = []
    risks = []

    if safe_float(scorecard.get("consistency_score", 0)) >= 70:
        strengths.append("Consistent upload activity")
    else:
        risks.append("Upload consistency needs improvement")

    if safe_float(scorecard.get("audience_pull_score", 0)) >= 70:
        strengths.append("Strong audience pull relative to subscriber base")
    else:
        risks.append("Audience pull is not yet converting strongly")

    if safe_float(scorecard.get("engagement_score", 0)) < 50:
        risks.append("Engagement is the main growth bottleneck")
    else:
        strengths.append("Engagement signals are healthy")

    if safe_float(scorecard.get("content_depth_score", 0)) < 40:
        risks.append("Comments are low compared with likes, so deeper discussion is limited")

    strengths_text = ", ".join(strengths) if strengths else "The channel has enough recent data to identify repeatable content patterns"
    risks_text = ", ".join(risks) if risks else "No major weakness detected from the current recent-video sample"

    return [
        f"Overall creator score: {scorecard.get('overall_score', 0)}/100 ({scorecard.get('grade', 'N/A')}).",
        f"Key strengths: {strengths_text}.",
        f"Main risks: {risks_text}.",
        f"Top recent signal: {top_title}. Recurring title themes detected: {keywords}.",
        "Primary recommendation: double down on the highest-scoring recent formats while improving packaging and comment triggers."
    ]


def build_strategy_executive_summary(channel, videos):
    signals = get_channel_signal_summary(videos)
    top_video = signals["top_video"]
    top_title = top_video.get("title") if top_video else "No standout video detected yet"
    keywords = ", ".join(signals["keywords"]) if signals["keywords"] else "not enough recurring theme data"

    cadence = signals["uploads_per_week"]
    if cadence >= 3:
        cadence_note = f"The recent cadence is aggressive at about {cadence} uploads per week, so the priority is quality control and repeatable series design."
    elif cadence > 0:
        cadence_note = f"The recent cadence is about {cadence} uploads per week, so the channel can grow by making each upload more strategically repeatable."
    else:
        cadence_note = "There is not enough upload-date data to estimate cadence."

    return [
        f"Strategic focus: turn the strongest recent content patterns into repeatable series instead of treating each upload as a separate experiment.",
        f"Best current signal: {top_title}.",
        f"Detected content themes: {keywords}.",
        cadence_note,
        "Primary recommendation: create a 70/20/10 system: 70% proven formats, 20% adjacent experiments, and 10% bold new tests."
    ]


def build_dna_executive_summary(channel, videos):
    signals = get_channel_signal_summary(videos)
    top_video = signals["top_video"]
    top_title = top_video.get("title") if top_video else "No standout video detected yet"
    keywords = ", ".join(signals["keywords"]) if signals["keywords"] else "not enough recurring theme data"

    return [
        f"Channel identity: {channel.get('title', 'This channel')} is strongest when the viewer can instantly recognize the topic, format, or emotional payoff.",
        f"Winning signal: {top_title}.",
        f"Recurring DNA themes: {keywords}.",
        f"Audience behavior: the current data suggests viewers respond best to recognizable topics, familiar names, and easy-to-understand video promises.",
        "Primary recommendation: convert the strongest repeated themes into named series so the channel becomes easier to remember and return to."
    ]


def build_smart_video_fallback(video, transcript):
    title = normalize_text(video.get("title"), "this video")
    channel = normalize_text(video.get("channel_title"), "this channel")
    views = safe_int(video.get("views", 0))
    likes = safe_int(video.get("likes", 0))
    comments = safe_int(video.get("comments", 0))
    engagement = safe_float(video.get("engagement_rate", 0))
    score = safe_float(video.get("performance_score", 0))

    transcript_signal = "The transcript was available, so the analysis can consider both metadata and spoken content." if transcript else "Transcript was unavailable, so this read is based on title, description, and performance signals."

    if views >= 1_000_000 and engagement < 1:
        performance_read = "The video has strong reach but weak interaction density. That usually means the topic or recognizable name attracted viewers, but the structure did not create enough reasons to react."
    elif engagement >= 4:
        performance_read = "The engagement rate is strong, which suggests the video gave viewers a reason to respond rather than only watch passively."
    elif score >= 45:
        performance_read = "The video has moderate performance signals. It likely has a clickable idea, but the title, hook, or pacing can be sharpened to drive more interaction."
    else:
        performance_read = "The video is underperforming on blended engagement signals. The idea may need clearer packaging, a stronger payoff, or a more immediate opening hook."

    return {
        "content_style": f"{title} is positioned as a focused YouTube video from {channel}, built around a clear topic that viewers can understand quickly. {transcript_signal} The format should be judged by how quickly it communicates the payoff and whether the first moments match the promise made by the title.",
        "target_audience": f"The likely audience includes viewers already interested in the subject, fans of {channel}, and casual users who click because the title suggests a familiar or high-interest moment. The video is most likely to work when the thumbnail and opening make the payoff obvious before the viewer has to think too much.",
        "why_it_performs": f"{performance_read} The video has {format_number(views)} views, {format_number(likes)} likes, {format_number(comments)} comments, and a {engagement}% engagement rate, giving it a performance score of {score}/100.",
        "improvement_suggestion": "Improve the first 15 seconds by clearly stating or showing the payoff immediately. Make the title more specific, strengthen the thumbnail contrast, and add a natural comment trigger near the most emotional, surprising, or useful moment."
    }


def build_smart_growth_fallback(channel, videos):
    signals = get_channel_signal_summary(videos)
    top_video = signals["top_video"]
    top_title = top_video.get("title") if top_video else "the strongest recent upload"
    keywords = ", ".join(signals["keywords"]) if signals["keywords"] else "the highest-performing recent topics"

    return {
        "positioning": f"Position {channel.get('title', 'this channel')} around the clearest repeatable promise visible in recent uploads. The strongest strategic signal is {top_title}, which should be studied as a template for topic selection, title framing, and viewer expectation. Instead of chasing unrelated trends, the channel should build a recognizable content lane around {keywords}.",
        "content_pillars": [
            f"Repeatable winners: build more videos around themes similar to {top_title}, because recent performance suggests that familiar topics and clear framing are easier for viewers to click.",
            f"Search and discovery: create videos around recurring title themes such as {keywords}, using searchable phrases like explained, best moments, ranking, breakdown, or why it worked.",
            "Community-led content: turn recurring comments, fan debates, and audience questions into videos so viewers feel directly involved in the channel direction.",
            "Packaging experiments: test stronger title promises and thumbnail layouts while keeping the underlying topic close to proven winners."
        ],
        "growth_moves": [
            "Create 2-3 named recurring series so subscribers know what kind of video is coming next.",
            "Use the top five recent videos as templates for new titles rather than starting from scratch for each upload.",
            "Add stronger opening hooks that confirm the title promise within the first 10-15 seconds.",
            "Track performance by format, not only by video, so weak experiments can be stopped quickly and winners can be repeated."
        ],
        "upload_strategy": f"The recent upload cadence is approximately {signals['uploads_per_week']} videos per week based on the analyzed sample. A strong plan is to publish mostly proven formats, with one controlled experiment after every few safe uploads. Review results every 10-15 videos and keep only the formats that beat the channel average for engagement and performance score.",
        "next_5_video_ideas": [
            f"A sequel or follow-up to {top_title} with a sharper title promise.",
            f"A ranking video built around {keywords}.",
            "A short breakdown explaining why the strongest recent video worked.",
            "A compilation or analysis video built around the most recognizable recurring topic.",
            "A community-response video based on comments or fan debate from recent uploads."
        ]
    }


def build_smart_dna_fallback(channel, videos):
    signals = get_channel_signal_summary(videos)
    top_video = signals["top_video"]
    top_title = top_video.get("title") if top_video else "the strongest recent upload"
    keywords = ", ".join(signals["keywords"]) if signals["keywords"] else "the recurring topics in recent uploads"

    return {
        "primary_content_style": f"{channel.get('title', 'This channel')}'s content DNA is strongest when the topic is instantly recognizable and the viewer can quickly understand the payoff. Recent uploads suggest that the channel should lean into familiar subjects, clear emotional hooks, and repeatable formats rather than disconnected one-off ideas. The strongest recent signal is {top_title}, which should be treated as a clue for what the audience already understands and values.",
        "winning_content_patterns": [
            f"Videos related to {keywords} appear to create a clearer identity because viewers can quickly understand the subject before clicking.",
            f"The strongest recent upload, {top_title}, should be reverse-engineered for topic angle, title structure, and audience expectation.",
            "Videos with recognizable names, moments, or themes are easier to package and more likely to create repeat viewing.",
            "Content that invites debate, nostalgia, ranking, or comparison can improve comment depth and community value."
        ],
        "growth_opportunities": [
            "Turn the strongest recurring themes into named series so the channel feels more predictable and memorable.",
            "Improve titles by making the emotional or curiosity payoff visible in the first few words.",
            "Create more follow-ups to top performers instead of constantly testing unrelated formats.",
            "Use comments from recent uploads as raw material for future videos, especially when viewers debate characters, rankings, scenes, or opinions."
        ],
        "upload_strategy": f"The channel should use a consistent weekly rhythm built around proven content patterns. Based on the analyzed upload sample, the current cadence is about {signals['uploads_per_week']} videos per week. Keep most uploads close to known winners, then use occasional experiments to test new angles without confusing the audience.",
        "audience_profile": "The likely audience wants fast recognition, clear payoff, and content that connects to topics they already care about. They probably respond well to familiar names, memorable moments, rankings, debates, and clips or analysis that feel easy to share. The more clearly each upload signals why it matters, the easier it becomes for casual viewers to click and returning viewers to build a habit."
    }


# =========================================================
# YOUTUBE HELPERS
# =========================================================

def youtube_get(endpoint, params):
    if not YOUTUBE_API_KEY:
        st.error("Missing YOUTUBE_API_KEY in Streamlit secrets.")
        st.stop()

    params = dict(params)
    params["key"] = YOUTUBE_API_KEY
    response = requests.get(f"{YOUTUBE_BASE_URL}/{endpoint}", params=params, timeout=20)

    if response.status_code != 200:
        st.error(f"YouTube API error: {response.text}")
        st.stop()

    return response.json()


def extract_video_id(url):
    try:
        parsed = urlparse(url)

        if parsed.hostname in ["youtu.be"]:
            return parsed.path.strip("/")

        if parsed.hostname and "youtube.com" in parsed.hostname:
            query = parse_qs(parsed.query)
            if "v" in query:
                return query["v"][0]

            shorts_match = re.search(r"/shorts/([^/?]+)", parsed.path)
            if shorts_match:
                return shorts_match.group(1)

            embed_match = re.search(r"/embed/([^/?]+)", parsed.path)
            if embed_match:
                return embed_match.group(1)
    except Exception:
        pass

    return None


@st.cache_data(ttl=3600, show_spinner=False)
def get_video_details(video_id):
    data = youtube_get(
        "videos",
        {
            "part": "snippet,statistics,contentDetails",
            "id": video_id
        }
    )

    items = data.get("items", [])
    if not items:
        return None

    item = items[0]
    snippet = item.get("snippet", {})
    stats = item.get("statistics", {})

    views = safe_int(stats.get("viewCount"))
    likes = safe_int(stats.get("likeCount"))
    comments = safe_int(stats.get("commentCount"))

    return {
        "video_id": video_id,
        "title": clean_text(snippet.get("title")),
        "description": clean_text(snippet.get("description")),
        "channel_title": snippet.get("channelTitle"),
        "channel_id": snippet.get("channelId"),
        "published_at": snippet.get("publishedAt"),
        "thumbnail": snippet.get("thumbnails", {}).get("high", {}).get("url"),
        "views": views,
        "likes": likes,
        "comments": comments,
        "engagement_rate": calculate_engagement_rate(likes, comments, views),
        "performance_score": calculate_video_score(views, likes, comments),
    }


@st.cache_data(ttl=3600, show_spinner=False)
def get_transcript(video_id):
    if YouTubeTranscriptApi is None:
        return ""

    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        text = " ".join([item.get("text", "") for item in transcript])
        return text[:6000]
    except Exception:
        return ""


@st.cache_data(ttl=3600, show_spinner=False)
def resolve_channel_id(channel_input):
    channel_input = channel_input.strip()

    if "watch?v=" in channel_input or "youtu.be" in channel_input or "/shorts/" in channel_input:
        video_id = extract_video_id(channel_input)
        video = get_video_details(video_id)
        return video["channel_id"] if video else None

    if "/channel/" in channel_input:
        return channel_input.split("/channel/")[-1].split("/")[0].split("?")[0]

    if "@" in channel_input:
        handle = channel_input.split("@")[-1].split("/")[0]
        data = youtube_get(
            "channels",
            {
                "part": "id",
                "forHandle": handle
            }
        )
        items = data.get("items", [])
        if items:
            return items[0]["id"]

    search_query = channel_input.replace("https://www.youtube.com/", "").replace("youtube.com/", "")
    data = youtube_get(
        "search",
        {
            "part": "snippet",
            "q": search_query,
            "type": "channel",
            "maxResults": 1
        }
    )

    items = data.get("items", [])
    if items:
        return items[0]["snippet"]["channelId"]

    return None


@st.cache_data(ttl=3600, show_spinner=False)
def get_channel_details(channel_id):
    data = youtube_get(
        "channels",
        {
            "part": "snippet,statistics,contentDetails",
            "id": channel_id
        }
    )

    items = data.get("items", [])
    if not items:
        return None

    item = items[0]
    snippet = item.get("snippet", {})
    stats = item.get("statistics", {})
    related = item.get("contentDetails", {}).get("relatedPlaylists", {})

    return {
        "channel_id": channel_id,
        "title": clean_text(snippet.get("title")),
        "description": clean_text(snippet.get("description")),
        "published_at": snippet.get("publishedAt"),
        "thumbnail": snippet.get("thumbnails", {}).get("high", {}).get("url"),
        "subscribers": safe_int(stats.get("subscriberCount")),
        "views": safe_int(stats.get("viewCount")),
        "video_count": safe_int(stats.get("videoCount")),
        "uploads_playlist_id": related.get("uploads")
    }


@st.cache_data(ttl=3600, show_spinner=False)
def get_recent_channel_videos(channel_id, max_results=20):
    channel = get_channel_details(channel_id)
    if not channel or not channel.get("uploads_playlist_id"):
        return []

    playlist_data = youtube_get(
        "playlistItems",
        {
            "part": "snippet",
            "playlistId": channel["uploads_playlist_id"],
            "maxResults": max_results
        }
    )

    video_ids = [
        item["snippet"]["resourceId"]["videoId"]
        for item in playlist_data.get("items", [])
        if item.get("snippet", {}).get("resourceId", {}).get("videoId")
    ]

    if not video_ids:
        return []

    details = youtube_get(
        "videos",
        {
            "part": "snippet,statistics,contentDetails",
            "id": ",".join(video_ids)
        }
    )

    videos = []
    for item in details.get("items", []):
        snippet = item.get("snippet", {})
        stats = item.get("statistics", {})

        views = safe_int(stats.get("viewCount"))
        likes = safe_int(stats.get("likeCount"))
        comments = safe_int(stats.get("commentCount"))

        videos.append({
            "video_id": item.get("id"),
            "title": clean_text(snippet.get("title")),
            "description": clean_text(snippet.get("description")),
            "published_at": snippet.get("publishedAt"),
            "views": views,
            "likes": likes,
            "comments": comments,
            "engagement_rate": calculate_engagement_rate(likes, comments, views),
            "performance_score": calculate_video_score(views, likes, comments),
            "thumbnail": snippet.get("thumbnails", {}).get("high", {}).get("url")
        })

    return videos


# =========================================================
# AI HELPER
# =========================================================

@st.cache_data(ttl=3600, show_spinner=False)
def generate_ai_json(prompt, fallback):
    if not NVIDIA_API_KEY:
        return fallback

    headers = {
        "Authorization": f"Bearer {NVIDIA_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "meta/llama-3.1-70b-instruct",
        "messages": [
            {
                "role": "system",
                "content": "You are a YouTube analytics strategist. Return only valid JSON. No markdown."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.4,
        "max_tokens": 1200
    }

    try:
        response = requests.post(NVIDIA_URL, headers=headers, json=payload, timeout=30)
        if response.status_code != 200:
            return fallback

        text = response.json()["choices"][0]["message"]["content"]
        parsed = extract_json(text)
        return parsed if parsed else fallback
    except Exception:
        return fallback


# =========================================================
# CREATOR SCORECARD
# =========================================================

def calculate_creator_scorecard(channel, videos):
    if not videos:
        return {
            "overall_score": 0,
            "grade": "N/A",
            "consistency_score": 0,
            "engagement_score": 0,
            "momentum_score": 0,
            "audience_pull_score": 0,
            "optimization_score": 0,
            "content_depth_score": 0,
            "verdict": "Not enough recent video data available."
        }

    df = pd.DataFrame(videos)

    avg_views = df["views"].mean()
    avg_engagement = df["engagement_rate"].mean()
    avg_video_score = df["performance_score"].mean()
    subscribers = channel.get("subscribers", 0)

    upload_dates = pd.to_datetime(df["published_at"], errors="coerce", utc=True).dropna()
    if len(upload_dates) >= 2:
        date_span = (upload_dates.max() - upload_dates.min()).days + 1
        uploads_per_week = len(upload_dates) / max(date_span / 7, 1)
    else:
        uploads_per_week = 0

    consistency_score = min(uploads_per_week / 3 * 100, 100)

    engagement_score = min(avg_engagement / 8 * 100, 100)

    if len(df) >= 6:
        recent_avg = df.head(5)["views"].mean()
        older_avg = df.tail(5)["views"].mean()
        momentum_score = min((recent_avg / max(older_avg, 1)) * 60, 100)
    else:
        momentum_score = min(avg_video_score, 100)

    audience_pull_score = min((avg_views / max(subscribers, 1)) * 1000, 100)

    title_scores = []
    for title in df["title"].fillna(""):
        score = 0
        if len(title) >= 35:
            score += 30
        if any(char.isdigit() for char in title):
            score += 20
        if any(word.lower() in title.lower() for word in ["why", "how", "best", "top", "explained", "secret", "moment", "scene"]):
            score += 25
        if len(title) <= 80:
            score += 25
        title_scores.append(score)

    optimization_score = sum(title_scores) / len(title_scores)

    content_depth_score = min((df["comments"].mean() / max(df["likes"].mean(), 1)) * 500, 100)

    overall = (
        consistency_score * 0.18 +
        engagement_score * 0.22 +
        momentum_score * 0.20 +
        audience_pull_score * 0.15 +
        optimization_score * 0.15 +
        content_depth_score * 0.10
    )

    overall = round(overall, 1)

    if overall >= 85:
        grade = "A+"
        verdict = "Excellent creator health. The channel has strong audience pull, engagement, and growth signals."
    elif overall >= 75:
        grade = "A"
        verdict = "Strong creator health. The channel is performing well with room to improve consistency or packaging."
    elif overall >= 65:
        grade = "B"
        verdict = "Good foundation. The channel has clear potential but needs stronger repeatable content systems."
    elif overall >= 50:
        grade = "C"
        verdict = "Moderate creator health. The channel needs better content packaging, consistency, and audience retention signals."
    else:
        grade = "D"
        verdict = "Weak creator health right now. Focus on consistency, stronger titles, and clearer content positioning."

    return {
        "overall_score": overall,
        "grade": grade,
        "consistency_score": round(consistency_score, 1),
        "engagement_score": round(engagement_score, 1),
        "momentum_score": round(momentum_score, 1),
        "audience_pull_score": round(audience_pull_score, 1),
        "optimization_score": round(optimization_score, 1),
        "content_depth_score": round(content_depth_score, 1),
        "verdict": verdict
    }


def render_creator_scorecard(scorecard):
    st.subheader("Creator Scorecard")

    col1, col2, col3 = st.columns([1.2, 1, 2])

    with col1:
        st.markdown(
            f"""
            <div class="score-card">
                <div class="small-muted">Overall Creator Score</div>
                <h1 style="font-size:56px;margin:8px 0;">{scorecard["overall_score"]}</h1>
                <h2 style="margin:0;">Grade: {scorecard["grade"]}</h2>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col2:
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=scorecard["overall_score"],
            gauge={"axis": {"range": [0, 100]}},
            number={"suffix": "/100"}
        ))
        fig.update_layout(
            height=260,
            margin=dict(l=20, r=20, t=20, b=20),
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#f8fafc")
        )
        st.plotly_chart(fig, width="stretch")

    with col3:
        st.markdown(
            f"""
            <div class="insight-card">
                <h4>Scorecard Verdict</h4>
                <p>{scorecard["verdict"]}</p>
            </div>
            """,
            unsafe_allow_html=True
        )

    score_df = pd.DataFrame({
        "Category": [
            "Consistency",
            "Engagement",
            "Momentum",
            "Audience Pull",
            "Packaging / Optimization",
            "Content Depth"
        ],
        "Score": [
            scorecard["consistency_score"],
            scorecard["engagement_score"],
            scorecard["momentum_score"],
            scorecard["audience_pull_score"],
            scorecard["optimization_score"],
            scorecard["content_depth_score"]
        ]
    })

    fig = px.bar(
        score_df,
        x="Category",
        y="Score",
        text="Score",
        range_y=[0, 100],
        title="Creator Score Breakdown"
    )
    fig.update_traces(textposition="outside", hovertemplate="%{x}<br>Creator score: %{y}/100<extra></extra>")
    fig = style_chart(fig, x_title="Creator Scorecard Category", y_title="Score out of 100", height=430)
    st.plotly_chart(fig, width="stretch")




def style_chart(fig, x_title=None, y_title=None, height=None):
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(15, 23, 42, 0.55)",
        font=dict(color="#e5e7eb", size=13),
        title_font=dict(color="#f8fafc", size=20),
        legend_title_text="Metric",
        margin=dict(l=40, r=30, t=70, b=50),
        hoverlabel=dict(
            bgcolor="#0f172a",
            font_size=13,
            font_color="#f8fafc"
        )
    )
    fig.update_xaxes(
        title_text=x_title,
        gridcolor="rgba(148, 163, 184, 0.16)",
        zerolinecolor="rgba(148, 163, 184, 0.18)"
    )
    fig.update_yaxes(
        title_text=y_title,
        gridcolor="rgba(148, 163, 184, 0.16)",
        zerolinecolor="rgba(148, 163, 184, 0.18)"
    )
    if height:
        fig.update_layout(height=height)
    return fig

# =========================================================
# AI INSIGHTS
# =========================================================

@st.cache_data(ttl=3600, show_spinner=False)
def get_video_ai_insights(video, transcript):
    fallback = build_smart_video_fallback(video, transcript)

    prompt = f"""
    You are Stratify, a premium YouTube content strategist.
    Analyze this video deeply and write useful product-style insights.

    Video title: {video["title"]}
    Description: {video["description"][:1800]}
    Views: {video["views"]}
    Likes: {video["likes"]}
    Comments: {video["comments"]}
    Engagement Rate: {video["engagement_rate"]}%
    Transcript context: {transcript[:4500] if transcript else "Transcript unavailable. Use metadata and performance signals."}

    Return ONLY valid JSON with these exact keys:
    {{
      "content_style": "2-4 detailed sentences explaining the actual content style, format, and viewer experience.",
      "target_audience": "2-4 detailed sentences describing who this is for and why they would click.",
      "why_it_performs": "2-4 detailed sentences explaining performance drivers using the metrics and content angle.",
      "improvement_suggestion": "2-4 detailed sentences with specific, practical improvements for title, hook, thumbnail, or structure."
    }}

    Do not use one-line answers. Do not return N/A. Do not use markdown.
    """

    result = generate_ai_json(prompt, fallback)
    return {**fallback, **(result or {})}


@st.cache_data(ttl=3600, show_spinner=False)
def get_growth_strategy(channel, videos):
    fallback = build_smart_growth_fallback(channel, videos)

    video_summary = "\n".join([
        f"- {v['title']} | Views: {v['views']} | Likes: {v['likes']} | Comments: {v['comments']} | Engagement: {v['engagement_rate']}% | Score: {v['performance_score']}"
        for v in videos[:18]
    ])

    prompt = f"""
    You are Stratify, a premium YouTube growth strategist.
    Create a detailed growth strategy for this creator using the recent video data.

    Channel: {channel["title"]}
    Description: {channel["description"][:1200]}
    Subscribers: {channel["subscribers"]}
    Total Views: {channel["views"]}
    Video Count: {channel["video_count"]}

    Recent Videos:
    {video_summary}

    Return ONLY valid JSON with these exact keys:
    {{
      "positioning": "A detailed paragraph of 3-5 sentences explaining the channel's best strategic positioning.",
      "content_pillars": ["3-5 detailed bullet points. Each bullet must be a full sentence with strategic reasoning.", "...", "..."],
      "growth_moves": ["4-6 detailed action steps. Each step must explain what to do and why.", "...", "..."],
      "upload_strategy": "A detailed 3-5 sentence upload plan with cadence, experiment ratio, and review cycle.",
      "next_5_video_ideas": ["Five specific video ideas tailored to this channel, not generic one-liners.", "...", "...", "...", "..."]
    }}

    Do not return one-liners. Do not return N/A. Do not use markdown. Make it feel like a premium consulting report.
    """

    result = generate_ai_json(prompt, fallback)
    return {**fallback, **(result or {})}


@st.cache_data(ttl=3600, show_spinner=False)
def get_channel_dna(channel, videos):
    fallback = build_smart_dna_fallback(channel, videos)

    video_summary = "\n".join([
        f"- {v['title']} | Views: {v['views']} | Likes: {v['likes']} | Comments: {v['comments']} | Engagement: {v['engagement_rate']}% | Score: {v['performance_score']}"
        for v in videos[:20]
    ])

    prompt = f"""
    You are Stratify, a premium YouTube channel DNA analyst.
    Analyze the channel identity, winning patterns, audience psychology, and growth opportunities.

    Channel: {channel["title"]}
    Description: {channel["description"][:1400]}
    Subscribers: {channel["subscribers"]}
    Total Views: {channel["views"]}
    Total Videos: {channel["video_count"]}

    Recent Videos:
    {video_summary}

    Return ONLY valid JSON with these exact keys:
    {{
      "primary_content_style": "A detailed paragraph of 3-5 sentences describing the channel's content DNA and format identity.",
      "winning_content_patterns": ["4-6 detailed patterns. Each must explain the pattern and why it works.", "...", "..."],
      "growth_opportunities": ["4-6 detailed opportunities with specific actions.", "...", "..."],
      "upload_strategy": "A detailed 3-5 sentence strategy explaining cadence, content mix, and experimentation.",
      "audience_profile": "A detailed 3-5 sentence audience profile including motivations, interests, and click triggers."
    }}

    Do not return one-liners. Do not return N/A. Do not use markdown. Make it feel like a premium channel report.
    """

    result = generate_ai_json(prompt, fallback)
    return {**fallback, **(result or {})}


# =========================================================
# UI COMPONENTS
# =========================================================

def render_metric_card(label, value):
    st.markdown(
        f"""
        <div class="metric-card">
            <h3>{label}</h3>
            <h2>{value}</h2>
        </div>
        """,
        unsafe_allow_html=True
    )


def normalize_text(value, fallback="Not available yet."):
    if value is None:
        return fallback
    if isinstance(value, list):
        value = "\n".join([str(v) for v in value if str(v).strip()])
    value = str(value).strip()
    if not value or value.lower() in ["n/a", "na", "none", "null"]:
        return fallback
    return value


def render_ai_insight(title, value):
    safe_title = escape(normalize_text(title, "Insight"))
    safe_value = escape(normalize_text(value))
    st.markdown(
        f"""
        <div class="insight-card">
            <h4>{safe_title}</h4>
            <p>{safe_value}</p>
        </div>
        """,
        unsafe_allow_html=True
    )


def render_list(title, items):
    st.markdown(f"### {escape(str(title))}")
    if not items:
        items = ["Not enough signal available yet. Analyze more recent videos to generate stronger recommendations."]
    for item in items:
        st.markdown(
            f"""
            <div class="dna-list-item">
                {escape(normalize_text(item))}
            </div>
            """,
            unsafe_allow_html=True
        )

# =========================================================
# EXPORT HELPERS - PDF
# =========================================================

def pdf_clean(value, fallback="Not available"):
    return escape(normalize_text(value, fallback)).replace("\n", "<br/>")


def pdf_bullet(value):
    return "• " + pdf_clean(value)


def format_pdf_date(value):
    if not value:
        return "Not available"
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt.strftime("%B %d, %Y")
    except Exception:
        return str(value)


def format_pdf_metric_value(key, value):
    key_text = str(key).lower()
    if "published" in key_text:
        return format_pdf_date(value)
    return normalize_text(value, "Not available")


def make_pdf_report(title, sections, metrics=None):
    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.55 * inch,
        leftMargin=0.55 * inch,
        topMargin=0.42 * inch,
        bottomMargin=0.55 * inch
    )

    page_width = letter[0] - doc.leftMargin - doc.rightMargin
    styles = getSampleStyleSheet()

    brand_style = ParagraphStyle(
        "StratifyBrand",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=25,
        leading=28,
        textColor=colors.white,
        spaceAfter=1
    )

    tagline_style = ParagraphStyle(
        "StratifyTagline",
        parent=styles["Normal"],
        fontSize=9.5,
        leading=12,
        textColor=colors.HexColor("#dbeafe")
    )

    title_style = ParagraphStyle(
        "StratifyReportTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=23,
        leading=28,
        textColor=colors.HexColor("#0f172a"),
        alignment=0,
        spaceBefore=16,
        spaceAfter=5
    )

    intro_style = ParagraphStyle(
        "StratifyIntro",
        parent=styles["BodyText"],
        fontSize=10.2,
        leading=14,
        textColor=colors.HexColor("#64748b"),
        spaceAfter=14
    )

    eyebrow_style = ParagraphStyle(
        "StratifyEyebrow",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=10,
        textColor=colors.HexColor("#0369a1"),
        spaceAfter=0
    )

    label_style = ParagraphStyle(
        "StratifyLabel",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=10.5,
        textColor=colors.HexColor("#64748b")
    )

    value_style = ParagraphStyle(
        "StratifyValue",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11.2,
        leading=13.5,
        textColor=colors.HexColor("#0f172a")
    )

    overview_value_style = ParagraphStyle(
        "StratifyOverviewValue",
        parent=styles["Normal"],
        fontSize=10.2,
        leading=13,
        textColor=colors.HexColor("#111827")
    )

    heading_style = ParagraphStyle(
        "StratifySectionHeading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=13.5,
        leading=17,
        textColor=colors.HexColor("#0f172a"),
        spaceBefore=2,
        spaceAfter=6
    )

    body_style = ParagraphStyle(
        "StratifyBody",
        parent=styles["BodyText"],
        fontSize=10.1,
        leading=14.7,
        textColor=colors.HexColor("#1f2937"),
        spaceAfter=6
    )

    bullet_style = ParagraphStyle(
        "StratifyBullet",
        parent=body_style,
        leftIndent=12,
        firstLineIndent=-8,
        spaceAfter=5
    )

    footer_style = ParagraphStyle(
        "StratifyFooter",
        parent=styles["Normal"],
        fontSize=8.5,
        leading=10,
        textColor=colors.HexColor("#94a3b8"),
        alignment=1
    )

    story = []

    # Clean PDF header: icon + report title only.
    # Website header is untouched.
    logo_flowable = ""
    try:
        if APP_ICON_PATH:
            logo_flowable = RLImage(
                str(APP_ICON_PATH),
                width=0.58 * inch,
                height=0.58 * inch
            )
    except Exception:
        logo_flowable = ""

    brand_copy = [
        Paragraph(pdf_clean(title), brand_style),
    ]

    if logo_flowable:
        header = Table(
            [[logo_flowable, brand_copy]],
            colWidths=[0.90 * inch, page_width - 0.90 * inch],
            rowHeights=[0.78 * inch]
        )
    else:
        header = Table([[brand_copy]], colWidths=[page_width], rowHeights=[0.78 * inch])

    header.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#0f172a")),
        ("LINEBELOW", (0, 0), (-1, -1), 3, colors.HexColor("#22c55e")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (0, 0), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 16),
        ("RIGHTPADDING", (0, 0), (-1, -1), 16),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(header)

    story.append(Paragraph(
        "Premium YouTube intelligence report built from performance signals, creator patterns, and strategic recommendations.",
        intro_style
    ))

    if metrics:
        overview_keys = [
            key for key in ["Video", "Channel", "Published"]
            if key in metrics
        ]
        kpi_items = [(key, value) for key, value in metrics.items() if key not in overview_keys]

        if overview_keys:
            overview_rows = [[Paragraph("REPORT OVERVIEW", eyebrow_style), ""]]
            for key in overview_keys:
                overview_rows.append([
                    Paragraph(pdf_clean(key), label_style),
                    Paragraph(pdf_clean(format_pdf_metric_value(key, metrics.get(key))), overview_value_style)
                ])

            overview_table = Table(
                overview_rows,
                colWidths=[1.25 * inch, page_width - 1.25 * inch],
                hAlign="CENTER"
            )
            overview_table.setStyle(TableStyle([
                ("SPAN", (0, 0), (-1, 0)),
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#dbeafe")),
                ("LINEBELOW", (0, 0), (-1, 0), 0.7, colors.HexColor("#dbeafe")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]))
            story.append(overview_table)
            story.append(Spacer(1, 10))

        if kpi_items:
            kpi_cards = []
            for key, value in kpi_items:
                card = Table(
                    [[Paragraph(pdf_clean(key), label_style)],
                     [Paragraph(pdf_clean(format_pdf_metric_value(key, value)), value_style)]],
                    colWidths=[1.55 * inch],
                    rowHeights=[0.26 * inch, 0.30 * inch]
                )
                card.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f1f5f9")),
                    ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#dbeafe")),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 9),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]))
                kpi_cards.append(card)

            rows = []
            for i in range(0, len(kpi_cards), 4):
                row = kpi_cards[i:i + 4]
                while len(row) < 4:
                    row.append("")
                rows.append(row)

            kpi_grid = Table(
                rows,
                colWidths=[page_width / 4] * 4,
                hAlign="CENTER"
            )
            kpi_grid.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]))
            story.append(kpi_grid)
            story.append(Spacer(1, 12))

    for section_title, section_content in sections:
        section_story = [Paragraph(pdf_clean(section_title), heading_style)]

        if isinstance(section_content, list):
            cleaned_items = section_content or ["Not enough signal available yet."]
            for item in cleaned_items:
                section_story.append(Paragraph(pdf_bullet(item), bullet_style))
        else:
            section_story.append(Paragraph(pdf_clean(section_content), body_style))

        section_table = Table([[section_story]], colWidths=[page_width], hAlign="CENTER")
        section_bg = colors.HexColor("#f8fafc") if str(section_title).lower() == "executive summary" else colors.white
        section_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), section_bg),
            ("LINEABOVE", (0, 0), (-1, -1), 0.8, colors.HexColor("#e2e8f0")),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 9),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(section_table)
        story.append(Spacer(1, 6))

    story.append(Spacer(1, 8))
    story.append(Paragraph(
        f"Generated by Stratify - {datetime.now().strftime('%B %d, %Y')}",
        footer_style
    ))

    doc.build(story)
    pdf = buffer.getvalue()
    buffer.close()
    return pdf

def build_video_report(video, insights):
    metrics = {
        "Video": video.get("title"),
        "Channel": video.get("channel_title"),
        "Published": format_date(video.get("published_at")),
        "Views": format_number(video.get("views", 0)),
        "Likes": format_number(video.get("likes", 0)),
        "Comments": format_number(video.get("comments", 0)),
        "Engagement Rate": f"{video.get('engagement_rate', 0)}%",
        "Performance Score": f"{video.get('performance_score', 0)}/100",
    }

    sections = [
        ("Executive Summary", build_video_executive_summary(video)),
        ("Content Style", insights.get("content_style")),
        ("Target Audience", insights.get("target_audience")),
        ("Why It Performs", insights.get("why_it_performs")),
        ("Improvement Suggestion", insights.get("improvement_suggestion")),
    ]

    return make_pdf_report("Single Video Analysis Report", sections, metrics)


def build_channel_report(channel, scorecard, videos):
    metrics = {
        "Channel": channel.get("title"),
        "Subscribers": format_number(channel.get("subscribers", 0)),
        "Total Views": format_number(channel.get("views", 0)),
        "Total Videos": format_number(channel.get("video_count", 0)),
        "Overall Creator Score": f"{scorecard.get('overall_score', 0)}/100",
        "Grade": scorecard.get("grade", "N/A"),
        "Consistency": f"{scorecard.get('consistency_score', 0)}/100",
        "Engagement": f"{scorecard.get('engagement_score', 0)}/100",
        "Momentum": f"{scorecard.get('momentum_score', 0)}/100",
        "Audience Pull": f"{scorecard.get('audience_pull_score', 0)}/100",
        "Packaging / Optimization": f"{scorecard.get('optimization_score', 0)}/100",
        "Content Depth": f"{scorecard.get('content_depth_score', 0)}/100",
    }

    top_videos = []
    if videos:
        df = pd.DataFrame(videos)
        top = df.sort_values("performance_score", ascending=False).head(10)
        for _, row in top.iterrows():
            top_videos.append(
                f"{row['title']} | Views: {format_number(row['views'])} | "
                f"Engagement: {row['engagement_rate']}% | Score: {row['performance_score']}/100"
            )

    sections = [
        ("Executive Summary", build_channel_executive_summary(channel, scorecard, videos)),
        ("Creator Scorecard Verdict", scorecard.get("verdict")),
        ("Top Recent Videos", top_videos if top_videos else ["No recent video data available."]),
    ]

    return make_pdf_report("Channel Intelligence Report", sections, metrics)


def build_strategy_report(channel, strategy, videos=None):
    metrics = {
        "Channel": channel.get("title"),
        "Subscribers": format_number(channel.get("subscribers", 0)),
        "Total Views": format_number(channel.get("views", 0)),
        "Total Videos": format_number(channel.get("video_count", 0)),
    }

    sections = [
        ("Executive Summary", build_strategy_executive_summary(channel, videos or [])),
        ("Recommended Positioning", strategy.get("positioning")),
        ("Content Pillars", strategy.get("content_pillars", [])),
        ("Growth Moves", strategy.get("growth_moves", [])),
        ("Upload Strategy", strategy.get("upload_strategy")),
        ("Next 5 Video Ideas", strategy.get("next_5_video_ideas", [])),
    ]

    return make_pdf_report("Growth Strategy Report", sections, metrics)


def build_dna_report(channel, dna, videos=None):
    metrics = {
        "Channel": channel.get("title"),
        "Subscribers": format_number(channel.get("subscribers", 0)),
        "Total Views": format_number(channel.get("views", 0)),
        "Total Videos": format_number(channel.get("video_count", 0)),
    }

    sections = [
        ("Executive Summary", build_dna_executive_summary(channel, videos or [])),
        ("Primary Content Style", dna.get("primary_content_style")),
        ("Winning Content Patterns", dna.get("winning_content_patterns", [])),
        ("Growth Opportunities", dna.get("growth_opportunities", [])),
        ("Upload Strategy", dna.get("upload_strategy")),
        ("Audience Profile", dna.get("audience_profile")),
    ]

    return make_pdf_report("Channel DNA Report", sections, metrics)


# =========================================================
# PAGE HEADER
# =========================================================

if APP_ICON_PATH:
    # Website header: restored to the clean big-logo layout.
    # PDF branding is handled only inside make_pdf_report().
    header_col1, header_col2 = st.columns([1.05, 6.5])

    with header_col1:
        st.image(str(APP_ICON_PATH), width=130)

    with header_col2:
        st.markdown(
            """
            <div class="main-title">Stratify</div>
            <div class="sub-title">See What Works. Create What Wins.</div>
            """,
            unsafe_allow_html=True
        )
else:
    st.markdown('<div class="main-title">Stratify</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">See What Works. Create What Wins.</div>', unsafe_allow_html=True)

tabs = st.tabs([
    "Single Video Analysis",
    "Channel Intelligence",
    "Video Comparison",
    "Growth Strategy Generator",
    "Channel DNA Analysis"
])


# =========================================================
# TAB 1: SINGLE VIDEO ANALYSIS
# =========================================================

with tabs[0]:
    st.header("Single Video Analysis")

    video_url = st.text_input("Paste a YouTube video link", key="single_video_url")

    if st.button("Analyze Video", width="stretch"):
        if not video_url.strip():
            st.warning("Please paste a YouTube video link.")
            st.stop()

        video_id = extract_video_id(video_url)
        if not video_id:
            st.error("Could not detect a valid YouTube video ID.")
            st.stop()

        with st.spinner("Analyzing video..."):
            video = get_video_details(video_id)
            transcript = get_transcript(video_id)

        if not video:
            st.error("Video not found.")
            st.stop()

        col1, col2 = st.columns([1, 2])

        with col1:
            if video["thumbnail"]:
                st.image(video["thumbnail"], width="stretch")

        with col2:
            st.subheader(video["title"])
            st.caption(f"Channel: {video['channel_title']}")
            st.caption(f"Published: {video['published_at']}")

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            render_metric_card("Views", format_number(video["views"]))
        with c2:
            render_metric_card("Likes", format_number(video["likes"]))
        with c3:
            render_metric_card("Comments", format_number(video["comments"]))
        with c4:
            render_metric_card("Performance Score", f"{video['performance_score']}/100")

        st.subheader("Engagement Summary")
        engagement_df = pd.DataFrame({
            "Metric": ["Likes", "Comments"],
            "Count": [video["likes"], video["comments"]]
        })
        fig = px.bar(
            engagement_df,
            x="Metric",
            y="Count",
            text="Count",
            title="Engagement Volume",
            labels={"Metric": "Engagement Type", "Count": "Number of Interactions"}
        )
        fig.update_traces(hovertemplate="%{x}<br>Interactions: %{y:,}<extra></extra>")
        fig = style_chart(fig, x_title="Engagement Type", y_title="Number of Interactions", height=420)
        st.plotly_chart(fig, width="stretch")

        with st.spinner("Generating insights..."):
            insights = get_video_ai_insights(video, transcript)

        st.subheader("AI Insights")
        render_ai_insight("Content Style", insights.get("content_style", "Not available"))
        render_ai_insight("Target Audience", insights.get("target_audience", "Not available"))
        render_ai_insight("Why It Performs", insights.get("why_it_performs", "Not available"))
        render_ai_insight("Improvement Suggestion", insights.get("improvement_suggestion", "Not available"))

        st.download_button(
            "Download Video Analysis Report",
            data=build_video_report(video, insights),
            file_name="stratify_video_analysis.pdf",
            mime="application/pdf",
            width="stretch"
        )


# =========================================================
# TAB 2: CHANNEL INTELLIGENCE + CREATOR SCORECARD
# =========================================================

with tabs[1]:
    st.header("Channel Intelligence")

    channel_input = st.text_input(
        "Paste a channel link, @handle, channel name, or video link",
        key="channel_intelligence_input"
    )

    max_videos = st.slider("Number of recent videos to analyze", 5, 50, 20)

    if st.button("Analyze Channel", width="stretch"):
        if not channel_input.strip():
            st.warning("Please enter a channel link, handle, name, or video link.")
            st.stop()

        with st.spinner("Finding channel..."):
            channel_id = resolve_channel_id(channel_input)

        if not channel_id:
            st.error("Could not find the channel.")
            st.stop()

        with st.spinner("Analyzing channel..."):
            channel = get_channel_details(channel_id)
            videos = get_recent_channel_videos(channel_id, max_videos)

        if not channel:
            st.error("Channel details not found.")
            st.stop()

        col1, col2 = st.columns([1, 3])

        with col1:
            if channel["thumbnail"]:
                st.image(channel["thumbnail"], width="stretch")

        with col2:
            st.subheader(channel["title"])
            st.write(channel["description"][:500] + ("..." if len(channel["description"]) > 500 else ""))

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            render_metric_card("Subscribers", format_number(channel["subscribers"]))
        with c2:
            render_metric_card("Total Views", format_number(channel["views"]))
        with c3:
            render_metric_card("Videos", format_number(channel["video_count"]))
        with c4:
            avg_views = pd.DataFrame(videos)["views"].mean() if videos else 0
            render_metric_card("Avg Recent Views", format_number(avg_views))

        scorecard = calculate_creator_scorecard(channel, videos)
        render_creator_scorecard(scorecard)

        if videos:
            df = pd.DataFrame(videos)

            st.subheader("Recent Video Performance")

            fig = px.line(
                df.sort_values("published_at"),
                x="published_at",
                y="views",
                markers=True,
                title="Recent Views Trend",
                labels={"published_at": "Published Date", "views": "Views"}
            )
            fig.update_traces(hovertemplate="Published: %{x}<br>Views: %{y:,}<extra></extra>")
            fig = style_chart(fig, x_title="Published Date", y_title="Views", height=430)
            st.plotly_chart(fig, width="stretch")

            fig2 = px.scatter(
                df,
                x="views",
                y="engagement_rate",
                size="likes",
                hover_name="title",
                title="Views vs Engagement Rate",
                labels={"views": "Views", "engagement_rate": "Engagement Rate (%)", "likes": "Likes"}
            )
            fig2.update_traces(hovertemplate="%{hovertext}<br>Views: %{x:,}<br>Engagement Rate: %{y:.2f}%<br>Bubble size: likes<extra></extra>")
            fig2 = style_chart(fig2, x_title="Views", y_title="Engagement Rate (%)", height=430)
            st.plotly_chart(fig2, width="stretch")

            st.dataframe(
                df[[
                    "title",
                    "views",
                    "likes",
                    "comments",
                    "engagement_rate",
                    "performance_score",
                    "published_at"
                ]],
                width="stretch"
            )

            st.download_button(
                "Download Channel Intelligence Report",
                data=build_channel_report(channel, scorecard, videos),
                file_name="stratify_channel_intelligence.pdf",
                mime="application/pdf",
                width="stretch"
            )


# =========================================================
# TAB 3: VIDEO COMPARISON
# =========================================================

with tabs[2]:
    st.header("Video Comparison")
    st.caption("Compare videos side-by-side instead of pasting everything into one messy box.")

    compare_count = st.slider("How many videos do you want to compare?", 2, 6, 3)
    video_inputs = []

    for i in range(compare_count):
        video_inputs.append(
            st.text_input(
                f"Video {i + 1} link",
                key=f"compare_video_url_{i}",
                placeholder="Paste YouTube video URL here"
            )
        )

    if st.button("Compare Videos", width="stretch"):
        urls = [u.strip() for u in video_inputs if u.strip()]

        if len(urls) < 2:
            st.warning("Please enter at least 2 video links.")
            st.stop()

        videos = []

        with st.spinner("Comparing videos..."):
            for url in urls:
                video_id = extract_video_id(url)
                if video_id:
                    video = get_video_details(video_id)
                    if video:
                        videos.append(video)

        if len(videos) < 2:
            st.error("Could not find at least 2 valid videos.")
            st.stop()

        df = pd.DataFrame(videos)
        df["Likes per 1K Views"] = (df["likes"] / df["views"].replace(0, 1) * 1000).round(2)
        df["Comments per 1K Views"] = (df["comments"] / df["views"].replace(0, 1) * 1000).round(2)
        df["Performance Label"] = df["performance_score"].apply(classify_performance)

        winner = df.sort_values("performance_score", ascending=False).iloc[0]
        most_viewed = df.sort_values("views", ascending=False).iloc[0]
        best_engagement = df.sort_values("engagement_rate", ascending=False).iloc[0]

        st.subheader("Comparison Verdict")
        c1, c2, c3 = st.columns(3)
        with c1:
            render_metric_card("Best Overall", f"{winner['performance_score']}/100")
            st.caption(winner["title"])
        with c2:
            render_metric_card("Most Viewed", format_number(most_viewed["views"]))
            st.caption(most_viewed["title"])
        with c3:
            render_metric_card("Best Engagement", f"{best_engagement['engagement_rate']}%")
            st.caption(best_engagement["title"])

        render_ai_insight(
            "Strategic Read",
            f"{winner['title']} is the strongest overall video in this comparison because it has the best blended performance score. Views alone do not always show quality, so Stratify compares views, likes, comments, engagement rate, and interaction density. Use the winning video's topic, packaging, and structure as the closest template for the next upload."
        )

        st.subheader("Performance Table")
        st.dataframe(
            df[[
                "title",
                "channel_title",
                "views",
                "likes",
                "comments",
                "engagement_rate",
                "Likes per 1K Views",
                "Comments per 1K Views",
                "performance_score",
                "Performance Label"
            ]],
            width="stretch"
        )

        fig = px.bar(
            df,
            x="title",
            y=["views", "likes", "comments"],
            barmode="group",
            title="Views, Likes, and Comments Comparison",
            labels={"title": "Video", "value": "Count", "variable": "Metric"}
        )
        fig.update_traces(hovertemplate="Video: %{x}<br>Count: %{y:,}<extra></extra>")
        fig = style_chart(fig, x_title="Video", y_title="Count", height=470)
        st.plotly_chart(fig, width="stretch")

        fig2 = px.bar(
            df,
            x="title",
            y="performance_score",
            text="performance_score",
            title="Performance Score Comparison",
            range_y=[0, 100],
            labels={"title": "Video", "performance_score": "Performance Score (0-100)"}
        )
        fig2.update_traces(
            texttemplate="%{text}/100",
            textposition="outside",
            hovertemplate="%{x}<br>Performance Score: %{y}/100<extra></extra>"
        )
        fig2 = style_chart(fig2, x_title="Video", y_title="Performance Score (0-100)", height=470)
        st.plotly_chart(fig2, width="stretch")

        fig3 = px.scatter(
            df,
            x="views",
            y="engagement_rate",
            size="comments",
            hover_name="title",
            title="Views vs Engagement Quality",
            labels={"views": "Views", "engagement_rate": "Engagement Rate (%)", "comments": "Comments"}
        )
        fig3.update_traces(hovertemplate="%{hovertext}<br>Views: %{x:,}<br>Engagement Rate: %{y:.2f}%<br>Bubble size: comments<extra></extra>")
        fig3 = style_chart(fig3, x_title="Views", y_title="Engagement Rate (%)", height=470)
        st.plotly_chart(fig3, width="stretch")

        radar_df = pd.DataFrame({
            "Video": df["title"],
            "Views Score": (df["views"] / max(df["views"].max(), 1) * 100).round(1),
            "Like Density": (df["Likes per 1K Views"] / max(df["Likes per 1K Views"].max(), 1) * 100).round(1),
            "Comment Density": (df["Comments per 1K Views"] / max(df["Comments per 1K Views"].max(), 1) * 100).round(1),
            "Engagement": (df["engagement_rate"] / max(df["engagement_rate"].max(), 1) * 100).round(1),
            "Overall": df["performance_score"]
        })

        st.subheader("Normalized Scorecard")
        st.dataframe(radar_df, width="stretch")


# =========================================================
# TAB 4: GROWTH STRATEGY GENERATOR
# =========================================================

with tabs[3]:
    st.header("Growth Strategy Generator")
    st.caption("A strategy report built from recent upload patterns, engagement signals, and repeatable content opportunities.")

    growth_input = st.text_input(
        "Paste a channel link, @handle, channel name, or video link",
        key="growth_channel_input"
    )

    if st.button("Generate Growth Strategy", width="stretch"):
        if not growth_input.strip():
            st.warning("Please enter a channel.")
            st.stop()

        with st.spinner("Analyzing channel strategy..."):
            channel_id = resolve_channel_id(growth_input)
            channel = get_channel_details(channel_id) if channel_id else None
            videos = get_recent_channel_videos(channel_id, 25) if channel_id else []

        if not channel:
            st.error("Could not analyze this channel.")
            st.stop()

        st.subheader(channel["title"])
        g1, g2, g3, g4 = st.columns(4)
        with g1:
            render_metric_card("Subscribers", format_number(channel["subscribers"]))
        with g2:
            render_metric_card("Total Views", format_number(channel["views"]))
        with g3:
            render_metric_card("Total Videos", format_number(channel["video_count"]))
        with g4:
            avg_score = round(pd.DataFrame(videos)["performance_score"].mean(), 1) if videos else 0
            render_metric_card("Recent Avg Score", f"{avg_score}/100")

        if videos:
            df = pd.DataFrame(videos)
            top_df = df.sort_values("performance_score", ascending=False).head(5)
            fig = px.bar(
                top_df,
                x="performance_score",
                y="title",
                orientation="h",
                title="Top Recent Videos by Performance Score",
                text="performance_score",
                range_x=[0, 100],
                labels={"performance_score": "Performance Score (0-100)", "title": "Video"}
            )
            fig.update_traces(
                texttemplate="%{text}/100",
                textposition="outside",
                hovertemplate="%{y}<br>Performance Score: %{x}/100<extra></extra>"
            )
            fig.update_layout(yaxis={"categoryorder": "total ascending"})
            fig = style_chart(fig, x_title="Performance Score (0-100)", y_title="Video", height=460)
            st.plotly_chart(fig, width="stretch")

        with st.spinner("Generating premium growth strategy..."):
            strategy = get_growth_strategy(channel, videos)

        render_ai_insight("Recommended Positioning", strategy.get("positioning", ""))

        col_a, col_b = st.columns(2)
        with col_a:
            render_list("Content Pillars", strategy.get("content_pillars", []))
        with col_b:
            render_list("Growth Moves", strategy.get("growth_moves", []))

        render_ai_insight("Upload Strategy", strategy.get("upload_strategy", ""))
        render_list("Next 5 Video Ideas", strategy.get("next_5_video_ideas", []))

        if videos:
            st.subheader("Recent Upload Signals")
            st.dataframe(
                pd.DataFrame(videos)[[
                    "title", "views", "likes", "comments", "engagement_rate", "performance_score", "published_at"
                ]],
                width="stretch"
            )

        st.download_button(
            "Download Growth Strategy Report",
            data=build_strategy_report(channel, strategy, videos),
            file_name="stratify_growth_strategy.pdf",
            mime="application/pdf",
            width="stretch"
        )


# =========================================================
# TAB 5: CHANNEL DNA ANALYSIS
# =========================================================

with tabs[4]:
    st.header("Channel DNA Analysis")
    st.caption("A deeper read of what the channel is, why people watch it, and which repeatable patterns should become the content system.")

    dna_input = st.text_input(
        "Paste a channel link, @handle, channel name, or video link",
        key="dna_channel_input"
    )

    if st.button("Analyze Channel DNA", width="stretch"):
        if not dna_input.strip():
            st.warning("Please enter a channel.")
            st.stop()

        with st.spinner("Reading channel DNA..."):
            channel_id = resolve_channel_id(dna_input)
            channel = get_channel_details(channel_id) if channel_id else None
            videos = get_recent_channel_videos(channel_id, 30) if channel_id else []

        if not channel:
            st.error("Could not analyze this channel.")
            st.stop()

        st.subheader(channel["title"])
        d1, d2, d3, d4 = st.columns(4)
        with d1:
            render_metric_card("Subscribers", format_number(channel["subscribers"]))
        with d2:
            render_metric_card("Total Views", format_number(channel["views"]))
        with d3:
            render_metric_card("Videos Analyzed", len(videos))
        with d4:
            avg_eng = round(pd.DataFrame(videos)["engagement_rate"].mean(), 2) if videos else 0
            render_metric_card("Avg Engagement", f"{avg_eng}%")

        if videos:
            df = pd.DataFrame(videos)
            fig = px.scatter(
                df,
                x="views",
                y="comments",
                size="likes",
                hover_name="title",
                title="Audience Reaction Map",
                labels={"views": "Views", "comments": "Comments", "likes": "Likes"}
            )
            fig.update_traces(hovertemplate="%{hovertext}<br>Views: %{x:,}<br>Comments: %{y:,}<br>Bubble size: likes<extra></extra>")
            fig = style_chart(fig, x_title="Views", y_title="Comments", height=460)
            st.plotly_chart(fig, width="stretch")

        with st.spinner("Generating Channel DNA report..."):
            dna = get_channel_dna(channel, videos)

        render_ai_insight("Primary Content Style", dna.get("primary_content_style", ""))

        col_a, col_b = st.columns(2)
        with col_a:
            render_list("Winning Content Patterns", dna.get("winning_content_patterns", []))
        with col_b:
            render_list("Growth Opportunities", dna.get("growth_opportunities", []))

        render_ai_insight("Upload Strategy", dna.get("upload_strategy", ""))
        render_ai_insight("Audience Profile", dna.get("audience_profile", ""))

        if videos:
            st.subheader("Content DNA Evidence")
            evidence_df = pd.DataFrame(videos)[[
                "title", "views", "likes", "comments", "engagement_rate", "performance_score"
            ]].sort_values("performance_score", ascending=False)
            st.dataframe(evidence_df, width="stretch")

        st.download_button(
            "Download Channel DNA Report",
            data=build_dna_report(channel, dna, videos),
            file_name="stratify_channel_dna.pdf",
            mime="application/pdf",
            width="stretch"
        )