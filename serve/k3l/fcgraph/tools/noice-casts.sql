-- noqa: disable=RF04

DROP TABLE IF EXISTS noice_variants_raw CASCADE;
CREATE TABLE noice_variants_raw (
    liked integer NOT NULL,
    casted integer NOT NULL,
    recasted integer NOT NULL,
    replied integer NOT NULL,
    quoted integer NOT NULL
);
GRANT ALL ON TABLE noice_variants_raw TO k3l_user;
GRANT SELECT ON TABLE noice_variants_raw TO k3l_readonly;

INSERT INTO noice_variants_raw (liked, casted, recasted, replied, quoted) VALUES
(1, 0, 1, 1, 3),
(1, 0, 5, 1, 3),
(1, 0, 5, 2, 3),
(1, 0, 2, 2, 3);

DROP VIEW IF EXISTS noice_variants CASCADE;
CREATE VIEW noice_variants AS
SELECT
    liked,
    casted,
    recasted,
    replied,
    quoted,
    'L'
    || liked
    || 'C'
    || casted
    || 'R'
    || recasted
    || 'Y'
    || replied
    || 'Q'
    || quoted AS weights
FROM noice_variants_raw;
GRANT ALL ON TABLE noice_variants TO k3l_user;
GRANT SELECT ON TABLE noice_variants TO k3l_readonly;

DROP VIEW IF EXISTS noice_tipper_scores CASCADE;
CREATE VIEW noice_tipper_scores AS
WITH va AS (
    SELECT
        va.address,
        va.fid,
        gt.v AS score
    FROM neynarv3.verifications AS va
    LEFT JOIN globaltrust AS gt ON va.fid = gt.i
    WHERE
        va.deleted_at IS NULL
        AND gt.strategy_id = 9
        AND gt.date = '2025-06-20'
)

SELECT DISTINCT
    va.fid,
    va.score
FROM noice_tippers AS t
INNER JOIN va ON t.address = va.address;
GRANT ALL ON TABLE noice_tipper_scores TO k3l_user;
GRANT SELECT ON TABLE noice_tipper_scores TO k3l_readonly;

SELECT
    fid,
    score
FROM noice_tipper_scores;

DROP VIEW IF EXISTS noice_candidate_casts CASCADE;
CREATE VIEW noice_candidate_casts AS
SELECT
    hash,
    fid,
    timestamp
FROM neynarv3.casts
WHERE
    timestamp >= '2025-05-21T17:47:59Z'
    AND timestamp < '2025-06-20T00:00:00Z';
GRANT ALL ON TABLE noice_candidate_casts TO k3l_user;
GRANT SELECT ON TABLE noice_candidate_casts TO k3l_readonly;
CREATE INDEX noice_candidate_casts_hash_idx ON noice_candidate_casts (hash);
CREATE INDEX noice_candidate_casts_fid_idx ON noice_candidate_casts (fid);

-- noqa: disable=ST07
DROP MATERIALIZED VIEW IF EXISTS noice_candidate_cast_actions CASCADE;
CREATE MATERIALIZED VIEW noice_candidate_cast_actions AS
WITH raw_quotes AS (
    SELECT
        fid,
        timestamp,
        unnest(embedded_casts) AS cast_hash
    FROM neynarv3.casts
),

q AS (
    SELECT
        fid,
        cast_hash,
        timestamp AS action_ts,
        count(*) AS count
    FROM raw_quotes
    WHERE
        timestamp >= '2025-05-21T17:47:59Z'
        AND timestamp < '2025-06-20T00:00:00Z'
    GROUP BY fid, cast_hash, timestamp
),

a AS (
    SELECT
        fid,
        cast_hash,
        action_ts,
        casted,
        replied,
        recasted,
        liked
    FROM k3l_cast_action_v1
    WHERE
        action_ts >= '2025-05-21T17:47:59Z'
        AND action_ts < '2025-06-20T00:00:00Z'
),

