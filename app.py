import streamlit as st
import json
from openai import OpenAI

# ---------- OpenAI client ----------
def get_openai_client(api_key: str | None):
    if api_key:
        return OpenAI(api_key=api_key)
    return OpenAI()  # uses environment variable if available


# ---------- Extract text from file ----------
def extract_text_from_file(uploaded_file) -> str:
    if uploaded_file is None:
        return ""

    file_type = uploaded_file.type

    # TXT
    if file_type == "text/plain":
        return uploaded_file.read().decode("utf-8", errors="ignore")

    # PDF
    if file_type == "application/pdf":
        try:
            from PyPDF2 import PdfReader
        except ImportError:
            st.error("PyPDF2 missing. Add to requirements.txt")
            return ""
        reader = PdfReader(uploaded_file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text

    # DOCX
    if file_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        try:
            import docx
        except ImportError:
            st.error("python-docx missing. Add to requirements.txt")
            return ""
        doc = docx.Document(uploaded_file)
        return "\n".join(p.text for p in doc.paragraphs)

    st.warning("Unsupported file type")
    return ""


# ---------- AI analysis ----------
def analyze_resume(client: OpenAI, resume_text: str, jd_text: str) -> dict:
    system_prompt = """
You are an expert HR recruiter and ATS system.
Compare a candidate's resume with a job description.

Return ONLY valid JSON with structure:
{
  "match_score": int,
  "verdict": "Strong match" | "Moderate match" | "Weak match",
  "summary": "overall summary",
  "strengths": ["point1", "point2"],
  "gaps": ["gap1", "gap2"],
  "improvement_suggestions": ["suggestion1", "suggestion2"],
  "recommended_role_level": "Junior / Mid-level / Senior"
}
"""

    user_content = f"""
JOB DESCRIPTION:
{jd_text}

RESUME:
{resume_text}
"""

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        temperature=0.2,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
    )

    content = response.choices[0].message.content
    try:
        return json.loads(content)
    except:
        return {"error": "Invalid JSON from model", "raw": content}


# ---------- Streamlit UI ----------
def main():
    st.set_page_config(page_title="ResumeMatch AI", page_icon="📄", layout="wide")

    st.title("📄 ResumeMatch AI – Resume Screening Agent")
    st.write("Upload resume + paste job description → get match score, strengths, gaps & suggestions.")

    st.sidebar.header("⚙️ Configuration")
    api_key = st.sidebar.text_input("OpenAI API Key (optional)", type="password")

    col1, col2 = st.columns(2)

    # Resume upload
    with col1:
        st.subheader("1️⃣ Upload Resume")
        uploaded_file = st.file_uploader("Upload PDF, DOCX, or TXT", type=["pdf", "docx", "txt"])

        resume_text = ""
        if uploaded_file:
            with st.spinner("Extracting text..."):
                resume_text = extract_text_from_file(uploaded_file)
            if resume_text:
                st.success("Resume extracted.")
                with st.expander("View Extracted Resume Text"):
                    st.text_area("Resume Text", resume_text, height=250)

    # Job description
    with col2:
        st.subheader("2️⃣ Paste Job Description")
        jd_text = st.text_area("Job Description", height=300)

    st.markdown("---")

    # Analyze button
    if st.button("🚀 Analyze Match"):
        if not resume_text:
            st.error("Upload resume first.")
            return
        if not jd_text.strip():
            st.error("Paste job description.")
            return

        client = get_openai_client(api_key)

        with st.spinner("Analyzing..."):
            result = analyze_resume(client, resume_text, jd_text)

        if "error" in result:
            st.error("Model error: Could not parse response")
            st.text(result["raw"])
            return

        # Results
        st.subheader("📊 Match Summary")
        st.metric("Match Score", f"{result['match_score']}/100")
        st.write(f"**Verdict:** {result['verdict']}")
        st.write(f"**Summary:** {result['summary']}")

        colA, colB = st.columns(2)

        with colA:
            st.markdown("### ✅ Strengths")
            for s in result["strengths"]:
                st.markdown(f"- {s}")

        with colB:
            st.markdown("### ⚠️ Gaps")
            for g in result["gaps"]:
                st.markdown(f"- {g}")

        st.markdown("### 🛠 Suggestions to Improve Resume")
        for sug in result["improvement_suggestions"]:
            st.markdown(f"- {sug}")

        st.write(f"**Recommended Role Level:** {result['recommended_role_level']}")


if __name__ == "__main__":
    main()
