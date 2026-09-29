# Secure EHR Insight

Secure EHR Insight provides a guardrail-protected semantic search interface for MIMIC-IV clinical records.

## Configuration

Create a `.env` file in the project root with:

```dotenv
DATABASE_URL=postgresql+psycopg://<user>:<password>@<host>/<database>?sslmode=require
GROQ_API_KEY=<your-groq-api-key>
```

The Neon database must have the `mimic_iv_transcript` table with pgvector enabled and 768-dimensional `clinical_embedding` values.

## Run

Start the API:

```powershell
uv run uvicorn app:app --reload
```

Start the Streamlit UI in a second terminal:

```powershell
uv run streamlit run ui.py
```

The frontend defaults to `http://localhost:8000`. Set `API_BASE_URL` in the environment when the API runs elsewhere.
