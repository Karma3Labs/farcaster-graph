-- *****IMPORTANT NOTE****: ON EIGEN8
SET ROLE neynar;
CREATE INDEX CONCURRENTLY casts_timestamp_index ON neynarv2.casts USING btree ("timestamp");
CREATE INDEX CONCURRENTLY casts_root_parent_url_idx ON neynarv2.casts USING btree (root_parent_url);
CREATE INDEX CONCURRENTLY casts_deleted_at_idx ON neynarv2.casts USING btree (deleted_at);
CREATE INDEX CONCURRENTLY follows_fid_target_timestamp_idx ON neynarv3.follows(fid, target_fid, timestamp) WHERE deleted_at IS NULL;
CREATE INDEX CONCURRENTLY reactions_type_target_timestamp_idx ON neynarv2.reactions(reaction_type, target_fid, timestamp) WHERE target_fid IS NOT NULL;
CREATE INDEX CONCURRENTLY reactions_timestamp_type_idx ON neynarv2.reactions("timestamp", reaction_type) WHERE target_fid IS NOT NULL;
CREATE INDEX CONCURRENTLY reactions_target_hash_deleted_at_timestamp_idx ON neynarv2.reactions 
				USING btree (target_hash, deleted_at, "timestamp" DESC) WITH (deduplicate_items='false');
----------------------------------------------------------------------------------------------------------------

SET ROLE k3l_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT,REFERENCES ON TABLES TO k3l_readonly;
----------------------------------------------------------------------------------------------------------------

CREATE UNLOGGED TABLE public.cache (
    cache_key varchar(255),
    cache_value jsonb,
    expires_at timestamp with time zone,
    insert_ts timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    update_ts timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT cache_pkey PRIMARY KEY (cache_key)
);
GRANT SELECT,INSERT, UPDATE, DELETE, REFERENCES ON public.k3l_recent_frame_interaction TO k3l_readonly;

----------------------------------------------------------------------------------------------------------------

CREATE UNLOGGED TABLE public.localtrust (
    strategy_id integer,
    i character varying(255),
    j character varying(255),
    v double precision,
    date date
);
----------------------------------------------------------------------------------------------------------------

CREATE TABLE public.localtrust_stats (
    date date,
    strategy_id_1_row_count bigint,
    strategy_id_1_mean double precision,
    strategy_id_1_stddev double precision,
    strategy_id_1_range double precision,
    strategy_id_3_row_count bigint,
    strategy_id_3_mean double precision,
    strategy_id_3_stddev double precision,
    strategy_id_3_range double precision,
    insert_ts timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);
----------------------------------------------------------------------------------------------------------------

