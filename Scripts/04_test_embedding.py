import os

from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer


# ============================================================
# CONFIGURATION
# ============================================================

MODEL_NAME = "NeuML/bioclinical-modernbert-base-embeddings"

TOP_K = 5


# ============================================================
# SEMANTIC VECTOR SEARCH
# ============================================================

def test_vector_search():

    # --------------------------------------------------------
    # 1. Load environment variables
    # --------------------------------------------------------

    load_dotenv()

    db_url = os.getenv("DATABASE_URL")

    if not db_url:
        raise ValueError(
            "DATABASE_URL not found in .env file."
        )

    # --------------------------------------------------------
    # 2. Connect to Neon
    # --------------------------------------------------------

    print("🔌 Connecting to Neon PostgreSQL...")

    engine = create_engine(
        db_url,
        pool_pre_ping=True
    )

    # --------------------------------------------------------
    # 3. Load local embedding model
    # --------------------------------------------------------

    print("\n⏳ Loading local BioClinical ModernBERT model...")

    model = SentenceTransformer(MODEL_NAME)

    # Verify dimension
    dimension = model.get_sentence_embedding_dimension()

    if dimension != 768:
        raise ValueError(
            f"Expected 768 dimensions, "
            f"but model produces {dimension}."
        )

    print("✅ Model loaded.")
    print("✅ Embedding dimension: 768")

    # --------------------------------------------------------
    # 4. User's natural-language query
    # --------------------------------------------------------

    query_text = (
        "Patient presenting with severe liver disease "
        "and fluid retention needing diuretics"
    )

    print("\n🔍 Semantic Query:")
    print(f'"{query_text}"')

    # --------------------------------------------------------
    # 5. Convert query into embedding locally
    # --------------------------------------------------------

    print("\n🧠 Generating query embedding locally...")

    query_vector = model.encode(
        query_text,
        normalize_embeddings=True
    ).tolist()

    print("✅ Query converted to 768-dimensional vector.")

    # --------------------------------------------------------
    # 6. Convert vector to PostgreSQL format
    # --------------------------------------------------------

    query_vector_string = (
        "["
        + ",".join(
            str(float(value))
            for value in query_vector
        )
        + "]"
    )

    # --------------------------------------------------------
    # 7. pgvector semantic search
    # --------------------------------------------------------

    search_sql = text("""
        SELECT
            id,
            subject_id,
            hadm_id,
            admission_type,
            test_name,
            drug,
            description,
            drg_severity,
            comments,

            clinical_embedding <=> 
                CAST(:query_vector AS vector(768))
                AS cosine_distance

        FROM mimic_iv_transcript

        WHERE clinical_embedding IS NOT NULL

        ORDER BY cosine_distance ASC

        LIMIT :top_k
    """)

    # --------------------------------------------------------
    # 8. Execute search
    # --------------------------------------------------------

    with engine.connect() as conn:

        results = conn.execute(
            search_sql,
            {
                "query_vector": query_vector_string,
                "top_k": TOP_K
            }
        ).mappings().fetchall()

    # --------------------------------------------------------
    # 9. Display results
    # --------------------------------------------------------

    print("\n" + "=" * 75)
    print(f"🏆 TOP {TOP_K} SEMANTICALLY SIMILAR CLINICAL RECORDS")
    print("=" * 75)

    if not results:

        print(
            "❌ No records with embeddings were found."
        )

        return

    for rank, row in enumerate(results, 1):

        print("\n" + "-" * 75)

        print(
            f"Rank {rank}"
        )

        print(
            f"Cosine Distance : "
            f"{row['cosine_distance']:.6f}"
        )

        print(
            f"Record ID       : {row['id']}"
        )

        print(
            f"Patient ID      : {row['subject_id']}"
        )

        print(
            f"Admission ID    : {row['hadm_id']}"
        )

        print(
            f"Admission Type  : {row['admission_type']}"
        )

        print(
            f"Diagnosis       : {row['description']}"
        )

        print(
            f"Drug            : {row['drug']}"
        )

        print(
            f"Test            : {row['test_name']}"
        )

        print(
            f"DRG Severity    : {row['drg_severity']}"
        )

        if row["comments"]:

            print(
                f"Comments        : "
                f"{str(row['comments'])[:300]}"
            )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    test_vector_search()