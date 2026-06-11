import os
import json
import streamlit as st
from openai import OpenAI


def fallback_insights(payload: dict) -> dict:
    """
    Fallback when Gemini fails or quota is hit.
    """
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
        target_audience = "Broad mainstream audience"
    elif views >= 100_000:
        target_audience = "Scalable niche audience"
    else:
        target_audience = "Focused niche audience"

    if engagement_rate >= 8:
        why_it_performs = "Strong interaction relative to views suggests the content resonates well with its audience."
    elif engagement_rate >= 4:
        why_it_performs = "Moderate interaction suggests the content has value but could be packaged more sharply."
    else:
        why_it_performs = "Lower interaction suggests the hook, positioning, or audience match may need improvement."

    improvement_suggestion = "Strengthen the first few seconds, clarify the value earlier, and end with a more engagement-worthy CTA."

    return {
        "content_style": content_style,
        "target_audience": target_audience,
        "why_it_performs": why_it_performs,
        "improvement_suggestion": improvement_suggestion,
    }


def safe_parse_ai_json(text: str) -> dict | None:
    """
    Tries to parse model output into JSON safely.
    """
    if not text:
        return None

    text = text.strip()

    # remove markdown fences if present
    text = text.replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(text)
    except Exception:
        return None

def generate_ai_insights(payload: dict, nvidia_api_key: str | None = None) -> dict:
    """
    NVIDIA first, fallback second.
    """
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
You are analyzing a YouTube video for a content intelligence app.

Return ONLY valid JSON with exactly these keys:
content_style
target_audience
why_it_performs
improvement_suggestion

Keep answers concise and specific.

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
                    "content": "You are a YouTube content strategist. Return only clean valid JSON."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.4,
            max_tokens=700
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

    except Exception as e:
        return {
            "ok": False,
            "mode": "fallback",
            "error": f"Gemini failed: {str(e)}",
            "data": fallback_insights(payload)
        }