-- noqa: disable=RF04

CREATE OR REPLACE FUNCTION array_union(anyarray, anyarray)
RETURNS anyarray LANGUAGE sql AS $$
    SELECT array_agg(el)
    FROM (
        SELECT unnest($1)
        UNION DISTINCT
        SELECT unnest($2)
    ) AS x (el)
$$;
ALTER FUNCTION array_union(anyarray, anyarray) OWNER TO k3l_user;
GRANT EXECUTE ON FUNCTION array_union(anyarray, anyarray) TO k3l_readonly;

CREATE OR REPLACE AGGREGATE array_union_agg (anyarray)(
    sfunc = array_union,
    stype = anyarray,
    initcond = '{}'
);
ALTER AGGREGATE array_union_agg (anyarray) OWNER TO k3l_user;
GRANT EXECUTE ON FUNCTION array_union_agg(anyarray) TO k3l_readonly;

DROP TABLE IF EXISTS noice_tippers_final_raw CASCADE;
CREATE TABLE noice_tippers_final_raw (
    from_fid bigint NOT NULL,
    all_to_fids text NOT NULL,
    unique_to_fid_count_across_tokens bigint NOT NULL,
    total_amount_across_tokens numeric NOT NULL,
    PRIMARY KEY (from_fid)
);
ALTER TABLE noice_tippers_final_raw OWNER TO k3l_user;
GRANT SELECT ON TABLE noice_tippers_final_raw TO k3l_readonly;

-- \COPY noice_tippers_final_raw FROM 'noice_unique_tippers_final.csv'
-- (FORMAT CSV, HEADER MATCH);

DROP MATERIALIZED VIEW IF EXISTS noice_tippers_final CASCADE;
CREATE MATERIALIZED VIEW noice_tippers_final AS
SELECT
    from_fid AS fid,
    string_to_array(
        regexp_replace(all_to_fids, '[\[\]\s]', '', 'g'),
        ','
    )::bigint [] AS tipped_fids,
    total_amount_across_tokens
FROM noice_tippers_final_raw;
ALTER MATERIALIZED VIEW noice_tippers_final OWNER TO k3l_user;
GRANT SELECT ON TABLE noice_tippers_final TO k3l_readonly;
CREATE INDEX noice_tippers_final_fid_idx ON noice_tippers_final (fid);

DROP TABLE IF EXISTS noice_all_txs CASCADE;
CREATE TABLE noice_all_txs (
    id uuid NOT NULL,
    from_fid bigint NOT NULL,
    to_fid bigint NOT NULL,
    token_address text NOT NULL,
    amount numeric NOT NULL,
    status text NOT NULL,
    type text NOT NULL,
    tx_hash text NOT NULL,
    action_reference_id text NOT NULL,
    idempotency_key text NOT NULL,
    raw_payload jsonb,
    created_at timestamp with time zone NOT NULL,
    chain_id bigint NOT NULL
);
ALTER TABLE noice_all_txs OWNER TO k3l_user;
GRANT SELECT ON TABLE noice_all_txs TO k3l_readonly;
-- \COPY noice_all_txs FROM 'all_transactions.csv' (FORMAT CSV, HEADER MATCH);
CREATE INDEX noice_all_txs_tx_hash_idx ON noice_all_txs (tx_hash);

DROP MATERIALIZED VIEW IF EXISTS noice_txs CASCADE;
CREATE MATERIALIZED VIEW noice_txs AS
SELECT DISTINCT
    id,
    from_fid,
    to_fid,
    token_address,
    amount,
    status,
    type,
    tx_hash,
    action_reference_id,
    idempotency_key,
    raw_payload,
    created_at,
    chain_id
FROM noice_all_txs
ORDER BY tx_hash;
ALTER MATERIALIZED VIEW noice_txs OWNER TO k3l_user;
GRANT SELECT ON TABLE noice_txs TO k3l_readonly;
CREATE INDEX noice_txs_tx_hash_idx ON noice_txs (tx_hash);

DROP MATERIALIZED VIEW IF EXISTS noice_tipping_actions CASCADE;
CREATE MATERIALIZED VIEW noice_tipping_actions AS
WITH a AS (
    SELECT
        from_fid,
        to_fid,
        type,
        CASE
            WHEN type = 'comment'
                THEN json_value(raw_payload, '$.data.parent_hash')
            WHEN type IN ('like', 'recast')
                THEN coalesce(
                    json_value(raw_payload, '$.data.cast.hash'),
                    json_value(raw_payload, '$.data.hash')
                )
        END AS cast_hash
    FROM noice_txs
    WHERE type IN ('comment', 'like', 'recast') AND raw_payload IS NOT NULL
)

SELECT from_fid, to_fid, type, cast_hash
FROM a
WHERE cast_hash IS NOT NULL;
ALTER MATERIALIZED VIEW noice_tipping_actions OWNER TO k3l_user;
GRANT SELECT ON TABLE noice_tipping_actions TO k3l_readonly;
CREATE INDEX noice_tipping_actions_cast_hash_idx ON noice_tipping_actions (cast_hash);
CREATE INDEX noice_tipping_actions_from_fid_idx ON noice_tipping_actions (from_fid, to_fid, type);
CREATE INDEX noice_tipping_actions_to_fid_idx ON noice_tipping_actions (to_fid, from_fid, type);

