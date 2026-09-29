"""
Secure EHR Insight — FastAPI Backend

Endpoints:
  GET  /api/patients  → list of patient IDs with embeddings
  POST /api/query     → guardrail-checked semantic search + LLM answer
"""

import os
import re
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text
from sentence_transformers import SentenceTransformer
from nemoguardrails import RailsConfig, LLMRails
from groq import Groq


# ============================================================
# CONFIGURATION
# ============================================================

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL not found in .env")
if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY not found in .env")

MODEL_NAME = "NeuML/bioclinical-modernbert-base-embeddings"
GROQ_MODEL = "qwen/qwen3.8-27b"
TOP_K = 5

BASE_DIR = Path(__file__).resolve().parent
GUARDRAILS_DIR = BASE_DIR / "Guardrails"

# Known guardrail refusal message (from rails.co)
GUARDRAIL_REFUSAL = (
    "I am an enterprise EHR retrieval system. "
    "For legal and compliance reasons, I cannot provide "
    "new medical diagnoses or recommend medication changes. "
    "Please consult the attending physician."
)

MEDICAL_ADVICE_TERMS = (
    "recommend",
    "suggest",
    "prescribe",
    "increase",
    "decrease",
    "change",
    "adjust",
    "best treatment",
    "should take",
    "should",
)

MEDICATION_TERMS = (
    "medication",
    "medications",
    "medicine",
    "medicines",
    "drug",
    "drugs",
    "dose",
    "dosage",
    "treatment",
    "therapy",
)


# ============================================================
# GLOBALS (populated at startup)
# ============================================================

db_engine = None
embedding_model = None
guardrails = None
groq_client = None


# ============================================================
# LIFESPAN — load heavy resources once
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    global db_engine, embedding_model, guardrails, groq_client

    print("[...] Loading database connection...")
    db_engine = create_engine(DATABASE_URL, pool_pre_ping=True)

    print("[...] Loading BioClinical ModernBERT embedding model...")
    embedding_model = SentenceTransformer(MODEL_NAME)
    dim = embedding_model.get_sentence_embedding_dimension()
    if dim != 768:
        raise RuntimeError(
            f"Expected 768-d embeddings, model produces {dim}-d"
        )
    print(f"[OK] Embedding model loaded ({dim}-d)")

    print("[...] Loading NeMo Guardrails...")
    config = RailsConfig.from_path(str(GUARDRAILS_DIR))
    guardrails = LLMRails(config)
    print("[OK] Guardrails loaded")

    print("[...] Initializing Groq client...")
    groq_client = Groq(api_key=GROQ_API_KEY)
    print("[OK] Groq client ready")

    print("[READY] Secure EHR Insight API is ready")
    yield

    # Shutdown — dispose DB pool
    if db_engine:
        db_engine.dispose()
    print("[STOP] Shutdown complete")


# ============================================================
# FASTAPI APP
# ============================================================

app = FastAPI(
    title="Secure EHR Insight API",
    description="Clinical EHR retrieval with guardrails",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "service": "Secure EHR Insight API",
        "docs": "/docs",
        "patients": "/api/patients",
        "query": "/api/query",
        "frontend": "Run `streamlit run ui.py` to open the Streamlit interface",
    }


# ============================================================
# REQUEST / RESPONSE MODELS
# ============================================================

class QueryRequest(BaseModel):
    subject_id: int
    query: str


class SourceRecord(BaseModel):
    id: int
    subject_id: int
    hadm_id: int | None = None
    admission_type: str | None = None
    drug: str | None = None
    test_name: str | None = None
    description: str | None = None
    drg_severity: int | None = None
    comments: str | None = None
    cosine_distance: float | None = None


class QueryResponse(BaseModel):
    allowed: bool
    message: str | None = None
    answer: str | None = None
    sources: list[SourceRecord] = Field(default_factory=list)


class PatientsResponse(BaseModel):
    patients: list[int]


def _guardrail_content(response) -> str:
    """Extract generated content from NeMo's dict or response object."""

    if isinstance(response, dict):
        return str(response.get("content") or response.get("message") or "")
    return str(getattr(response, "content", "") or "")


def _is_medical_advice_request(query: str) -> bool:
    """Return true for treatment requests while allowing record lookups."""

    normalized_query = re.sub(r"\s+", " ", query.lower()).strip()
    has_advice_term = any(term in normalized_query for term in MEDICAL_ADVICE_TERMS)
    has_medication_term = any(term in normalized_query for term in MEDICATION_TERMS)
    return has_advice_term and has_medication_term


def _is_guardrail_refusal(text: str) -> bool:
    """Recognize configured and equivalent refusal responses."""

    normalized_text = re.sub(r"\s+", " ", text.lower()).strip()
    return (
        GUARDRAIL_REFUSAL.lower() in normalized_text
        or (
            "cannot" in normalized_text
            and any(term in normalized_text for term in ("suggest", "recommend", "prescribe"))
            and any(term in normalized_text for term in MEDICATION_TERMS)
        )
    )


def _structured_answer(sources: list[SourceRecord]) -> str:
    """Provide a useful local answer when remote LLM synthesis is unavailable."""

    lines = ["Retrieved clinical records matching the query:"]
    for index, source in enumerate(sources, 1):
        details = []
        if source.test_name:
            details.append(f"test: {source.test_name}")
        if source.description:
            details.append(f"description: {source.description}")
        if source.drug:
            details.append(f"drug: {source.drug}")
        if source.admission_type:
            details.append(f"admission: {source.admission_type}")
        if source.comments:
            details.append(f"notes: {source.comments}")
        details.append(f"cosine distance: {source.cosine_distance}")
        lines.append(f"{index}. " + "; ".join(details))
    return "\n".join(lines)


