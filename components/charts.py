"""
Reusable Plotly chart builders for the analysis report.

Kept deliberately simple (no shared global state, pure functions that return
a `go.Figure`) so they're easy to drop into any Streamlit panel with
`st.plotly_chart(fig, use_container_width=True)`.
"""

import plotly.graph_objects as go

ACCENT = "#6C5CE7"
ACCENT_SOFT = "#A29BFE"
GOOD = "#00B894"
WARN = "#FDCB6E"
BAD = "#E17055"
TRACK = "rgba(255,255,255,0.08)"


def _band_color(value: float) -> str:
    if value >= 75:
        return GOOD
    if value >= 50:
        return WARN
    return BAD


def score_gauge(value: float, title: str) -> go.Figure:
    """A 0-100 radial gauge, color-coded by band."""
    value = max(0, min(100, value or 0))
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=value,
            number={"suffix": "", "font": {"size": 36, "color": "#F5F3FF"}},
            title={"text": title, "font": {"size": 14, "color": "#C7C2FF"}},
            gauge={
                "axis": {"range": [0, 100], "tickcolor": "#C7C2FF", "tickfont": {"color": "#C7C2FF"}},
                "bar": {"color": _band_color(value)},
                "bgcolor": "rgba(0,0,0,0)",
                "borderwidth": 0,
                "steps": [
                    {"range": [0, 50], "color": TRACK},
                    {"range": [50, 75], "color": TRACK},
                    {"range": [75, 100], "color": TRACK},
                ],
            },
        )
    )
    fig.update_layout(
        height=220,
        margin=dict(l=20, r=20, t=50, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        font={"color": "#F5F3FF"},
    )
    return fig


def quality_radar(scores: dict) -> go.Figure:
    """Radar chart for the six 0-10 resume quality dimensions."""
    labels = list(scores.keys())
    values = list(scores.values())
    if labels:
        labels = labels + [labels[0]]
        values = values + [values[0]]

    fig = go.Figure()
    fig.add_trace(
        go.Scatterpolar(
            r=values,
            theta=labels,
            fill="toself",
            line=dict(color=ACCENT_SOFT, width=2),
            fillcolor="rgba(108,92,231,0.35)",
            name="Resume Quality",
        )
    )
    fig.update_layout(
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(
                visible=True,
                range=[0, 10],
                tickfont={"color": "#C7C2FF", "size": 9},
                gridcolor="rgba(255,255,255,0.12)",
            ),
            angularaxis=dict(tickfont={"color": "#F5F3FF", "size": 11}, gridcolor="rgba(255,255,255,0.12)"),
        ),
        showlegend=False,
        height=380,
        margin=dict(l=40, r=40, t=30, b=30),
        paper_bgcolor="rgba(0,0,0,0)",
        font={"color": "#F5F3FF"},
    )
    return fig


def skill_match_bar(matching: list, partial: list, missing: list) -> go.Figure:
    """Horizontal stacked-style bar comparing skill match buckets by count."""
    categories = ["Matching", "Partially Matching", "Missing"]
    counts = [len(matching or []), len(partial or []), len(missing or [])]
    colors = [GOOD, WARN, BAD]

    fig = go.Figure(
        go.Bar(
            x=counts,
            y=categories,
            orientation="h",
            marker_color=colors,
            text=counts,
            textposition="outside",
            textfont={"color": "#F5F3FF"},
        )
    )
    fig.update_layout(
        height=220,
        margin=dict(l=10, r=30, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False, color="#C7C2FF"),
        yaxis=dict(showgrid=False, color="#F5F3FF"),
    )
    return fig
