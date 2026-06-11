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

    best_video = (
        df.sort_values("Performance Score", ascending=False).iloc[0]
        if not df.empty else None
    )

    st.subheader("🚀 Creator Growth Strategy")

    m1, m2, m3 = st.columns(3)

    with m1:
        st.metric("Average Views", format_number(avg_views))

    with m2:
        st.metric("Average Engagement", f"{avg_engagement}%")

    with m3:
        st.metric("Videos Studied", len(df))

    st.divider()

    st.markdown("## 🎯 Channel Positioning")

    st.info(
        f"""
        **{channel.get('title', 'This channel')}** has a foundation to grow through
        stronger content packaging, clearer audience targeting,
        and a more repeatable content strategy.
        """
    )

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("## ✅ What's Working")

        if best_video is not None:
            st.success(
                f"Top Performing Video:\n\n**{best_video['Title']}**"
            )

        st.write("• Existing audience interest is visible.")
        st.write("• Content niche already has engagement.")
        st.write("• There are repeatable content opportunities.")

    with col2:
        st.markdown("## ⚠ Growth Bottlenecks")

        st.warning(
            """
            • Content formats may not be consistent.

            • Titles could create stronger curiosity.

            • New viewers may lack context.

            • Packaging is likely limiting growth.
            """
        )

    st.divider()

    st.markdown("## 📅 30-Day Growth Plan")

    plan1, plan2, plan3 = st.columns(3)

    with plan1:
        st.markdown(
            """
            ### Week 1

            - Identify top 3 videos
            - Study titles
            - Study thumbnails
            - Identify common themes
            """
        )

    with plan2:
        st.markdown(
            """
            ### Week 2

            - Create 3 videos around winning topics
            - Improve first 5 seconds
            - Improve hooks
            """
        )

    with plan3:
        st.markdown(
            """
            ### Week 3-4

            - Double down on winners
            - Remove weak formats
            - Increase posting consistency
            """
        )

    st.divider()

    st.markdown("## 💡 Next 10 Video Ideas")

    ideas = [
        "Follow-up to your best performing video",
        "Behind the scenes of a popular topic",
        "Ranking format within your niche",
        "Audience reaction video",
        "Common mistakes in your niche",
        "Myth vs Reality format",
        "Top 5 list format",
        "Beginner guide version",
        "Expert breakdown version",
        "Most requested audience topic"
    ]

    for i, idea in enumerate(ideas, start=1):
        st.write(f"**{i}.** {idea}")

    st.divider()

    st.markdown("## 🎬 Content Expansion Opportunities")

    exp1, exp2, exp3 = st.columns(3)

    with exp1:
        st.success(
            """
            ### Shorts

            Convert best moments
            into short-form clips.
            """
        )

    with exp2:
        st.info(
            """
            ### Series Content

            Turn successful topics
            into repeatable series.
            """
        )

    with exp3:
        st.warning(
            """
            ### Audience Growth

            Create content that
            attracts new viewers.
            """
        )

    st.divider()

    st.markdown("## 🏁 Strategic Recommendation")

    st.success(
        """
        Focus less on producing more videos.

        Focus on repeating what already works,
        improving packaging,
        and increasing retention in the first 30 seconds.

        The fastest growth usually comes from
        improving winning formats rather than
        constantly testing completely new ones.
        """
    )


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
    st.caption("Understand what is working on a channel, what is underperforming, and what content patterns are worth repeating.")

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

        if df.empty:
            st.warning("No videos found for this channel.")
            st.stop()

        avg_score = round(df["Performance Score"].mean(), 1)
        avg_engagement = round(df["Engagement Rate"].mean(), 2)
        avg_views = int(df["Views"].mean())

        top_video = df.sort_values("Performance Score", ascending=False).iloc[0]
        highest_views_video = df.sort_values("Views", ascending=False).iloc[0]
        highest_engagement_video = df.sort_values("Engagement Rate", ascending=False).iloc[0]

        hidden_gems = df[
            (df["Views"] < df["Views"].median()) &
            (df["Engagement Rate"] > df["Engagement Rate"].median())
        ].sort_values("Engagement Rate", ascending=False)

        col1, col2 = st.columns([1, 3])

        with col1:
            if channel.get("thumbnail"):
                st.image(channel.get("thumbnail"), width="stretch")

        with col2:
            st.subheader(channel.get("title", "Unknown Channel"))
            st.write(channel.get("description", "")[:500])

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Subscribers", format_number(channel.get("subscribers", 0)))
        m2.metric("Total Views", format_number(channel.get("total_views", 0)))
        m3.metric("Total Videos", format_number(channel.get("video_count", 0)))
        m4.metric("Videos Analyzed", len(videos))

        st.divider()

        st.subheader("Channel Health")

        h1, h2, h3, h4 = st.columns(4)

        with h1:
            st.metric("Avg Performance", f"{avg_score}/100")

        with h2:
            st.metric("Avg Views", format_number(avg_views))

        with h3:
            st.metric("Avg Engagement", f"{avg_engagement}%")

        with h4:
            if avg_score >= 70:
                health_label = "Strong"
            elif avg_score >= 50:
                health_label = "Moderate"
            else:
                health_label = "Needs Work"

            st.metric("Channel Health", health_label)

        st.divider()

        st.subheader("Winning Content")

        win1, win2, win3 = st.columns(3)

        with win1:
            st.success(
                f"""
                ### 🏆 Best Overall

                **{top_video['Title']}**

                Score: **{top_video['Performance Score']}/100**  
                Views: **{format_number(top_video['Views'])}**  
                Engagement: **{top_video['Engagement Rate']}%**
                """
            )

        with win2:
            st.info(
                f"""
                ### 👀 Most Viewed

                **{highest_views_video['Title']}**

                Views: **{format_number(highest_views_video['Views'])}**  
                Score: **{highest_views_video['Performance Score']}/100**  
                Engagement: **{highest_views_video['Engagement Rate']}%**
                """
            )

        with win3:
            st.warning(
                f"""
                ### 💬 Best Engagement

                **{highest_engagement_video['Title']}**

                Engagement: **{highest_engagement_video['Engagement Rate']}%**  
                Views: **{format_number(highest_engagement_video['Views'])}**  
                Score: **{highest_engagement_video['Performance Score']}/100**
                """
            )

        st.divider()

        st.subheader("Reach vs Engagement Map")

        st.caption("Top-right videos are the strongest: they combine high reach with strong engagement.")

        fig_scatter = px.scatter(
            df,
            x="Views",
            y="Engagement Rate",
            size="Comments",
            hover_name="Title",
            text="Performance Score",
            title="Which videos combine reach and engagement?"
        )
        fig_scatter.update_traces(textposition="top center")
        st.plotly_chart(fig_scatter, width="stretch")

        st.divider()

        st.subheader("Hidden Opportunities")

        if not hidden_gems.empty:
            gem_cols = st.columns(min(3, len(hidden_gems)))

            for col, (_, row) in zip(gem_cols, hidden_gems.head(3).iterrows()):
                with col:
                    st.info(
                        f"""
                        ### 💎 Hidden Gem

                        **{row['Title']}**

                        This video has above-average engagement but below-average reach.

                        Views: **{format_number(row['Views'])}**  
                        Engagement: **{row['Engagement Rate']}%**  
                        Score: **{row['Performance Score']}/100**
                        """
                    )
        else:
            st.write("No clear hidden gems found in this sample. Try analyzing more videos.")

        st.divider()

        st.subheader("Content Pattern Diagnosis")

        d1, d2 = st.columns(2)

        with d1:
            st.success(
                f"""
                ### What Seems To Work

                - The best overall video is **{top_video['Title']}**
                - The highest-reach video is **{highest_views_video['Title']}**
                - Use these videos to identify repeatable topic angles, title patterns, and pacing styles.
                """
            )

        with d2:
            st.warning(
                f"""
                ### What Needs Improvement

                - Average engagement is **{avg_engagement}%**
                - Average performance score is **{avg_score}/100**
                - If these numbers are low, the channel may need stronger hooks, better titles, or clearer audience targeting.
                """
            )

        st.divider()

        st.subheader("Recommended Creator Actions")

        a1, a2, a3 = st.columns(3)

        with a1:
            st.info(
                """
                ### Repeat Winners

                Turn your best-performing video themes into repeatable formats or series.
                """
            )

        with a2:
            st.warning(
                """
                ### Fix Packaging

                Improve titles and thumbnails for videos with decent engagement but low reach.
                """
            )

        with a3:
            st.success(
                """
                ### Double Down

                Use hidden gems as clues for what your core audience actually wants.
                """
            )

        with st.expander("View detailed video data"):
            st.dataframe(
                df[
                    [
                        "Title",
                        "Views",
                        "Likes",
                        "Comments",
                        "Engagement Rate",
                        "Performance Score",
                    ]
                ],
                width="stretch",
                hide_index=True,
            )

