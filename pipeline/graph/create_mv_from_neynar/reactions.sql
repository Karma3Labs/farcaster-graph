CREATE MATERIALIZED VIEW mv_reactions AS
SELECT
    generate_ulid() as id,
    created_at,
    updated_at,
    timestamp,
    deleted_at,
    fid,
    target_fid as target_cast_fid,
    reaction_type as type,
    hash,
    target_hash as target_cast_hash,
    target_url
FROM
    reactions;