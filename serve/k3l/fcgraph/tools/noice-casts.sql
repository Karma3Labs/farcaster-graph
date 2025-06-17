-- noqa: disable=RF04

CREATE TABLE noice_variants_raw (
    liked integer NOT NULL,
    casted integer NOT NULL,
    recasted integer NOT NULL,
    replied integer NOT NULL
);

TRUNCATE noice_variants_raw;
INSERT INTO noice_variants_raw VALUES
(1, 0, 1, 1),
(1, 0, 5, 1),
(1, 0, 5, 2),
(1, 0, 2, 2);

-- noqa: ST06
CREATE VIEW noice_variants AS
SELECT
    'L'
    || liked
    || 'C'
    || casted
    || 'R'
    || recasted
    || 'Y'
    || replied AS weights,
    liked,
    casted,
    recasted,
    replied
FROM noice_variants_raw;

CREATE VIEW noice_tipper_scores AS
WITH va AS (
    SELECT
        va.address,
        va.fid,
        gt.v AS score
    FROM verified_addresses AS va
    LEFT JOIN globaltrust AS gt ON va.fid = gt.i
    WHERE
        gt.strategy_id = 9
        AND gt.date = '2025-06-09'
)

SELECT DISTINCT
    va.fid,
    va.score
FROM noice_tippers AS t
INNER JOIN va ON t.address = va.address
;

CREATE VIEW noice_candidate_casts AS
SELECT * FROM neynarv2.casts AS c
WHERE
    c.timestamp >= '2025-05-21T17:47:59Z'
    AND c.timestamp < '2025-06-08T00:00:00Z';

CREATE VIEW noice_candidate_cast_actions AS
SELECT * FROM k3l_cast_action_v1 AS ca
WHERE
    ca.action_ts >= '2025-05-21T17:47:59Z'
    AND ca.action_ts < '2025-06-08T00:00:00Z';

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
        + var.replied * ca.replied AS combined_weight
    FROM noice_variants AS var
    CROSS JOIN noice_candidate_cast_actions AS ca
    JOIN neynarv2.casts cac ON ca.cast_hash = cac.hash
    WHERE ca.fid != cac.fid
)

SELECT
    ca.weights,
    c.hash,
    sum(ca.combined_weight * cas.score) AS score
FROM noice_candidate_casts AS c
INNER JOIN ca ON c.hash = ca.hash
INNER JOIN noice_tipper_scores AS cas ON ca.fid = cas.fid
GROUP BY c.hash, ca.weights
HAVING sum(ca.combined_weight * cas.score) > 0
ORDER BY score DESC;
-- REFRESH MATERIALIZED VIEW noice_casts_dry;

CREATE INDEX noice_casts_dry_hash_idx ON noice_casts_dry (hash);

DROP MATERIALIZED VIEW IF EXISTS noice_casts_hydrated CASCADE;
CREATE MATERIALIZED VIEW noice_casts_hydrated AS
SELECT
    cs.weights,
    cs.score,
    c.hash,
    c.fid,
    p.username,
    c.timestamp,
    c.parent_hash,
    c.parent_url,
    c.root_parent_hash,
    c.root_parent_url,
    c.text
FROM noice_casts_dry cs
INNER JOIN neynarv2.casts AS c ON c.hash = cs.hash
INNER JOIN neynarv3.profiles AS p ON p.fid = c.fid
ORDER BY score DESC;

CREATE TABLE noice_discounted_fids (fid bigint PRIMARY KEY);
INSERT INTO noice_discounted_fids VALUES (2), (3), (12), (239), (3621);

DROP VIEW IF EXISTS noice_casts_dry_30k CASCADE;
DROP VIEW IF EXISTS noice_casts_dry_10k CASCADE;
CREATE VIEW noice_casts_dry_10k AS
SELECT
    weights,
    hash,
    fid,
    score,
    rank
FROM (
    SELECT
        n.weights,
        n.hash,
        n.fid,
        score,
        row_number() OVER (
            PARTITION BY n.weights
            ORDER BY n.score DESC
        ) AS rank
    FROM noice_casts_hydrated n
    LEFT JOIN noice_discounted_fids ndf ON n.fid = ndf.fid
    WHERE ndf.fid IS NULL
) AS ranked
WHERE rank <= 10000;

DROP VIEW IF EXISTS noice_top_creators;
CREATE VIEW noice_top_creators AS
SELECT
    c.weights,
    c.fid,
    p.username,
    count(*) AS count,
    array_agg(c.rank) AS ranks,
    sum(c.score) AS total_score
FROM noice_casts_dry_10k AS c
INNER JOIN neynarv3.profiles AS p ON p.fid = c.fid
GROUP BY c.weights, c.fid, p.username;

SELECT * FROM noice_top_creators
WHERE weights = 'L1C0R2Y2'
ORDER BY count DESC;

DROP VIEW IF EXISTS noice_top_tippers;
CREATE VIEW noice_top_tippers AS
SELECT
    c.weights,
    t.fid,
    p.username,
    count(DISTINCT c.fid) AS count,
    array_agg(DISTINCT c.fid) AS creators
FROM noice_tipper_scores t
INNER JOIN noice_candidate_cast_actions ca ON t.fid = ca.fid
INNER JOIN noice_casts_dry_10k c ON c.hash = ca.cast_hash
INNER JOIN neynarv3.profiles p ON p.fid = t.fid
GROUP BY c.weights, t.fid, p.username;

SELECT * FROM noice_top_tippers
WHERE weights = 'L1C0R2Y2'
ORDER BY count DESC;
