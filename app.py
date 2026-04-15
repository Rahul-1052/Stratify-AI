import html
from datetime import datetime
from urllib.parse import parse_qs, urlparse

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils.ai_utils import analyze_video, compare_videos
from utils.youtube_utils import get_video_details


st.set_page_config(page_title="Stratify AI", page_icon="📈", layout="wide")


def safe(value):
    if value is None:
        return ""
    return html.escape(str(value))


def extract_video_id(youtube_url: str):
    try:
        parsed_url = urlparse(youtube_url.strip())

        if parsed_url.hostname in ["www.youtube.com", "youtube.com", "m.youtube.com"]:
            query_params = parse_qs(parsed_url.query)
            return query_params.get("v", [None])[0]

        if parsed_url.hostname == "youtu.be":
            return parsed_url.path.lstrip("/")

        return None
    except Exception:
        return None


def format_publish_date(date_str: str) -> str:
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ")
        return dt.strftime("%b %d, %Y")
    except Exception:
        return date_str


def score_metric(value, low, medium, high):
    if value >= high:
        return 100
    elif value >= medium:
        return 75
    elif value >= low:
        return 50
    elif value > 0:
        return 25
    return 0


def get_score_label(score):
    if score >= 80:
        return "Excellent"
    elif score >= 65:
        return "Strong"
    elif score >= 45:
        return "Average"
    return "Needs Improvement"


def get_score_color(score):
    if score >= 80:
        return "#22c55e"
    elif score >= 65:
        return "#3b82f6"
    elif score >= 45:
        return "#f59e0b"
    return "#ef4444"


def get_performance_signal(views, engagement_rate):
    if views >= 100000 and engagement_rate < 1.5:
        return "High reach, weak engagement"
    elif views < 20000 and engagement_rate >= 3:
        return "Low reach, strong engagement"
    elif views >= 100000 and engagement_rate >= 3:
        return "High reach, strong engagement"
    return "Moderate performance"


def benchmark_decision(score, engagement_rate):
    if score >= 70 and engagement_rate >= 2.5:
        return "Yes — strong benchmark candidate."
    elif score >= 50:
        return "Possibly — selective insights."
    return "No — weak benchmark candidate."


@st.cache_data(show_spinner=False, ttl=600)
def fetch_video_data(video_id):
    """
    Supports both:
    1. get_video_details(video_id) -> dict | None
    2. get_video_details(video_id) -> (dict | None, debug_dict)
    """
    result = get_video_details(video_id)

    if isinstance(result, tuple) and len(result) == 2:
        return result

    if result is None:
        return None, {
            "ok": False,
            "stage": "fetch_failed",
            "video_id": video_id,
            "message": "YouTube API returned no data.",
        }

    return result, {
        "ok": True,
        "stage": "success",
        "video_id": video_id,
        "message": "Video fetched successfully.",
    }


def prepare_video_metrics(video_data):
    views = int(video_data.get("views", 0))
    likes = int(video_data.get("likes", 0))
    comments = int(video_data.get("comments", 0))

    like_rate = (likes / views) * 100 if views > 0 else 0
    comment_rate = (comments / views) * 100 if views > 0 else 0
    engagement_rate = ((likes + comments) / views) * 100 if views > 0 else 0

    likes_per_1k = (likes / views) * 1000 if views > 0 else 0
    comments_per_1k = (comments / views) * 1000 if views > 0 else 0

    views_score = score_metric(views, 10000, 50000, 200000)
    like_rate_score = score_metric(like_rate, 0.5, 1.5, 3.0)
    comment_rate_score = score_metric(comment_rate, 0.05, 0.15, 0.4)
    engagement_score = score_metric(engagement_rate, 1.0, 2.5, 5.0)

    final_score = round(
        (views_score * 0.20)
        + (like_rate_score * 0.30)
        + (comment_rate_score * 0.20)
        + (engagement_score * 0.30),
        1,
    )

    score_label = get_score_label(final_score)
    score_color = get_score_color(final_score)
    performance_signal = get_performance_signal(views, engagement_rate)
    decision = benchmark_decision(final_score, engagement_rate)
    confidence = "High" if views >= 100000 else "Medium" if views >= 20000 else "Low"

    return {
        **video_data,
        "views": views,
        "likes": likes,
        "comments": comments,
        "like_rate": round(like_rate, 2),
        "comment_rate": round(comment_rate, 2),
        "engagement_rate": round(engagement_rate, 2),
        "likes_per_1k": round(likes_per_1k, 2),
        "comments_per_1k": round(comments_per_1k, 2),
        "final_score": final_score,
        "score_label": score_label,
        "score_color": score_color,
        "performance_signal": performance_signal,
        "decision": decision,
        "confidence": confidence,
    }


