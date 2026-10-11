"""
Builds a human-readable Markdown version of the analysis JSON, so users can
download a portable report instead of (or alongside) the raw JSON.
"""

from datetime import datetime


def _get(d, key, default=""):
    if not isinstance(d, dict):
        return default
    val = d.get(key, default)
    return default if val is None else val


def _bullets(items):
    items = [str(i).strip() for i in (items or []) if str(i).strip()]
    if not items:
        return "_Not specified._\n"
    return "\n".join(f"- {i}" for i in items) + "\n"


def build_markdown_report(result: dict, candidate_label: str = "Candidate") -> str:
    ats = _get(result, "ats_score", {})
    fit = _get(result, "job_fit_percentage", {})
    gap = _get(result, "skill_gap_analysis", {})
    quality = _get(result, "resume_quality_scores", {})
    interview = _get(result, "interview_questions", {})
    roadmap = _get(result, "learning_roadmap", {})
    career = _get(result, "career_recommendations", {})
    verdict = _get(result, "final_hiring_recommendation", {})

    lines = []
    lines.append(f"# Candidate Intelligence Brief — {candidate_label}")
    lines.append(f"_Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}_\n")

    lines.append("## 1. ATS Compatibility Score")
    lines.append(f"**Score: {_get(ats, 'score', 'N/A')}/100**\n")
    lines.append(_get(ats, "explanation", "") + "\n")
    lines.append("**Optimization issues:**")
    lines.append(_bullets(_get(ats, "optimization_issues", [])))
    lines.append("**Missing keywords:**")
    lines.append(_bullets(_get(ats, "missing_keywords", [])))

    lines.append("## 2. Job Fit Analysis")
    lines.append(f"**Fit: {_get(fit, 'score', 'N/A')}%**\n")
    lines.append(_get(fit, "explanation", "") + "\n")
    lines.append("**Strengths:**")
    lines.append(_bullets(_get(fit, "strengths", [])))
    lines.append("**Weaknesses:**")
    lines.append(_bullets(_get(fit, "weaknesses", [])))

    lines.append("## 3. Skill Match Analysis")
    lines.append("**Matching Skills:**")
    lines.append(_bullets(_get(result, "matching_skills", [])))
    lines.append("**Partially Matching Skills:**")
    lines.append(_bullets(_get(result, "partially_matching_skills", [])))
    lines.append("**Missing Skills:**")
    lines.append(_bullets(_get(result, "missing_skills", [])))
    lines.append("**Emerging Skills to Learn:**")
    lines.append(_bullets(_get(gap, "emerging_skills_to_learn", [])))
    if _get(gap, "summary"):
        lines.append(f"_{_get(gap, 'summary')}_\n")

    lines.append("## 4. Project Relevance Analysis")
    for proj in _get(result, "project_analysis", []):
        lines.append(f"### {_get(proj, 'project_name', 'Project')}")
        lines.append(f"Relevance: **{_get(proj, 'relevance_score', 'N/A')}/100**\n")
        lines.append("Technologies: " + ", ".join(_get(proj, "technologies_used", []) or ["Not specified"]))
        lines.append(f"\nBusiness impact: {_get(proj, 'business_impact', 'Not specified')}\n")
        lines.append(f"Recruiter impression: {_get(proj, 'recruiter_impression', 'Not specified')}\n")
        lines.append("Suggestions:")
        lines.append(_bullets(_get(proj, "improvement_suggestions", [])))

    lines.append("## 5. Resume Quality Review")
    for label, key in [
        ("Structure", "structure"), ("Readability", "readability"),
        ("Keyword Optimization", "keyword_optimization"), ("Technical Depth", "technical_depth"),
        ("Quantified Achievements", "quantified_achievements"), ("Industry Alignment", "industry_alignment"),
    ]:
        lines.append(f"- **{label}:** {_get(quality, key, 'N/A')}/10")
    if _get(quality, "overall_comment"):
        lines.append(f"\n_{_get(quality, 'overall_comment')}_\n")

    lines.append("## 6. Recruiter Feedback")
    lines.append("**Top Strengths:**")
    lines.append(_bullets(_get(result, "strengths", [])))
    lines.append("**Top Weaknesses:**")
    lines.append(_bullets(_get(result, "weaknesses", [])))
    lines.append("**Immediate Improvements:**")
    lines.append(_bullets(_get(result, "immediate_improvements", [])))

    lines.append("## 7. Resume Rewrite Suggestions")
    for item in _get(result, "resume_rewrite_suggestions", []):
        lines.append(f"- **Original:** {_get(item, 'original_bullet', '')}")
        lines.append(f"  **Improved:** {_get(item, 'improved_bullet', '')}")
        if _get(item, "why_improved"):
            lines.append(f"  _Why: {_get(item, 'why_improved')}_")

    lines.append("\n## 8. Interview Preparation")
    for label, key in [
        ("Technical Questions", "technical_questions"),
        ("Project-Based Questions", "project_based_questions"),
        ("HR Questions", "hr_questions"),
        ("Scenario-Based Questions", "scenario_based_questions"),
    ]:
        lines.append(f"**{label}:**")
        lines.append(_bullets(_get(interview, key, [])))

    lines.append("## 9. Learning Roadmap")
    for label, key in [
        ("Immediate (1 Month)", "immediate_1_month"),
        ("Intermediate (3 Months)", "intermediate_3_months"),
        ("Advanced (6 Months)", "advanced_6_months"),
    ]:
        phase = _get(roadmap, key, {})
        lines.append(f"### {label}")
        lines.append("Technologies: " + ", ".join(_get(phase, "technologies", []) or ["—"]))
        lines.append("\nCertifications: " + ", ".join(_get(phase, "certifications", []) or ["—"]))
        lines.append("\nProjects to build: " + ", ".join(_get(phase, "projects_to_build", []) or ["—"]) + "\n")

    lines.append("## 10. Career Recommendations")
    lines.append("**Suitable Roles:**")
    lines.append(_bullets(_get(career, "suitable_roles", [])))
    lines.append(f"**Salary Range:** {_get(career, 'salary_range', 'N/A')}\n")
    lines.append(f"**Market Readiness:** {_get(career, 'market_readiness', 'N/A')}\n")
    lines.append("**Next Career Steps:**")
    lines.append(_bullets(_get(career, "next_career_steps", [])))

    lines.append("## 11. Final Hiring Recommendation")
    lines.append(f"**Decision: {_get(verdict, 'decision', 'N/A')}**\n")
    lines.append(_get(verdict, "justification", ""))

    return "\n".join(lines)
