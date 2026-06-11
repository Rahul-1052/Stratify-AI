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
    "actionable_recommendations": []
}


def normalize_insights(data: dict | None) -> dict:
    if not isinstance(data, dict):
        data = {}

    normalized = {}

    for key, default_value in REQUIRED_KEYS.items():
        value = data.get(key, default_value)

        if value is None or value == "":
            value = default_value

        normalized[key] = value

    if not isinstance(normalized["actionable_recommendations"], list):
        normalized["actionable_recommendations"] = [
            str(normalized["actionable_recommendations"])
        ]

    return normalized


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
- actionable_recommendations must be an array of exactly 3 strings.
- Make the analysis specific to this video, not generic.

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
            temperature=0.25,
            max_tokens=1000
        )

        text = response.choices[0].message.content
        parsed = safe_parse_ai_json(text)

        if parsed:
            return {
                "ok": True,
                "mode": "nvidia",
                "error": None,
                "data": normalize_insights(parsed)
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