def metric_card(title, value):
    st.markdown(
        f"""
        <div style="
            background: linear-gradient(135deg, #111827, #1f2937);
            padding: 16px;
            border-radius: 18px;
            border: 1px solid rgba(255,255,255,0.08);
            box-shadow: 0 8px 24px rgba(0,0,0,0.25);
            min-height: 100px;
        ">
            <div style="font-size: 0.9rem; color: #9ca3af; margin-bottom: 8px;">{safe(title)}</div>
            <div style="font-size: 1.6rem; font-weight: 700; color: white;">{safe(value)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def insight_card(title, body, accent="#93c5fd", min_height=180):
    st.markdown(
        f"""
        <div style="
            background: #111827;
            padding: 20px;
            border-radius: 18px;
            border: 1px solid rgba(255,255,255,0.08);
            min-height: {min_height}px;
        ">
            <div style="color: {accent}; font-weight: 700; margin-bottom: 10px;">{safe(title)}</div>
            <div style="color: white; font-size: 1.03rem; line-height: 1.65;">{safe(body)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def create_score_gauge(score):
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=score,
            number={"suffix": "/100", "font": {"size": 34}},
            title={"text": "Performance Score"},
            gauge={
                "axis": {"range": [0, 100]},
                "bar": {"color": "#7c3aed"},
                "steps": [
                    {"range": [0, 45], "color": "#3f1d1d"},
                    {"range": [45, 65], "color": "#4a3411"},
                    {"range": [65, 80], "color": "#172554"},
                    {"range": [80, 100], "color": "#052e16"},
                ],
            },
        )
    )

    fig.update_layout(
        paper_bgcolor="#0f172a",
        plot_bgcolor="#0f172a",
        font={"color": "white"},
        margin=dict(l=20, r=20, t=60, b=20),
        height=320,
    )
    return fig


def create_metric_bar_chart(views, likes, comments):
    df = pd.DataFrame(
        {
            "Metric": ["Views", "Likes", "Comments"],
            "Value": [views, likes, comments],
        }
    )

    fig = px.bar(df, x="Metric", y="Value", title="Performance Breakdown", text="Value")
    fig.update_traces(texttemplate="%{text:,}", textposition="outside")
    fig.update_layout(
        paper_bgcolor="#0f172a",
        plot_bgcolor="#0f172a",
        font={"color": "white"},
        xaxis_title="",
        yaxis_title="Count",
        margin=dict(l=20, r=20, t=60, b=20),
        height=360,
    )
    return fig


def create_engagement_chart(like_rate, comment_rate, engagement_rate):
    df = pd.DataFrame(
        {
            "Metric": ["Like Rate", "Comment Rate", "Engagement Rate"],
            "Value": [like_rate, comment_rate, engagement_rate],
        }
    )

    fig = px.bar(df, x="Metric", y="Value", title="Engagement Quality", text="Value")
    fig.update_traces(texttemplate="%{text:.2f}%", textposition="outside")
    fig.update_layout(
        paper_bgcolor="#0f172a",
        plot_bgcolor="#0f172a",
        font={"color": "white"},
        xaxis_title="",
        yaxis_title="Percentage",
        margin=dict(l=20, r=20, t=60, b=20),
        height=360,
    )
    return fig


