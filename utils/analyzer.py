from utils.youtube_utils import extract_video_id, fetch_video_metadata
from utils.transcript_utils import fetch_transcript, clean_transcript
from utils.ai_utils import generate_ai_insights


def calculate_performance_score(views: int, engagement_rate: float, like_count: int, comment_count: int) -> int:
    """
    Simple composite score out of 100.
    """
    score = 0

    # Views score
    if views >= 1_000_000:
        score += 35
    elif views >= 100_000:
        score += 25
    elif views >= 10_000:
        score += 15
    else:
        score += 8

    # Engagement score
    if engagement_rate >= 8:
        score += 35
    elif engagement_rate >= 4:
        score += 25
    elif engagement_rate >= 2:
        score += 15
    else:
        score += 8

    # Likes/comments activity
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


def analyze_video(video_url: str, youtube_api_key: str, gemini_api_key: str | None = None) -> dict:
    """
    Main pipeline:
    URL -> Metadata -> Transcript -> AI -> Final output
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

    ai_result = generate_ai_insights(payload, gemini_api_key)

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