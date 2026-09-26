
--Install pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- Check if pgvector is installed
SELECT extname, extversion
FROM pg_extension
WHERE extname = 'vector';

-- Create Table
CREATE TABLE mimic_iv_transcript (
    subject_id BIGINT,
    hadm_id BIGINT,
    admission_type TEXT,
    admission_location TEXT,
    discharge_location TEXT,
    insurance TEXT,
    marital_status TEXT,
    race TEXT,
    gender TEXT,
    anchor_age INTEGER,
    drug TEXT,
    formulary_drug_cd TEXT,
    prod_strength TEXT,
    dose_val_rx DOUBLE PRECISION,
    dose_unit_rx TEXT,
    form_unit_disp TEXT,
    route TEXT,
    eventtype TEXT,
    careunit TEXT,
    order_type TEXT,
    order_subtype TEXT,
    transaction_type TEXT,
    spec_type_desc TEXT,
    test_name TEXT,
    org_name TEXT,
    ab_name TEXT,
    comments TEXT,
    drg_type TEXT,
    description TEXT,
    drg_severity DOUBLE PRECISION,
    drg_mortality DOUBLE PRECISION
);