CREATE MATERIALIZED VIEW mv_follow_links AS
SELECT 
    generate_ulid() as id,
    fid AS follower_fid,
    target_fid AS following_fid
FROM 
    links
WHERE 
    type = 'follow'::text;