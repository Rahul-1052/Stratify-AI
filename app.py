import streamlit as st
from utils.analyzer import analyze_video

st.set_page_config(page_title="Stratify AI", page_icon="📊", layout="wide")

st.title("Stratify AI")
st.caption("YouTube Content Intelligence")

youtube_api_key = st.secrets.get("YOUTUBE_API_KEY", "")
gemini_api_key = st.secrets.get("GEMINI_API_KEY", "")

video_url = st.text_input("Paste a YouTube link")

analyze_btn = st.button("Analyze Video", use_container_width=True)

if analyze_btn:
    if not video_url.strip():
        st.warning("Please paste a YouTube link.")
        st.stop()

    with st.spinner("Analyzing video..."):
        result = analyze_video(
            video_url=video_url,
            youtube_api_key=youtube_api_key,
            gemini_api_key=gemini_api_key
        )

    if not result.get("ok"):
        st.error(result.get("error", "Something went wrong."))
        st.stop()

    metadata = result["metadata"]
    transcript = result["transcript"]
    ai = result["ai"]

    # Thumbnail + title
    col1, col2 = st.columns([1, 2])
    with col1:
        if metadata.get("thumbnail"):
            st.image(metadata["thumbnail"], use_container_width=True)
    with col2:
        st.subheader(metadata.get("title", "Unknown Title"))
        st.write(f"**Channel:** {metadata.get('channel', 'Unknown')}")
        st.write(f"**Published:** {metadata.get('published_at', 'Unknown')}")
        st.write(f"**Performance Score:** {result.get('performance_score', 0)}/100")

    # Metrics
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Views", f"{metadata.get('views', 0):,}")
    m2.metric("Likes", f"{metadata.get('likes', 0):,}")
    m3.metric("Comments", f"{metadata.get('comments', 0):,}")
    m4.metric("Engagement Rate", f"{metadata.get('engagement_rate', 0)}%")

    st.divider()

    # Transcript status
    st.subheader("Transcript Status")
    if transcript.get("ok"):
        st.success(
            f"Transcript available | Source: {transcript.get('source')} | Language: {transcript.get('language')}"
        )
        with st.expander("View Transcript Excerpt"):
            st.write((transcript.get("text") or "")[:2500])
    else:
        st.warning(transcript.get("error", "Transcript unavailable."))

    st.divider()

    # AI insights
    st.subheader("AI Insights")
    if ai.get("mode") == "gemini":
        st.success("Gemini insights generated successfully.")
    else:
        st.info("Fallback insights shown because Gemini was unavailable.")

    insights = ai.get("data", {})

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Content Style**")
        st.write(insights.get("content_style", "N/A"))

        st.markdown("**Target Audience**")
        st.write(insights.get("target_audience", "N/A"))

    with c2:
        st.markdown("**Why It Performs**")
        st.write(insights.get("why_it_performs", "N/A"))

        st.markdown("**Improvement Suggestion**")
        st.write(insights.get("improvement_suggestion", "N/A"))

    with st.expander("Debug Info"):
        st.json({
            "video_id": result.get("video_id"),
            "transcript_status": transcript,
            "ai_status": {
                "ok": ai.get("ok"),
                "mode": ai.get("mode"),
                "error": ai.get("error")
            }
        })