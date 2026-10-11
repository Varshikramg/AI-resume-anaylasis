"""
Prompt construction for the AI Talent Intelligence & Recruitment Assistant.

This module builds the single large prompt sent to Claude. It embeds:
  - The persona / role instructions
  - The job description and resume context (from the RAG retrieval step)
  - A strict output JSON schema
  - Formatting rules to keep the response machine-parseable
"""

# The JSON schema the model must return. Kept as a raw string so it can be
# dropped directly into the prompt and shown to the model verbatim.
OUTPUT_SCHEMA = """
{
  "ats_score": {
    "score": 0,
    "explanation": "string - how the score was calculated",
    "optimization_issues": ["string", "..."],
    "missing_keywords": ["string", "..."]
  },
  "job_fit_percentage": {
    "score": 0,
    "explanation": "string - why this percentage was assigned",
    "strengths": ["string", "..."],
    "weaknesses": ["string", "..."]
  },
  "matching_skills": ["string", "..."],
  "partially_matching_skills": ["string", "..."],
  "missing_skills": ["string", "..."],
  "skill_gap_analysis": {
    "emerging_skills_to_learn": ["string", "..."],
    "summary": "string - short narrative on the overall skill gap"
  },
  "project_analysis": [
    {
      "project_name": "string",
      "relevance_score": 0,
      "technologies_used": ["string", "..."],
      "business_impact": "string",
      "recruiter_impression": "string",
      "improvement_suggestions": ["string", "..."]
    }
  ],
  "resume_quality_scores": {
    "structure": 0,
    "readability": 0,
    "keyword_optimization": 0,
    "technical_depth": 0,
    "quantified_achievements": 0,
    "industry_alignment": 0,
    "overall_comment": "string"
  },
  "strengths": ["string", "string", "string", "string", "string"],
  "weaknesses": ["string", "string", "string", "string", "string"],
  "immediate_improvements": ["string", "..."],
  "resume_rewrite_suggestions": [
    {
      "original_bullet": "string - the weak bullet as found in the resume",
      "improved_bullet": "string - rewritten with action verbs and measurable impact",
      "why_improved": "string - short note on what changed and why"
    }
  ],
  "interview_questions": {
    "technical_questions": ["string", "... (10 total)"],
    "project_based_questions": ["string", "... (5 total)"],
    "hr_questions": ["string", "... (5 total)"],
    "scenario_based_questions": ["string", "... (5 total)"]
  },
  "learning_roadmap": {
    "immediate_1_month": {
      "technologies": ["string", "..."],
      "certifications": ["string", "..."],
      "projects_to_build": ["string", "..."]
    },
    "intermediate_3_months": {
      "technologies": ["string", "..."],
      "certifications": ["string", "..."],
      "projects_to_build": ["string", "..."]
    },
    "advanced_6_months": {
      "technologies": ["string", "..."],
      "certifications": ["string", "..."],
      "projects_to_build": ["string", "..."]
    }
  },
  "career_recommendations": {
    "suitable_roles": ["string", "..."],
    "salary_range": "string - realistic range with currency and context (e.g. region/seniority)",
    "market_readiness": "string - e.g. Entry-ready / Needs upskilling / Highly competitive",
    "next_career_steps": ["string", "..."]
  },
  "final_hiring_recommendation": {
    "decision": "Hire | Consider | Reject",
    "justification": "string - detailed, evidence-based reasoning for the decision"
  }
}
""".strip()


SYSTEM_PROMPT = """You are an expert AI Talent Intelligence and Recruitment Assistant.
You analyze a candidate's resume against a target job description using retrieved
resume context supplied by a RAG (Retrieval-Augmented Generation) pipeline.

Operating rules:
- Use ONLY the information present in the provided resume context and job description.
- Do NOT hallucinate skills, projects, certifications, employers, dates, or achievements
  that are not present or clearly implied in the resume context.
- If information needed for a field is not present in the resume, say so explicitly
  (e.g. "Not specified in resume") rather than inventing it.
- Be objective, evidence-based, and data-driven. Justify every score.
- Consider semantic similarity, not just exact keyword overlap, when matching skills.
- Evaluate the candidate from four lenses simultaneously: recruiter, ATS system,
  hiring manager, and technical interviewer.
- Output MUST be a single valid JSON object and NOTHING else - no markdown fences,
  no commentary, no preamble, no trailing text.
"""


