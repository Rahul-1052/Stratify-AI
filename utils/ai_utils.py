import os
import json
import streamlit as st
from openai import OpenAI


def fallback_insights(payload: dict) -> dict:
    views = payload.get("views", 0) or 0
    engagement_rate = payload.get("engagement_rate", 0) or 0
    title = (payload.get("title") or "").lower()

    if any(word in title for word in ["tutorial", "how to", "guide"]):
        content_style = "Educational / tutorial"
    elif any(word in title for word in ["podcast", "interview"]):
        content_style = "Long-form conversation"
    elif "review" in title:
        content_style = "Review / opinion content"
    else:
        content_style = "General video content"

    if views >= 1_000_000:
        viral_potential = "High"
        hook_strength = "Strong"
    elif views >= 100_000:
        viral_potential = "Medium"
        hook_strength = "Moderate"
    else:
        viral_potential = "Low"
        hook_strength = "Needs improvement"

    if engagement_rate >= 4:
        retention_drivers = "The video likely performs because the topic has clear audience interest and enough interaction signal."
    else:
        retention_drivers = "The video may need a stronger opening hook, clearer positioning, or more audience engagement prompts."

    return {
        "content_style": content_style,
        "target_audience": "Audience inferred from title, metadata, and engagement metrics.",
        "hook_strength": hook_strength,
        "viewer_retention_drivers": retention_drivers,
        "content_gaps": "Add more context, stronger framing, and clearer value for first-time viewers.",
        "viral_potential": viral_potential,
        "actionable_recommendations": [
            "Improve the first 5 seconds with a clearer hook.",
            "Add stronger title/thumbnail alignment.",
            "Use a more direct call-to-action to increase comments."
        ],
    }


def safe_parse_ai_json(text: str) -> dict | None:
    if not text:
        return None

    text = text.strip()
    text = text.replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(text)
    except Exception:
        return None


def generate_ai_insights(payload: dict, nvidia_api_key: str | None = None) -> dict:
    nvidia_api_key = nvidia_api_key or st.secrets.get("NVIDIA_API_KEY", "") or os.getenv("NVIDIA_API_KEY")

    if not nvidia_api_key:
        return {
            "ok": False,
            "mode": "fallback",
            "error": "Missing NVIDIA_API_KEY.",
            "data": fallback_insights(payload)
        }

    try:
        client = OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=nvidia_api_key
        )

        prompt = f"""
You are Stratify AI, an expert YouTube content strategist.

Analyze the video using the metadata and transcript excerpt.

Return ONLY valid JSON.
Do not use markdown.
Do not include explanations outside JSON.

The JSON must contain exactly these keys:
content_style
target_audience
hook_strength
viewer_retention_drivers
content_gaps
viral_potential
actionable_recommendations

Rules:
- content_style: one specific phrase.
- target_audience: one concise sentence.
- hook_strength: score and reason, example "7/10 — strong emotional opening but title could be sharper."
- viewer_retention_drivers: 2-3 concise bullet-style points in one string.
- content_gaps: 2-3 concise bullet-style points in one string.
- viral_potential: score out of 100 with reason.
- actionable_recommendations: array of exactly 3 specific recommendations.

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
                    "content": "You are a senior YouTube strategist. Return only valid JSON."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.35,
            max_tokens=900
        )

        text = response.choices[0].message.content
        parsed = safe_parse_ai_json(text)

        if parsed:
            return {
                "ok": True,
                "mode": "nvidia",
                "error": None,
                "data": parsed
            }

        return {
            "ok": False,
            "mode": "fallback",
            "error": "NVIDIA returned non-JSON output.",
            "data": fallback_insights(payload)
        }

    except Exception as e:
        return {
            "ok": False,
            "mode": "fallback",
            "error": f"NVIDIA failed: {str(e)}",
            "data": fallback_insights(payload)
        }