# ============================================================
# GET /api/patients
# ============================================================

@app.get("/api/patients", response_model=PatientsResponse)
def get_patients():
    """Return the first 50 unique patient IDs that have embeddings."""

    sql = text("""
        SELECT DISTINCT subject_id
        FROM mimic_iv_transcript
        WHERE clinical_embedding IS NOT NULL
        ORDER BY subject_id
        LIMIT 50;
    """)

    with db_engine.connect() as conn:
        rows = conn.execute(sql).fetchall()

    patient_ids = [row[0] for row in rows]
    return PatientsResponse(patients=patient_ids)


# ============================================================
# POST /api/query
# ============================================================

@app.post("/api/query", response_model=QueryResponse)
async def post_query(payload: QueryRequest):
    """
    1. Check guardrails
    2. Vector search (only if guardrail passes)
    3. Synthesize answer via Groq LLM
    """

    subject_id = payload.subject_id
    user_query = payload.query

    # ----------------------------------------------------------
    # STEP 1 — Input Guardrails Check
    # ----------------------------------------------------------

    try:
        guardrail_response = await guardrails.generate_async(
            messages=[{"role": "user", "content": user_query}]
        )
        guardrail_text = _guardrail_content(guardrail_response)
    except Exception as e:
        print(f"[WARN] Guardrail error (blocking query): {e}")
        return QueryResponse(
            allowed=False,
            message=GUARDRAIL_REFUSAL,
            sources=[],
        )

    # If guardrail returned the refusal message → block immediately
    if _is_guardrail_refusal(guardrail_text) or _is_medical_advice_request(user_query):
        return QueryResponse(
            allowed=False,
            message=GUARDRAIL_REFUSAL,
            sources=[],
        )

    user_query = user_query.strip()
    if not user_query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    # ----------------------------------------------------------
    # STEP 2 — Vector Search & Retrieval
    # ----------------------------------------------------------

    # Encode query using local BioClinical ModernBERT
    query_vector = embedding_model.encode(
        user_query,
        normalize_embeddings=True,
    ).tolist()

    query_vector_string = (
        "[" + ",".join(str(float(v)) for v in query_vector) + "]"
    )

    search_sql = text("""
        SELECT
            id,
            subject_id,
            hadm_id,
            admission_type,
            drug,
            test_name,
            description,
            drg_severity,
            comments,
            clinical_embedding <=> CAST(:query_vector AS vector(768))
                AS cosine_distance
        FROM mimic_iv_transcript
        WHERE clinical_embedding IS NOT NULL
          AND subject_id = :subject_id
        ORDER BY cosine_distance ASC
        LIMIT :top_k;
    """)

    with db_engine.connect() as conn:
        rows = conn.execute(
            search_sql,
            {
                "query_vector": query_vector_string,
                "subject_id": subject_id,
                "top_k": TOP_K,
            },
        ).mappings().fetchall()

    if not rows:
        return QueryResponse(
            allowed=True,
            answer="No clinical records found for this patient with matching embeddings.",
            sources=[],
        )

    # Build source records
    sources = []
    for row in rows:
        sources.append(
            SourceRecord(
                id=row["id"],
                subject_id=row["subject_id"],
                hadm_id=row.get("hadm_id"),
                admission_type=row.get("admission_type"),
                drug=row.get("drug"),
                test_name=row.get("test_name"),
                description=row.get("description"),
                drg_severity=row.get("drg_severity"),
                comments=str(row["comments"])[:500] if row.get("comments") else None,
                cosine_distance=round(float(row["cosine_distance"]), 6),
            )
        )

    # ----------------------------------------------------------
    # STEP 3 — Synthesize Response via Groq LLM
    # ----------------------------------------------------------

    context_lines = []
    for i, src in enumerate(sources, 1):
        parts = [f"Record {i}:"]
        if src.admission_type:
            parts.append(f"  Admission: {src.admission_type}")
        if src.drug:
            parts.append(f"  Drug: {src.drug}")
        if src.test_name:
            parts.append(f"  Lab Test: {src.test_name}")
        if src.description:
            parts.append(f"  Diagnosis: {src.description}")
        if src.drg_severity is not None:
            parts.append(f"  Severity: {src.drg_severity}")
        if src.comments:
            parts.append(f"  Notes: {src.comments}")
        parts.append(f"  Cosine Distance: {src.cosine_distance}")
        context_lines.append("\n".join(parts))

    context_block = "\n\n".join(context_lines)

    system_prompt = (
        "You are a clinical EHR assistant. You ONLY summarize and explain "
        "existing medical records. You NEVER provide new diagnoses, prescribe "
        "medications, or recommend treatment changes. Base your answer strictly "
        "on the retrieved clinical records below.\n\n"
        f"Patient ID: {subject_id}\n\n"
        f"Retrieved Clinical Records:\n{context_block}"
    )

    try:
        llm_response = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_query},
            ],
            temperature=0.3,
            max_tokens=1024,
        )
        answer = llm_response.choices[0].message.content
    except Exception as e:
        print(f"[WARN] LLM synthesis error: {e}")
        answer = _structured_answer(sources)

    return QueryResponse(
        allowed=True,
        answer=answer,
        sources=sources,
    )


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
def health():
    return {"status": "ok"}
