"""
AI Talent Intelligence & Recruitment Assistant — Streamlit front end.

Run with:
    streamlit run streamlit_app.py

What it does:
  1. Accepts a job description (pasted text) and a resume (pasted text or
     uploaded PDF/DOCX/TXT file) — the resume text stands in for the
     retrieved context a RAG pipeline would normally supply.
  2. Builds the structured analysis prompt (prompts/analysis_prompt.py).
  3. Sends it to an LLM — Claude via Anthropic, or any OpenRouter-hosted
     model (e.g. DeepSeek) — depending on LLM_PROVIDER.
  4. Renders the structured JSON analysis as an interactive "candidate
     intelligence brief" with gauges, radar charts, and downloadable reports.
"""

import os
from datetime import datetime

import streamlit as st
from dotenv import load_dotenv

from components import sections
from prompts.analysis_prompt import build_prompt
from utils.file_extractor import extract_text_from_upload
from utils.llm_client import (
    DEFAULT_ANTHROPIC_MODEL,
    DEFAULT_OPENROUTER_MODEL,
    LLMAnalysisError,
    run_resume_analysis,
)
from utils.report_export import build_markdown_report

load_dotenv()

st.set_page_config(
    page_title="AI Resume Intelligence Analyzer",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --------------------------------------------------------------------------
# Styling
# --------------------------------------------------------------------------
st.markdown(
    """
    <style>
    .stApp { background: radial-gradient(circle at top left, #1A1825 0%, #0F0E17 55%); }
    .hero {
        background: linear-gradient(120deg, #6C5CE7 0%, #341F97 100%);
        border-radius: 18px;
        padding: 28px 32px;
        margin-bottom: 22px;
        box-shadow: 0 8px 30px rgba(108, 92, 231, 0.25);
    }
    .hero h1 { margin: 0; font-size: 1.9rem; color: #FFFFFF; }
    .hero p { margin: 6px 0 0 0; color: #E8E5FF; font-size: 0.98rem; }
    div[data-testid="stMetric"] {
        background: #1A1825;
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 12px;
        padding: 10px 14px;
    }
    .stTabs [data-baseweb="tab"] { font-weight: 600; }
    .streamlit-expanderHeader { font-weight: 600; }
    section[data-testid="stSidebar"] { border-right: 1px solid rgba(255,255,255,0.06); }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="hero">
        <h1>🧠 AI Talent Intelligence &amp; Recruitment Assistant</h1>
        <p>Resume vs. job-description analysis evaluated as a recruiter, ATS system,
        hiring manager, and technical interviewer — all in one report.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------
# Sidebar — model / provider configuration
# --------------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ Model Settings")

    env_provider = (os.getenv("LLM_PROVIDER") or "openrouter").strip().lower()
    provider_choice = st.selectbox(
        "LLM Provider",
        options=["openrouter", "anthropic"],
        index=0 if env_provider != "anthropic" else 1,
        help=(
            "OpenRouter gives you access to DeepSeek, Grok, Llama, and dozens "
            "of other models through one API. Anthropic calls Claude directly."
        ),
    )

    if provider_choice == "anthropic":
        model_input = st.text_input(
            "Claude Model", value=os.getenv("CLAUDE_MODEL", DEFAULT_ANTHROPIC_MODEL)
        )
        api_key_input = st.text_input(
            "Anthropic API Key (optional override)",
            type="password",
            help="Leave blank to use ANTHROPIC_API_KEY from your .env file.",
        )
        env_key = os.getenv("ANTHROPIC_API_KEY", "")
    else:
        model_input = st.text_input(
            "OpenRouter Model",
            value=os.getenv("OPENROUTER_MODEL", DEFAULT_OPENROUTER_MODEL),
            help="Any OpenRouter model id, e.g. deepseek/deepseek-chat-v3-0324, "
            "x-ai/grok-2-latest, meta-llama/llama-3.3-70b-instruct.",
        )
        api_key_input = st.text_input(
            "OpenRouter API Key (optional override)",
            type="password",
            help="Leave blank to use OPENROUTER_API_KEY from your .env file.",
        )
        env_key = os.getenv("OPENROUTER_API_KEY", "")

    is_configured = bool(api_key_input) or (bool(env_key) and "REPLACE_WITH_YOUR_KEY" not in env_key)
    if is_configured:
        st.success(f"Ready · {provider_choice} · {model_input}")
    else:
        st.warning("No API key configured yet — add one above or in your .env file.")

    st.divider()
    candidate_label = st.text_input("Candidate label (for the report title)", value="Candidate")

    st.divider()
    if st.button("🗑️ Clear current analysis", use_container_width=True):
        for key in ("result", "generated_at"):
            st.session_state.pop(key, None)
        st.rerun()

    st.caption(
        "Built for a RAG-style workflow: paste in whatever resume context your "
        "retrieval step returns, or upload a resume file directly."
    )

# --------------------------------------------------------------------------
# Input section
# --------------------------------------------------------------------------
col_jd, col_resume = st.columns(2)

with col_jd:
    st.subheader("📋 Job Description")
    job_description = st.text_area(
        "Paste the target job description",
        height=280,
        placeholder="Paste the full job description here…",
        label_visibility="collapsed",
    )

with col_resume:
    st.subheader("🧑‍💼 Resume / Retrieved Context")
    paste_tab, upload_tab = st.tabs(["Paste Text", "Upload File"])

    with paste_tab:
        resume_text_input = st.text_area(
            "Paste resume text or RAG-retrieved context",
            height=235,
            placeholder="Paste resume text, or the context chunks your RAG "
            "pipeline retrieved, here…",
            label_visibility="collapsed",
        )

    with upload_tab:
        uploaded_file = st.file_uploader(
            "Upload a .pdf, .docx, or .txt resume", type=["pdf", "docx", "txt"]
        )

resume_text = ""
upload_error = None
if uploaded_file is not None:
    try:
        resume_text = extract_text_from_upload(uploaded_file)
        st.caption(f"✅ Extracted {len(resume_text):,} characters from **{uploaded_file.name}**")
    except ValueError as exc:
        upload_error = str(exc)
elif resume_text_input.strip():
    resume_text = resume_text_input.strip()

run_clicked = st.button("🔍 Run Full Analysis", type="primary", use_container_width=True)

# --------------------------------------------------------------------------
# Run analysis
# --------------------------------------------------------------------------
if run_clicked:
    if upload_error:
        st.error(upload_error)
    elif not job_description.strip():
        st.error("Please paste a job description.")
    elif not resume_text.strip():
        st.error("Please paste resume text or upload a resume file.")
    elif not is_configured:
        st.error("Please configure an API key for the selected provider in the sidebar.")
    else:
        prompt = build_prompt(job_description, resume_text)
        with st.spinner(f"Analyzing against the job description using {model_input}…"):
            try:
                result = run_resume_analysis(
                    prompt,
                    provider=provider_choice,
                    model=model_input,
                    api_key=api_key_input or None,
                )
                st.session_state["result"] = result
                st.session_state["generated_at"] = datetime.now()
            except LLMAnalysisError as exc:
                st.error(f"Analysis failed: {exc}")
                if getattr(exc, "raw_response", ""):
                    with st.expander("Raw model output (for debugging)"):
                        st.code(exc.raw_response[:4000])

# --------------------------------------------------------------------------
# Report
# --------------------------------------------------------------------------
result = st.session_state.get("result")

if result:
    st.divider()
    generated_at = st.session_state.get("generated_at", datetime.now())
    header_col, dl_col1, dl_col2 = st.columns([3, 1, 1])
    with header_col:
        st.subheader(f"📊 Candidate Intelligence Report — {candidate_label}")
        st.caption(f"Generated {generated_at.strftime('%Y-%m-%d %H:%M')}")
    with dl_col1:
        st.download_button(
            "⬇️ Markdown report",
            data=build_markdown_report(result, candidate_label),
            file_name=f"{candidate_label.replace(' ', '_').lower()}_report.md",
            mime="text/markdown",
            use_container_width=True,
        )
    with dl_col2:
        import json

        st.download_button(
            "⬇️ Raw JSON",
            data=json.dumps(result, indent=2),
            file_name=f"{candidate_label.replace(' ', '_').lower()}_analysis.json",
            mime="application/json",
            use_container_width=True,
        )

    tabs = st.tabs(
        [
            "Overview",
            "Skills",
            "Projects",
            "Resume Quality",
            "Recruiter Feedback",
            "Rewrite Suggestions",
            "Interview Prep",
            "Learning Roadmap",
            "Career",
            "Final Verdict",
        ]
    )
    with tabs[0]:
        sections.render_overview(result)
    with tabs[1]:
        sections.render_skills(result)
    with tabs[2]:
        sections.render_projects(result)
    with tabs[3]:
        sections.render_quality(result)
    with tabs[4]:
        sections.render_recruiter_feedback(result)
    with tabs[5]:
        sections.render_rewrites(result)
    with tabs[6]:
        sections.render_interview_prep(result)
    with tabs[7]:
        sections.render_roadmap(result)
    with tabs[8]:
        sections.render_career(result)
    with tabs[9]:
        sections.render_verdict(result)
else:
    st.info("Fill in the job description and resume above, then click **Run Full Analysis**.")