def create_comparison_chart(video_a, video_b):
    df = pd.DataFrame(
        {
            "Metric": ["Views", "Likes", "Comments", "Engagement Rate", "Score"],
            "Video A": [
                video_a["views"],
                video_a["likes"],
                video_a["comments"],
                video_a["engagement_rate"],
                video_a["final_score"],
            ],
            "Video B": [
                video_b["views"],
                video_b["likes"],
                video_b["comments"],
                video_b["engagement_rate"],
                video_b["final_score"],
            ],
        }
    )

    melted = df.melt(id_vars="Metric", var_name="Video", value_name="Value")
    fig = px.bar(
        melted,
        x="Metric",
        y="Value",
        color="Video",
        barmode="group",
        title="Video A vs Video B",
        text="Value",
    )
    fig.update_layout(
        paper_bgcolor="#0f172a",
        plot_bgcolor="#0f172a",
        font={"color": "white"},
        xaxis_title="",
        yaxis_title="Value",
        margin=dict(l=20, r=20, t=60, b=20),
        height=420,
    )
    return fig


def render_video_summary_card(video_data, label):
    st.markdown(
        f"""
        <div style="
            background: linear-gradient(135deg, #111827, #1f2937);
            padding: 22px;
            border-radius: 20px;
            border: 1px solid rgba(255,255,255,0.08);
            box-shadow: 0 10px 28px rgba(0,0,0,0.22);
            min-height: 220px;
        ">
            <div style="font-size: 0.95rem; color: #a78bfa; font-weight: 700; margin-bottom: 10px;">
                {safe(label)}
            </div>
            <div style="font-size: 1.35rem; font-weight: 800; color: white; line-height: 1.35;">
                {safe(video_data.get('title', 'Untitled Video'))}
            </div>
            <div style="margin-top: 14px; color: #cbd5e1; font-size: 1rem;">
                📺 <b>Channel:</b> {safe(video_data.get('channel', 'Unknown'))}
            </div>
            <div style="margin-top: 8px; color: #cbd5e1; font-size: 1rem;">
                📅 <b>Published:</b> {safe(format_publish_date(video_data.get('published_at', '')))}
            </div>
            <div style="margin-top: 12px; color: #93c5fd; font-size: 1rem; font-weight: 600;">
                {safe(video_data.get('performance_signal', ''))}
            </div>
            <div style="margin-top: 10px; color: #94a3b8; font-size: 0.92rem;">
                Confidence Level: <b>{safe(video_data.get('confidence', ''))}</b>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_score_card(video_data):
    st.markdown(
        f"""
        <div style="
            background: linear-gradient(135deg, #0f172a, #111827);
            padding: 24px;
            border-radius: 20px;
            border: 1px solid rgba(255,255,255,0.08);
            box-shadow: 0 10px 28px rgba(0,0,0,0.22);
            text-align: center;
            min-height: 220px;
        ">
            <div style="font-size: 0.95rem; color: #9ca3af;">Performance Score</div>
            <div style="font-size: 2.6rem; font-weight: 800; color: {video_data['score_color']}; margin-top: 10px;">
                {video_data['final_score']}
            </div>
            <div style="font-size: 1rem; font-weight: 700; color: white; margin-top: 8px;">
                {safe(video_data['score_label'])}
            </div>
            <div style="margin-top: 14px; color: #cbd5e1; font-size: 0.95rem;">
                {safe(video_data['decision'])}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_video_metrics(video_data):
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1:
        metric_card("Views", f"{video_data['views']:,}")
    with c2:
        metric_card("Likes", f"{video_data['likes']:,}")
    with c3:
        metric_card("Comments", f"{video_data['comments']:,}")
    with c4:
        metric_card("Engagement Rate", f"{video_data['engagement_rate']:.2f}%")
    with c5:
        metric_card("Like Rate", f"{video_data['like_rate']:.2f}%")
    with c6:
        metric_card("Comment Rate", f"{video_data['comment_rate']:.2f}%")


def render_key_takeaway(video_data):
    message = (
        "strongly converts attention into engagement"
        if video_data["final_score"] > 70
        else "needs stronger engagement conversion to perform like a benchmark-worthy video"
    )

    st.info(
        f"This video shows {video_data['performance_signal']}. "
        f"It is rated {video_data['score_label']}, which suggests it {message}."
    )


def render_ai_analysis_tabs(video_data, analysis):
    st.subheader("🧠 AI Insights")
    tab1, tab2, tab3 = st.tabs(["Core Insights", "Behavioral Insight", "Decision View"])

    with tab1:
        a1, a2 = st.columns(2)
        with a1:
            insight_card("Content Style", analysis.get("content_style", ""), "#93c5fd")
            st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)
            insight_card("Target Audience", analysis.get("target_audience", ""), "#86efac")
        with a2:
            insight_card("Why It Performs", analysis.get("engagement_reason", ""), "#fbbf24")
            st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)
            insight_card("Improvement Suggestion", analysis.get("improvement_suggestion", ""), "#f87171")

    with tab2:
        insight_card(
            "Psychological Triggers",
            analysis.get("psychological_triggers", ""),
            "#c084fc",
            220,
        )

    with tab3:
        d1, d2 = st.columns(2)
        with d1:
            metric_card("Performance Score", f"{video_data['final_score']}/100")
            st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)
            metric_card("Rating", video_data["score_label"])
        with d2:
            st.markdown(
                f"""
                <div style="
                    background: linear-gradient(135deg, #111827, #1f2937);
                    padding: 20px;
                    border-radius: 18px;
                    border: 1px solid rgba(255,255,255,0.08);
                    min-height: 220px;
                ">
                    <div style="color: #93c5fd; font-weight: 700; margin-bottom: 10px;">Performance Signal</div>
                    <div style="color: white; font-size: 1.02rem; margin-bottom: 18px;">
                        {safe(video_data['performance_signal'])}
                    </div>
                    <div style="color: #c4b5fd; font-weight: 700; margin-bottom: 10px;">Benchmark Decision</div>
                    <div style="color: white; font-size: 1.02rem; line-height: 1.7;">
                        {safe(video_data['decision'])}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )


st.markdown(
    """
    <style>
    .main {
        background:
            radial-gradient(circle at top left, rgba(124, 58, 237, 0.10), transparent 28%),
            radial-gradient(circle at top right, rgba(37, 99, 235, 0.10), transparent 28%),
            #0b1220;
    }

    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 1300px;
    }

    h1, h2, h3 {
        letter-spacing: -0.02em;
    }

    div[data-testid="stTextInput"] input {
        border-radius: 12px;
        border: 1px solid rgba(255,255,255,0.12);
        background-color: #111827;
        color: white;
        padding: 0.75rem 1rem;
    }

    div[data-testid="stTextInput"] label p,
    div[data-testid="stRadio"] label p,
    div[data-testid="stMarkdownContainer"] p {
        color: white;
    }

    div[data-testid="stButton"] > button {
        background: linear-gradient(135deg, #2563eb, #7c3aed);
        color: white;
        border: none;
        border-radius: 12px;
        font-weight: 700;
        padding: 0.65rem 1.2rem;
    }

    div[data-testid="stButton"] > button:hover {
        opacity: 0.94;
    }

    div[data-testid="stExpander"] {
        border-radius: 14px;
        border: 1px solid rgba(255,255,255,0.08);
        overflow: hidden;
    }

    div[data-testid="stTabs"] button {
        font-weight: 600;
    }

    div[data-testid="stDataFrame"] {
        border-radius: 16px;
        overflow: hidden;
        border: 1px solid rgba(255,255,255,0.08);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# HERO
st.markdown(
    """
    <div style="
        padding: 30px;
        border-radius: 24px;
        background: linear-gradient(135deg, rgba(17,24,39,0.96), rgba(15,23,42,0.96));
        border: 1px solid rgba(255,255,255,0.08);
        box-shadow: 0 20px 50px rgba(0,0,0,0.35);
        margin-bottom: 14px;
    ">
        <div style="font-size: 2.35rem; font-weight: 900; color: white;">
            🧠 Stratify AI
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.caption("© 2026 Rahul Karaka · Stratify AI · All Rights Reserved")

st.markdown("Decode what drives video performance — using data + AI.")
st.caption("AI-powered content intelligence for performance-driven decisions")
st.caption(
    "• Decode engagement patterns  \n"
    "• Understand audience psychology  \n"
    "• Benchmark winning content"
)

st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

st.subheader("🔗 Input")
input_col1, input_col2 = st.columns(2)

with input_col1:
    youtube_link_a = st.text_input(
        "Video A URL",
        placeholder="Paste first YouTube video link here",
    )

with input_col2:
    youtube_link_b = st.text_input(
        "Video B URL (optional)",
        placeholder="Paste second YouTube video link for comparison",
    )

video_a = None
video_b = None
video_data_a = None
video_data_b = None
debug_a = None
debug_b = None

if youtube_link_a:
    video_id_a = extract_video_id(youtube_link_a)
    if video_id_a:
        video_data_a, debug_a = fetch_video_data(video_id_a)

        if video_data_a:
            video_a = prepare_video_metrics(video_data_a)
        else:
            st.error("Could not fetch details for Video A.")
            with st.expander("Debug details for Video A"):
                st.json(debug_a)
    else:
        st.error("Invalid YouTube URL for Video A.")

if youtube_link_b:
    video_id_b = extract_video_id(youtube_link_b)
    if video_id_b:
        video_data_b, debug_b = fetch_video_data(video_id_b)

        if video_data_b:
            video_b = prepare_video_metrics(video_data_b)
        else:
            st.error("Could not fetch details for Video B.")
            with st.expander("Debug details for Video B"):
                st.json(debug_b)
    else:
        st.error("Invalid YouTube URL for Video B.")

if video_a and not video_b:
    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    left, right = st.columns([2.2, 1])

    with left:
        render_video_summary_card(video_a, "Video Intelligence")

    with right:
        render_score_card(video_a)

    render_key_takeaway(video_a)

    st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)
    render_video_metrics(video_a)

    st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)

    st.success(f"Decision Intelligence: {video_a['decision']}")

    with st.expander("View thumbnail"):
        if video_a.get("thumbnail"):
            st.image(video_a["thumbnail"], width=260)

    if st.button("Analyze Video A with AI", key="analyze_video_a_btn"):
        with st.spinner("Analyzing video..."):
            analysis = analyze_video(video_a)

        st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
        render_ai_analysis_tabs(video_a, analysis)

    st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)
    st.subheader("📉 Visual Intelligence")

    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.plotly_chart(
            create_metric_bar_chart(video_a["views"], video_a["likes"], video_a["comments"]),
            use_container_width=True,
            key="single_metric_bar_chart",
        )

    with chart_col2:
        st.plotly_chart(
            create_score_gauge(video_a["final_score"]),
            use_container_width=True,
            key="single_score_gauge",
        )

    chart_col3, chart_col4 = st.columns(2)

    with chart_col3:
        st.plotly_chart(
            create_engagement_chart(
                video_a["like_rate"],
                video_a["comment_rate"],
                video_a["engagement_rate"],
            ),
            use_container_width=True,
            key="single_engagement_chart",
        )

    with chart_col4:
        st.markdown(
            f"""
            <div style="
                background: linear-gradient(135deg, #111827, #1f2937);
                padding: 24px;
                border-radius: 20px;
                border: 1px solid rgba(255,255,255,0.08);
                box-shadow: 0 10px 28px rgba(0,0,0,0.18);
                min-height: 360px;
            ">
                <div style="font-size: 1.15rem; font-weight: 700; color: white; margin-bottom: 20px;">
                    Engagement Diagnostics
                </div>
                <div style="color: #cbd5e1; font-size: 1rem; margin-bottom: 16px;">
                    👍 <b>Likes per 1K views:</b> {video_a['likes_per_1k']:.2f}
                </div>
                <div style="color: #cbd5e1; font-size: 1rem; margin-bottom: 16px;">
                    💬 <b>Comments per 1K views:</b> {video_a['comments_per_1k']:.2f}
                </div>
                <div style="color: #cbd5e1; font-size: 1rem; margin-bottom: 16px;">
                    📈 <b>Engagement quality:</b> {safe(video_a['score_label'])}
                </div>
                <div style="color: #93c5fd; font-size: 1rem; line-height: 1.7; margin-top: 24px;">
                    This panel helps interpret whether the video is only getting reach,
                    or also converting attention into meaningful audience response.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

elif video_a and video_b:
    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
    st.subheader("⚔️ Comparative Intelligence")

    comp_left, comp_right = st.columns(2)

    with comp_left:
        render_video_summary_card(video_a, "Video A")
        st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)
        render_score_card(video_a)

    with comp_right:
        render_video_summary_card(video_b, "Video B")
        st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)
        render_score_card(video_b)

    st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)

    compare_table = pd.DataFrame(
        {
            "Metric": [
                "Views",
                "Likes",
                "Comments",
                "Engagement Rate",
                "Like Rate",
                "Comment Rate",
                "Performance Score",
            ],
            "Video A": [
                f"{video_a['views']:,}",
                f"{video_a['likes']:,}",
                f"{video_a['comments']:,}",
                f"{video_a['engagement_rate']:.2f}%",
                f"{video_a['like_rate']:.2f}%",
                f"{video_a['comment_rate']:.2f}%",
                f"{video_a['final_score']}/100",
            ],
            "Video B": [
                f"{video_b['views']:,}",
                f"{video_b['likes']:,}",
                f"{video_b['comments']:,}",
                f"{video_b['engagement_rate']:.2f}%",
                f"{video_b['like_rate']:.2f}%",
                f"{video_b['comment_rate']:.2f}%",
                f"{video_b['final_score']}/100",
            ],
        }
    )

    st.dataframe(compare_table, use_container_width=True, hide_index=True)

    winner = "Video A" if video_a["final_score"] >= video_b["final_score"] else "Video B"
    winner_score = max(video_a["final_score"], video_b["final_score"])

    st.success(
        f"Comparison Decision: {winner} is currently the stronger benchmark candidate with a score of {winner_score}/100."
    )

    render_key_takeaway(video_a if winner == "Video A" else video_b)

    thumb1, thumb2 = st.columns(2)
    with thumb1:
        with st.expander("View Video A thumbnail"):
            if video_a.get("thumbnail"):
                st.image(video_a["thumbnail"], width=260)

    with thumb2:
        with st.expander("View Video B thumbnail"):
            if video_b.get("thumbnail"):
                st.image(video_b["thumbnail"], width=260)

    st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)
    st.subheader("🤖 AI Comparison Verdict")

    if st.button("Compare Videos with AI", key="compare_videos_ai_btn"):
        with st.spinner("Analyzing comparison..."):
            comparison_result = compare_videos(video_a, video_b)

        st.markdown(
            """
            <div style="
                background: linear-gradient(135deg, #111827, #1f2937);
                padding: 24px;
                border-radius: 20px;
                border-left: 4px solid #7c3aed;
                border: 1px solid rgba(255,255,255,0.08);
                margin-top: 8px;
                margin-bottom: 8px;
            "></div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(f"### 🏆 Winner: {comparison_result.get('winner', '')}")
        st.write(comparison_result.get("reason", ""))
        st.markdown(f"**Key Difference:** {comparison_result.get('key_difference', '')}")
        st.markdown(f"**Strategy Insight:** {comparison_result.get('strategy_insight', '')}")

    st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)
    st.subheader("🧠 AI Analysis")

    analysis_choice = st.radio(
        "Choose which video to analyze deeply",
        ["Video A", "Video B"],
        horizontal=True,
    )

    selected_video = video_a if analysis_choice == "Video A" else video_b

    if st.button("Analyze Selected Video with AI", key="analyze_selected_video_btn"):
        with st.spinner("Analyzing selected video..."):
            analysis = analyze_video(selected_video)

        render_ai_analysis_tabs(selected_video, analysis)

    st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)
    st.subheader("📊 Comparison Charts")

    chart_left, chart_right = st.columns(2)

    with chart_left:
        st.plotly_chart(
            create_comparison_chart(video_a, video_b),
            use_container_width=True,
            key="comparison_bar_chart",
        )

    with chart_right:
        st.plotly_chart(
            create_score_gauge(video_a["final_score"]),
            use_container_width=True,
            key="comparison_gauge_video_a",
        )
        st.plotly_chart(
            create_score_gauge(video_b["final_score"]),
            use_container_width=True,
            key="comparison_gauge_video_b",
        )