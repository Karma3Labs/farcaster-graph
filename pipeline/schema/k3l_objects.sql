
CREATE TABLE IF NOT EXISTS k3l_recent_parent_casts (
    id bigint NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at timestamp without time zone,
    "timestamp" timestamp without time zone NOT NULL,
    fid bigint NOT NULL,
    hash bytea NOT NULL,
    parent_hash bytea,
    parent_fid bigint,
    parent_url text,
    text text NOT NULL,
    embeds jsonb DEFAULT '{}'::jsonb NOT NULL,
    mentions bigint[] DEFAULT '{}'::bigint[] NOT NULL,
    mentions_positions smallint[] DEFAULT '{}'::smallint[] NOT NULL,
    root_parent_hash bytea,
    root_parent_url text
);

CREATE INDEX IF NOT EXISTS k3l_recent_parent_casts_hash_idx
    ON public.k3l_recent_parent_casts USING btree (hash);

CREATE UNIQUE INDEX IF NOT EXISTS k3l_recent_parent_casts_idx
    ON public.k3l_recent_parent_casts USING btree (id);

CREATE INDEX IF NOT EXISTS k3l_recent_parent_casts_fid_timestamp_index
    ON public.k3l_recent_parent_casts USING btree
    (fid ASC NULLS LAST, "timestamp" ASC NULLS LAST);

CREATE INDEX IF NOT EXISTS k3l_recent_parent_casts_parent_hash_parent_fid_index
    ON public.k3l_recent_parent_casts USING btree
    (parent_hash ASC NULLS LAST, parent_fid ASC NULLS LAST)
    WHERE parent_hash IS NOT NULL AND parent_fid IS NOT NULL;

CREATE INDEX IF NOT EXISTS k3l_recent_parent_casts_hash_parent_url_index
    ON public.k3l_recent_parent_casts USING btree
    (hash ASC NULLS LAST, parent_url ASC NULLS LAST)
    WHERE parent_url IS NOT NULL;

CREATE INDEX IF NOT EXISTS k3l_recent_parent_casts_hash_timestamp_index
    ON public.k3l_recent_parent_casts USING btree
    (hash ASC NULLS LAST, "timestamp" ASC NULLS LAST);

CREATE INDEX IF NOT EXISTS k3l_recent_parent_casts_hash_root_parent_url_index
    ON public.k3l_recent_parent_casts USING btree
    (hash ASC NULLS LAST, root_parent_url ASC NULLS LAST)
    WHERE root_parent_url IS NOT NULL;

------------------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS k3l_cast_action (
  fid bigint NOT NULL,
  cast_hash bytea NOT NULL,
  casted int NOT NULL,
  replied int NOT NULL,
  recasted int NOT NULL,
  liked int NOT NULL,
  action_ts timestamp without time zone NOT NULL,
  created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  CONSTRAINT k3l_cast_action_cast_hash_action_ts_pk PRIMARY KEY (cast_hash, action_ts, fid)
)
PARTITION BY RANGE (action_ts);

CREATE INDEX IF NOT EXISTS k3l_cast_action_fid_idx ON public.k3l_cast_action 
USING btree(fid);

CREATE INDEX IF NOT EXISTS k3l_cast_action_fid_ts_idx ON public.k3l_cast_action 
USING btree(fid, action_ts);

CREATE INDEX IF NOT EXISTS k3l_cast_action_cast_hash_idx ON public.k3l_cast_action 
USING btree(cast_hash);

CREATE INDEX IF NOT EXISTS k3l_cast_action_timestamp_idx ON public.k3l_cast_action 
USING btree (action_ts);

CREATE UNIQUE IF NOT EXISTS INDEX k3l_cast_action_unique_idx ON public.k3l_cast_action 
USING btree(cast_hash, fid, action_ts);

CREATE TABLE IF NOT EXISTS k3l_cast_action_y2024m04 PARTITION OF k3l_cast_action
    FOR VALUES FROM ('2024-04-01') TO ('2024-05-01');
CREATE TABLE IF NOT EXISTS k3l_cast_action_y2024m05 PARTITION OF k3l_cast_action
    FOR VALUES FROM ('2024-05-01') TO ('2024-06-01');
