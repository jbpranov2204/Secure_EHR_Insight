"""
Secure EHR Insight — Streamlit Frontend

A premium clinical chat interface for querying patient EHR records
with guardrail-protected semantic search.
"""

import streamlit as st
import requests
import os

# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Secure EHR Insight",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# API CONFIGURATION
# ============================================================

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")

# ============================================================
# CUSTOM CSS — Premium Dark Clinical Theme
# ============================================================

st.markdown("""
<style>
/* ── Import Google Font ── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

/* ── Global ── */
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* ── Main background ── */
.stApp {
    background: linear-gradient(135deg, #0f0f1a 0%, #1a1a2e 50%, #16213e 100%);
}

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0d1117 0%, #161b22 100%);
    border-right: 1px solid rgba(48, 54, 61, 0.6);
}

section[data-testid="stSidebar"] .stSelectbox label {
    color: #e6edf3 !important;
    font-weight: 600;
    font-size: 0.9rem;
    letter-spacing: 0.02em;
}

/* ── Chat messages ── */
.stChatMessage {
    background: rgba(22, 27, 34, 0.7) !important;
    border: 1px solid rgba(48, 54, 61, 0.5) !important;
    border-radius: 12px !important;
    backdrop-filter: blur(10px);
    padding: 1rem 1.2rem !important;
    margin-bottom: 0.8rem !important;
}

/* ── Chat input ── */
.stChatInput > div {
    background: rgba(22, 27, 34, 0.8) !important;
    border: 1px solid rgba(56, 139, 253, 0.3) !important;
    border-radius: 12px !important;
    transition: border-color 0.3s ease;
}

.stChatInput > div:focus-within {
    border-color: rgba(56, 139, 253, 0.7) !important;
    box-shadow: 0 0 0 3px rgba(56, 139, 253, 0.1) !important;
}

/* ── Expander ── */
.streamlit-expanderHeader {
    background: rgba(22, 27, 34, 0.6) !important;
    border: 1px solid rgba(48, 54, 61, 0.5) !important;
    border-radius: 8px !important;
    color: #8b949e !important;
    font-weight: 500;
}

/* ── Warning / blocked banner ── */
div[data-testid="stAlert"] {
    border-radius: 10px !important;
    border-left: 4px solid #f85149 !important;
    background: rgba(248, 81, 73, 0.08) !important;
}

/* ── Header banner ── */
.ehr-header {
    background: linear-gradient(135deg, rgba(56,139,253,0.12) 0%, rgba(139,92,246,0.12) 100%);
    border: 1px solid rgba(56, 139, 253, 0.2);
    border-radius: 16px;
    padding: 1.5rem 2rem;
    margin-bottom: 1.5rem;
    text-align: center;
}
.ehr-header h1 {
    background: linear-gradient(135deg, #58a6ff, #bc8cff);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-size: 2rem;
    font-weight: 700;
    margin: 0 0 0.3rem 0;
}
.ehr-header p {
    color: #8b949e;
    font-size: 0.95rem;
    margin: 0;
}

/* ── Source card ── */
.source-card {
    background: rgba(22, 27, 34, 0.6);
    border: 1px solid rgba(48, 54, 61, 0.6);
    border-radius: 10px;
    padding: 1rem 1.2rem;
    margin-bottom: 0.6rem;
    transition: border-color 0.2s ease;
}
.source-card:hover {
    border-color: rgba(56, 139, 253, 0.4);
}
.source-card .rank-badge {
    display: inline-block;
    background: linear-gradient(135deg, #388bfd, #8b5cf6);
    color: #fff;
    font-size: 0.75rem;
    font-weight: 600;
    padding: 2px 10px;
    border-radius: 20px;
    margin-bottom: 0.5rem;
}
.source-card .distance {
    color: #7ee787;
    font-size: 0.8rem;
    font-weight: 500;
    float: right;
}
.source-card .field-label {
    color: #8b949e;
    font-size: 0.78rem;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
.source-card .field-value {
    color: #e6edf3;
    font-size: 0.88rem;
    margin-bottom: 0.3rem;
}

/* ── Sidebar status pill ── */
.status-pill {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: rgba(46, 160, 67, 0.15);
    border: 1px solid rgba(46, 160, 67, 0.3);
    color: #7ee787;
    font-size: 0.78rem;
    font-weight: 500;
    padding: 4px 12px;
    border-radius: 20px;
}
.status-pill.error {
    background: rgba(248, 81, 73, 0.15);
    border-color: rgba(248, 81, 73, 0.3);
    color: #f85149;
}

/* ── Guardrail blocked banner ── */
.guardrail-block {
    background: linear-gradient(135deg, rgba(248,81,73,0.08) 0%, rgba(219,55,55,0.08) 100%);
    border: 1px solid rgba(248, 81, 73, 0.3);
    border-left: 4px solid #f85149;
    border-radius: 10px;
    padding: 1rem 1.2rem;
    margin: 0.5rem 0;
}
.guardrail-block .block-title {
    color: #f85149;
    font-weight: 600;
    font-size: 0.95rem;
    margin-bottom: 0.4rem;
}
.guardrail-block .block-reason {
    color: #f0883e;
    font-size: 0.88rem;
    line-height: 1.5;
}
</style>
""", unsafe_allow_html=True)