ca AS (
    SELECT
        fid,
        cast_hash,
        action_ts,
        coalesce(a.casted, 0) AS casted,
        coalesce(a.replied, 0) AS replied,
        coalesce(a.recasted, 0) AS recasted,
        coalesce(a.liked, 0) AS liked,
        coalesce(q.count, 0) AS quoted
    FROM a
    FULL OUTER JOIN
        q
        USING (fid, cast_hash, action_ts)
)

SELECT
    ca.fid,
    ca.cast_hash,
    ca.action_ts,
    ca.casted,
    ca.replied,
    ca.recasted,
    ca.liked,
    ca.quoted
FROM ca
INNER JOIN
    noice_candidate_casts AS c
    ON ca.cast_hash = c.hash
INNER JOIN
    noice_tipper_scores AS ts
    ON ca.fid = ts.fid
WHERE
    c.fid != ca.fid;
GRANT ALL ON TABLE noice_candidate_cast_actions TO k3l_user;
GRANT SELECT ON TABLE noice_candidate_cast_actions TO k3l_readonly;
CREATE INDEX noice_candidate_cast_actions_fid_hash_idx
ON noice_candidate_cast_actions (fid, cast_hash);

DROP MATERIALIZED VIEW IF EXISTS noice_casts_dry CASCADE;
CREATE MATERIALIZED VIEW noice_casts_dry AS
WITH ca AS (
-- combined weight of cast actions per cast (hash) per actor (fid)
    SELECT
        var.weights,
        ca.cast_hash AS hash,
        ca.fid,
        var.liked * ca.liked
        + var.casted * ca.casted
        + var.recasted * ca.recasted
        + var.replied * ca.replied
        + var.quoted * ca.quoted AS combined_weight
    FROM noice_variants AS var
    CROSS JOIN noice_candidate_cast_actions AS ca
)

SELECT
    ca.weights,
    ca.hash,
    sum(ca.combined_weight * cas.score) AS score,
    count(DISTINCT ca.fid) AS num_tippers
-- FROM noice_candidate_casts AS c
FROM ca -- ON c.hash = ca.hash
INNER JOIN noice_tipper_scores AS cas ON ca.fid = cas.fid
GROUP BY ca.weights, ca.hash
HAVING sum(ca.combined_weight * cas.score) > 0;
GRANT ALL ON TABLE noice_casts_dry TO k3l_user;
GRANT SELECT ON TABLE noice_casts_dry TO k3l_readonly;
CREATE INDEX noice_casts_dry_hash_idx ON noice_casts_dry (hash);

-- noqa: disable=ST06
DROP MATERIALIZED VIEW IF EXISTS noice_casts_hydrated CASCADE;
CREATE MATERIALIZED VIEW noice_casts_hydrated AS
SELECT
    cs.weights,
    row_number() OVER (
        PARTITION BY cs.weights
        ORDER BY cs.score DESC
    ) AS rank,
    cs.score,
    cs.num_tippers,
    c.hash,
    c.fid,
    p.username,
    c.timestamp,
    c.parent_hash,
    c.parent_url,
    c.root_parent_hash,
    c.root_parent_url,
    c.text
FROM noice_casts_dry AS cs
INNER JOIN neynarv3.casts AS c ON cs.hash = c.hash
INNER JOIN neynarv3.profiles AS p ON c.fid = p.fid
WHERE c.fid NOT IN (2, 3, 12, 239, 3621);
GRANT ALL ON TABLE noice_casts_hydrated TO k3l_user;
GRANT SELECT ON TABLE noice_casts_hydrated TO k3l_readonly;
CREATE INDEX noice_casts_hydrated_weights_rank_idx
ON noice_casts_hydrated (weights, rank);
CREATE INDEX noice_casts_hydrated_fid_idx ON noice_casts_hydrated (fid);
CREATE INDEX noice_casts_hydrated_hash_idx ON noice_casts_hydrated (hash);

SELECT
    weights,
    rank,
    score,
    num_tippers,
    hash,
    fid,
    username,
    timestamp,
    parent_hash,
    parent_url,
    root_parent_hash,
    root_parent_url,
    text
