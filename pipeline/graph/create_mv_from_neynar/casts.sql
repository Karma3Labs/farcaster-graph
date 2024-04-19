CREATE MATERIALIZED VIEW mv_casts AS
SELECT
    generate_ulid() as id,
    created_at,
    updated_at,
    deleted_at,
    timestamp,
    fid,
    hash,
    parent_hash,
    parent_fid,
    parent_url,
    text,
    embeds::json,
    ARRAY_TO_JSON(mentions) as mentions,
    ARRAY_TO_JSON(mentions_positions) as mentions_positions,
    root_parent_hash,
    root_parent_url
FROM
    casts;