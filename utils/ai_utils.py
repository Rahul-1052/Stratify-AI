import os
import json
import re
import streamlit as st
from openai import OpenAI


REQUIRED_KEYS = {
    "content_style": "N/A",
    "target_audience": "N/A",
    "hook_strength": "N/A",
    "viewer_retention_drivers": "N/A",
    "content_gaps": "N/A",
    "viral_potential": "N/A",
    "actionable_recommendations": [],
    "why_this_video_works": [],
    "what_to_copy": [],
    "what_to_improve": [],
    "better_titles": [],
    "thumbnail_concepts": [],
    "next_video_ideas": []
}

LIST_KEYS = [
    "actionable_recommendations",
    "why_this_video_works",
    "what_to_copy",
    "what_to_improve",
    "better_titles",
    "thumbnail_concepts",
    "next_video_ideas"
]

CHANNEL_DNA_KEYS = {
    "primary_content_style": "N/A",
    "audience_profile": "N/A",
    "winning_content_patterns": [],
    "underperforming_patterns": [],
    "growth_opportunities": [],
    "recommended_content_pillars": [],
    "upload_strategy": "N/A",
    "30_day_channel_plan": []
}

CHANNEL_DNA_LIST_KEYS = [
    "winning_content_patterns",
    "underperforming_patterns",
    "growth_opportunities",
    "recommended_content_pillars",
    "30_day_channel_plan"
]


def normalize_insights(data: dict | None) -> dict:
    if not isinstance(data, dict):
        data = {}

    normalized = {}

    for key, default_value in REQUIRED_KEYS.items():
        value = data.get(key, default_value)

        if value is None or value == "":
            value = default_value

        normalized[key] = value

    for key in LIST_KEYS:
        if not isinstance(normalized[key], list):
            normalized[key] = [str(normalized[key])] if normalized[key] else []

    return normalized


def normalize_channel_dna(data: dict | None) -> dict:
    if not isinstance(data, dict):
        data = {}

    normalized = {}

    for key, default_value in CHANNEL_DNA_KEYS.items():
        value = data.get(key, default_value)

        if value is None or value == "":
            value = default_value

        normalized[key] = value

    for key in CHANNEL_DNA_LIST_KEYS:
        if not isinstance(normalized[key], list):
            normalized[key] = [str(normalized[key])] if normalized[key] else []

    return normalized


def fallback_insights(payload: dict) -> dict:
    views = payload.get("views", 0) or 0
    engagement_rate = payload.get("engagement_rate", 0) or 0
    title_raw = payload.get("title") or "this video"
    title = title_raw.lower()

    if any(word in title for word in ["tutorial", "how to", "guide"]):
        content_style = "Educational / tutorial"
    elif any(word in title for word in ["podcast", "interview"]):
        content_style = "Long-form conversation"
    elif "review" in title:
        content_style = "Review / opinion content"
    elif any(word in title for word in ["edit", "scene", "moment", "compilation", "blacklist"]):
        content_style = "Entertainment / fan compilation"
    else:
        content_style = "General video content"

    if views >= 1_000_000:
        viral_potential = "85/100 — High reach potential based on strong view volume."
        hook_strength = "8/10 — Strong initial appeal based on high audience interest."
    elif views >= 100_000:
        viral_potential = "65/100 — Medium potential with room for stronger packaging."
        hook_strength = "6/10 — Moderate hook strength."
    else:
        viral_potential = "40/100 — Low to medium potential unless title, thumbnail, or niche targeting improves."
        hook_strength = "5/10 — Needs a clearer opening reason to keep viewers watching."

    if engagement_rate >= 4:
        retention_drivers = "Strong topic interest; audience interaction is healthy; content likely connects with a clear niche."
    else:
        retention_drivers = "Recognizable topic or character interest; emotional/high-intensity moments may support retention; stronger pacing could improve watch time."

    return normalize_insights({
        "content_style": content_style,
        "target_audience": "Audience inferred from title, metadata, transcript, and engagement metrics.",
        "hook_strength": hook_strength,
        "viewer_retention_drivers": retention_drivers,
        "content_gaps": "Opening context may be unclear for new viewers; title/thumbnail could be more specific; stronger call-to-action could improve engagement.",
        "viral_potential": viral_potential,
        "actionable_recommendations": [
            "Make the first 3 seconds more direct and emotionally clear.",
            "Use a title that highlights the strongest character, conflict, or payoff.",
            "Add a comment prompt that invites fans to debate or react."
        ],
        "why_this_video_works": [
            "The topic appears to match an existing audience interest.",
            "The title suggests a recognizable moment or clear content angle.",
            "The video has enough metadata signal to support a focused niche."
        ],
        "what_to_copy": [
            "Repeat the strongest topic or character angle.",
            "Keep the title focused on a clear payoff.",
            "Use the most intense or recognizable moment early."
        ],
        "what_to_improve": [
            "Make the first few seconds easier for new viewers to understand.",
            "Improve title specificity and emotional pull.",
            "Use stronger calls-to-action to increase comments."
        ],
        "better_titles": [
            f"Why {title_raw} Got Everyone Talking",
            f"The Moment That Made {title_raw} Worth Watching",
            f"{title_raw} — The Scene Fans Can't Stop Rewatching"
        ],
        "thumbnail_concepts": [
            "Close-up reaction shot with a short emotional phrase.",
            "Split-screen conflict image showing two opposing forces.",
            "High-contrast frame highlighting the strongest moment."
        ],
        "next_video_ideas": [
            "Create a follow-up around the strongest character or topic.",
            "Make a shorter high-retention version for Shorts.",
            "Create a ranking or comparison video based on the same niche."
        ]
    })