FROM noice_casts_hydrated
WHERE weights = 'L1C0R2Y2Q3' AND rank <= 10000;

DROP VIEW IF EXISTS noice_casts_dry_ranked CASCADE;
CREATE VIEW noice_casts_dry_ranked AS
SELECT
    weights,
    hash,
    fid,
    score,
    num_tippers,
    rank
FROM noice_casts_hydrated;
GRANT ALL ON TABLE noice_casts_dry_ranked TO k3l_user;
GRANT SELECT ON TABLE noice_casts_dry_ranked TO k3l_readonly;

DROP VIEW IF EXISTS noice_casts_dry_ranked_10k CASCADE;
CREATE VIEW noice_casts_dry_ranked_10k AS
SELECT
    weights,
    hash,
    fid,
    score,
    num_tippers,
    rank
FROM noice_casts_dry_ranked
WHERE rank <= 10000;
GRANT ALL ON TABLE noice_casts_dry_ranked_10k TO k3l_user;
GRANT SELECT ON TABLE noice_casts_dry_ranked_10k TO k3l_readonly;

SELECT
    weights,
    hash,
    fid,
    score,
    num_tippers,
    rank
FROM noice_casts_dry_ranked
WHERE weights = 'L1C0R2Y2Q3'
ORDER BY rank;

-- add follower count
DROP VIEW IF EXISTS noice_top_creators CASCADE;
CREATE VIEW noice_top_creators AS
WITH creators AS (
    SELECT
        c.weights,
        c.fid,
        p.username,
        count(*) AS count,
        array_agg(c.rank) AS ranks,
        sum(c.score) AS total_score
    FROM noice_casts_dry_ranked_10k AS c
    INNER JOIN neynarv3.profiles AS p ON c.fid = p.fid
    GROUP BY c.weights, c.fid, p.username
)

SELECT
    cr.weights,
    cr.fid,
    cr.username,
    cr.count,
    cr.ranks,
    cr.total_score,
    coalesce(gt.v, 0) AS openrank_score,
    coalesce(f.count, 0) AS follower_count
FROM creators AS cr
LEFT OUTER JOIN globaltrust AS gt
    ON
        cr.fid = gt.i
        AND gt.strategy_id = 9
        AND gt.date = '2025-06-20'
LEFT OUTER JOIN k3l_follower_counts AS f ON cr.fid = f.fid;
GRANT ALL ON TABLE noice_top_creators TO k3l_user;
GRANT SELECT ON TABLE noice_top_creators TO k3l_readonly;

SELECT
    weights,
    fid,
    username,
    count,
    ranks,
    total_score
FROM noice_top_creators
WHERE weights = 'L1C0R2Y2Q3'
ORDER BY count DESC;

-- another column interaction_count:
--   unique interaction count across all top 10k casts
-- count -> creator_count
-- sort by interaction_counts
DROP VIEW IF EXISTS noice_top_tippers CASCADE;
CREATE VIEW noice_top_tippers AS
SELECT
    c.weights,
    t.fid,
    p.username,
    count(*) AS interaction_count,
    count(DISTINCT c.fid) AS creator_count,
    array_agg(DISTINCT c.fid) AS creators
FROM noice_tipper_scores AS t
INNER JOIN noice_candidate_cast_actions AS ca ON t.fid = ca.fid
INNER JOIN noice_casts_dry_ranked AS c ON ca.cast_hash = c.hash
INNER JOIN neynarv3.profiles AS p ON t.fid = p.fid
WHERE c.rank <= 10000
GROUP BY c.weights, t.fid, p.username;
GRANT ALL ON TABLE noice_top_tippers TO k3l_user;
GRANT SELECT ON TABLE noice_top_tippers TO k3l_readonly;

SELECT
    weights,
    fid,
    username,
    creator_count,
    creators
FROM noice_top_tippers
WHERE weights = 'L1C0R2Y2Q3'
ORDER BY interaction_count DESC;
