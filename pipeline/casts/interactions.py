import logging
from enum import IntEnum

import psycopg2
import psycopg2.extras

from config import settings
from timer import Timer


class InteractionType(IntEnum):
    # Note: Match it with `neynarv3.reactions.reaction_type`
    LIKE = 1
    RECAST = 2

    # not in the neynarv3.reactions.reaction_type
    REPLY = 11


@Timer(name="update_reply_interactions")
def update_reply_interactions(logger: logging.Logger, pg_dsn: str):
    LIMIT = 10_000_000
    sql = f"""
BEGIN;

-- Fetch and lock the current cursor
WITH current_cursor AS (
    {get_current_cursor_cte_with_lock(InteractionType.REPLY)}
),
last_timestamp AS (
    {get_last_timestamp_cte("casts", LIMIT)}
),
batch_of_updates AS (
    SELECT
        id,
        fid,
        parent_fid as target_fid,
        created_at,
        deleted_at,
        updated_at
    FROM neynarv3.casts
    WHERE
        parent_hash IS NOT NULL
        AND updated_at > (SELECT processed_updates_til FROM current_cursor)
        AND updated_at <= (SELECT updated_at FROM last_timestamp)
),
aggregated_results AS (
    SELECT
        fid AS source,
        target_fid AS target,
        SUM(
            CASE
                -- Case 0: The interaction is not in the seen_casts table - we are seeing it for the first time.
                WHEN id NOT IN (SELECT id FROM public.seen_casts) THEN
                    CASE WHEN deleted_at is NULL THEN 1 ELSE 0
                ELSE
                    CASE WHEN deleted_at is not NULL THEN 0 ELSE -1 
                END
            END
        ) AS value
    FROM batch_of_updates
    GROUP BY fid, target_fid
),
inserted_ids AS (
    INSERT INTO public.seen_casts (id, interaction_type)
    SELECT id, {InteractionType.REPLY.value}
    FROM batch_of_updates
    ON CONFLICT (id, interaction_type) DO NOTHING
    RETURNING 1
),
{insert_data_sql(InteractionType.REPLY)}

COMMIT;
"""
    query_db(sql, logger, pg_dsn)


@Timer(name="update_likes_interactions")
def update_likes_interactions(logger: logging.Logger, pg_dsn: str):
    LIMIT = 10_000_000
    sql = f"""
BEGIN;

-- Fetch and lock the current cursor for likes (interaction_type = 1)
WITH current_cursor AS (
    {get_current_cursor_cte_with_lock(InteractionType.LIKE)}
),
last_timestamp AS (
    {get_last_timestamp_cte("reactions", LIMIT)}
),
batch_of_updates AS (
    SELECT
        neynarv3.reactions.id,
        neynarv3.reactions.fid,
        neynarv3.reactions.target_fid,
        neynarv3.reactions.created_at,
        neynarv3.reactions.deleted_at
    FROM neynarv3.reactions
    INNER JOIN neynarv3.fids ON neynarv3.fids.fid = neynarv3.reactions.target_fid
    WHERE
        neynarv3.reactions.reaction_type = {InteractionType.LIKE.value}
        AND neynarv3.reactions.target_fid IS NOT NULL
        AND neynarv3.reactions.updated_at > (SELECT processed_updates_til FROM current_cursor)
        AND neynarv3.reactions.updated_at <= (SELECT updated_at FROM last_timestamp)
),
aggregated_results AS (
    SELECT
        fid AS source,
        target_fid AS target,
        SUM(
            CASE
                -- Case 0: The interaction is not in the seen_reactions table - we are seeing it for the first time.
                WHEN id NOT IN (SELECT id FROM public.seen_reactions) THEN
                    CASE WHEN deleted_at is NULL THEN 1 ELSE 0
                ELSE
                    CASE WHEN deleted_at is not NULL THEN -1 ELSE 1 
                END
            END
        ) AS value
    FROM batch_of_updates
    GROUP BY fid, target_fid
),
inserted_ids AS (
    INSERT INTO public.seen_reactions (id)
    SELECT id
    FROM batch_of_updates
    ON CONFLICT (id) DO NOTHING
    RETURNING 1
),
{insert_data_sql(InteractionType.LIKE)}

COMMIT;
"""
    query_db(sql, logger, pg_dsn)


def query_db(sql: str, logger: logging.Logger, pg_dsn: str):
    with psycopg2.connect(
        pg_dsn,
        connect_timeout=settings.POSTGRES_TIMEOUT_SECS,
    ) as conn:
        with conn.cursor() as cursor:
            logger.info(f"Executing: {sql}")
            cursor.execute(sql)


def get_last_timestamp_cte(table_name: str, limit: int):
    return f"""
    SELECT updated_at 
    FROM (
        SELECT DISTINCT updated_at
        FROM (
            SELECT updated_at
            FROM {table_name}
            WHERE updated_at > (SELECT processed_updates_til FROM current_cursor)
            ORDER BY updated_at ASC
            LIMIT {limit}  -- Apply limit before deduplication
        ) limited_chunk
    ) limited_timestamps
    ORDER BY updated_at DESC
    LIMIT 1 OFFSET 1  -- We are getting the second largest timestamp to handle the case of incomplete updates when at the tip. 
    -- The whole chunk can have only 1 distinct timestamp when we are at the tip, updated_at is NULL in that case and we do 0 processing.
    """


def get_current_cursor_cte_with_lock(interaction_type: InteractionType):
    return f"""
    SELECT COALESCE(
        (SELECT next_cursor 
         FROM public.k3l_farcaster_interaction_cursors 
         WHERE interaction_type = {interaction_type}
         FOR UPDATE),  -- Lock this specific row
        '1970-01-01'::timestamp
    ) AS processed_updates_til
    """


def insert_data_sql(interaction_type: InteractionType):
    return f"""
inserted AS (
    -- Insert the aggregated results into the table
    INSERT INTO public.k3l_farcaster_interactions (source, target, interaction_type, value)
    SELECT 
        source,
        target,
        {interaction_type.value} AS interaction_type,
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
    {interaction_type.value} AS interaction_type,
    updated_at AS next_cursor
FROM last_timestamp
WHERE updated_at IS NOT NULL
ON CONFLICT (interaction_type) 
DO UPDATE SET 
    next_cursor = EXCLUDED.next_cursor;
    """
