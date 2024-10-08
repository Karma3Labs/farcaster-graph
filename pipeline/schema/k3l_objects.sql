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
CREATE MATERIALIZED VIEW public.k3l_frame_interaction AS
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
  GROUP BY reactions.fid, 'like'::text, urls.url_id, ((((((urls.scheme || '://'::text) ||
        CASE
            WHEN (urls.subdomain <> ''::text) THEN (urls.subdomain || '.'::text)
            ELSE ''::text
        END) || urls.domain) || '.'::text) || (urls.tld)::text) || urls.path)
  WITH NO DATA;

CREATE UNIQUE INDEX k3l_frame_interaction_fid_action_type_url_idunique 
ON public.k3l_frame_interaction 
USING btree (fid, action_type, url_id) NULLS NOT DISTINCT;

CREATE INDEX k3l_frame_interaction_url_id_index ON public.k3l_frame_interaction USING btree (url_id);

CREATE INDEX k3l_frame_interaction_fid_index ON public.k3l_frame_interaction USING btree (fid)

CREATE INDEX k3l_frame_interaction_url_index ON public.k3l_frame_interaction USING btree (url)

------------------------------------------------------------------------------------
CREATE MATERIALIZED VIEW public.k3l_recent_parent_casts AS
SELECT 
	*
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
CREATE TABLE public.k3l_channel_fids (
  channel_id text NOT NULL,
  fid bigint NOT NULL,
  score real NOT NULL,
  rank bigint NOT NULL,
  compute_ts timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
  strategy_name text NOT NULL
 );

CREATE INDEX k3l_channel_fids_id_idx ON public.k3l_channel_fids USING btree(channel_id, compute_ts, fid);

CREATE INDEX k3l_channel_fids_rank_idx ON public.k3l_channel_fids USING btree(channel_id, rank);

CREATE INDEX k3l_channel_fids_ts_idx ON public.k3l_channel_fids USING btree(channel_id, compute_ts);
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

------------------------------------------------------------------------------------

CREATE MATERIALIZED VIEW public.k3l_channel_rank AS
 WITH latest_compute AS (
   select max(compute_ts) as max_ts, channel_id 
   from k3l_channel_fids 
   group by channel_id
 )
SELECT
 	row_number() OVER () AS pseudo_id,
 	cfids.* 
FROM k3l_channel_fids as cfids
INNER JOIN latest_compute ON (cfids.compute_ts = latest_compute.max_ts
                              AND cfids.channel_id = latest_compute.channel_id)
WITH NO DATA;

CREATE UNIQUE INDEX k3l_channel_rank_idx ON public.k3l_channel_rank USING btree (pseudo_id);

CREATE INDEX k3l_channel_rank_rank_idx ON public.k3l_channel_rank USING btree (rank);

CREATE INDEX k3l_channel_rank_fid_idx ON public.k3l_channel_rank USING btree (fid);

CREATE INDEX k3l_channel_rank_ch_idx ON public.k3l_channel_rank USING btree (channel_id);

CREATE INDEX k3l_channel_rank_ch_fid_idx ON public.k3l_channel_rank USING btree (channel_id, fid);

------------------------------------------------------------------------------------
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

CREATE INDEX idx_automod_data_affected_userid ON public.automod_data USING btree (affected_userid);

CREATE INDEX idx_automod_data_ch_userid_idx ON public.automod_data USING btree (channel_id, affected_userid)

-------------------------------------------------------------------------------------
CREATE TABLE public.warpcast_channels_data (
	id text NOT NULL,
	url text NOT NULL,
	name text NOT NULL,
	description text NULL,
	imageurl text NULL,
    headerImageUrl text NULL,
	leadfid int8 NULL,
    moderatorFids int8[] NULL,
	createdat timestamp NULL,
	followercount int4 NOT NULL,
    memberCount int4 NOT NULL,
    pinnedCastHash text NULL,
	insert_ts timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);
CREATE UNIQUE INDEX idx_warpcast_channels_data_ch_id_idx ON public.warpcast_channels_data USING btree (id);

GRANT SELECT,REFERENCES ON TABLE public.warpcast_channels_data TO k3l_readonly;

----------------------------------------------
CREATE TABLE public.k3l_top_casters (
	i int8 NOT NULL,
	v float8 NOT NULL,
	date_iso date NOT NULL,
	cast_hash bytea NULL
);

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
CREATE INDEX warpcast_followers_ch_id_idx ON public.warpcast_followers USING btree (channel_id);
CREATE INDEX warpcast_followers_fid_idx ON public.warpcast_followers USING btree (fid);

GRANT SELECT,REFERENCES ON TABLE public.warpcast_followers TO k3l_readonly;
-------------------------------------------------