def fallback_channel_dna(payload: dict) -> dict:
    summary = payload.get("channel_summary", {})

    return normalize_channel_dna({
        "primary_content_style": "Metadata-driven creator content with identifiable performance patterns.",
        "audience_profile": "The audience is likely built around viewers who already respond to the channel's recurring topics, titles, and content themes.",
        "winning_content_patterns": [
            "Repeat the topics and title angles found in the highest-viewed videos.",
            "Study videos with above-average engagement for audience loyalty signals.",
            "Use high-performing videos as templates for future formats."
        ],
        "underperforming_patterns": [
            "Videos with low views may have weaker packaging or less clear topic demand.",
            "Low-engagement uploads may not give viewers a strong reason to comment or react.",
            "Inconsistent topic framing may make it harder for new viewers to understand the channel."
        ],
        "growth_opportunities": [
            "Turn best-performing topics into repeatable series.",
            "Improve titles and thumbnails around clear emotional payoff.",
            "Create follow-up videos based on top-performing recent uploads."
        ],
        "recommended_content_pillars": [
            "Repeatable winner formats",
            "Audience reaction or discussion content",
            "Short-form clips from strongest topics"
        ],
        "upload_strategy": f"Use the {summary.get('videos_analyzed', 'recent')} analyzed videos to identify the top 2-3 repeatable formats and post around those consistently.",
        "30_day_channel_plan": [
            "Week 1: Identify top videos and extract common title/topic patterns.",
            "Week 2: Publish follow-ups based on the strongest performers.",
            "Week 3: Test improved packaging on similar topics.",
            "Week 4: Double down on the best-performing format and plan a repeatable series."
        ]
    })


def safe_parse_ai_json(text: str) -> dict | None:
    if not text:
        return None

    text = text.strip()
    text = text.replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(text)
    except Exception:
        pass

    match = re.search(r"\{.*\}", text, re.DOTALL)

    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            return None

    return None


