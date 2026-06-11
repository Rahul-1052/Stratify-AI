import streamlit as st
from utils.analyzer import analyze_video

st.set_page_config(page_title="Stratify AI", page_icon="📊", layout="wide")

st.title("Stratify AI")
st.caption("YouTube Content Intelligence")

youtube_api_key = st.secrets.get("YOUTUBE_API_KEY", "")
nvidia_api_key = st.secrets.get("NVIDIA_API_KEY", "")

video_url = st.text_input("Paste a YouTube link")

analyze_btn = st.button("Analyze Video", width="stretch")

if analyze_btn:
    if not video_url.strip():
        st.warning("Please paste a YouTube link.")
        st.stop()

    if not youtube_api_key:
        st.error("Missing YOUTUBE_API_KEY in Streamlit secrets.")
        st.stop()

    if not nvidia_api_key:
        st.warning("Missing NVIDIA_API_KEY in Streamlit secrets. Fallback insights may be shown.")

    with st.spinner("Analyzing video..."):
        result = analyze_video(
            video_url=video_url,
            youtube_api_key=youtube_api_key,
            nvidia_api_key=nvidia_api_key
        )

    if not result.get("ok"):
        st.error(result.get("error", "Something went wrong."))
        st.stop()

    metadata = result["metadata"]
    transcript = result["transcript"]
    ai = result["ai"]

    col1, col2 = st.columns([1, 2])

    with col1:
        if metadata.get("thumbnail"):
            st.image(metadata["thumbnail"], width="stretch")

    with col2:
        st.subheader(metadata.get("title", "Unknown Title"))
        st.write(f"**Channel:** {metadata.get('channel', 'Unknown')}")
        st.write(f"**Published:** {metadata.get('published_at', 'Unknown')}")
        st.write(f"**Performance Score:** {result.get('performance_score', 0)}/100")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Views", f"{metadata.get('views', 0):,}")
    m2.metric("Likes", f"{metadata.get('likes', 0):,}")
    m3.metric("Comments", f"{metadata.get('comments', 0):,}")
    m4.metric("Engagement Rate", f"{metadata.get('engagement_rate', 0)}%")

    st.divider()

    st.subheader("Transcript Status")

    if transcript.get("ok"):
        st.success(
            f"Transcript available | Source: {transcript.get('source')} | Language: {transcript.get('language')}"
        )

        with st.expander("View Transcript Excerpt"):
            st.write((transcript.get("text") or "")[:2500])

    else:
        st.warning(
            "Transcript unavailable: YouTube may block transcript requests from hosted cloud environments. "
            "AI insights were generated using video metadata only."
        )

    st.divider()

    st.subheader("AI Insights")

    if ai.get("ok") and ai.get("mode") == "nvidia":
        if transcript.get("ok"):
            st.success("NVIDIA AI insights generated successfully using metadata and transcript context.")
        else:
            st.success("NVIDIA AI insights generated successfully using video metadata only.")
    elif ai.get("ok"):
        st.success(f"AI insights generated successfully via {ai.get('mode', 'provider')}.")
    else:
        st.info("AI fallback insights shown because the live AI provider was unavailable.")

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