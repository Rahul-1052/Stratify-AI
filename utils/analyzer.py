from utils.youtube_utils import extract_video_id, fetch_video_metadata
from utils.transcript_utils import fetch_transcript, clean_transcript
from utils.ai_utils import generate_ai_insights


def calculate_performance_score(
    views: int,
    engagement_rate: float,
    like_count: int,
    comment_count: int
) -> int:
    """
    Simple composite score out of 100.
    """
    score = 0

    if views >= 1_000_000:
        score += 35
    elif views >= 100_000:
        score += 25
    elif views >= 10_000:
        score += 15
    else:
        score += 8

    if engagement_rate >= 8:
        score += 35
    elif engagement_rate >= 4:
        score += 25
    elif engagement_rate >= 2:
        score += 15
    else:
        score += 8

    if like_count >= 10000:
        score += 20
    elif like_count >= 1000:
        score += 12
    else:
        score += 6

    if comment_count >= 1000:
        score += 10
    elif comment_count >= 100:
        score += 6
    else:
        score += 3

    return min(score, 100)


def analyze_video(
    video_url: str,
    youtube_api_key: str,
    nvidia_api_key: str | None = None
) -> dict:
    """
    Main pipeline:
    URL -> Metadata -> Transcript -> Strategy -> Final output
    """
    video_id = extract_video_id(video_url)

    if not video_id:
        return {
            "ok": False,
            "error": "Invalid YouTube URL."
        }

    metadata = fetch_video_metadata(video_id, youtube_api_key)

    if not metadata.get("ok"):
        return {
            "ok": False,
            "error": metadata.get("error", "Metadata fetch failed."),
            "stage": "metadata"
        }

    transcript_result = fetch_transcript(video_id)
    transcript_text = transcript_result["text"] if transcript_result.get("ok") else ""

    payload = {
        "title": metadata.get("title"),
        "channel": metadata.get("channel"),
        "description": metadata.get("description"),
        "views": metadata.get("views"),
        "likes": metadata.get("likes"),
        "comments": metadata.get("comments"),
        "engagement_rate": metadata.get("engagement_rate"),
        "transcript_excerpt": clean_transcript(transcript_text, max_chars=5000),
    }

    ai_result = generate_ai_insights(payload, nvidia_api_key)

    performance_score = calculate_performance_score(
        views=metadata.get("views", 0),
        engagement_rate=metadata.get("engagement_rate", 0),
        like_count=metadata.get("likes", 0),
        comment_count=metadata.get("comments", 0)
    )

    return {
        "ok": True,
        "video_id": video_id,
        "metadata": metadata,
        "transcript": transcript_result,
        "ai": ai_result,
        "performance_score": performance_score
    }


def build_channel_dna_payload(channel_summary: dict) -> dict:
    """
    Builds the payload for Channel DNA Analysis.
    This does not depend on transcripts, so it works better on Streamlit Cloud.
    """
    return {
        "task": "channel_dna_analysis",
        "channel_summary": channel_summary
    }


def generate_channel_dna(
    channel_videos,
    nvidia_api_key: str | None = None
) -> dict:
    """
    Generates Channel DNA Analysis from recent channel videos.

    Expected channel_videos:
    pandas DataFrame with columns:
    title, views, likes, comments, engagement_rate, published_at
    """

    if channel_videos is None or channel_videos.empty:
        return {
            "ok": False,
            "error": "Not enough channel data to generate Channel DNA."
        }

    df = channel_videos.copy()

    required_columns = ["title", "views", "likes", "comments", "engagement_rate"]
    missing_columns = [col for col in required_columns if col not in df.columns]

    if missing_columns:
        return {
            "ok": False,
            "error": f"Missing required columns for Channel DNA: {', '.join(missing_columns)}"
        }

    df["views"] = df["views"].fillna(0).astype(int)
    df["likes"] = df["likes"].fillna(0).astype(int)
    df["comments"] = df["comments"].fillna(0).astype(int)
    df["engagement_rate"] = df["engagement_rate"].fillna(0).astype(float)

    top_videos = df.sort_values("views", ascending=False).head(5)
    low_videos = df.sort_values("views", ascending=True).head(5)
    high_engagement_videos = df.sort_values("engagement_rate", ascending=False).head(5)

    channel_summary = {
        "videos_analyzed": int(len(df)),
        "average_views": round(float(df["views"].mean()), 2),
        "average_likes": round(float(df["likes"].mean()), 2),
        "average_comments": round(float(df["comments"].mean()), 2),
        "average_engagement_rate": round(float(df["engagement_rate"].mean()), 2),
        "top_performing_videos": top_videos[
            ["title", "views", "likes", "comments", "engagement_rate"]
        ].to_dict("records"),
        "underperforming_videos": low_videos[
            ["title", "views", "likes", "comments", "engagement_rate"]
        ].to_dict("records"),
        "highest_engagement_videos": high_engagement_videos[
            ["title", "views", "likes", "comments", "engagement_rate"]
        ].to_dict("records"),
    }

    if "published_at" in df.columns:
        channel_summary["recent_uploads"] = df[
            ["title", "published_at", "views", "engagement_rate"]
        ].head(10).to_dict("records")

    payload = build_channel_dna_payload(channel_summary)

    ai_result = generate_ai_insights(payload, nvidia_api_key)

    return {
        "ok": True,
        "channel_summary": channel_summary,
        "ai": ai_result
    }