def generate_ai_insights(payload: dict, nvidia_api_key: str | None = None) -> dict:
    nvidia_api_key = nvidia_api_key or st.secrets.get("NVIDIA_API_KEY", "") or os.getenv("NVIDIA_API_KEY")

    is_channel_dna = payload.get("task") == "channel_dna_analysis"

    if not nvidia_api_key:
        return {
            "ok": False,
            "mode": "fallback",
            "error": "Strategy engine unavailable.",
            "data": fallback_channel_dna(payload) if is_channel_dna else fallback_insights(payload)
        }

    try:
        client = OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=nvidia_api_key
        )

        if is_channel_dna:
            prompt = f"""
You are Stratify AI, a senior YouTube growth strategist.

Analyze this YouTube channel using only the provided metadata and performance data.

Return ONLY valid JSON.
Do not use markdown.
Do not include explanations outside JSON.

You MUST return this exact JSON structure:

{{
  "primary_content_style": "one specific phrase describing the channel's main content style",
  "audience_profile": "one clear paragraph describing the likely audience",
  "winning_content_patterns": [
    "specific winning pattern 1",
    "specific winning pattern 2",
    "specific winning pattern 3"
  ],
  "underperforming_patterns": [
    "specific weak pattern 1",
    "specific weak pattern 2",
    "specific weak pattern 3"
  ],
  "growth_opportunities": [
    "specific growth opportunity 1",
    "specific growth opportunity 2",
    "specific growth opportunity 3"
  ],
  "recommended_content_pillars": [
    "content pillar 1",
    "content pillar 2",
    "content pillar 3"
  ],
  "upload_strategy": "specific upload strategy based on recent channel performance",
  "30_day_channel_plan": [
    "week 1 plan",
    "week 2 plan",
    "week 3 plan",
    "week 4 plan"
  ]
}}

Rules:
- Do not omit any key.
- Do not rename keys.
- Do not return null values.
- Make every answer specific to the channel data.
- Do not mention transcripts.
- Avoid generic advice.
- Use titles, views, likes, comments, engagement rate, top videos, weak videos, and recent uploads.

Channel Data:
{json.dumps(payload.get("channel_summary", {}), indent=2)}
"""
        else:
            prompt = f"""
You are Stratify AI, a senior YouTube strategist and creator growth analyst.

Your job is not just to describe the video.
Your job is to help a creator understand:
- why the video may perform
- what should be repeated
- what should be improved
- what title/thumbnail strategy would increase click-through
- what video should be made next

Analyze the video using metadata and transcript excerpt.

Return ONLY valid JSON.
Do not use markdown.
Do not include explanations outside JSON.

You MUST return this exact JSON structure with all keys filled:

{{
  "content_style": "one specific phrase describing the format/style",
  "target_audience": "one concise sentence describing the likely viewer group",
  "hook_strength": "score out of 10 plus one clear reason",
  "viewer_retention_drivers": "2-3 concise retention reasons in one string",
  "content_gaps": "2-3 concise weaknesses or missing opportunities in one string",
  "viral_potential": "score out of 100 plus one clear reason",
  "why_this_video_works": [
    "specific reason 1",
    "specific reason 2",
    "specific reason 3"
  ],
  "what_to_copy": [
    "specific thing to repeat 1",
    "specific thing to repeat 2",
    "specific thing to repeat 3"
  ],
  "what_to_improve": [
    "specific improvement 1",
    "specific improvement 2",
    "specific improvement 3"
  ],
  "better_titles": [
    "better title 1",
    "better title 2",
    "better title 3"
  ],
  "thumbnail_concepts": [
    "thumbnail concept 1",
    "thumbnail concept 2",
    "thumbnail concept 3"
  ],
  "next_video_ideas": [
    "next video idea 1",
    "next video idea 2",
    "next video idea 3"
  ],
  "actionable_recommendations": [
    "specific recommendation 1",
    "specific recommendation 2",
    "specific recommendation 3"
  ]
}}

Rules:
- Do not omit any key.
- Do not rename keys.
- Do not return null values.
- All list fields must contain exactly 3 strings.
- Make every answer specific to this video, not generic.
- Use the transcript if available.
- If transcript is unavailable, rely on title, description, and metadata.
- Better titles should be realistic YouTube titles, not corporate-sounding.
- Thumbnail concepts should describe the visual idea and emotional trigger.
- Next video ideas should be based on the same audience and content niche.

Video Data:
Title: {payload.get("title")}
Channel: {payload.get("channel")}
Description: {payload.get("description")}
Views: {payload.get("views")}
Likes: {payload.get("likes")}
Comments: {payload.get("comments")}
Engagement Rate: {payload.get("engagement_rate")}
Transcript Excerpt: {payload.get("transcript_excerpt")}
"""

        response = client.chat.completions.create(
            model="meta/llama-3.3-70b-instruct",
            messages=[
                {
                    "role": "system",
                    "content": "You are a senior YouTube strategist. Return only complete valid JSON with all required keys."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.35,
            max_tokens=1800
        )

        text = response.choices[0].message.content
        parsed = safe_parse_ai_json(text)

        if parsed:
            return {
                "ok": True,
                "mode": "strategy",
                "error": None,
                "data": normalize_channel_dna(parsed) if is_channel_dna else normalize_insights(parsed)
            }

        return {
            "ok": False,
            "mode": "fallback",
            "error": "Strategy engine returned non-JSON output.",
            "data": fallback_channel_dna(payload) if is_channel_dna else fallback_insights(payload)
        }

    except Exception as e:
        return {
            "ok": False,
            "mode": "fallback",
            "error": f"Strategy engine failed: {str(e)}",
            "data": fallback_channel_dna(payload) if is_channel_dna else fallback_insights(payload)
        }