CREATE TABLE IF NOT EXISTS k3l_cast_action_y2024m06 PARTITION OF k3l_cast_action
    FOR VALUES FROM ('2024-06-01') TO ('2024-07-01');
CREATE TABLE IF NOT EXISTS k3l_cast_action_y2024m07 PARTITION OF k3l_cast_action
    FOR VALUES FROM ('2024-07-01') TO ('2024-08-01'); 
CREATE TABLE IF NOT EXISTS k3l_cast_action_y2024m08 PARTITION OF k3l_cast_action
    FOR VALUES FROM ('2024-08-01') TO ('2024-09-01');
CREATE TABLE IF NOT EXISTS k3l_cast_action_y2024m09 PARTITION OF k3l_cast_action
    FOR VALUES FROM ('2024-09-01') TO ('2024-10-01'); 
CREATE TABLE IF NOT EXISTS k3l_cast_action_y2024m10 PARTITION OF k3l_cast_action
    FOR VALUES FROM ('2024-10-01') TO ('2024-11-01'); 
CREATE TABLE IF NOT EXISTS k3l_cast_action_y2024m11 PARTITION OF k3l_cast_action
    FOR VALUES FROM ('2024-11-01') TO ('2024-12-01'); 
CREATE TABLE IF NOT EXISTS k3l_cast_action_y2024m12 PARTITION OF k3l_cast_action
    FOR VALUES FROM ('2024-12-01') TO ('2025-01-01'); 
CREATE TABLE IF NOT EXISTS k3l_cast_action_y2025m01 PARTITION OF k3l_cast_action
    FOR VALUES FROM ('2025-01-01') TO ('2025-02-01'); 

------------------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.k3l_channel_fids
(
    channel_id text NOT NULL,
    fid bigint NOT NULL,
    score real NOT NULL,
    rank bigint NOT NULL,
    compute_ts timestamp without time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
    strategy_name text NOT NULL,
    CONSTRAINT k3l_channel_fids_compute_ts_unique PRIMARY KEY (channel_id, fid, compute_ts, strategy_name)
);

CREATE INDEX IF NOT EXISTS k3l_channel_fids_compute_ts_idx
    ON public.k3l_channel_fids USING btree
    (compute_ts ASC NULLS LAST);

CREATE INDEX IF NOT EXISTS k3l_channel_fids_id_idx
    ON public.k3l_channel_fids USING btree
    (channel_id ASC NULLS LAST, compute_ts ASC NULLS LAST, fid ASC NULLS LAST);

CREATE INDEX IF NOT EXISTS k3l_channel_fids_rank_idx
    ON public.k3l_channel_fids USING btree
    (channel_id ASC NULLS LAST, rank ASC NULLS LAST);

CREATE INDEX IF NOT EXISTS k3l_channel_fids_ts_idx
    ON public.k3l_channel_fids USING btree
    (channel_id ASC NULLS LAST, compute_ts ASC NULLS LAST);

------------------------------------------------------------------------------------

CREATE MATERIALIZED VIEW IF NOT EXISTS public.k3l_channel_rank
AS
 WITH latest_compute AS (
        SELECT max(k3l_channel_fids.compute_ts) AS max_ts,
            k3l_channel_fids.channel_id
           FROM k3l_channel_fids
          GROUP BY k3l_channel_fids.channel_id
        )
 SELECT row_number() OVER () AS pseudo_id,
    cfids.channel_id,
    cfids.fid,
    cfids.score,
    cfids.rank,
    cfids.compute_ts,
    cfids.strategy_name
   FROM k3l_channel_fids cfids
     JOIN latest_compute ON cfids.compute_ts = latest_compute.max_ts AND cfids.channel_id = latest_compute.channel_id
WITH DATA;

CREATE INDEX k3l_channel_rank_ch_idx
    ON public.k3l_channel_rank USING btree (channel_id);

CREATE INDEX k3l_channel_rank_fid_idx
    ON public.k3l_channel_rank USING btree (fid);

CREATE UNIQUE INDEX k3l_channel_rank_idx
    ON public.k3l_channel_rank USING btree (pseudo_id);

CREATE INDEX k3l_channel_rank_rank_idx
    ON public.k3l_channel_rank USING btree (rank);
