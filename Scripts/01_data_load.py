import psycopg
import os
from dotenv import load_dotenv

load_dotenv()

CSV_FILE = "MIMIC_IV_Trasncript.csv"
with psycopg.connect(os.getenv("DATABASE_URL")) as conn:
    with conn.cursor() as cur:

        with open(CSV_FILE, "r", encoding="utf-8") as f:
            with cur.copy("""
                COPY mimic_iv_transcript
                FROM STDIN
                WITH (
                    FORMAT CSV,
                    HEADER TRUE,
                    NULL ''
                )
            """) as copy:
                while data := f.read(1024 * 1024):
                    copy.write(data)

    conn.commit()

print("CSV loaded successfully!")