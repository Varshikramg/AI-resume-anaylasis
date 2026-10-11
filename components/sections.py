"""
Streamlit rendering functions for each section of the candidate intelligence
report. Every function takes the parsed analysis dict (or a sub-dict of it)
and is defensive about missing keys, since LLM output - even with a strict
schema - can occasionally omit a field.
"""

import streamlit as st

from components.charts import quality_radar, score_gauge, skill_match_bar

DECISION_STYLE = {
    "hire": ("#00B894", "✅ HIRE"),
    "consider": ("#FDCB6E", "🟡 CONSIDER"),
    "reject": ("#E17055", "❌ REJECT"),
}


def g(d, key, default=None):
    """Safe nested-dict getter that tolerates None/missing values."""
    if not isinstance(d, dict):
        return default
    val = d.get(key, default)
    return default if val is None else val


def bullet_list(items, empty_text="Not specified in the resume context."):
    items = [i for i in (items or []) if str(i).strip()]
    if not items:
        st.caption(empty_text)
        return
    for item in items:
        st.markdown(f"- {item}")


def render_overview(result: dict):
    ats = g(result, "ats_score", {})
    fit = g(result, "job_fit_percentage", {})
    ats_score = g(ats, "score", 0) if isinstance(ats, dict) else ats
    fit_score = g(fit, "score", 0) if isinstance(fit, dict) else fit

    try:
        ats_score = float(ats_score)
    except (TypeError, ValueError):
        ats_score = 0
    try:
        fit_score = float(fit_score)
    except (TypeError, ValueError):
        fit_score = 0

    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(score_gauge(ats_score, "ATS Compatibility Score"), use_container_width=True)
        with st.expander("How this score was calculated"):
            st.write(g(ats, "explanation", "Not provided."))
        with st.expander("ATS optimization issues"):
            bullet_list(g(ats, "optimization_issues", []))
        with st.expander("Missing keywords"):
            bullet_list(g(ats, "missing_keywords", []))

    with col2:
        st.plotly_chart(score_gauge(fit_score, "Job Fit Percentage"), use_container_width=True)
        with st.expander("Why this percentage was assigned"):
            st.write(g(fit, "explanation", "Not provided."))
        with st.expander("Strengths for this role"):
            bullet_list(g(fit, "strengths", []))
        with st.expander("Weaknesses for this role"):
            bullet_list(g(fit, "weaknesses", []))


