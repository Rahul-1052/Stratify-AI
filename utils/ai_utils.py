import json
import os
import re
import os
import streamlit as st
import google.generativeai as genai

import os
import streamlit as st

try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
except:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
import google.generativeai as genai


GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)


def _get_model():
    if not GEMINI_API_KEY:
        raise ValueError("Missing GEMINI_API_KEY in environment variables.")
    return genai.GenerativeModel("gemini-1.5-flash")


def _clean_json_text(text: str) -> str:
    if not text:
        return ""

    text = text.strip()

    # Remove markdown code fences if Gemini returns them
    text = re.sub(r"^```json\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^```\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    # Try to isolate JSON object
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        text = text[start:end + 1]

    return text.strip()


def _safe_json_loads(text: str):
    cleaned = _clean_json_text(text)
    return json.loads(cleaned)


def _truncate_text(text, limit=220):
    if text is None:
        return ""
    text = str(text).strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."


def _video_context_block(video_data: dict) -> str:
    return f"""
VIDEO TITLE: {video_data.get("title", "Unknown")}
CHANNEL: {video_data.get("channel", "Unknown")}
PUBLISHED: {video_data.get("published_at", "Unknown")}
VIEWS: {video_data.get("views", 0)}
LIKES: {video_data.get("likes", 0)}
COMMENTS: {video_data.get("comments", 0)}
ENGAGEMENT RATE: {video_data.get("engagement_rate", 0)}%
LIKE RATE: {video_data.get("like_rate", 0)}%
COMMENT RATE: {video_data.get("comment_rate", 0)}%
PERFORMANCE SCORE: {video_data.get("final_score", 0)}/100
PERFORMANCE LABEL: {video_data.get("score_label", "Unknown")}
PERFORMANCE SIGNAL: {video_data.get("performance_signal", "Unknown")}
BENCHMARK DECISION: {video_data.get("decision", "Unknown")}
CONFIDENCE LEVEL: {video_data.get("confidence", "Unknown")}
""".strip()


def analyze_video(video_data: dict) -> dict:
    """
    Analyze a single YouTube video and return structured portfolio-grade insights.
    """

    fallback = {
        "content_style": "Could not determine the content style confidently from the available signals.",
        "target_audience": "Could not determine the target audience confidently from the available signals.",
        "engagement_reason": "The video shows measurable audience interaction, but a deeper explanation could not be generated at this time.",
        "improvement_suggestion": "Test a stronger hook, clearer value proposition, and more comment-worthy CTA to improve engagement quality.",
        "psychological_triggers": "Likely triggers include curiosity, relevance, clarity, and perceived usefulness, but the signal is not strong enough for a more confident breakdown.",
    }

    try:
        model = _get_model()

        prompt = f"""
You are a senior content strategist for a premium AI video intelligence platform called ShopPulse AI.

Your task:
Analyze the YouTube video performance signals below and generate strategic insight for creators, marketers, and product-focused portfolio reviewers.

Important rules:
1. Return ONLY valid JSON.
2. Do NOT wrap the response in markdown.
3. Keep each field concise but insightful.
4. Avoid generic phrases like "good engagement" unless you explain why.
5. Base your reasoning on the data provided.
6. Write in a premium product-intelligence tone.
7. Each field should feel specific, strategic, and portfolio-worthy.

Video data:
{_video_context_block(video_data)}

Return JSON with exactly these keys:
{{
  "content_style": "...",
  "target_audience": "...",
  "engagement_reason": "...",
  "improvement_suggestion": "...",
  "psychological_triggers": "..."
}}

Field guidance:
- content_style: infer the likely format/style of the video content
- target_audience: infer who this video is likely resonating with
- engagement_reason: explain why the current performance pattern may be happening
- improvement_suggestion: give one sharp, practical improvement idea
- psychological_triggers: explain the likely emotional/behavioral triggers behind response

Make the insight useful for decision-making, not just description.
""".strip()

        response = model.generate_content(prompt)
        parsed = _safe_json_loads(response.text)

        return {
            "content_style": _truncate_text(
                parsed.get("content_style", fallback["content_style"]), 220
            ),
            "target_audience": _truncate_text(
                parsed.get("target_audience", fallback["target_audience"]), 220
            ),
            "engagement_reason": _truncate_text(
                parsed.get("engagement_reason", fallback["engagement_reason"]), 420
            ),
            "improvement_suggestion": _truncate_text(
                parsed.get("improvement_suggestion", fallback["improvement_suggestion"]), 420
            ),
            "psychological_triggers": _truncate_text(
                parsed.get("psychological_triggers", fallback["psychological_triggers"]), 420
            ),
        }

    except Exception:
        return fallback


def compare_videos(video_a: dict, video_b: dict) -> dict:
    """
    Compare two YouTube videos and return structured AI comparison insight.
    """

    winner = "Video A" if video_a.get("final_score", 0) >= video_b.get("final_score", 0) else "Video B"

    fallback = {
        "winner": winner,
        "reason": "One video shows a stronger overall balance of reach and engagement, making it the better benchmark candidate.",
        "key_difference": "The strongest separation appears to come from engagement efficiency rather than raw visibility alone.",
        "strategy_insight": "Use the stronger video as the benchmark for hooks, audience fit, and engagement conversion strategy.",
    }

    try:
        model = _get_model()

        prompt = f"""
You are a senior content intelligence analyst for ShopPulse AI.

Your task:
Compare two YouTube videos and determine which one is the stronger benchmark candidate.

Important rules:
1. Return ONLY valid JSON.
2. Do NOT wrap the response in markdown.
3. Be specific and strategic.
4. Focus on benchmark quality, not only raw popularity.
5. Use the score, engagement rate, like rate, comment rate, and signal pattern to justify your answer.
6. Write in a premium decision-intelligence tone.

VIDEO A
{_video_context_block(video_a)}

VIDEO B
{_video_context_block(video_b)}

Return JSON with exactly these keys:
{{
  "winner": "Video A or Video B",
  "reason": "...",
  "key_difference": "...",
  "strategy_insight": "..."
}}

Field guidance:
- winner: choose the stronger benchmark candidate
- reason: explain clearly why it wins
- key_difference: explain the single biggest difference between the two
- strategy_insight: tell the user what to learn or copy from the stronger video

Do not be vague. Make the answer feel like a product strategy insight.
""".strip()

        response = model.generate_content(prompt)
        parsed = _safe_json_loads(response.text)

        ai_winner = parsed.get("winner", winner)
        if ai_winner not in ["Video A", "Video B"]:
            ai_winner = winner

        return {
            "winner": ai_winner,
            "reason": _truncate_text(parsed.get("reason", fallback["reason"]), 420),
            "key_difference": _truncate_text(
                parsed.get("key_difference", fallback["key_difference"]), 260
            ),
            "strategy_insight": _truncate_text(
                parsed.get("strategy_insight", fallback["strategy_insight"]), 420
            ),
        }

    except Exception:
        return fallback