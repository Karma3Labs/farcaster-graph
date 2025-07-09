from enum import IntEnum
import logging
import psycopg2
import psycopg2.extras
from timer import Timer
from config import settings


class InteractionType(IntEnum):
    # Note: Match it with `neynarv2.reactions.reaction_type`
    LIKE = 1


@Timer(name="update_likes_interactions")
def update_likes_interactions(logger: logging.Logger, pg_dsn: str, insert_limit: int):
    LIMIT = 10_000
    sql = f"""
BEGIN;

-- Fetch and lock the current cursor for likes (interaction_type = 1)
WITH current_cursor AS (
    SELECT COALESCE(
        (SELECT next_cursor 
         FROM public.k3l_farcaster_interaction_cursors 
         WHERE interaction_type = {InteractionType.LIKE.value}
         FOR UPDATE),  -- Lock this specific row
        '1970-01-01'::timestamp
    ) AS processed_updates_til
),
last_timestamp AS (
    SELECT updated_at 
    FROM (
        SELECT DISTINCT updated_at
        FROM (
            SELECT updated_at
            FROM neynarv2.reactions
            WHERE updated_at > (SELECT processed_updates_til FROM current_cursor)
            ORDER BY updated_at ASC
            LIMIT {LIMIT}  -- Apply limit before deduplication
        ) limited_chunk
    ) limited_timestamps
    ORDER BY updated_at DESC
    LIMIT 1 OFFSET 1  -- We are getting the second largest timestamp to handle the case of incomplete updates when at the tip. 
    -- The whole chunk can have only 1 distinct timestamp when we are at the tip, updated_at is NULL in that case and we do 0 processing.
),
batch_of_updates AS (
    SELECT
        fid,
        target_fid,
        created_at,
        deleted_at,
        updated_at
    FROM neynarv2.reactions
    WHERE
        reaction_type = {InteractionType.LIKE.value}
        AND target_fid IS NOT NULL
        AND updated_at > (SELECT processed_updates_til FROM current_cursor)
        AND updated_at <= (SELECT updated_at FROM last_timestamp)
),
aggregated_results AS (
    SELECT
        fid AS source,
        target_fid AS target,
        SUM(
            CASE
                -- Case 1: The reaction is currently in a "deleted" state.
                WHEN deleted_at IS NOT NULL THEN
                    -- Check if it was also CREATED in this same window.
                    -- If so, its net change is 0. Otherwise, it's -1.
                    CASE WHEN created_at > (SELECT processed_updates_til FROM current_cursor) THEN 0 ELSE -1 END
                
                -- Case 2: The reaction is in an "active" (not deleted) state.
                -- This means it's a new "like".
                ELSE 1
            END
        ) AS value
    FROM batch_of_updates
    GROUP BY fid, target_fid
),
inserted AS (
    -- Insert the aggregated results into the table
    INSERT INTO public.k3l_farcaster_interactions (source, target, interaction_type, value)
    SELECT 
        source,
        target,
        {InteractionType.LIKE.value} AS interaction_type, -- 1 for likes
        value
    FROM aggregated_results
    WHERE value != 0 -- Only insert non-zero interactions
    ON CONFLICT (source, target, interaction_type) 
    DO UPDATE SET 
        value = k3l_farcaster_interactions.value + EXCLUDED.value
    RETURNING 1  -- dummy value to keep the CTE happy
)
-- Update the cursor for the next query (only if we processed data)
INSERT INTO public.k3l_farcaster_interaction_cursors (interaction_type, next_cursor)
SELECT 
    {InteractionType.LIKE.value} AS interaction_type,
    updated_at AS next_cursor
FROM last_timestamp
WHERE updated_at IS NOT NULL
ON CONFLICT (interaction_type) 
DO UPDATE SET 
    next_cursor = EXCLUDED.next_cursor;

COMMIT;
"""

    with psycopg2.connect(
        pg_dsn,
        connect_timeout=settings.POSTGRES_TIMEOUT_SECS,
    ) as conn:
        with conn.cursor() as cursor:
            logger.info(f"Executing: {sql}")
            cursor.execute(sql)
