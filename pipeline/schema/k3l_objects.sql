CREATE MATERIALIZED VIEW public.k3l_rank AS
 WITH latest_gt AS (
         SELECT max(globaltrust_1.date) AS dt,
            globaltrust_1.strategy_id
           FROM public.globaltrust globaltrust_1
          GROUP BY globaltrust_1.strategy_id
        ), latest_gt_config AS (
         SELECT DISTINCT ON (globaltrust_config.strategy_id) globaltrust_config.strategy_id,
            globaltrust_config.strategy_name
           FROM public.globaltrust_config
          ORDER BY globaltrust_config.strategy_id, globaltrust_config.date DESC
        )
 SELECT row_number() OVER () AS pseudo_id,
    row_number() OVER (PARTITION BY globaltrust.date, globaltrust.strategy_id ORDER BY globaltrust.v DESC) AS rank,
    globaltrust.v AS score,
    globaltrust.i AS profile_id,
    globaltrust.strategy_id,
    latest_gt_config.strategy_name,
    globaltrust.date
   FROM ((public.globaltrust
     JOIN latest_gt_config ON ((globaltrust.strategy_id = latest_gt_config.strategy_id)))
     JOIN latest_gt ON (((globaltrust.strategy_id = latest_gt.strategy_id) AND (globaltrust.date = latest_gt.dt))))
  WITH NO DATA;

CREATE UNIQUE INDEX k3l_rank_idx ON public.k3l_rank USING btree (pseudo_id);

CREATE INDEX k3l_rank_profile_id_strategy_id_idx ON public.k3l_rank USING btree (profile_id, strategy_id);

CREATE INDEX k3l_rank_strategy_id_idx ON public.k3l_rank USING btree (strategy_id)

CREATE INDEX k3l_rank_profile_id_idx ON public.k3l_rank USING btree (profile_id)

------------------------------------------------------------------------------------
CREATE MATERIALIZED VIEW public.k3l_recent_parent_casts AS
SELECT 
	id,
    created_at,
    updated_at,
    deleted_at,
    "timestamp",
    fid,
    hash,
    parent_hash,
    parent_fid,
    parent_url,
    text,
    embeds,
    mentions,
    mentions_positions,
    root_parent_hash,
    root_parent_url
FROM casts
  WHERE casts.parent_hash IS NULL
  AND casts.deleted_at IS NULL
  AND casts.timestamp 
  	BETWEEN now() - interval '5 days'
    		AND now()
WITH NO DATA;

CREATE INDEX k3l_recent_parent_casts_hash_idx ON public.k3l_recent_parent_casts USING btree (hash);

CREATE UNIQUE INDEX k3l_recent_parent_casts_idx ON public.k3l_recent_parent_casts USING btree (id);
------------------------------------------------------------------------------------

CREATE TABLE k3l_cast_action (
  fid bigint NOT NULL,
  cast_hash bytea NOT NULL,
  casted int NOT NULL,
  replied int NOT NULL,
  recasted int NOT NULL,
  liked int NOT NULL,
  action_ts timestamp without time zone NOT NULL,
  created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
)
PARTITION BY RANGE (action_ts);

CREATE INDEX k3l_cast_action_fid_idx ON public.k3l_cast_action 
USING btree(fid);

CREATE INDEX k3l_cast_action_cast_hash_idx ON public.k3l_cast_action 
USING btree(cast_hash);

CREATE INDEX k3l_cast_action_timestamp_idx ON public.k3l_cast_action 
USING btree (action_ts);

CREATE UNIQUE INDEX k3l_cast_action_unique_idx ON public.k3l_cast_action 
USING btree(cast_hash, fid, action_ts);

CREATE TABLE k3l_cast_action_y2024m04 PARTITION OF k3l_cast_action
    FOR VALUES FROM ('2024-04-01') TO ('2024-05-01');
CREATE TABLE k3l_cast_action_y2024m05 PARTITION OF k3l_cast_action
    FOR VALUES FROM ('2024-05-01') TO ('2024-06-01');
CREATE TABLE k3l_cast_action_y2024m06 PARTITION OF k3l_cast_action
    FOR VALUES FROM ('2024-06-01') TO ('2024-07-01');
CREATE TABLE k3l_cast_action_y2024m07 PARTITION OF k3l_cast_action
    FOR VALUES FROM ('2024-07-01') TO ('2024-08-01'); 
CREATE TABLE k3l_cast_action_y2024m08 PARTITION OF k3l_cast_action
    FOR VALUES FROM ('2024-08-01') TO ('2024-09-01');
CREATE TABLE k3l_cast_action_y2024m09 PARTITION OF k3l_cast_action
    FOR VALUES FROM ('2024-09-01') TO ('2024-10-01'); 
CREATE TABLE k3l_cast_action_y2024m10 PARTITION OF k3l_cast_action
    FOR VALUES FROM ('2024-10-01') TO ('2024-11-01'); 
CREATE TABLE k3l_cast_action_y2024m11 PARTITION OF k3l_cast_action
    FOR VALUES FROM ('2024-11-01') TO ('2024-12-01'); 
CREATE TABLE k3l_cast_action_y2024m12 PARTITION OF k3l_cast_action
    FOR VALUES FROM ('2024-12-01') TO ('2025-01-01'); 
CREATE TABLE k3l_cast_action_y2025m01 PARTITION OF k3l_cast_action
    FOR VALUES FROM ('2025-01-01') TO ('2025-02-01'); 

------------------------------------------------------------------------------------

