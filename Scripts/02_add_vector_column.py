import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv


def apply_pgvector():
    load_dotenv()

    db_url = os.getenv("DATABASE_URL")

    if not db_url:
        raise ValueError("DATABASE_URL not found in .env")

    engine = create_engine(db_url)

    print("🚀 Connecting to Neon PostgreSQL...")

    try:
        with engine.begin() as conn:

             # Enable pgvector
            print("🔧 Enabling pgvector extension...")

            conn.execute(text("""
                CREATE EXTENSION IF NOT EXISTS vector;
            """))

            print("✅ pgvector extension enabled.")

            print("🧠 Adding clinical_embedding column...")

            conn.execute(text("""
                ALTER TABLE mimic_iv_transcript
                ADD COLUMN IF NOT EXISTS clinical_embedding vector(768);
            """))

            # Verify the column
            verify = conn.execute(text("""
                SELECT column_name, data_type, udt_name
                FROM information_schema.columns
                WHERE table_name = 'mimic_iv_transcript'
                  AND column_name = 'clinical_embedding';
            """)).fetchone()

            if verify:
                print(
                    f"✅ Schema upgrade complete!\n"
                    f"Column: {verify[0]}\n"
                    f"Data type: {verify[1]}\n"
                    f"PostgreSQL type: {verify[2]}"
                )
            else:
                print("❌ Column was not found.")

    except Exception as e:
        print(f"❌ Error applying schema: {e}")


if __name__ == "__main__":
    apply_pgvector()