def render_skills(result: dict):
    matching = g(result, "matching_skills", [])
    partial = g(result, "partially_matching_skills", [])
    missing = g(result, "missing_skills", [])
    gap = g(result, "skill_gap_analysis", {})

    st.plotly_chart(skill_match_bar(matching, partial, missing), use_container_width=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("**✅ Matching Skills**")
        bullet_list(matching)
    with c2:
        st.markdown("**🟡 Partially Matching**")
        bullet_list(partial)
    with c3:
        st.markdown("**🔴 Missing Skills**")
        bullet_list(missing)

    st.markdown("**🚀 Emerging Skills to Learn**")
    bullet_list(g(gap, "emerging_skills_to_learn", []))
    summary = g(gap, "summary", "")
    if summary:
        st.info(summary)


def render_projects(result: dict):
    projects = g(result, "project_analysis", [])
    if not projects:
        st.caption("No distinct projects were identified in the resume context.")
        return

    for proj in projects:
        name = g(proj, "project_name", "Untitled Project")
        score = g(proj, "relevance_score", 0)
        with st.expander(f"📁 {name} — Relevance {score}/100"):
            st.progress(min(max(int(score or 0), 0), 100) / 100)
            st.markdown("**Technologies Used**")
            bullet_list(g(proj, "technologies_used", []))
            st.markdown("**Business Impact**")
            st.write(g(proj, "business_impact", "Not specified in resume."))
            st.markdown("**Recruiter Impression**")
            st.write(g(proj, "recruiter_impression", "Not provided."))
            st.markdown("**Suggestions for Improvement**")
            bullet_list(g(proj, "improvement_suggestions", []))


def render_quality(result: dict):
    quality = g(result, "resume_quality_scores", {})
    dims = {
        "Structure": g(quality, "structure", 0),
        "Readability": g(quality, "readability", 0),
        "Keyword Optimization": g(quality, "keyword_optimization", 0),
        "Technical Depth": g(quality, "technical_depth", 0),
        "Quantified Achievements": g(quality, "quantified_achievements", 0),
        "Industry Alignment": g(quality, "industry_alignment", 0),
    }
    dims = {k: float(v) if isinstance(v, (int, float, str)) and str(v).replace(".", "", 1).isdigit() else 0 for k, v in dims.items()}

    col1, col2 = st.columns([3, 2])
    with col1:
        st.plotly_chart(quality_radar(dims), use_container_width=True)
    with col2:
        for label, val in dims.items():
            st.metric(label, f"{val:g} / 10")

    comment = g(quality, "overall_comment", "")
    if comment:
        st.info(comment)


def render_recruiter_feedback(result: dict):
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**💪 Top Strengths**")
        bullet_list(g(result, "strengths", []))
    with c2:
        st.markdown("**⚠️ Top Weaknesses**")
        bullet_list(g(result, "weaknesses", []))

    st.markdown("**🛠️ Immediate Improvements**")
    bullet_list(g(result, "immediate_improvements", []))


def render_rewrites(result: dict):
    rewrites = g(result, "resume_rewrite_suggestions", [])
    if not rewrites:
        st.caption("No specific rewrite suggestions were generated.")
        return
    for i, item in enumerate(rewrites, start=1):
        st.markdown(f"**Bullet {i}**")
        st.markdown(f"❌ *Original:* {g(item, 'original_bullet', '—')}")
        st.markdown(f"✅ *Improved:* {g(item, 'improved_bullet', '—')}")
        why = g(item, "why_improved", "")
        if why:
            st.caption(f"Why: {why}")
        st.divider()


def render_interview_prep(result: dict):
    q = g(result, "interview_questions", {})
    tabs = st.tabs(["Technical (10)", "Project-Based (5)", "HR (5)", "Scenario-Based (5)"])
    with tabs[0]:
        bullet_list(g(q, "technical_questions", []))
    with tabs[1]:
        bullet_list(g(q, "project_based_questions", []))
    with tabs[2]:
        bullet_list(g(q, "hr_questions", []))
    with tabs[3]:
        bullet_list(g(q, "scenario_based_questions", []))


def render_roadmap(result: dict):
    roadmap = g(result, "learning_roadmap", {})
    horizons = [
        ("immediate_1_month", "🟢 Immediate (1 Month)"),
        ("intermediate_3_months", "🟡 Intermediate (3 Months)"),
        ("advanced_6_months", "🔴 Advanced (6 Months)"),
    ]
    cols = st.columns(3)
    for col, (key, label) in zip(cols, horizons):
        with col:
            st.markdown(f"**{label}**")
            phase = g(roadmap, key, {})
            st.caption("Technologies")
            bullet_list(g(phase, "technologies", []))
            st.caption("Certifications")
            bullet_list(g(phase, "certifications", []))
            st.caption("Projects to Build")
            bullet_list(g(phase, "projects_to_build", []))


def render_career(result: dict):
    career = g(result, "career_recommendations", {})
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Suitable Roles**")
        bullet_list(g(career, "suitable_roles", []))
        st.markdown("**Next Career Steps**")
        bullet_list(g(career, "next_career_steps", []))
    with c2:
        st.metric("Estimated Salary Range", g(career, "salary_range", "Not specified"))
        st.metric("Market Readiness", g(career, "market_readiness", "Not specified"))


def render_verdict(result: dict):
    verdict = g(result, "final_hiring_recommendation", {})
    decision = str(g(verdict, "decision", "Consider")).strip().lower()
    color, label = DECISION_STYLE.get(decision, DECISION_STYLE["consider"])

    st.markdown(
        f"""
        <div style="background:{color}22;border:1px solid {color};border-radius:14px;
                    padding:18px 24px;margin-bottom:16px;">
            <span style="font-size:1.4rem;font-weight:700;color:{color};">{label}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("**Justification**")
    st.write(g(verdict, "justification", "Not provided."))
