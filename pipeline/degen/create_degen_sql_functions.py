# File: create_degen_functions.py

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from dotenv import load_dotenv
import os
from config import settings

load_dotenv()

# SQL statements
CREATE_PARSE_DEGEN_TIP_FUNCTION = """
CREATE OR REPLACE FUNCTION parse_degen_tip(cast_text TEXT)
RETURNS TABLE(degen_amount NUMERIC, is_valid BOOLEAN) AS $$
DECLARE
    match TEXT;
BEGIN
    -- Use regexp_matches to extract the DEGEN amount
    SELECT (regexp_matches(cast_text, '(\\d+(?:\\.\\d+)?)\\s*\\$DEGEN'))[1] INTO match;

    IF match IS NOT NULL THEN
        degen_amount := match::NUMERIC;
        is_valid := TRUE;
    ELSE
        degen_amount := 0;
        is_valid := FALSE;
    END IF;

    RETURN NEXT;
END;
$$ LANGUAGE plpgsql;
"""

CREATE_UPDATE_DEGEN_TIPS_FUNCTION = """
CREATE OR REPLACE FUNCTION update_degen_tips()
RETURNS void AS $$
DECLARE
    last_processed_timestamp TIMESTAMP WITH TIME ZONE;
    rows_inserted INTEGER;
BEGIN
    SELECT COALESCE(MAX(parsed_at), CURRENT_TIMESTAMP)
    INTO last_processed_timestamp
    FROM k3l_degen_tips;

    WITH deduct_degen AS (
        SELECT
            casts.parent_hash AS cast_hash
        FROM
            casts
        WHERE
            UPPER(casts.text) LIKE '%DEDEGEN%'
            AND casts.fid = ANY(ARRAY[2904, 15983, 12493, 250874, 307834, 403619, 269694, 234616, 4482, 274, 243818, 385955, 210201, 3642, 539, 294226, 16405, 3827, 320215, 7637, 4027, 9135, 7258, 211186, 10174, 7464, 13505, 11299, 1048, 2341, 617, 191503, 4877, 3103, 12990, 390940, 7237, 5034, 195117, 8447, 20147, 262938, 307739, 17064, 351897, 426045, 326433, 273147, 270504, 419741, 446697, 354795])
            AND casts.deleted_at IS NULL
            AND casts."timestamp" > last_processed_timestamp
        GROUP BY
            casts.parent_hash
        HAVING COUNT(*) >= 5
    ),
    nuke_degen AS (
        SELECT
            casts.parent_hash AS cast_hash
        FROM
            casts
        WHERE
            UPPER(casts.text) LIKE '%DEDEGEN%'
            AND casts.fid IN (2904, 15983, 12493)
            AND casts.deleted_at IS NULL
            AND casts."timestamp" > last_processed_timestamp
        GROUP BY
            casts.parent_hash
    ),
    parsed_casts AS (
        SELECT
            casts.*,
            p.degen_amount,
            p.is_valid
        FROM
            casts,
            LATERAL parse_degen_tip(casts.text) p
        WHERE
            casts."timestamp" > last_processed_timestamp
    ),
    new_tips AS (
        INSERT INTO k3l_degen_tips (cast_hash, parent_hash, fid, parent_fid, degen_amount, "timestamp", parent_timestamp)
        SELECT
            parsed_casts.hash,
            parsed_casts.parent_hash,
            parsed_casts.fid,
            parsed_casts.parent_fid,
            parsed_casts.degen_amount,
            parsed_casts."timestamp",
            parent_casts."timestamp"
        FROM
            parsed_casts
        INNER JOIN
            casts AS parent_casts ON parsed_casts.parent_hash = parent_casts.hash
        WHERE
            parsed_casts.is_valid
            AND parsed_casts.parent_hash IS NOT NULL
            AND parsed_casts.parent_fid <> parsed_casts.fid
            AND parsed_casts.deleted_at IS NULL
            AND parsed_casts.fid NOT IN (217745, 234434, 244128, 364927)
            AND parsed_casts.parent_fid NOT IN (364927)
            AND COALESCE(ARRAY_POSITION(parsed_casts.mentions, 364927), 0) = 0
            AND NOT EXISTS (
                SELECT 1
                FROM k3l_degen_tips
                WHERE k3l_degen_tips.cast_hash = parsed_casts.hash
            )
            AND NOT EXISTS (
                SELECT 1
                FROM deduct_degen
                WHERE deduct_degen.cast_hash = parsed_casts.parent_hash
            )
            AND NOT EXISTS (
                SELECT 1
                FROM nuke_degen
                WHERE nuke_degen.cast_hash = parsed_casts.parent_hash
            )
        ORDER BY parsed_casts."timestamp" DESC
        RETURNING 1
    )
    SELECT COUNT(*) INTO rows_inserted FROM new_tips;

    RAISE NOTICE 'Inserted % new eligible DEGEN tips', rows_inserted;
END;
$$ LANGUAGE plpgsql;
"""

def create_functions():
  pg_dsn = settings.POSTGRES_DSN.get_secret_value()

  conn = None
  try:
      # Connect to the database
      conn = psycopg2.connect(pg_dsn)
      conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)

      # Create a cursor
      cur = conn.cursor()

      # Create the functions
      cur.execute(CREATE_PARSE_DEGEN_TIP_FUNCTION)
      cur.execute(CREATE_UPDATE_DEGEN_TIPS_FUNCTION)

      print("Functions created successfully.")

  except (Exception, psycopg2.Error) as error:
      print("Error while connecting to PostgreSQL", error)

  finally:
      if conn:
          cur.close()
          conn.close()
          print("PostgreSQL connection is closed")

if __name__ == "__main__":
  create_functions()