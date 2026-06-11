import streamlit as st
import pandas as pd
import plotly.express as px

from utils.analyzer import analyze_video, calculate_performance_score
from utils.youtube_utils import (
    extract_video_id,
    fetch_video_metadata,
    fetch_channel_latest_videos,
)

st.set_page_config(page_title="Stratify AI", page_icon="📊", layout="wide")

st.title("Stratify AI")
st.caption("AI-Powered Creator Intelligence Platform")

youtube_api_key = st.secrets.get("YOUTUBE_API_KEY", "")
nvidia_api_key = st.secrets.get("NVIDIA_API_KEY", "")

st.sidebar.title("Stratify AI")
analysis_mode = st.sidebar.radio(
    "Choose Analysis Type",
    [
        "Single Video Analysis",
        "Channel Intelligence",
        "Video Comparison",
        "Growth Strategy Generator",
    ],
)

if not youtube_api_key:
    st.error("Missing YOUTUBE_API_KEY in Streamlit secrets.")
    st.stop()


def format_number(value):
    try:
        return f"{int(value):,}"
    except Exception:
        return "0"


def render_ai_insights(ai, transcript):
    insights = ai.get("data", {})

    st.subheader("AI Insights")

    if ai.get("ok") and ai.get("mode") == "nvidia":
        if transcript.get("ok"):
            st.success("NVIDIA AI insights generated using metadata + transcript.")
        else:
            st.success("NVIDIA AI insights generated using metadata only.")
    elif ai.get("ok"):
        st.success(f"AI insights generated via {ai.get('mode', 'provider')}.")
    else:
        st.info("Fallback insights shown because live AI was unavailable.")

    st.markdown(
        """
        <style>
        .insight-card {
            background-color: #111827;
            border: 1px solid #263244;
            border-radius: 16px;
            padding: 20px;
            min-height: 155px;
            margin-bottom: 18px;
        }
        .insight-title {
            color: #93c5fd;
            font-size: 13px;
            font-weight: 800;
            margin-bottom: 12px;
            text-transform: uppercase;
            letter-spacing: 0.8px;
        }
        .insight-text {
            color: #f9fafb;
            font-size: 16px;
            line-height: 1.55;
        }
        .recommendation-card {
            background-color: #0f172a;
            border: 1px solid #263244;
            border-left: 5px solid #22c55e;
            border-radius: 12px;
            padding: 16px 18px;
            margin-bottom: 12px;
            color: #f9fafb;
            font-size: 16px;
            line-height: 1.5;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    def card(title, value):
        st.markdown(
            f"""
            <div class="insight-card">
                <div class="insight-title">{title}</div>
                <div class="insight-text">{value or "N/A"}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    r1c1, r1c2, r1c3 = st.columns(3)

    with r1c1:
        card("Content Style", insights.get("content_style", "N/A"))

    with r1c2:
        card("Target Audience", insights.get("target_audience", "N/A"))

    with r1c3:
        card("Hook Strength", insights.get("hook_strength", "N/A"))

    r2c1, r2c2, r2c3 = st.columns(3)

    with r2c1:
        card("Viral Potential", insights.get("viral_potential", "N/A"))

    with r2c2:
        card("Retention Drivers", insights.get("viewer_retention_drivers", "N/A"))

    with r2c3:
        card("Content Gaps", insights.get("content_gaps", "N/A"))

    st.markdown("### Actionable Recommendations")

    recommendations = insights.get("actionable_recommendations", [])

    if isinstance(recommendations, list) and recommendations:
        for i, rec in enumerate(recommendations, 1):
            st.markdown(
                f"""
                <div class="recommendation-card">
                    <strong>{i}.</strong> {rec}
                </div>
                """,
                unsafe_allow_html=True
            )
    else:
        st.write("N/A")

def video_card(video):
    with st.container(border=True):
        col1, col2 = st.columns([1, 3])

        with col1:
            if video.get("thumbnail"):
                st.image(video.get("thumbnail"), width="stretch")

        with col2:
            st.markdown(f"### {video.get('title', 'Unknown Title')}")
            st.write(f"**Channel:** {video.get('channel', 'Unknown')}")
            st.write(f"**Published:** {video.get('published_at', 'Unknown')}")

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Views", format_number(video.get("views", 0)))
            m2.metric("Likes", format_number(video.get("likes", 0)))
            m3.metric("Comments", format_number(video.get("comments", 0)))
            m4.metric("Engagement", f"{video.get('engagement_rate', 0)}%")


def videos_to_dataframe(videos):
    rows = []

    for video in videos:
        score = calculate_performance_score(
            views=video.get("views", 0),
            engagement_rate=video.get("engagement_rate", 0),
            like_count=video.get("likes", 0),
            comment_count=video.get("comments", 0),
        )

        rows.append({
            "Title": video.get("title", "Unknown"),
            "Published": video.get("published_at", ""),
            "Views": video.get("views", 0),
            "Likes": video.get("likes", 0),
            "Comments": video.get("comments", 0),
            "Engagement Rate": video.get("engagement_rate", 0),
            "Performance Score": score,
        })

    return pd.DataFrame(rows)


def generate_growth_strategy(channel, df):
    avg_views = int(df["Views"].mean()) if not df.empty else 0
    avg_engagement = round(df["Engagement Rate"].mean(), 2) if not df.empty else 0
    best_video = df.sort_values("Performance Score", ascending=False).iloc[0] if not df.empty else None

    st.subheader("Creator Growth Diagnosis")

    c1, c2, c3 = st.columns(3)
    c1.metric("Avg Views", format_number(avg_views))
    c2.metric("Avg Engagement", f"{avg_engagement}%")
    c3.metric("Videos Studied", len(df))

    st.markdown("### Current Positioning")
    st.write(
        f"{channel.get('title', 'This channel')} appears to have a content base that can be improved through stronger packaging, clearer repeatable formats, and more intentional audience targeting."
    )

    st.markdown("### Strongest Signal")
    if best_video is not None:
        st.write(f"Your strongest recent signal is: **{best_video['Title']}**")
        st.write(
            "This should be studied for topic, title structure, pacing, and audience emotion."
        )

    st.markdown("### 30-Day Growth Plan")
    st.write("- Identify the top 3 videos by performance score and turn them into repeatable content formats.")
    st.write("- Rewrite titles to make the emotional payoff clearer.")
    st.write("- Add stronger first 5-second hooks in every video.")
    st.write("- Use comment prompts that invite reactions, opinions, or debate.")

    st.markdown("### Next 10 Video Ideas")
    ideas = [
        "A sequel or follow-up to the best performing recent video",
        "A breakdown explaining why the top video worked",
        "A shorter, high-retention version of the same topic",
        "A comparison video using two popular topics or characters",
        "A reaction-style video built around audience comments",
        "A beginner-friendly version of the channel’s strongest niche",
        "A myth-vs-reality format around the channel topic",
        "A ranking video based on fan favorites",
        "A controversial but safe opinion video",
        "A compilation or recap optimized around one clear emotion",
    ]

    for i, idea in enumerate(ideas, 1):
        st.write(f"{i}. {idea}")


if analysis_mode == "Single Video Analysis":
    st.header("Single Video Analysis")
    video_url = st.text_input("Paste a YouTube video link")

    analyze_btn = st.button("Analyze Video", width="stretch")

    if analyze_btn:
        if not video_url.strip():
            st.warning("Please paste a YouTube link.")
            st.stop()

        if not nvidia_api_key:
            st.warning("Missing NVIDIA_API_KEY in Streamlit secrets. Fallback insights may be shown.")

        with st.spinner("Analyzing video..."):
            result = analyze_video(
                video_url=video_url,
                youtube_api_key=youtube_api_key,
                nvidia_api_key=nvidia_api_key,
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
        m1.metric("Views", format_number(metadata.get("views", 0)))
        m2.metric("Likes", format_number(metadata.get("likes", 0)))
        m3.metric("Comments", format_number(metadata.get("comments", 0)))
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
        render_ai_insights(ai, transcript)


elif analysis_mode == "Channel Intelligence":
    st.header("Channel Intelligence")
    channel_input = st.text_input("Paste a YouTube channel URL, @handle, or channel name")
    max_videos = st.slider("Number of recent videos to analyze", 5, 20, 10)

    analyze_btn = st.button("Analyze Channel", width="stretch")

    if analyze_btn:
        if not channel_input.strip():
            st.warning("Please enter a channel URL, handle, or name.")
            st.stop()

        with st.spinner("Fetching channel intelligence..."):
            result = fetch_channel_latest_videos(channel_input, youtube_api_key, max_results=max_videos)

        if not result.get("ok"):
            st.error(result.get("error", "Channel analysis failed."))
            st.stop()

        channel = result["channel"]
        videos = result["videos"]
        df = videos_to_dataframe(videos)

        col1, col2 = st.columns([1, 3])

        with col1:
            if channel.get("thumbnail"):
                st.image(channel.get("thumbnail"), width="stretch")

        with col2:
            st.subheader(channel.get("title", "Unknown Channel"))
            st.write(channel.get("description", "")[:400])

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Subscribers", format_number(channel.get("subscribers", 0)))
        m2.metric("Total Views", format_number(channel.get("total_views", 0)))
        m3.metric("Total Videos", format_number(channel.get("video_count", 0)))
        m4.metric("Videos Analyzed", len(videos))

        st.divider()

        st.subheader("Performance Dashboard")

        if not df.empty:
            fig_views = px.bar(df, x="Title", y="Views", title="Recent Video Views")
            st.plotly_chart(fig_views, width="stretch")

            fig_score = px.line(df, x="Title", y="Performance Score", markers=True, title="Performance Score by Video")
            st.plotly_chart(fig_score, width="stretch")

            st.dataframe(
                df[["Title", "Views", "Likes", "Comments", "Engagement Rate", "Performance Score"]],
                width="stretch",
                hide_index=True,
            )

            st.subheader("Top Performing Videos")
            top_df = df.sort_values("Performance Score", ascending=False).head(5)
            st.dataframe(top_df, width="stretch", hide_index=True)


elif analysis_mode == "Video Comparison":
    st.header("Video Comparison")
    st.caption("Compare 2–3 videos side-by-side and identify the stronger content strategy.")

    video_a = st.text_input("Video A URL")
    video_b = st.text_input("Video B URL")
    video_c = st.text_input("Video C URL optional")

    compare_btn = st.button("Compare Videos", width="stretch")

    if compare_btn:
        urls = [video_a, video_b, video_c]
        video_ids = [extract_video_id(url) for url in urls if url.strip()]
        video_ids = [vid for vid in video_ids if vid]

        if len(video_ids) < 2:
            st.warning("Please provide at least two valid YouTube video links.")
            st.stop()

        videos = []

        with st.spinner("Comparing videos..."):
            for vid in video_ids:
                metadata = fetch_video_metadata(vid, youtube_api_key)
                if metadata.get("ok"):
                    metadata["Performance Score"] = calculate_performance_score(
                        views=metadata.get("views", 0),
                        engagement_rate=metadata.get("engagement_rate", 0),
                        like_count=metadata.get("likes", 0),
                        comment_count=metadata.get("comments", 0),
                    )
                    videos.append(metadata)

        if len(videos) < 2:
            st.error("Could not fetch enough valid videos for comparison.")
            st.stop()

        df = pd.DataFrame([
            {
                "Title": video.get("title"),
                "Views": video.get("views"),
                "Likes": video.get("likes"),
                "Comments": video.get("comments"),
                "Engagement Rate": video.get("engagement_rate"),
                "Performance Score": video.get("Performance Score"),
            }
            for video in videos
        ])

        st.subheader("Comparison Table")
        st.dataframe(df, width="stretch", hide_index=True)

        fig = px.bar(df, x="Title", y="Performance Score", title="Performance Score Comparison")
        st.plotly_chart(fig, width="stretch")

        winner = df.sort_values("Performance Score", ascending=False).iloc[0]

        st.subheader("AI-Style Verdict")
        st.success(f"Winner: {winner['Title']}")

        st.write("This video currently has the strongest overall performance signal based on views, engagement, likes, comments, and composite score.")

        st.markdown("### Strategic Takeaways")
        st.write("- Study the winner’s title structure and topic angle.")
        st.write("- Compare the opening hook and emotional payoff.")
        st.write("- Use the lower-performing video as a rewrite opportunity for title, thumbnail, and pacing.")


elif analysis_mode == "Growth Strategy Generator":
    st.header("Growth Strategy Generator")
    st.caption("Generate a creator growth direction using recent channel performance.")

    channel_input = st.text_input("Paste a YouTube channel URL, @handle, or channel name")
    max_videos = st.slider("Videos to study", 5, 20, 10)

    strategy_btn = st.button("Generate Growth Strategy", width="stretch")

    if strategy_btn:
        if not channel_input.strip():
            st.warning("Please enter a channel URL, handle, or name.")
            st.stop()

        with st.spinner("Building growth strategy..."):
            result = fetch_channel_latest_videos(channel_input, youtube_api_key, max_results=max_videos)

        if not result.get("ok"):
            st.error(result.get("error", "Growth strategy generation failed."))
            st.stop()

        channel = result["channel"]
        videos = result["videos"]
        df = videos_to_dataframe(videos)

        st.subheader(channel.get("title", "Unknown Channel"))

        m1, m2, m3 = st.columns(3)
        m1.metric("Subscribers", format_number(channel.get("subscribers", 0)))
        m2.metric("Total Views", format_number(channel.get("total_views", 0)))
        m3.metric("Videos Studied", len(videos))

        st.divider()

        generate_growth_strategy(channel, df)