# ============================================================
# SESSION STATE
# ============================================================

if "messages" not in st.session_state:
    st.session_state.messages = []

if "patients" not in st.session_state:
    st.session_state.patients = []

if "api_status" not in st.session_state:
    st.session_state.api_status = "checking"


# ============================================================
# LOAD PATIENTS
# ============================================================

@st.cache_data(ttl=300)
def fetch_patients():
    """Fetch patient IDs from the API."""
    resp = requests.get(f"{API_BASE}/api/patients", timeout=10)
    resp.raise_for_status()
    return resp.json().get("patients", [])


def check_api_health():
    """Check if backend is reachable."""
    try:
        resp = requests.get(f"{API_BASE}/health", timeout=5)
        return resp.status_code == 200
    except Exception:
        return False


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:
    st.markdown("""
    <div style="text-align:center; padding: 1rem 0 0.5rem 0;">
        <span style="font-size: 2.5rem;">🏥</span>
        <h2 style="
            background: linear-gradient(135deg, #58a6ff, #bc8cff);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-size: 1.3rem;
            font-weight: 700;
            margin: 0.5rem 0 0.2rem 0;
        ">Secure EHR Insight</h2>
        <p style="color: #8b949e; font-size: 0.8rem; margin:0;">
            Clinical Intelligence Platform
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # API health
    api_ok = check_api_health()
    if api_ok:
        st.markdown(
            '<div class="status-pill">● API Connected</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="status-pill error">● API Offline</div>',
            unsafe_allow_html=True,
        )
        st.warning(
            "Backend is not running. Start it with:\n"
            "```\nuvicorn app:app --reload\n```"
        )

    st.markdown("")

    # Patient selector
    try:
        patients = fetch_patients()
    except requests.RequestException as e:
        st.error(f"Failed to connect to API: {e}")
        patients = []

    if patients:
        selected_patient = st.selectbox(
            "🔍 Select Patient ID",
            options=patients,
            index=0,
            help="Choose a patient to query their clinical records",
        )
    else:
        selected_patient = None
        st.info("No patients loaded. Ensure the API is running.")

    st.markdown("---")

    # Info section
    st.markdown("""
    <div style="padding: 0.5rem 0;">
        <p style="color: #8b949e; font-size: 0.78rem; font-weight: 500; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.5rem;">
            🛡️ Guardrails Active
        </p>
        <p style="color: #7ee787; font-size: 0.82rem; margin-bottom: 0.3rem;">
            ✓ Medical advice blocked
        </p>
        <p style="color: #7ee787; font-size: 0.82rem; margin-bottom: 0.3rem;">
            ✓ Prescription requests blocked
        </p>
        <p style="color: #7ee787; font-size: 0.82rem; margin-bottom: 0.3rem;">
            ✓ Diagnosis requests blocked
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    st.markdown("""
    <div style="padding: 0.5rem 0;">
        <p style="color: #8b949e; font-size: 0.78rem; font-weight: 500; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.5rem;">
            🧠 Model Stack
        </p>
        <p style="color: #e6edf3; font-size: 0.82rem; margin-bottom: 0.3rem;">
            Embeddings: BioClinical ModernBERT
        </p>
        <p style="color: #e6edf3; font-size: 0.82rem; margin-bottom: 0.3rem;">
            LLM: Qwen 3 32B (Groq)
        </p>
        <p style="color: #e6edf3; font-size: 0.82rem; margin-bottom: 0.3rem;">
            Vector DB: Neon PostgreSQL
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()


# ============================================================
# MAIN AREA — HEADER
# ============================================================

st.markdown("""
<div class="ehr-header">
    <h1>🏥 Secure EHR Insight</h1>
    <p>AI-powered clinical record retrieval with enterprise guardrails</p>
</div>
""", unsafe_allow_html=True)

if selected_patient:
    st.markdown(
        f"<p style='color: #8b949e; font-size: 0.85rem; margin-bottom: 1rem;'>"
        f"Querying records for <strong style='color: #58a6ff;'>Patient {selected_patient}</strong>"
        f"</p>",
        unsafe_allow_html=True,
    )


# ============================================================
# RENDER CHAT HISTORY
# ============================================================

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg["role"] == "assistant" and msg.get("blocked"):
            st.warning(
                "🚫 Query Blocked by Guardrail: "
                "This query is not allowed under clinical policy."
            )
            st.caption(msg["content"])
        else:
            st.markdown(msg["content"])

        # Show source records if present
        if msg.get("sources"):
            with st.expander("📋 View Retrieved Records", expanded=False):
                for i, src in enumerate(msg["sources"], 1):
                    distance_display = (
                        f"{src.get('cosine_distance', 0):.6f}"
                        if src.get("cosine_distance") is not None
                        else "N/A"
                    )
                    card_html = f"""
                    <div class="source-card">
                        <span class="rank-badge">Rank {i}</span>
                        <span class="distance">⚡ Distance: {distance_display}</span>
                        <div style="clear:both; margin-top: 0.5rem;"></div>
                    """
                    fields = [
                        ("Record ID", src.get("id")),
                        ("Patient ID", src.get("subject_id")),
                        ("Admission ID", src.get("hadm_id")),
                        ("Admission Type", src.get("admission_type")),
                        ("Diagnosis", src.get("description")),
                        ("Drug", src.get("drug")),
                        ("Lab Test", src.get("test_name")),
                        ("Severity", src.get("drg_severity")),
                    ]
                    for label, value in fields:
                        if value is not None:
                            card_html += f"""
                            <div>
                                <span class="field-label">{label}</span><br>
                                <span class="field-value">{value}</span>
                            </div>
                            """
                    if src.get("comments"):
                        card_html += f"""
                        <div>
                            <span class="field-label">Notes</span><br>
                            <span class="field-value">{src['comments'][:300]}</span>
                        </div>
                        """
                    card_html += "</div>"
                    st.markdown(card_html, unsafe_allow_html=True)


# ============================================================
# CHAT INPUT
# ============================================================

if prompt := st.chat_input("Ask a clinical query regarding this patient..."):

    if not selected_patient:
        st.warning("Please select a patient ID first.")
        st.stop()

    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Send to API
    with st.chat_message("assistant"):
        with st.spinner("🔍 Processing query..."):
            try:
                resp = requests.post(
                    f"{API_BASE}/api/query",
                    json={
                        "subject_id": selected_patient,
                        "query": prompt,
                    },
                    timeout=60,
                )
                resp.raise_for_status()
                data = resp.json()

                if not data.get("allowed", True):
                    # Guardrail blocked
                    block_msg = data.get("message", "Query was blocked by clinical policy guardrails.")
                    st.warning(
                        "🚫 Query Blocked by Guardrail: "
                        "This query is not allowed under clinical policy."
                    )
                    st.caption(block_msg)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": block_msg,
                        "blocked": True,
                        "sources": [],
                    })
                else:
                    # Allowed — show answer
                    answer = data.get("answer", "No answer generated.")
                    sources = data.get("sources", [])

                    st.markdown(answer)

                    if sources:
                        with st.expander("📋 View Retrieved Records", expanded=False):
                            for i, src in enumerate(sources, 1):
                                distance_display = (
                                    f"{src.get('cosine_distance', 0):.6f}"
                                    if src.get("cosine_distance") is not None
                                    else "N/A"
                                )
                                card_html = f"""
                                <div class="source-card">
                                    <span class="rank-badge">Rank {i}</span>
                                    <span class="distance">⚡ Distance: {distance_display}</span>
                                    <div style="clear:both; margin-top: 0.5rem;"></div>
                                """
                                fields = [
                                    ("Record ID", src.get("id")),
                                    ("Patient ID", src.get("subject_id")),
                                    ("Admission ID", src.get("hadm_id")),
                                    ("Admission Type", src.get("admission_type")),
                                    ("Diagnosis", src.get("description")),
                                    ("Drug", src.get("drug")),
                                    ("Lab Test", src.get("test_name")),
                                    ("Severity", src.get("drg_severity")),
                                ]
                                for label, value in fields:
                                    if value is not None:
                                        card_html += f"""
                                        <div>
                                            <span class="field-label">{label}</span><br>
                                            <span class="field-value">{value}</span>
                                        </div>
                                        """
                                if src.get("comments"):
                                    card_html += f"""
                                    <div>
                                        <span class="field-label">Notes</span><br>
                                        <span class="field-value">{src['comments'][:300]}</span>
                                    </div>
                                    """
                                card_html += "</div>"
                                st.markdown(card_html, unsafe_allow_html=True)

                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": answer,
                        "blocked": False,
                        "sources": sources,
                    })

            except requests.exceptions.ConnectionError:
                st.error(
                    "🔌 Cannot connect to the backend API. "
                    "Please start the server with: `uvicorn app:app --reload`"
                )
            except Exception as e:
                st.error(f"❌ Error: {e}")