CREATE UNLOGGED TABLE public.globaltrust (
    strategy_id integer,
    i bigint,
    v real,
    date date DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE ONLY public.globaltrust
    ADD CONSTRAINT globaltrust_strategy_name_date_i_unique UNIQUE (strategy_id, date, i);

CREATE INDEX globaltrust_id_idx ON public.globaltrust USING btree (strategy_id);

----------------------------------------------------------------------------------------------------------------

CREATE TABLE public.globaltrust_config (
	strategy_id int4 NOT NULL,
	strategy_name varchar(255) NOT NULL,
	pretrust text NULL,
	localtrust text NULL,
	alpha float4 NULL,
	"date" date NOT NULL DEFAULT CURRENT_TIMESTAMP,
	CONSTRAINT globaltrust_config_pkey PRIMARY KEY (strategy_id, date)
);

INSERT INTO public.globaltrust_config (strategy_id, strategy_name, pretrust, localtrust, alpha, date) VALUES
(1, 'follows', 'pretrustAllEqually', 'existingConnections', 0.5, '2023-12-07'),
(3, 'engagement', 'pretrustAllEqually', 'l1rep6rec3m12enhancedConnections', 0.5, '2023-12-07'),
(5, 'activity', 'pretrustAllEqually', 'l1rep1rec1m1enhancedConnections', 0.5, '2023-12-07'),
(7, 'OG circles', 'pretrustSpecificUsernames', 'existingConnections', 0.5, '2023-12-07'),
(9, 'OG engagement', 'pretrustSpecificUsernames', 'l1rep6rec3m12enhancedConnections', 0.5, '2023-12-07'),
(11, 'OG activity', 'pretrustSpecificUsernames', 'l1rep1rec1m1enhancedConnections', 0.5, '2023-12-07'),
(1, 'follows', 'pretrustTopTier', 'existingConnections', 0.5, '2024-03-14'),
(3, 'engagement', 'pretrustTopTier', 'l1rep6rec3m12enhancedConnections', 0.5, '2024-03-14');

----------------------------------------------------------------------------------------------------------------

CREATE TABLE public.pretrust (
    fid bigint NOT NULL,
    fname text NOT NULL,
    fid_active_tier integer NOT NULL,
    fid_active_tier_name text NOT NULL,
    data_source character varying(32) DEFAULT 'Dune'::character varying,
    insert_ts timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE ONLY public.pretrust
    ADD CONSTRAINT fid_insert_ts_unique UNIQUE (fid, insert_ts);
----------------------------------------------------------------------------------------------------------------

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
CREATE TABLE public.k3l_url_labels (
    url_id bigint NOT NULL,
    url text NOT NULL,
    category character varying(32),
    insert_ts timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    processed_ts timestamp without time zone,
    latest_cast_dt timestamp with time zone NOT NULL,
    earliest_cast_dt timestamp with time zone NOT NULL,
    parsed_ts timestamp without time zone,
    scheme text,
    domain text,
    subdomain text,
    tld character varying(32),
    path text
);

ALTER TABLE public.k3l_url_labels ALTER COLUMN url_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.k3l_url_labels_url_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

ALTER TABLE ONLY public.k3l_url_labels
    ADD CONSTRAINT k3l_url_labels_pkey PRIMARY KEY (url_id);
    
ALTER TABLE ONLY public.k3l_url_labels
    ADD CONSTRAINT k3l_url_labels_url_unique UNIQUE (url);
    
CREATE INDEX k3l_url_labels_earliest_cast_dt_idx ON public.k3l_url_labels USING btree (earliest_cast_dt);

CREATE INDEX k3l_url_labels_latest_cast_dt_idx ON public.k3l_url_labels USING btree (latest_cast_dt);

------------------------------------------------------------------------------------
CREATE TABLE public.k3l_cast_embed_url_mapping (
    url_id bigint,
    cast_id bigint
);

CREATE INDEX k3l_cast_embed_url_mapping_cast_id_index ON public.k3l_cast_embed_url_mapping USING btree (cast_id);
CREATE INDEX k3l_cast_embed_url_mapping_url_id_index ON public.k3l_cast_embed_url_mapping USING btree (url_id);

ALTER TABLE ONLY public.k3l_cast_embed_url_mapping
    ADD CONSTRAINT k3l_cast_embed_url_mapping_cast_id_fkey FOREIGN KEY (cast_id) REFERENCES public.casts(id);
    
ALTER TABLE ONLY public.k3l_cast_embed_url_mapping
    ADD CONSTRAINT k3l_cast_embed_url_mapping_url_id_fkey FOREIGN KEY (url_id) REFERENCES public.k3l_url_labels(url_id);

------------------------------------------------------------------------------------
CREATE MATERIALIZED VIEW public.k3l_recent_frame_interaction AS
 SELECT casts.fid,
    'cast'::text AS action_type,
    urls.url_id,
    ((((((urls.scheme || '://'::text) ||
        CASE
            WHEN (urls.subdomain <> ''::text) THEN (urls.subdomain || '.'::text)
            ELSE ''::text
        END) || urls.domain) || '.'::text) || (urls.tld)::text) || urls.path) AS url
   FROM ((public.casts
     JOIN public.k3l_cast_embed_url_mapping url_map ON ((url_map.cast_id = casts.id) AND (casts.deleted_at IS NULL)))
     JOIN public.k3l_url_labels urls ON (((urls.url_id = url_map.url_id) AND ((urls.category)::text = 'frame'::text))))
  WHERE public.casts.timestamp BETWEEN now() - interval '30 days' AND now()
  GROUP BY casts.fid, 'cast'::text, urls.url_id, ((((((urls.scheme || '://'::text) ||
        CASE
            WHEN (urls.subdomain <> ''::text) THEN (urls.subdomain || '.'::text)
            ELSE ''::text
        END) || urls.domain) || '.'::text) || (urls.tld)::text) || urls.path)
UNION
 SELECT reactions.fid,
    'recast'::text AS action_type,
    urls.url_id,
    ((((((urls.scheme || '://'::text) ||
        CASE
            WHEN (urls.subdomain <> ''::text) THEN (urls.subdomain || '.'::text)
            ELSE ''::text
        END) || urls.domain) || '.'::text) || (urls.tld)::text) || urls.path) AS url
   FROM (((public.casts
     JOIN public.reactions 
        ON (((reactions.target_hash = casts.hash) AND (reactions.reaction_type = 2) AND (casts.deleted_at IS NULL))))
     JOIN public.k3l_cast_embed_url_mapping url_map ON ((casts.id = url_map.cast_id)))
     JOIN public.k3l_url_labels urls ON (((urls.url_id = url_map.url_id) AND ((urls.category)::text = 'frame'::text))))
    WHERE public.casts.timestamp BETWEEN now() - interval '30 days'AND now()
  GROUP BY reactions.fid, 'recast'::text, urls.url_id, ((((((urls.scheme || '://'::text) ||
        CASE
            WHEN (urls.subdomain <> ''::text) THEN (urls.subdomain || '.'::text)
            ELSE ''::text
        END) || urls.domain) || '.'::text) || (urls.tld)::text) || urls.path)
UNION
 SELECT reactions.fid,
    'like'::text AS action_type,
    urls.url_id,
    ((((((urls.scheme || '://'::text) ||
        CASE
            WHEN (urls.subdomain <> ''::text) THEN (urls.subdomain || '.'::text)
            ELSE ''::text
        END) || urls.domain) || '.'::text) || (urls.tld)::text) || urls.path) AS url
   FROM (((public.casts
     JOIN public.reactions 
        ON (((reactions.target_hash = casts.hash) AND (reactions.reaction_type = 1) AND (casts.deleted_at IS NULL))))
     JOIN public.k3l_cast_embed_url_mapping url_map ON ((casts.id = url_map.cast_id)))
     JOIN public.k3l_url_labels urls ON (((urls.url_id = url_map.url_id) AND ((urls.category)::text = 'frame'::text))))
    WHERE public.casts.timestamp BETWEEN now() - interval '30 days' AND now()
  GROUP BY reactions.fid, 'like'::text, urls.url_id, ((((((urls.scheme || '://'::text) ||
        CASE
            WHEN (urls.subdomain <> ''::text) THEN (urls.subdomain || '.'::text)
            ELSE ''::text
        END) || urls.domain) || '.'::text) || (urls.tld)::text) || urls.path)
  WITH NO DATA;

CREATE UNIQUE INDEX k3l_recent_frame_interaction_fid_type_url_unq 
ON public.k3l_recent_frame_interaction 
USING btree (fid, action_type, url_id) NULLS NOT DISTINCT;

CREATE INDEX k3l_recent_frame_interaction_url_id_idx ON public.k3l_recent_frame_interaction USING btree (url_id);

CREATE INDEX k3l_recent_frame_interaction_fid_idx ON public.k3l_recent_frame_interaction USING btree (fid);

CREATE INDEX k3l_recent_frame_interaction_url_idx ON public.k3l_recent_frame_interaction USING btree (url);

REFRESH MATERIALIZED VIEW k3l_recent_frame_interaction WITH DATA;

GRANT SELECT,REFERENCES ON public.k3l_recent_frame_interaction TO k3l_readonly;

------------------------------------------------------------------------------------
CREATE MATERIALIZED VIEW public.k3l_recent_parent_casts AS
SELECT 
	*
FROM casts
  WHERE casts.parent_hash IS NULL
  AND casts.deleted_at IS NULL
  AND casts.timestamp 
  	BETWEEN now() - interval '30 days'
    		AND now()
WITH NO DATA;

CREATE INDEX k3l_recent_parent_casts_hash_idx ON public.k3l_recent_parent_casts USING btree (hash);

CREATE UNIQUE INDEX k3l_recent_parent_casts_idx ON public.k3l_recent_parent_casts USING btree (id);

GRANT SELECT,REFERENCES ON public.k3l_recent_parent_casts TO k3l_readonly;

------------------------------------------------------------------------------------

CREATE TABLE public.k3l_channel_fids (
  channel_id text NOT NULL,
  fid bigint NOT NULL,
  score real NOT NULL,
  rank bigint NOT NULL,
  compute_ts timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  strategy_name text NOT NULL
 );

CREATE INDEX k3l_channel_fids_id_idx ON public.k3l_channel_fids USING btree(channel_id, compute_ts, fid);

CREATE INDEX k3l_channel_fids_ch_strat_ts_idx ON public.k3l_channel_fids USING btree (channel_id, strategy_name, compute_ts)

CREATE INDEX k3l_channel_fids_strat_ts_idx ON public.k3l_channel_fids USING btree (strategy_name, compute_ts)

------------------------------------------------------------------------------------
CREATE TYPE channel_rank_status AS ENUM ('pending', 'inprogress', 'completed', 'errored', 'terminated');

CREATE TABLE public.k3l_channel_rank_log (
  run_id text NOT NULL,
  num_days int2 NOT NULL,
  channel_id text NOT NULL,
  batch_id int2 NOT NULL,
  rank_status channel_rank_status DEFAULT 'pending',
  num_fids int4 NULL,
  inactive_seeds int8[] NULL,
  elapsed_time_ms bigint NULL,
  run_ts timestamp with time zone DEFAULT CURRENT_TIMESTAMP
) PARTITION BY RANGE (run_ts);

CREATE INDEX k3l_channel_rank_log_run_idx ON public.k3l_channel_rank_log USING btree (run_id);

CREATE TABLE k3l_channel_rank_log_y2025m03 PARTITION OF k3l_channel_rank_log
    FOR VALUES FROM ('2025-03-01') TO ('2025-04-01');


CREATE TABLE k3l_channel_rank_log_y2025m04 PARTITION OF k3l_channel_rank_log
    FOR VALUES FROM ('2025-04-01') TO ('2025-05-01');


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

CREATE INDEX k3l_cast_action_fid_ts_idx ON public.k3l_cast_action 
USING btree(fid, action_ts);

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
CREATE TABLE k3l_cast_action_y2025m02 PARTITION OF k3l_cast_action
    FOR VALUES FROM ('2025-02-01') TO ('2025-03-01');
CREATE TABLE k3l_cast_action_y2025m03 PARTITION OF k3l_cast_action
    FOR VALUES FROM ('2025-03-01') TO ('2025-04-01');
CREATE TABLE k3l_cast_action_y2025m04 PARTITION OF k3l_cast_action
    FOR VALUES FROM ('2025-04-01') TO ('2025-05-01');

-- Added on 2025-04-02 - Vj
ALTER TABLE k3l_cast_action ADD COLUMN channel_id TEXT NULL;

------------------------------------------------------------------------------------

CREATE TABLE public.k3l_cast_action_v1 (
    channel_id TEXT NULL,
    fid bigint NOT NULL,
    cast_hash bytea NOT NULL,
    casted integer NOT NULL,
    replied integer NOT NULL,
    recasted integer NOT NULL,
    liked integer NOT NULL,
    action_ts timestamp without time zone NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
	UNIQUE(cast_hash, fid, action_ts)
)
PARTITION BY RANGE (action_ts);

CREATE INDEX k3l_cast_action_v1_covering_idx ON k3l_cast_action_v1
    USING btree (cast_hash, action_ts, fid) INCLUDE (casted, replied, recasted, liked);
CREATE INDEX k3l_cast_action_v1_fid_idx ON k3l_cast_action_v1 USING btree (fid);
CREATE INDEX k3l_cast_action_v1_fid_ts_idx ON k3l_cast_action_v1 USING btree (fid, action_ts);
CREATE INDEX k3l_cast_action_v1_timestamp_idx ON k3l_cast_action_v1 USING btree (action_ts);
CREATE INDEX k3l_cast_action_v1_ch_idx ON k3l_cast_action_v1 USING btree (channel_id);
GRANT SELECT,REFERENCES ON TABLE public.k3l_cast_action_v1 TO k3l_readonly;

CREATE TABLE k3l_cast_action_v1_y2024m09 PARTITION OF k3l_cast_action_v1
    FOR VALUES FROM ('2024-09-01') TO ('2024-10-01');
CREATE TABLE k3l_cast_action_v1_y2024m10 PARTITION OF k3l_cast_action_v1
    FOR VALUES FROM ('2024-10-01') TO ('2024-11-01');
CREATE TABLE k3l_cast_action_v1_y2024m11 PARTITION OF k3l_cast_action_v1
    FOR VALUES FROM ('2024-11-01') TO ('2024-12-01');
CREATE TABLE k3l_cast_action_v1_y2024m12 PARTITION OF k3l_cast_action_v1
    FOR VALUES FROM ('2024-12-01') TO ('2025-01-01');
CREATE TABLE k3l_cast_action_v1_y2025m01 PARTITION OF k3l_cast_action_v1
    FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');
CREATE TABLE k3l_cast_action_v1_y2025m02 PARTITION OF k3l_cast_action_v1
    FOR VALUES FROM ('2025-02-01') TO ('2025-03-01');
CREATE TABLE k3l_cast_action_v1_y2025m03 PARTITION OF k3l_cast_action_v1
    FOR VALUES FROM ('2025-03-01') TO ('2025-04-01');
CREATE TABLE k3l_cast_action_v1_y2025m04 PARTITION OF k3l_cast_action_v1
    FOR VALUES FROM ('2025-04-01') TO ('2025-05-01');

-------------------------------------------------
-- *****IMPORTANT NOTE****: ON EIGEN8
CREATE VIEW public.k3l_cast_action AS
    SELECT * FROM k3l_cast_action_v1;

GRANT SELECT,REFERENCES ON VIEW public.k3l_cast_action TO k3l_readonly;
------------------------------------------------------------------------------------


CREATE MATERIALIZED VIEW public.k3l_channel_rank AS
SELECT
 	row_number() OVER () AS pseudo_id,
 	cfids.* 
FROM k3l_channel_fids as cfids
WITH NO DATA;

CREATE UNIQUE INDEX k3l_channel_rank_unq_idx ON public.k3l_channel_rank USING btree (pseudo_id);
CREATE INDEX k3l_channel_rank_rank_idx ON public.k3l_channel_rank USING btree (rank);
CREATE INDEX k3l_channel_rank_fid_idx ON public.k3l_channel_rank USING btree (fid);
CREATE INDEX k3l_channel_rank_ch_strat_idx ON public.k3l_channel_rank USING btree (channel_id, strategy_name);
CREATE INDEX k3l_channel_rank_ch_strat_fid_idx ON public.k3l_channel_rank USING btree (channel_id, strategy_name, fid);
CREATE INDEX k3l_channel_rank_ch_fid_idx ON public.k3l_channel_rank USING btree (channel_id, fid);

GRANT SELECT,REFERENCES ON public.k3l_channel_rank TO k3l_readonly;

------------------------------------------------------------------------------------
CREATE TABLE public.cura_hidden_fids (
    channel_id text NOT NULL,
    hidden_fid int8 NOT NULL,
    hider_fid int8 NOT NULL,
    is_active boolean NOT NULL,
    created_at timestamp with time zone,
    updated_at timestamp with time zone,
    insert_ts timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    update_ts timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX cura_hidden_fids_ch_fid_act_idx
    ON public.cura_hidden_fids USING btree (action, channel_id, hidden_fid, is_active);

GRANT SELECT,REFERENCES ON public.cura_hidden_fids TO k3l_readonly;
-------------------------------------------------------------------------------------
CREATE TABLE public.automod_data (
    created_at timestamp without time zone,
    action text,
    actor text,
    affected_username text,
    affected_userid bigint,
    cast_hash text,
    channel_id text,
    date_iso date
);

CREATE INDEX idx_automod_data_action_ch_userid 
    ON public.automod_data USING btree (action, channel_id, affected_userid);

GRANT SELECT,REFERENCES ON public.automod_data TO k3l_readonly;
-------------------------------------------------------------------------------------
CREATE TABLE public.warpcast_channels_data (
	id text NOT NULL,
	url text NOT NULL,
	name text NOT NULL,
	description text NULL,
	imageurl text NULL,
    headerimageurl text NULL,
	leadfid int8 NULL,
    moderatorfids int8[] NULL,
	createdat timestamp NULL,
	followercount int4 NOT NULL,
    memberfount int4 NOT NULL,
    pinnedfasthash text NULL,
	insert_ts timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);
CREATE UNIQUE INDEX idx_warpcast_channels_data_ch_id_idx ON public.warpcast_channels_data USING btree (id);

GRANT SELECT,REFERENCES ON TABLE public.warpcast_channels_data TO k3l_readonly;

-------------------------------------------------------------------------------------
-- *****IMPORTANT NOTE****: ON EIGEN8
CREATE VIEW public.warpcast_channels_data AS
    SELECT
    channel_id AS id,
    url,
    description,
    image_url AS imageurl,
    lead_fid AS leadfid,
    moderator_fids AS moderatorfids,
    created_at AS createdat,
    follower_count AS followercount,
    "timestamp" AS insert_ts
    FROM
    neynarv2.channels;

GRANT SELECT, REFERENCES ON TABLE public.warpcast_channels_data TO k3l_readonly;

----------------------------------------------
CREATE TABLE public.k3l_top_casters (
	i int8 NOT NULL,
	v float8 NOT NULL,
	date_iso date NOT NULL,
	cast_hash bytea NULL
);
GRANT SELECT,REFERENCES ON TABLE public.k3l_top_casters TO k3l_readonly;

-----------------------------------------

CREATE TABLE public.k3l_top_spammers (
  fid int8 NOT NULL,
  display_name text NOT NULL,
  total_outgoing int8 NOT NULL,
  spammer_score float8 NOT NULL,
  total_parent_casts int8 NOT NULL,
  total_replies_with_parent_hash int8 NOT NULL,
  global_openrank_score float8 NOT NULL,
  global_rank int8 NOT NULL,
  total_global_rank_rows int8 NOT NULL,
  date_iso date NOT NULL
);

GRANT SELECT,REFERENCES ON TABLE public.k3l_top_spammers TO k3l_readonly;

----------------------------------------------------------
CREATE UNLOGGED TABLE public.localtrust_stats_v2 (
    date date,
    strategy_id_row_count bigint,
    strategy_id_mean double precision,
    strategy_id_stddev double precision,
    strategy_id_range double precision,
    strategy_id int8,
    insert_ts timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);

---------------------------------------------------------------
-- Table structure
CREATE TABLE public.pretrust_v2 (
	fid int8 NULL,
	fname text NULL,
	fid_active_tier int4 NULL,
	fid_active_tier_name text NULL,
	data_source varchar(32) NULL,
	insert_ts timestamp NULL,
	strategy_id int8 NULL
);

-- How it was created
-- CREATE TABLE public.pretrust_v2 AS (
-- SELECT * from public.pretrust
-- )

-- ALTER TABLE pretrust_v2
-- ADD COLUMN strategy_id int8;

-- UPDATE pretrust_v2
-- SET strategy_id = 1

-- INSERT INTO pretrust_v2 (fid,fname,fid_active_tier,
-- fid_active_tier_name,data_source,insert_ts,strategy_id)
-- SELECT fid,fname,fid_active_tier,
-- fid_active_tier_name,data_source,insert_ts,3
-- FROM pretrust;

-- UPLOADED THE NEW PRETRUST CSV FROM DUNE QUERY
-- https://dune.com/queries/4005516/6743472
-- SELECT DISTINCT
--     q.fid,
--     fid_info.display_name as fname,
--     q.fid_active_tier,
--     q.fid_active_tier_name,
--     'dune' as data_source,
--     current_timestamp as insert_ts,
--     9 as strategy_id
-- FROM
--     query_3418402 AS q
-- INNER JOIN
--     dune.neynar.dataset_farcaster_warpcast_power_users AS pu
--     ON q.fid = pu.fid
-- LEFT JOIN query_3418402 AS engagement_recieved
--     ON q.fid = engagement_recieved.fid
-- LEFT JOIN dune.neynar.dataset_farcaster_profile_with_addresses AS fid_info
--     ON q.fid = fid_info.fid
-- WHERE
--     q.fid_active_tier IN (2, 3, 4)
-------------------------------------------------
CREATE TABLE public.warpcast_followers (
  fid int8 NOT NULL,
  followedAt bigint NOT NULL,
  insert_ts timestamp without time zone NOT NULL,
  channel_id text NOT NULL
 );
 
CREATE INDEX warpcast_followers_ts_ch_fid_idx ON public.warpcast_followers USING btree (insert_ts, channel_id, fid);
CREATE INDEX warpcast_followers_ch_fid_idx ON public.warpcast_followers USING btree (channel_id, fid);
CREATE INDEX warpcast_followers_ch_id_idx ON public.warpcast_followers USING btree (channel_id);
CREATE INDEX warpcast_followers_fid_idx ON public.warpcast_followers USING btree (fid);

GRANT SELECT,REFERENCES ON TABLE public.warpcast_followers TO k3l_readonly;
-------------------------------------------------
-- *****IMPORTANT NOTE****: ON EIGEN8
CREATE VIEW public.warpcast_followers AS
    SELECT
        fid,
        max(ROUND(EXTRACT(EPOCH FROM (timestamp)),0)) AS followedAt,
        max(timestamp) AS insert_ts,
        channel_id
    FROM
        neynarv2.channel_follows
    WHERE
        deleted_at IS NULL
    GROUP BY
		fid, channel_id;

GRANT SELECT,REFERENCES ON TABLE public.warpcast_followers TO k3l_readonly;
-------------------------------------------------
CREATE TABLE public.warpcast_members (
  fid int8 NOT NULL,
  memberAt bigint NOT NULL,
  insert_ts timestamp without time zone NOT NULL,
  channel_id text NOT NULL
 );

CREATE INDEX warpcast_members_ts_ch_fid_idx ON public.warpcast_members USING btree (insert_ts, channel_id, fid);
CREATE INDEX warpcast_members_ch_fid_idx ON public.warpcast_members USING btree (channel_id, fid);
CREATE INDEX warpcast_members_ch_id_idx ON public.warpcast_members USING btree (channel_id);
CREATE INDEX warpcast_members_fid_idx ON public.warpcast_members USING btree (fid);

GRANT SELECT,REFERENCES ON TABLE public.warpcast_members TO k3l_readonly;

-------------------------------------------------
-- *****IMPORTANT NOTE****: ON EIGEN8
CREATE VIEW public.warpcast_members AS
    SELECT
        fid,
        max(ROUND(EXTRACT(EPOCH FROM (timestamp)),0)) AS memberAt,
        max(timestamp) AS insert_ts,
        channel_id
    FROM
        neynarv2.channel_members
    WHERE
        deleted_at IS NULL
    GROUP BY
		fid, channel_id;

GRANT SELECT,REFERENCES ON TABLE public.warpcast_members TO k3l_readonly;

-------------------------------------------------
-- *****IMPORTANT NOTE****: ON EIGEN8
CREATE VIEW public.verifications AS
    SELECT
        id,
        created_at,
        updated_at,
        deleted_at,
        timestamp,
        fid,
        json_build_object('address', '0x' || encode(address, 'hex')) as claim
    FROM
        neynarv3.verifications
    WHERE
        deleted_at IS NULL;

GRANT SELECT,REFERENCES ON TABLE public.verifications TO k3l_readonly;
-------------------------------------------------------------------------------------
-- *****IMPORTANT NOTE****: ON EIGEN8
CREATE VIEW public.links AS
    SELECT
      id,
      fid,
      target_fid,
      timestamp,
      created_at,
      updated_at,
      deleted_at,
      'follow' as type,
      display_timestamp
    FROM
        neynarv3.follows;

GRANT SELECT, REFERENCES ON TABLE public.links TO k3l_readonly;
-------------------------------------------------

CREATE TABLE k3l_channel_metrics (
    metric_ts   timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    channel_id  TEXT NOT NULL,
    metric      TEXT NOT NULL,
    int_value   INT8,
    float_value NUMERIC,
    insert_ts 	timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
  	UNIQUE(metric_ts, channel_id, metric)
) PARTITION BY RANGE (metric_ts);

GRANT SELECT, REFERENCES ON TABLE public.links TO k3l_readonly;

CREATE OR REPLACE FUNCTION end_week_9amoffset(timestamp, interval)
  RETURNS timestamptz AS $$ 
    SELECT 
            date_trunc('week', $1 + $2 - '9 hours'::interval)  -- force to monday 9am
            - $2 + '9 hours'::interval -- revert force
            + '7 days'::interval - '1 seconds'::interval -- end of week
    $$
  LANGUAGE sql 
  IMMUTABLE;

GRANT EXECUTE ON FUNCTION end_week_9amoffset(timestamp, interval) TO k3l_readonly;


CREATE TABLE k3l_channel_metrics_y2025m01 PARTITION OF k3l_channel_metrics FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');
CREATE TABLE k3l_channel_metrics_y2025m02 PARTITION OF k3l_channel_metrics FOR VALUES FROM ('2025-02-01') TO ('2025-03-01');
CREATE TABLE k3l_channel_metrics_y2025m03 PARTITION OF k3l_channel_metrics FOR VALUES FROM ('2025-03-01') TO ('2025-04-01');
CREATE TABLE k3l_channel_metrics_y2025m04 PARTITION OF k3l_channel_metrics FOR VALUES FROM ('2025-04-01') TO ('2025-05-01');
-------------------------------------------------

CREATE TABLE public.k3l_channel_points_bal (
	fid int8 NOT NULL,
    channel_id text NOT NULL,
	balance numeric NOT NULL,
    latest_earnings numeric NOT NULL,
    latest_score real NOT NULL,
    latest_adj_score real NOT NULL,
    insert_ts timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    update_ts timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX k3l_channel_points_bal_ch_fid_idx ON public.k3l_channel_points_bal USING btree (channel_id, fid);

CREATE INDEX k3l_channel_points_bal_ch_bal_idx ON public.k3l_channel_points_bal USING btree (channel_id, balance);

GRANT SELECT,REFERENCES ON TABLE public.k3l_channel_points_bal TO k3l_readonly;

-------------------------------------------------
CREATE TABLE public.k3l_channel_points_log (
	fid int8 NOT NULL,
  channel_id text NOT NULL,
 	earnings numeric NOT NULL,
  model_name text NOT NULL,
  insert_ts timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
  notes TEXT NULL
) PARTITION BY RANGE (insert_ts);

CREATE INDEX k3l_channel_points_log_ch_fid_idx ON public.k3l_channel_points_log USING btree (channel_id, fid);

CREATE INDEX k3l_channel_points_log_ch_mdl_idx ON public.k3l_channel_points_log USING btree (channel_id, model_name);

CREATE INDEX k3l_channel_points_log_ch_mdl_fid_idx ON public.k3l_channel_points_log USING btree (channel_id, model_name, fid);

CREATE TABLE k3l_channel_points_log_y2024m12 PARTITION OF k3l_channel_points_log
    FOR VALUES FROM ('2024-12-01') TO ('2025-01-01');

CREATE TABLE k3l_channel_points_log_y2025m01 PARTITION OF k3l_channel_points_log
    FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');

CREATE TABLE k3l_channel_points_log_y2025m02 PARTITION OF k3l_channel_points_log
    FOR VALUES FROM ('2025-02-01') TO ('2025-03-01');

CREATE TABLE k3l_channel_points_log_y2025m03 PARTITION OF k3l_channel_points_log
    FOR VALUES FROM ('2025-03-01') TO ('2025-04-01');

CREATE TABLE k3l_channel_points_log_y2025m04 PARTITION OF k3l_channel_points_log
    FOR VALUES FROM ('2025-04-01') TO ('2025-05-01');
-------------------------------------------------
CREATE TABLE public.k3l_channel_tokens_bal (
	fid int8 NOT NULL,
    channel_id text NOT NULL,
	balance bigint NOT NULL,
    latest_earnings bigint NOT NULL,
    insert_ts timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    update_ts timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX k3l_channel_tokens_bal_ch_fid_idx 
    ON public.k3l_channel_tokens_bal USING btree (channel_id, fid);

GRANT SELECT,REFERENCES ON TABLE public.k3l_channel_tokens_bal TO k3l_readonly;

-------------------------------------------------
CREATE TYPE tokens_dist_status AS ENUM ('submitted', 'success', 'failure');
CREATE SEQUENCE tokens_dist_seq;

CREATE TABLE public.k3l_channel_tokens_log (
	fid int8 NOT NULL,
    -- fid_addess is NULL because
    -- .....custody address is nullable in fids table 
    -- .....and not all fids have verified addresses
    -- fid_addess is TYPE TEXT because
    -- .....verfications address is a string in a jsonb column
    -- .....custoday address is bytea but assuming verified address will be used more
    -- .....also viem and other javascript libraries use strings
    fid_address text NULL, 
    channel_id text NOT NULL,
	amt bigint NOT NULL,
    latest_points real NOT NULL,
    points_ts timestamp without time zone NOT NULL,
    dist_id int4 NOT NULL, -- dist_id per channel group
    batch_id int2 NOT NULL, -- batch_id per dist_id
    dist_status tokens_dist_status NULL,
    dist_reason text NULL,
    txn_hash text NULL,
    insert_ts timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    update_ts timestamp with time zone DEFAULT CURRENT_TIMESTAMP
)
PARTITION BY RANGE (points_ts);

CREATE INDEX k3l_channel_tokens_log_dist_idx ON public.k3l_channel_tokens_log USING btree (dist_id);

CREATE INDEX k3l_channel_tokens_log_ch_fid_idx ON public.k3l_channel_tokens_log USING btree (channel_id, fid);

CREATE INDEX k3l_channel_tokens_log_pending_idx ON public.k3l_channel_tokens_log (dist_status) 
    WHERE dist_status != 'success';

CREATE INDEX k3l_channel_tokens_log_hash_idx ON public.k3l_channel_tokens_log USING HASH (txn_hash);

CREATE TABLE k3l_channel_tokens_log_y2024m12 PARTITION OF k3l_channel_tokens_log
    FOR VALUES FROM ('2024-12-01') TO ('2025-01-01');

CREATE TABLE k3l_channel_tokens_log_y2025m01 PARTITION OF k3l_channel_tokens_log
    FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');

CREATE TABLE k3l_channel_tokens_log_y2025m02 PARTITION OF k3l_channel_tokens_log
    FOR VALUES FROM ('2025-02-01') TO ('2025-03-01');

CREATE TABLE k3l_channel_tokens_log_y2025m03 PARTITION OF k3l_channel_tokens_log
    FOR VALUES FROM ('2025-03-01') TO ('2025-04-01');

CREATE TABLE k3l_channel_tokens_log_y2025m04 PARTITION OF k3l_channel_tokens_log
    FOR VALUES FROM ('2025-04-01') TO ('2025-05-01');


GRANT SELECT,REFERENCES ON TABLE public.k3l_channel_tokens_log TO k3l_readonly;
-------------------------------------------------
CREATE TABLE public.k3l_channel_rewards_config (
    channel_id text NOT NULL,
    symbol text NULL,
    is_ranked boolean NOT NULL DEFAULT true,
    is_points boolean NOT NULL DEFAULT false,
    is_tokens boolean NOT NULL DEFAULT false,
    token_airdrop_budget int8 NOT NULL DEFAULT 25000000,
    token_daily_budget int8 NOT NULL DEFAULT 434981,
    token_tax_pct numeric NOT NULL DEFAULT 0.02,
    total_supply int8 NOT NULL DEFAULT 1000000000,
    creator_cut int2 NOT NULL DEFAULT 500,
    vesting_months int2 NOT NULL DEFAULT 36,
    airdrop_pmil int2 NOT NULL DEFAULT 50,
    community_supply int8 NOT NULL DEFAULT 500000000,
    insert_ts timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    update_ts timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT k3l_channel_rewards_config_ch_unq UNIQUE ( channel_id )
);

CREATE INDEX k3l_channel_rewards_config_ch_idx ON public.k3l_channel_rewards_config USING btree (channel_id);
GRANT SELECT,REFERENCES ON TABLE public.k3l_channel_rewards_config TO k3l_readonly;
-- bootstrap data as of 2025-01-07 19:35:09.586911+00
-- INSERT INTO k3l_channel_rewards_config (channel_id, is_points)
-- SELECT channel_id, is_allowed FROM k3l_channel_points_allowlist

-------------------------------------------------
-- TODO drop this once all jobs are migrated to channel_rewards_config
CREATE TABLE public.k3l_channel_points_allowlist (
    channel_id text NOT NULL,
    is_allowed boolean NOT NULL DEFAULT true,
    insert_ts timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT k3l_channel_points_allowlist_ch_uniq UNIQUE (channel_id)
);

GRANT SELECT,REFERENCES ON TABLE public.k3l_channel_points_allowlist TO k3l_readonly;
-------------------------------------------------
CREATE TABLE public.k3l_channel_domains (
    id int GENERATED ALWAYS AS IDENTITY, 
    channel_id text NOT NULL,
    interval_days smallint NOT NULL, -- constrain datatype to auto-fail on bad data
    domain int NOT NULL,
    category text NOT NULL,
    insert_ts timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT openrank_reqs_pkey PRIMARY KEY (id),
    UNIQUE (channel_id, category),
    UNIQUE ( domain )
);

GRANT SELECT,REFERENCES ON TABLE public.k3l_channel_openrank_req_ids TO k3l_readonly;
-------------------------------------------------
CREATE TABLE public.k3l_channel_openrank_results (
    channel_domain_id int NOT NULL,
    fid bigint NOT NULL,
    channel_id text NOT NULL,
    req_id text NOT NULL,
    score real NOT NULL,
    rank bigint NOT NULL,
    insert_ts timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT k3l_channel_openrank_results_fkey 
        FOREIGN KEY (channel_domain_id) 
            REFERENCES public.k3l_channel_domains(id)
)
PARTITION BY RANGE (insert_ts);

CREATE INDEX k3l_ch_or_results_ch_idx ON public.k3l_channel_openrank_results USING btree (channel_id);

CREATE INDEX k3l_ch_or_results_fid_idx ON public.k3l_channel_openrank_results USING btree (fid);

CREATE TABLE k3l_channel_openrank_results_y2024m11 PARTITION OF k3l_channel_openrank_results
    FOR VALUES FROM ('2024-11-01') TO ('2024-12-01');
CREATE TABLE k3l_channel_openrank_results_y2024m12 PARTITION OF k3l_channel_openrank_results
    FOR VALUES FROM ('2024-12-01') TO ('2025-01-01');
CREATE TABLE k3l_channel_openrank_results_y2025m01 PARTITION OF k3l_channel_openrank_results
    FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');
CREATE TABLE k3l_channel_openrank_results_y2025m02 PARTITION OF k3l_channel_openrank_results
    FOR VALUES FROM ('2025-02-01') TO ('2025-03-01');
CREATE TABLE k3l_channel_openrank_results_y2025m03 PARTITION OF k3l_channel_openrank_results
    FOR VALUES FROM ('2025-03-01') TO ('2025-04-01');

GRANT SELECT,REFERENCES ON TABLE public.k3l_channel_openrank_results TO k3l_readonly;
-------------------------------------------------
CREATE INDEX k3l_reactions_updated_at ON neynarv3.reactions(updated_at);

-------------------------------------------------

CREATE TABLE public.k3l_farcaster_interactions (
    id SERIAL PRIMARY KEY,
    source INTEGER NOT NULL,
    target INTEGER NOT NULL,
    interaction_type INTEGER NOT NULL,
    value INTEGER NOT NULL
);

ALTER TABLE
    ONLY public.k3l_farcaster_interactions
ADD
    CONSTRAINT k3l_farcaster_interactions_source_target_interaction_type_uniq UNIQUE (source, target, interaction_type);

ALTER TABLE 
    public.k3l_farcaster_interactions
ADD 
    CONSTRAINT chk_value_non_negative CHECK (value >= 0);

CREATE TABLE public.k3l_farcaster_interaction_cursors (
    interaction_type INTEGER NOT NULL PRIMARY KEY,
    next_cursor TIMESTAMP NOT NULL
);

CREATE TABLE public.seen_reactions (
    id UUID NOT NULL PRIMARY KEY REFERENCES neynarv3.reactions(id)
);

-------------------------------------------------