DROP VIEW IF EXISTS noice_tipping_stats CASCADE;
CREATE VIEW noice_tipping_stats AS
SELECT
    from_fid AS fid,
    count(*) AS num_tips,
    count(DISTINCT to_fid) AS num_tipped_fids,
    array_agg(DISTINCT to_fid) AS tipped_fids
FROM noice_tipping_actions
GROUP BY from_fid;
ALTER VIEW noice_tipping_stats OWNER TO k3l_user;
GRANT SELECT ON TABLE noice_tipping_stats TO k3l_readonly;

DROP VIEW IF EXISTS noice_gt CASCADE;
CREATE VIEW noice_gt AS
SELECT
    i,
    v
FROM globaltrust
WHERE strategy_id = 9 AND date = '2025-07-01';
ALTER VIEW noice_gt OWNER TO k3l_user;
GRANT SELECT ON TABLE noice_gt TO k3l_readonly;

DROP TABLE IF EXISTS noice_variants_raw CASCADE;
CREATE TABLE noice_variants_raw (
    liked integer NOT NULL,
    casted integer NOT NULL,
    recasted integer NOT NULL,
    replied integer NOT NULL,
    quoted integer NOT NULL
);
ALTER TABLE noice_variants_raw OWNER TO k3l_user;
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
ALTER TABLE noice_variants OWNER TO k3l_user;
GRANT SELECT ON TABLE noice_variants TO k3l_readonly;

DROP VIEW IF EXISTS noice_tipper_scores CASCADE;
CREATE VIEW noice_tipper_scores AS
SELECT DISTINCT
    t.fid,
    gt.v AS score,
    t.total_amount_across_tokens,
    t.tipped_fids,
    coalesce((
        WITH fids (i) AS (SELECT unnest(t.tipped_fids))

        SELECT sum(cgt.v)
        FROM noice_gt AS cgt
        INNER JOIN fids ON cgt.i = fids.i
    ), 0) AS tipped_fids_openrank_score
FROM noice_tippers_final AS t
LEFT JOIN noice_gt AS gt ON t.fid = gt.i;
ALTER VIEW noice_tipper_scores OWNER TO k3l_user;
GRANT SELECT ON TABLE noice_tipper_scores TO k3l_readonly;

-- noice-tipper-scores.csv
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
    AND timestamp < '2025-07-01T00:00:00Z';
ALTER VIEW noice_candidate_casts OWNER TO k3l_user;
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
        AND timestamp < '2025-07-01T00:00:00Z'
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
        AND action_ts < '2025-07-01T00:00:00Z'
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
ALTER MATERIALIZED VIEW noice_candidate_cast_actions OWNER TO k3l_user;
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
    count(DISTINCT ca.fid) AS num_tippers,
    array_agg(DISTINCT ca.fid) AS tippers
-- FROM noice_candidate_casts AS c
FROM ca -- ON c.hash = ca.hash
INNER JOIN noice_tipper_scores AS cas ON ca.fid = cas.fid
GROUP BY ca.weights, ca.hash
HAVING sum(ca.combined_weight * cas.score) > 0;
ALTER MATERIALIZED VIEW noice_casts_dry OWNER TO k3l_user;
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
    cs.tippers,
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
ALTER MATERIALIZED VIEW noice_casts_hydrated OWNER TO k3l_user;
GRANT SELECT ON TABLE noice_casts_hydrated TO k3l_readonly;
CREATE INDEX noice_casts_hydrated_weights_rank_idx
ON noice_casts_hydrated (weights, rank);
CREATE INDEX noice_casts_hydrated_fid_idx ON noice_casts_hydrated (fid);
CREATE INDEX noice_casts_hydrated_hash_idx ON noice_casts_hydrated (hash);

DROP VIEW IF EXISTS noice_casts_hydrated_10k CASCADE;
CREATE VIEW noice_casts_hydrated_10k AS
SELECT
    c.weights,
    c.rank,
    c.score,
    c.num_tippers,
    c.tippers,
    c.hash,
    c.fid,
    coalesce(f.count, 0) AS follower_count,
    c.username,
    c.timestamp,
    c.parent_hash,
    c.parent_url,
    c.root_parent_hash,
    c.root_parent_url,
    c.text
FROM noice_casts_hydrated AS c
LEFT OUTER JOIN k3l_follower_counts AS f ON c.fid = f.fid
WHERE c.weights = 'L1C0R2Y2Q3' AND c.rank <= 10000;
ALTER VIEW noice_casts_hydrated_10k OWNER TO k3l_user;
GRANT SELECT ON TABLE noice_casts_hydrated_10k TO k3l_readonly;