def build_prompt(job_description: str, resume_context: str) -> str:
    """
    Build the full user-turn prompt sent to Claude.

    Args:
        job_description: Raw text of the target job description.
        resume_context: Retrieved resume text/context from the RAG pipeline
                         (or raw extracted resume text).

    Returns:
        A formatted prompt string ready to send as the `user` message content.
    """
    job_description = (job_description or "").strip()
    resume_context = (resume_context or "").strip()

    prompt = f"""{SYSTEM_PROMPT}

==================== JOB DESCRIPTION ====================
{job_description}

==================== RETRIEVED RESUME CONTEXT ====================
{resume_context}

==================== TASK ====================
Perform the following analyses using ONLY the inputs above:

1. ATS COMPATIBILITY SCORE
   - Provide an ATS score (0-100).
   - Explain exactly how the score was calculated (formatting, section headers,
     keyword density, parsability, file structure clues if mentioned, etc.).
   - Identify concrete ATS optimization issues.
   - Identify missing keywords the resume should include for this job.

2. JOB FIT ANALYSIS
   - Provide a Job Fit Percentage (0-100).
   - Explain the reasoning (alignment between responsibilities/requirements and
     candidate's experience).
   - List strengths and weaknesses relative to this specific job.

3. SKILL MATCH ANALYSIS
   - Matching Skills (clearly present in both resume and JD).
   - Partially Matching Skills (related/adjacent/semantically similar skills).
   - Missing Skills (required by JD, not evidenced in resume).
   - Emerging Skills Candidate Should Learn (forward-looking, relevant to the role
     and current industry trends).

4. PROJECT RELEVANCE ANALYSIS
   For EACH project found in the resume context, provide:
   - Relevance Score (0-100) against the job description.
   - Technologies Used (as stated in the resume).
   - Business Impact (as stated or reasonably inferable from the resume - do not invent numbers).
   - Recruiter Impression (how a recruiter would perceive this project for this role).
   - Suggestions for Improvement (how to better present this project).

5. RESUME QUALITY REVIEW
   Score each (0-10) and give an overall comment:
   - Resume Structure
   - Readability
   - Keyword Optimization
   - Technical Depth
   - Quantified Achievements
   - Industry Alignment

6. RECRUITER FEEDBACK
   - Top 5 Strengths
   - Top 5 Weaknesses
   - Immediate Improvements (actionable, prioritized list)

7. RESUME REWRITE SUGGESTIONS
   - Identify weak bullet points from the resume context and rewrite them into
     strong, industry-standard bullet points using measurable impact and strong
     action verbs. For each, include the original bullet, the improved bullet,
     and a short note on what changed.
   - If a bullet has no quantifiable detail in the resume, propose a realistic
     placeholder metric format (e.g. "[X]%", "[Y] users") rather than inventing
     a specific fabricated number, and make this clear in "why_improved".

8. INTERVIEW PREPARATION
   - 10 Technical Questions (tailored to the candidate's stated skills/tech stack
     AND the job's requirements).
   - 5 Project-Based Questions (specific to the projects found in the resume context).
   - 5 HR Questions.
   - 5 Scenario-Based Questions (situational/behavioral, relevant to the target role).

9. LEARNING ROADMAP
   A personalized roadmap with three horizons (Immediate - 1 Month,
   Intermediate - 3 Months, Advanced - 6 Months). For each horizon, list:
   - Technologies to learn
   - Relevant certifications
   - Projects to build to demonstrate the new skills

10. CAREER RECOMMENDATIONS
    - Suitable Roles (based on current skill set + trajectory)
    - Salary Range (realistic, with currency and context such as region/level -
      clearly state these are estimates)
    - Market Readiness (e.g. Entry-ready / Needs upskilling / Highly competitive)
    - Next Career Steps

11. FINAL HIRING RECOMMENDATION
    - Decision: one of "Hire", "Consider", or "Reject"
    - Detailed, evidence-based justification referencing the analyses above.

==================== OUTPUT FORMAT ====================
Return ONLY a single valid JSON object matching EXACTLY this schema (same keys,
same nesting, same types). Do not add extra top-level keys. Do not wrap the JSON
in markdown code fences. Do not include any text before or after the JSON.

{OUTPUT_SCHEMA}
"""
    return prompt
