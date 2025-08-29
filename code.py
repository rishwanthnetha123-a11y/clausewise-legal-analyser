import streamlit as st
import os
import re
import json
import tempfile
import requests
import docx
import PyPDF2
from dotenv import load_dotenv

# ---------------- Load API ----------------
load_dotenv()
HF_API_TOKEN = os.getenv("HF_API_TOKEN")
if not HF_API_TOKEN:
    st.error("⚠️ Please set the HF_API_TOKEN environment variable with your Hugging Face token.")
    st.stop()

MODEL_ID = "ibm-granite/granite-3.3-2b-base"
HF_API_URL = f"https://ibm-granite/granite-3.3-2b-base/{MODEL_ID}"
HEADERS = {"Authorization": f"Bearer {HF_API_TOKEN}"}

ALLOWED_EXTENSIONS = {"pdf", "docx", "txt"}

# ---------------- Prompt ----------------
PROMPT_TEMPLATE = """
You are an expert legal analyst (India context unless otherwise specified). 
Given the following clause from a contract, produce a JSON object with these fields:
- clause_text
- issues (list)
- risk_level (low/medium/high with justification)
- recommended_action
- tags (list)

Return only valid JSON.

Clause:
\"\"\"{clause}\"\"\"
"""

# ---------------- Utilities ----------------
def extract_text_from_docx(path):
    doc = docx.Document(path)
    return "\n".join([p.text for p in doc.paragraphs if p.text.strip()])

def extract_text_from_pdf(path):
    text = []
    reader = PyPDF2.PdfReader(path)
    for page in reader.pages:
        txt = page.extract_text()
        if txt:
            text.append(txt)
    return "\n".join(text)

def extract_text(file_path, ext):
    if ext == "docx":
        return extract_text_from_docx(file_path)
    elif ext == "pdf":
        return extract_text_from_pdf(file_path)
    elif ext == "txt":
        return open(file_path, encoding="utf-8", errors="ignore").read()
    return ""

def split_into_clauses(text, max_clause_chars=1500):
    text = re.sub(r"\r\n|\r", "\n", text)
    candidates = re.split(r"(?m)(?:\n\s*\d+\.\s+|\n\s*[A-Z]\)\s+|\n\s*\d+\)\s+)", text)
    if len(candidates) < 2:
        candidates = [p.strip() for p in text.split("\n\n") if p.strip()]
    clauses = []
    for c in candidates:
        if len(c) > max_clause_chars:
            parts = re.split(r"(?<=[\.\?\!])\s+", c)
            cur = ""
            for p in parts:
                if len(cur) + len(p) < max_clause_chars:
                    cur += " " + p
                else:
                    clauses.append(cur.strip())
                    cur = p
            if cur:
                clauses.append(cur.strip())
        else:
            if c.strip():
                clauses.append(c.strip())
    return [c for c in clauses if len(c) > 20]

def call_granite(clause):
    payload = {
        "inputs": PROMPT_TEMPLATE.format(clause=clause),
        "parameters": {"max_new_tokens": 400, "temperature": 0.0, "return_full_text": False}
    }
    try:
        resp = requests.post(HF_API_URL, headers=HEADERS, json=payload, timeout=120)
        if resp.status_code != 200:
            return {"error": f"HTTP {resp.status_code}", "raw": resp.text}
        data = resp.json()
        if isinstance(data, list) and "generated_text" in data[0]:
            text_out = data[0]["generated_text"]
        elif isinstance(data, dict) and "generated_text" in data:
            text_out = data["generated_text"]
        else:
            text_out = str(data)
        m = re.search(r"\{.*\}", text_out, flags=re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                return {"error": "JSON parse error", "raw": text_out}
        return {"error": "No JSON in output", "raw": text_out}
    except Exception as e:
        return {"error": str(e)}

def summarize_text(text, max_len=400):
    payload = {
        "inputs": (
            "You are a legal assistant. Summarize the following legal contract. "
            "Highlight: (1) Key parties, (2) Obligations, (3) Risks, "
            "(4) Governing law/jurisdiction.\n\n"
            f"{text}"
        ),
        "parameters": {"max_new_tokens": max_len, "temperature": 0.3, "return_full_text": False}
    }
    try:
        resp = requests.post(HF_API_URL, headers=HEADERS, json=payload, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list) and "generated_text" in data[0]:
            return data[0]["generated_text"].strip()
        elif isinstance(data, dict) and "generated_text" in data:
            return data["generated_text"].strip()
        return str(data)
    except Exception as e:
        return f"⚠️ Error during summarization: {e}"

# ---------------- Streamlit UI ----------------
st.set_page_config(page_title="ClauseWise — Legal Analyzer", layout="wide")

# Sidebar
st.sidebar.title("⚖️ ClauseWise")
st.sidebar.info("AI-powered **contract analyzer** for Indian legal professionals.\n\n"
                "- Upload contracts (.pdf, .docx, .txt)\n"
                "- Clause-level risk analysis\n"
                "- Summarized obligations, risks, and parties")

# Main Title
st.title("📜 ClauseWise — Legal Analyzer")
st.caption(f"Using IBM Granite model: `{MODEL_ID}` (Hugging Face Inference API)")

# Upload section
uploaded_file = st.file_uploader("📂 Upload a contract", type=list(ALLOWED_EXTENSIONS))

if uploaded_file is not None:
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(uploaded_file.read())
        tmp_path = tmp.name
    text = extract_text(tmp_path, uploaded_file.name.split(".")[-1].lower())
    if not text.strip():
        st.error("❌ Could not extract text from file")
        st.stop()

    st.success("✅ File uploaded and text extracted")

    with st.expander("📖 Preview Extracted Text (first 2000 chars)"):
        st.text_area("Extracted Text", text[:2000], height=200)

    if st.button("🔍 Analyze Clauses"):
        clauses = split_into_clauses(text)
        st.info(f"Found **{len(clauses)}** clauses (showing first 20)")
        clauses = clauses[:20]

        results = []
        progress = st.progress(0)
        for i, clause in enumerate(clauses):
            res = call_granite(clause)
            res.setdefault("clause_text", clause)
            results.append(res)
            progress.progress((i+1)/len(clauses))

        # Results Layout
        st.header("📑 Analysis Results")

        # Show summary first
        all_text = " ".join([r.get("clause_text", "") for r in results])
        summary = summarize_text(all_text, max_len=400)

        st.subheader("📌 Contract Summary")
        st.write(summary)

        # Show each clause
        st.subheader("📜 Clause-Level Details")
        for i, r in enumerate(results):
            risk = r.get("risk_level","N/A")
            with st.expander(f"Clause {i+1} — Risk: {risk}"):
                col1, col2 = st.columns([2,1])
                with col1:
                    st.markdown("**Clause Text:**")
                    st.write(r.get("clause_text"))
                    st.markdown("**Issues:**")
                    st.write(r.get("issues"))
                    st.markdown("**Recommended Action:**")
                    st.write(r.get("recommended_action"))
                with col2:
                    st.markdown("**Tags:**")
                    st.write(r.get("tags"))
                st.json(r)
