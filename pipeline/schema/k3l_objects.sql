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