-- noice-casts-hydrated-10k.csv
SELECT
    weights,
    rank,
    score,
    num_tippers,
    tippers,
    hash,
    fid,
    follower_count,
    username,
    timestamp,
    parent_hash,
    parent_url,
    root_parent_hash,
    root_parent_url,
    text
FROM noice_casts_hydrated_10k;

DROP VIEW IF EXISTS noice_casts_dry_ranked CASCADE;
CREATE VIEW noice_casts_dry_ranked AS
SELECT
    weights,
    hash,
    fid,
    score,
    num_tippers,
    tippers,
    rank
FROM noice_casts_hydrated;
ALTER VIEW noice_casts_dry_ranked OWNER TO k3l_user;
GRANT SELECT ON TABLE noice_casts_dry_ranked TO k3l_readonly;

DROP VIEW IF EXISTS noice_casts_dry_ranked_10k CASCADE;
CREATE VIEW noice_casts_dry_ranked_10k AS
SELECT
    weights,
    hash,
    fid,
    score,
    num_tippers,
    tippers,
    rank
FROM noice_casts_dry_ranked
WHERE rank <= 10000;
ALTER VIEW noice_casts_dry_ranked_10k OWNER TO k3l_user;
GRANT SELECT ON TABLE noice_casts_dry_ranked_10k TO k3l_readonly;

-- noice-casts-dry-ranked.csv
SELECT
    weights,
    hash,
    fid,
    score,
    num_tippers,
    tippers,
    rank
FROM noice_casts_dry_ranked
WHERE weights = 'L1C0R2Y2Q3'
ORDER BY rank;

DROP VIEW IF EXISTS noice_top_creators CASCADE;
CREATE VIEW noice_top_creators AS
WITH creators AS (
    SELECT
        c.weights,
        c.fid,
        p.username,
        count(*) AS cast_count,
        array_agg(c.rank) AS cast_ranks,
        sum(c.score) AS cast_score_total,
        array_length(array_union_agg(c.tippers), 1) AS tipper_count,
        array_union_agg(c.tippers) AS tippers
    FROM noice_casts_dry_ranked_10k AS c
    INNER JOIN neynarv3.profiles AS p ON c.fid = p.fid
    GROUP BY c.weights, c.fid, p.username
)

SELECT
    cr.weights,
    cr.fid,
    cr.username,
    cr.cast_count,
    cr.cast_ranks,
    cr.cast_score_total,
    cr.tipper_count,
    cr.tippers,
    (
        WITH tippers (i) AS (SELECT unnest(cr.tippers))

        SELECT sum(tgt.v)
        FROM noice_gt AS tgt
        INNER JOIN tippers USING (i)
    ) AS tipper_openrank_score_total,
    coalesce(gt.v, 0) AS openrank_score,
    coalesce(f.count, 0) AS follower_count
FROM creators AS cr
LEFT OUTER JOIN noice_gt AS gt
    ON
        cr.fid = gt.i
LEFT OUTER JOIN k3l_follower_counts AS f ON cr.fid = f.fid;
ALTER VIEW noice_top_creators OWNER TO k3l_user;
GRANT SELECT ON TABLE noice_top_creators TO k3l_readonly;

-- noice-top-creators.csv
SELECT
    weights,
    fid,
    username,
    cast_count,
    openrank_score,
    cast_ranks,
    cast_score_total,
    tipper_count,
    tippers,
    tipper_openrank_score_total,
    follower_count
FROM noice_top_creators
WHERE weights = 'L1C0R2Y2Q3'
ORDER BY cast_count DESC;

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
ALTER VIEW noice_top_tippers OWNER TO k3l_user;
GRANT SELECT ON TABLE noice_top_tippers TO k3l_readonly;

-- TODO(ek) - merge noice_tippers_final into noice_tipper_scores above

-- noice-top-tippers.csv
SELECT
    t.weights,
    t.fid,
    t.username,
    t.interaction_count,
    t.creator_count,
    t.creators,
    (
        WITH creators (i) AS (SELECT unnest(t.creators))

        SELECT sum(cgt.v)
        FROM noice_gt AS cgt
        INNER JOIN creators USING (i)
    ) AS creator_openrank_score_total,
    coalesce(gt.v, 0) AS openrank_score,
    coalesce(f.count, 0) AS follower_count,
    ft.num_tips,
    ft.num_tipped_fids,
    coalesce((
        WITH fids (i) AS (SELECT unnest(ft.tipped_fids))

        SELECT sum(cgt2.v)
        FROM noice_gt AS cgt2
        INNER JOIN fids USING (i)
    ), 0) AS tipped_fids_openrank_score,
    ft.tipped_fids
FROM noice_top_tippers AS t
LEFT OUTER JOIN noice_gt AS gt
    ON
        t.fid = gt.i
LEFT OUTER JOIN k3l_follower_counts_matview AS f ON t.fid = f.fid
LEFT OUTER JOIN noice_tipping_stats AS ft ON t.fid = ft.fid
WHERE t.weights = 'L1C0R2Y2Q3'
ORDER BY creator_openrank_score_total DESC;