elif analysis_mode == "Video Comparison":
    st.header("Video Comparison")
    st.caption("Compare 2–3 videos and understand which one has the stronger content strategy.")

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

        with st.spinner("Building comparison intelligence..."):
            for index, vid in enumerate(video_ids, start=1):
                metadata = fetch_video_metadata(vid, youtube_api_key)

                if metadata.get("ok"):
                    score = calculate_performance_score(
                        views=metadata.get("views", 0),
                        engagement_rate=metadata.get("engagement_rate", 0),
                        like_count=metadata.get("likes", 0),
                        comment_count=metadata.get("comments", 0),
                    )

                    views = metadata.get("views", 0)
                    likes = metadata.get("likes", 0)
                    comments = metadata.get("comments", 0)
                    engagement = metadata.get("engagement_rate", 0)

                    reach_score = min(int((views / max(views, 1)) * 100), 100)
                    engagement_score = min(int(engagement * 10), 100)
                    community_score = min(int((comments / max(likes, 1)) * 1000), 100)

                    metadata["Performance Score"] = score
                    metadata["Reach Score"] = reach_score
                    metadata["Engagement Score"] = engagement_score
                    metadata["Community Score"] = community_score
                    metadata["Label"] = f"Video {chr(64 + index)}"
                    videos.append(metadata)

        if len(videos) < 2:
            st.error("Could not fetch enough valid videos for comparison.")
            st.stop()

        max_views = max(video.get("views", 0) for video in videos) or 1

        for video in videos:
            video["Reach Score"] = min(int((video.get("views", 0) / max_views) * 100), 100)

        df = pd.DataFrame([
            {
                "Video": video.get("Label"),
                "Title": video.get("title"),
                "Views": video.get("views"),
                "Likes": video.get("likes"),
                "Comments": video.get("comments"),
                "Engagement Rate": video.get("engagement_rate"),
                "Performance Score": video.get("Performance Score"),
                "Reach Score": video.get("Reach Score"),
                "Engagement Score": video.get("Engagement Score"),
                "Community Score": video.get("Community Score"),
            }
            for video in videos
        ])

        winner = df.sort_values("Performance Score", ascending=False).iloc[0]
        weakest = df.sort_values("Performance Score", ascending=True).iloc[0]

        st.divider()

        st.subheader("Winner Summary")

        w1, w2, w3 = st.columns(3)

        with w1:
            st.metric("Winner", winner["Video"])

        with w2:
            st.metric("Winning Score", f"{winner['Performance Score']}/100")

        with w3:
            st.metric("Videos Compared", len(videos))

        st.success(f"🏆 **{winner['Video']} wins:** {winner['Title']}")

        st.divider()

        st.subheader("Side-by-Side Video Cards")

        card_cols = st.columns(len(videos))

        for col, video in zip(card_cols, videos):
            with col:
                with st.container(border=True):
                    if video.get("thumbnail"):
                        st.image(video.get("thumbnail"), width="stretch")

                    st.markdown(f"### {video.get('Label')}")
                    st.write(video.get("title", "Unknown Title")[:140])

                    st.metric("Performance", f"{video.get('Performance Score')}/100")
                    st.metric("Views", format_number(video.get("views", 0)))
                    st.metric("Engagement", f"{video.get('engagement_rate', 0)}%")

        st.divider()

        st.subheader("Plain-English Comparison")

        for video in videos:
            score = video.get("Performance Score", 0)
            views = video.get("views", 0)
            engagement = video.get("engagement_rate", 0)
            comments = video.get("comments", 0)

            if score >= 75:
                verdict = "Strong performer"
                explanation = "This video has a strong overall signal and is worth repeating as a content format."
            elif score >= 55:
                verdict = "Moderate performer"
                explanation = "This video has some useful signals, but the packaging or engagement can be improved."
            else:
                verdict = "Needs improvement"
                explanation = "This video does not show a strong breakout signal yet."

            with st.container(border=True):
                st.markdown(f"### {video.get('Label')} — {verdict}")
                st.write(f"**Title:** {video.get('title', 'Unknown Title')}")
                st.write(f"**Performance Score:** {score}/100")
                st.write(f"**Views:** {format_number(views)}")
                st.write(f"**Engagement Rate:** {engagement}%")
                st.write(f"**Comments:** {format_number(comments)}")
                st.info(explanation)

        st.divider()

        st.subheader("Comparison Matrix")

        st.dataframe(
            df[
                [
                    "Video",
                    "Title",
                    "Views",
                    "Likes",
                    "Comments",
                    "Engagement Rate",
                    "Performance Score",
                    "Reach Score",
                    "Engagement Score",
                    "Community Score",
                ]
            ],
            width="stretch",
            hide_index=True,
        )

        st.divider()

        st.subheader("Strategic Verdict")

        v1, v2 = st.columns(2)

        with v1:
            st.success(
                f"""
                ### What to Repeat

                **{winner['Video']}** has the strongest total signal.

                Repeat this video's:
                - topic angle
                - title structure
                - emotional promise
                - pacing pattern
                """
            )

        with v2:
            st.warning(
                f"""
                ### What to Improve

                **{weakest['Video']}** has the biggest improvement opportunity.

                Improve this video's:
                - opening hook
                - thumbnail clarity
                - title curiosity
                - audience promise
                """
            )

        st.divider()

        st.subheader("Creator Decision")

        if winner["Performance Score"] >= 75:
            st.success(
                """
                This is a strong content direction. Build a follow-up video using the same format,
                but improve the title and opening hook even further.
                """
            )
        elif winner["Performance Score"] >= 55:
            st.info(
                """
                This is a workable content direction. The winning video has signals worth testing again,
                but packaging and retention still need improvement.
                """
            )
        else:
            st.warning(
                """
                None of these videos show strong breakout signals yet. Focus on testing stronger topics,
                clearer titles, and more direct hooks.
                """
            )


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