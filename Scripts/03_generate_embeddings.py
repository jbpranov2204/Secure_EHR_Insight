import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from tqdm import tqdm


# ============================================================
# CONFIGURATION
# ============================================================

MODEL_NAME = "NeuML/bioclinical-modernbert-base-embeddings"

DB_BATCH_SIZE = 10       # Number of rows fetched from Neon at once
MODEL_BATCH_SIZE = 10    # Number of texts embedded at once
DEMO_LIMIT = 500


# ============================================================
# BUILD CLINICAL TEXT
# ============================================================

def build_clinical_text(row):
    """
    Converts structured clinical fields into a single text string
    that will be passed to the local embedding model.
    """

    components = []

    if row["admission_type"]:
        components.append(
            f"Admission: {row['admission_type']}"
        )

    if row["drug"]:
        components.append(
            f"Prescribed: {row['drug']}"
        )

    if row["test_name"]:
        components.append(
            f"Lab Test: {row['test_name']}"
        )

    if row["drg_severity"] is not None:
        components.append(
            f"Severity Level: {row['drg_severity']}"
        )

    if row["description"]:
        components.append(
            f"Diagnosis: {row['description']}"
        )

    if row["comments"]:
        # Limit very long comments
        comments = str(row["comments"])[:250]

        components.append(
            f"Notes: {comments}"
        )

    return " | ".join(components)


# ============================================================
# MAIN FUNCTION
# ============================================================

def generate_and_store_embeddings():

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
    print(f"   Model: {MODEL_NAME}")

    model = SentenceTransformer(MODEL_NAME)

    # --------------------------------------------------------
    # 4. Verify embedding dimension
    # --------------------------------------------------------

    embedding_dimension = (
        model.get_sentence_embedding_dimension()
    )

    print(
        f"   Embedding dimension: {embedding_dimension}"
    )

    if embedding_dimension != 768:
        raise ValueError(
            f"CRITICAL ERROR: Model produces "
            f"{embedding_dimension} dimensions, "
            f"but database expects vector(768)."
        )

    print("✅ Model dimension matches vector(768).")

    # --------------------------------------------------------
    # 5. Process database records
    # --------------------------------------------------------

    processed = 0

    with engine.begin() as conn:

        print("\n🚀 Starting embedding generation...")

        while True:

            # Stop when demo limit is reached
            if DEMO_LIMIT is not None:
                if processed >= DEMO_LIMIT:
                    break

                remaining = DEMO_LIMIT - processed
                current_batch_size = min(
                    DB_BATCH_SIZE,
                    remaining
                )
            else:
                current_batch_size = DB_BATCH_SIZE

            # ------------------------------------------------
            # Fetch records that don't have embeddings
            # ------------------------------------------------

            query = text("""
                SELECT
                    id,
                    admission_type,
                    drug,
                    test_name,
                    drg_severity,
                    description,
                    comments
                FROM mimic_iv_transcript
                WHERE clinical_embedding IS NULL
                ORDER BY id
                LIMIT :batch_size
            """)

            rows = conn.execute(
                query,
                {
                    "batch_size": current_batch_size
                }
            ).mappings().fetchall()

            # ------------------------------------------------
            # No more records
            # ------------------------------------------------

            if not rows:
                print(
                    "\n✅ No more records require embeddings."
                )
                break

            # ------------------------------------------------
            # Build clinical texts
            # ------------------------------------------------

            clinical_texts = []
            record_ids = []

            for row in rows:

                clinical_text = build_clinical_text(row)

                # Skip records with no usable clinical data
                if not clinical_text.strip():
                    print(
                        f"⚠️ Skipping ID {row['id']} "
                        f"because no clinical text was found."
                    )
                    continue

                clinical_texts.append(clinical_text)
                record_ids.append(row["id"])

            # ------------------------------------------------
            # Nothing usable in this batch
            # ------------------------------------------------

            if not clinical_texts:
                continue

            # ------------------------------------------------
            # Generate embeddings LOCALLY
            # ------------------------------------------------

            embeddings = model.encode(
                clinical_texts,
                batch_size=MODEL_BATCH_SIZE,
                show_progress_bar=False,
                convert_to_numpy=True,
                normalize_embeddings=True
            )

            # ------------------------------------------------
            # Store embeddings in Neon
            # ------------------------------------------------

            for record_id, embedding in zip(
                record_ids,
                embeddings
            ):

                embedding_string = (
                    "[" +
                    ",".join(
                        str(float(value))
                        for value in embedding
                    ) +
                    "]"
                )

                update_query = text("""
                    UPDATE mimic_iv_transcript
                    SET clinical_embedding = CAST(
                        :embedding AS vector(768)
                    )
                    WHERE id = :id
                """)

                conn.execute(
                    update_query,
                    {
                        "embedding": embedding_string,
                        "id": record_id
                    }
                )

            processed += len(clinical_texts)

            print(
                f"✅ Processed: {processed}"
                + (
                    f"/{DEMO_LIMIT}"
                    if DEMO_LIMIT is not None
                    else ""
                )
            )

    # --------------------------------------------------------
    # Finished
    # --------------------------------------------------------

    print("\n🎉 Embedding generation complete!")
    print(
        f"📊 Total records processed: {processed}"
    )
    print(
        "💾 Embeddings stored in "
        "mimic_iv_transcript.clinical_embedding"
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    generate_and_store_embeddings()