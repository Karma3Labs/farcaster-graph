--
-- PostgreSQL database dump
--

-- Dumped from database version 16.2
-- Dumped by pg_dump version 16.1

-- Started on 2024-04-10 14:08:45 PDT

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- TOC entry 320 (class 1259 OID 16560)
-- Name: casts; Type: TABLE; Schema: public; Owner: replicator
--

CREATE TABLE public.casts (
    id uuid DEFAULT public.generate_ulid() NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    "timestamp" timestamp with time zone NOT NULL,
    deleted_at timestamp with time zone,
    fid bigint NOT NULL,
    parent_fid bigint,
    hash bytea NOT NULL,
    root_parent_hash bytea,
    parent_hash bytea,
    root_parent_url text,
    parent_url text,
    text text NOT NULL,
    embeds json DEFAULT '[]'::json NOT NULL,
    mentions json DEFAULT '[]'::json NOT NULL,
    mentions_positions json DEFAULT '[]'::json NOT NULL
);


ALTER TABLE public.casts OWNER TO replicator;

--
-- TOC entry 314 (class 1259 OID 16436)
-- Name: chain_events; Type: TABLE; Schema: public; Owner: replicator
--

CREATE TABLE public.chain_events (
    id uuid DEFAULT public.generate_ulid() NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    block_timestamp timestamp with time zone NOT NULL,
    fid bigint NOT NULL,
    chain_id bigint NOT NULL,
    block_number bigint NOT NULL,
    transaction_index smallint NOT NULL,
    log_index smallint NOT NULL,
    type smallint NOT NULL,
    block_hash bytea NOT NULL,
    transaction_hash bytea NOT NULL,
    body json NOT NULL,
    raw bytea NOT NULL
);


ALTER TABLE public.chain_events OWNER TO replicator;

--
-- TOC entry 315 (class 1259 OID 16451)
-- Name: fids; Type: TABLE; Schema: public; Owner: replicator
--

CREATE TABLE public.fids (
    fid bigint NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    registered_at timestamp with time zone NOT NULL,
    chain_event_id uuid NOT NULL,
    custody_address bytea NOT NULL,
    recovery_address bytea NOT NULL
);


ALTER TABLE public.fids OWNER TO replicator;

--
-- TOC entry 318 (class 1259 OID 16516)
-- Name: fnames; Type: TABLE; Schema: public; Owner: replicator
--

CREATE TABLE public.fnames (
    id uuid DEFAULT public.generate_ulid() NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    registered_at timestamp with time zone NOT NULL,
    deleted_at timestamp with time zone,
    fid bigint NOT NULL,
    type smallint NOT NULL,
    username text NOT NULL
);


ALTER TABLE public.fnames OWNER TO replicator;

--
-- TOC entry 326 (class 1259 OID 16749)
-- Name: globaltrust; Type: TABLE; Schema: public; Owner: replicator
--

CREATE TABLE public.globaltrust (
    strategy_id integer,
    i bigint,
    v real,
    date date DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.globaltrust OWNER TO replicator;

--
-- TOC entry 327 (class 1259 OID 16753)
-- Name: globaltrust_config; Type: TABLE; Schema: public; Owner: replicator
--

CREATE TABLE public.globaltrust_config (
    strategy_id integer NOT NULL,
    strategy_name character varying(255) NOT NULL,
    pretrust text,
    localtrust text,
    alpha real,
    date date DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE public.globaltrust_config OWNER TO replicator;

--
-- TOC entry 328 (class 1259 OID 16759)
-- Name: k3l_cast_embed_url_mapping; Type: TABLE; Schema: public; Owner: replicator
--

CREATE TABLE public.k3l_cast_embed_url_mapping (
    url_id integer,
    cast_id uuid
);


ALTER TABLE public.k3l_cast_embed_url_mapping OWNER TO replicator;

--
-- TOC entry 329 (class 1259 OID 16762)
-- Name: k3l_url_labels; Type: TABLE; Schema: public; Owner: replicator
--

CREATE TABLE public.k3l_url_labels (
    url_id integer NOT NULL,
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


ALTER TABLE public.k3l_url_labels OWNER TO replicator;

--
-- TOC entry 321 (class 1259 OID 16591)
-- Name: reactions; Type: TABLE; Schema: public; Owner: replicator
--

CREATE TABLE public.reactions (
    id uuid DEFAULT public.generate_ulid() NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    "timestamp" timestamp with time zone NOT NULL,
    deleted_at timestamp with time zone,
    fid bigint NOT NULL,
    target_cast_fid bigint,
    type smallint NOT NULL,
    hash bytea NOT NULL,
    target_cast_hash bytea,
    target_url text
);


ALTER TABLE public.reactions OWNER TO replicator;

--
-- TOC entry 330 (class 1259 OID 16768)
-- Name: k3l_frame_interaction; Type: MATERIALIZED VIEW; Schema: public; Owner: replicator
--

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
     JOIN public.k3l_cast_embed_url_mapping url_map ON ((url_map.cast_id = casts.id)))
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
     JOIN public.reactions ON (((reactions.target_cast_hash = casts.hash) AND (reactions.type = 2))))
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
     JOIN public.reactions ON (((reactions.target_cast_hash = casts.hash) AND (reactions.type = 1))))
     JOIN public.k3l_cast_embed_url_mapping url_map ON ((casts.id = url_map.cast_id)))
     JOIN public.k3l_url_labels urls ON (((urls.url_id = url_map.url_id) AND ((urls.category)::text = 'frame'::text))))
  GROUP BY reactions.fid, 'like'::text, urls.url_id, ((((((urls.scheme || '://'::text) ||
        CASE
            WHEN (urls.subdomain <> ''::text) THEN (urls.subdomain || '.'::text)
            ELSE ''::text
        END) || urls.domain) || '.'::text) || (urls.tld)::text) || urls.path)
  WITH NO DATA;


ALTER MATERIALIZED VIEW public.k3l_frame_interaction OWNER TO replicator;

--
-- TOC entry 331 (class 1259 OID 16775)
-- Name: k3l_rank; Type: MATERIALIZED VIEW; Schema: public; Owner: replicator
--

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


ALTER MATERIALIZED VIEW public.k3l_rank OWNER TO replicator;

--
-- TOC entry 332 (class 1259 OID 16780)
-- Name: k3l_url_labels_url_id_seq; Type: SEQUENCE; Schema: public; Owner: replicator
--

ALTER TABLE public.k3l_url_labels ALTER COLUMN url_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.k3l_url_labels_url_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 312 (class 1259 OID 16385)
-- Name: kysely_migration; Type: TABLE; Schema: public; Owner: replicator
--

CREATE TABLE public.kysely_migration (
    name character varying(255) NOT NULL,
    "timestamp" character varying(255) NOT NULL
);


ALTER TABLE public.kysely_migration OWNER TO replicator;

--
-- TOC entry 313 (class 1259 OID 16392)
-- Name: kysely_migration_lock; Type: TABLE; Schema: public; Owner: replicator
--

CREATE TABLE public.kysely_migration_lock (
    id character varying(255) NOT NULL,
    is_locked integer DEFAULT 0 NOT NULL
);


ALTER TABLE public.kysely_migration_lock OWNER TO replicator;

--
-- TOC entry 322 (class 1259 OID 16623)
-- Name: links; Type: TABLE; Schema: public; Owner: replicator
--

CREATE TABLE public.links (
    id uuid DEFAULT public.generate_ulid() NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    "timestamp" timestamp with time zone NOT NULL,
    deleted_at timestamp with time zone,
    fid bigint NOT NULL,
    target_fid bigint NOT NULL,
    display_timestamp timestamp with time zone,
    type text NOT NULL,
    hash bytea NOT NULL
);


ALTER TABLE public.links OWNER TO replicator;

--
-- TOC entry 336 (class 1259 OID 18691)
-- Name: localtrust; Type: TABLE; Schema: public; Owner: replicator
--

CREATE TABLE public.localtrust (
    strategy_id integer,
    i character varying(255),
    j character varying(255),
    v double precision,
    date date
);


ALTER TABLE public.localtrust OWNER TO replicator;

--
-- TOC entry 335 (class 1259 OID 18687)
-- Name: localtrust_stats; Type: TABLE; Schema: public; Owner: replicator
--

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


ALTER TABLE public.localtrust_stats OWNER TO replicator;

--
-- TOC entry 319 (class 1259 OID 16535)
-- Name: messages; Type: TABLE; Schema: public; Owner: replicator
--

CREATE TABLE public.messages (
    id uuid DEFAULT public.generate_ulid() NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    "timestamp" timestamp with time zone NOT NULL,
    deleted_at timestamp with time zone,
    pruned_at timestamp with time zone,
    revoked_at timestamp with time zone,
    fid bigint NOT NULL,
    type smallint NOT NULL,
    hash_scheme smallint NOT NULL,
    signature_scheme smallint NOT NULL,
    hash bytea NOT NULL,
    signature bytea NOT NULL,
    signer bytea NOT NULL,
    body json NOT NULL,
    raw bytea NOT NULL
);


ALTER TABLE public.messages OWNER TO replicator;

--
-- TOC entry 338 (class 1259 OID 23348)
-- Name: mv_channel_fids; Type: MATERIALIZED VIEW; Schema: public; Owner: replicator
--

CREATE MATERIALIZED VIEW public.mv_channel_fids AS
 SELECT "substring"(root_parent_url, 'https://warpcast.com/~/channel/(.*)'::text) AS channel,
    fid
   FROM public.casts
  WHERE (root_parent_url ~~ 'https://warpcast.com/~/channel/%'::text)
  GROUP BY ("substring"(root_parent_url, 'https://warpcast.com/~/channel/(.*)'::text)), fid
  WITH NO DATA;


ALTER MATERIALIZED VIEW public.mv_channel_fids OWNER TO replicator;

--
-- TOC entry 339 (class 1259 OID 23529)
-- Name: mv_channel_fids_all; Type: MATERIALIZED VIEW; Schema: public; Owner: replicator
--

CREATE MATERIALIZED VIEW public.mv_channel_fids_all AS
 SELECT "substring"(root_parent_url, 'https://.*/([^/]*)$'::text) AS channel,
    fid
   FROM public.casts
  WHERE (root_parent_url ~~ 'https://%'::text)
  GROUP BY ("substring"(root_parent_url, 'https://.*/([^/]*)$'::text)), fid
  WITH NO DATA;


ALTER MATERIALIZED VIEW public.mv_channel_fids_all OWNER TO replicator;

--
-- TOC entry 337 (class 1259 OID 23275)
-- Name: mv_channel_stats; Type: MATERIALIZED VIEW; Schema: public; Owner: replicator
--

CREATE MATERIALIZED VIEW public.mv_channel_stats AS
 SELECT "substring"(root_parent_url, 'https://warpcast.com/~/channel/(.*)'::text) AS channel,
    count(DISTINCT fid) AS total_unique_casters,
    count(*) AS total_casts,
    max(created_at) AS most_recent_cast
   FROM public.casts
  WHERE (root_parent_url ~~ 'https://warpcast.com/~/channel/%'::text)
  GROUP BY ("substring"(root_parent_url, 'https://warpcast.com/~/channel/(.*)'::text))
  WITH NO DATA;


ALTER MATERIALIZED VIEW public.mv_channel_stats OWNER TO replicator;

--
-- TOC entry 333 (class 1259 OID 16786)
-- Name: mv_follow_links; Type: MATERIALIZED VIEW; Schema: public; Owner: replicator
--

CREATE MATERIALIZED VIEW public.mv_follow_links AS
 SELECT id,
    fid AS follower_fid,
    target_fid AS following_fid
   FROM public.links
  WHERE (type = 'follow'::text)
  WITH NO DATA;


ALTER MATERIALIZED VIEW public.mv_follow_links OWNER TO replicator;

--
-- TOC entry 334 (class 1259 OID 18623)
-- Name: pretrust; Type: TABLE; Schema: public; Owner: replicator
--

CREATE TABLE public.pretrust (
    fid bigint NOT NULL,
    fname text NOT NULL,
    fid_active_tier integer NOT NULL,
    fid_active_tier_name text NOT NULL,
    data_source character varying(32) DEFAULT 'Dune'::character varying,
    insert_ts timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.pretrust OWNER TO replicator;

--
-- TOC entry 316 (class 1259 OID 16465)
-- Name: signers; Type: TABLE; Schema: public; Owner: replicator
--

CREATE TABLE public.signers (
    id uuid DEFAULT public.generate_ulid() NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    added_at timestamp with time zone NOT NULL,
    removed_at timestamp with time zone,
    fid bigint NOT NULL,
    requester_fid bigint NOT NULL,
    add_chain_event_id uuid NOT NULL,
    remove_chain_event_id uuid,
    key_type smallint NOT NULL,
    metadata_type smallint NOT NULL,
    key bytea NOT NULL,
    metadata json NOT NULL
);


ALTER TABLE public.signers OWNER TO replicator;

--
-- TOC entry 347 (class 1259 OID 39155)
-- Name: signers_new; Type: TABLE; Schema: public; Owner: replicator
--

CREATE TABLE public.signers_new (
    id uuid DEFAULT public.generate_ulid() NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    added_at timestamp with time zone NOT NULL,
    removed_at timestamp with time zone,
    fid bigint NOT NULL,
    requester_fid bigint NOT NULL,
    add_chain_event_id uuid NOT NULL,
    remove_chain_event_id uuid,
    key_type smallint NOT NULL,
    metadata_type smallint NOT NULL,
    key bytea NOT NULL,
    metadata json NOT NULL
);


ALTER TABLE public.signers_new OWNER TO replicator;

--
-- TOC entry 325 (class 1259 OID 16693)
-- Name: storage_allocations; Type: TABLE; Schema: public; Owner: replicator
--

CREATE TABLE public.storage_allocations (
    id uuid DEFAULT public.generate_ulid() NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    rented_at timestamp with time zone NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    chain_event_id uuid NOT NULL,
    fid bigint NOT NULL,
    units smallint NOT NULL,
    payer bytea NOT NULL
);


ALTER TABLE public.storage_allocations OWNER TO replicator;

--
-- TOC entry 324 (class 1259 OID 16669)
-- Name: user_data; Type: TABLE; Schema: public; Owner: replicator
--

CREATE TABLE public.user_data (
    id uuid DEFAULT public.generate_ulid() NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    "timestamp" timestamp with time zone NOT NULL,
    deleted_at timestamp with time zone,
    fid bigint NOT NULL,
    type smallint NOT NULL,
    hash bytea NOT NULL,
    value text NOT NULL
);


ALTER TABLE public.user_data OWNER TO replicator;

--
-- TOC entry 317 (class 1259 OID 16499)
-- Name: username_proofs; Type: TABLE; Schema: public; Owner: replicator
--

CREATE TABLE public.username_proofs (
    id uuid DEFAULT public.generate_ulid() NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    "timestamp" timestamp with time zone NOT NULL,
    deleted_at timestamp with time zone,
    fid bigint NOT NULL,
    type smallint NOT NULL,
    username text NOT NULL,
    signature bytea NOT NULL,
    owner bytea NOT NULL
);


ALTER TABLE public.username_proofs OWNER TO replicator;

--
-- TOC entry 323 (class 1259 OID 16646)
-- Name: verifications; Type: TABLE; Schema: public; Owner: replicator
--

CREATE TABLE public.verifications (
    id uuid DEFAULT public.generate_ulid() NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    "timestamp" timestamp with time zone NOT NULL,
    deleted_at timestamp with time zone,
    fid bigint NOT NULL,
    hash bytea NOT NULL,
    signer_address bytea NOT NULL,
    block_hash bytea NOT NULL,
    signature bytea NOT NULL
);


ALTER TABLE public.verifications OWNER TO replicator;

--
-- TOC entry 3579 (class 2606 OID 16574)
-- Name: casts casts_hash_unique; Type: CONSTRAINT; Schema: public; Owner: replicator
--

ALTER TABLE ONLY public.casts
    ADD CONSTRAINT casts_hash_unique UNIQUE (hash);


--
-- TOC entry 3583 (class 2606 OID 16572)
-- Name: casts casts_pkey; Type: CONSTRAINT; Schema: public; Owner: replicator
--

ALTER TABLE ONLY public.casts
    ADD CONSTRAINT casts_pkey PRIMARY KEY (id);


--
-- TOC entry 3546 (class 2606 OID 16446)
-- Name: chain_events chain_events_block_number_log_index_unique; Type: CONSTRAINT; Schema: public; Owner: replicator
--

ALTER TABLE ONLY public.chain_events
    ADD CONSTRAINT chain_events_block_number_log_index_unique UNIQUE (block_number, log_index);


--
-- TOC entry 3550 (class 2606 OID 16444)
-- Name: chain_events chain_events_pkey; Type: CONSTRAINT; Schema: public; Owner: replicator
--

ALTER TABLE ONLY public.chain_events
    ADD CONSTRAINT chain_events_pkey PRIMARY KEY (id);


--
-- TOC entry 3629 (class 2606 OID 18631)
-- Name: pretrust fid_insert_ts_unique; Type: CONSTRAINT; Schema: public; Owner: replicator
--

ALTER TABLE ONLY public.pretrust
    ADD CONSTRAINT fid_insert_ts_unique UNIQUE (fid, insert_ts);


--
-- TOC entry 3553 (class 2606 OID 16459)
-- Name: fids fids_pkey; Type: CONSTRAINT; Schema: public; Owner: replicator
--

ALTER TABLE ONLY public.fids
    ADD CONSTRAINT fids_pkey PRIMARY KEY (fid);


--
-- TOC entry 3565 (class 2606 OID 16527)
-- Name: fnames fnames_fid_unique; Type: CONSTRAINT; Schema: public; Owner: replicator
--

ALTER TABLE ONLY public.fnames
    ADD CONSTRAINT fnames_fid_unique UNIQUE (fid);


--
-- TOC entry 3567 (class 2606 OID 16525)
-- Name: fnames fnames_pkey; Type: CONSTRAINT; Schema: public; Owner: replicator
--

ALTER TABLE ONLY public.fnames
    ADD CONSTRAINT fnames_pkey PRIMARY KEY (id);


--
-- TOC entry 3569 (class 2606 OID 16529)
-- Name: fnames fnames_username_unique; Type: CONSTRAINT; Schema: public; Owner: replicator
--

ALTER TABLE ONLY public.fnames
    ADD CONSTRAINT fnames_username_unique UNIQUE (username);


--
-- TOC entry 3621 (class 2606 OID 16791)
-- Name: globaltrust_config globaltrust_config_pkey; Type: CONSTRAINT; Schema: public; Owner: replicator
--

ALTER TABLE ONLY public.globaltrust_config
    ADD CONSTRAINT globaltrust_config_pkey PRIMARY KEY (strategy_id, date);


--
-- TOC entry 3619 (class 2606 OID 16793)
-- Name: globaltrust globaltrust_strategy_name_date_i_unique; Type: CONSTRAINT; Schema: public; Owner: replicator
--

ALTER TABLE ONLY public.globaltrust
    ADD CONSTRAINT globaltrust_strategy_name_date_i_unique UNIQUE (strategy_id, date, i);


--
-- TOC entry 3623 (class 2606 OID 16795)
-- Name: k3l_url_labels k3l_url_labels_pkey; Type: CONSTRAINT; Schema: public; Owner: replicator
--

ALTER TABLE ONLY public.k3l_url_labels
    ADD CONSTRAINT k3l_url_labels_pkey PRIMARY KEY (url_id);


--
-- TOC entry 3625 (class 2606 OID 16797)
-- Name: k3l_url_labels k3l_url_labels_url_unique; Type: CONSTRAINT; Schema: public; Owner: replicator
--

ALTER TABLE ONLY public.k3l_url_labels
    ADD CONSTRAINT k3l_url_labels_url_unique UNIQUE (url);


--
-- TOC entry 3543 (class 2606 OID 16397)
-- Name: kysely_migration_lock kysely_migration_lock_pkey; Type: CONSTRAINT; Schema: public; Owner: replicator
--

ALTER TABLE ONLY public.kysely_migration_lock
    ADD CONSTRAINT kysely_migration_lock_pkey PRIMARY KEY (id);


--
-- TOC entry 3541 (class 2606 OID 16391)
-- Name: kysely_migration kysely_migration_pkey; Type: CONSTRAINT; Schema: public; Owner: replicator
--

ALTER TABLE ONLY public.kysely_migration
    ADD CONSTRAINT kysely_migration_pkey PRIMARY KEY (name);


--
-- TOC entry 3598 (class 2606 OID 16634)
-- Name: links links_hash_unique; Type: CONSTRAINT; Schema: public; Owner: replicator
--

ALTER TABLE ONLY public.links
    ADD CONSTRAINT links_hash_unique UNIQUE (hash);


--
-- TOC entry 3600 (class 2606 OID 16632)
-- Name: links links_pkey; Type: CONSTRAINT; Schema: public; Owner: replicator
--

ALTER TABLE ONLY public.links
    ADD CONSTRAINT links_pkey PRIMARY KEY (id);


--
-- TOC entry 3572 (class 2606 OID 16546)
-- Name: messages messages_hash_unique; Type: CONSTRAINT; Schema: public; Owner: replicator
--

ALTER TABLE ONLY public.messages
    ADD CONSTRAINT messages_hash_unique UNIQUE (hash);


--
-- TOC entry 3574 (class 2606 OID 16544)
-- Name: messages messages_pkey; Type: CONSTRAINT; Schema: public; Owner: replicator
--

ALTER TABLE ONLY public.messages
    ADD CONSTRAINT messages_pkey PRIMARY KEY (id);


--
-- TOC entry 3589 (class 2606 OID 16619)
-- Name: reactions reactions_fid_type_target_cast_hash_target_url_unique; Type: CONSTRAINT; Schema: public; Owner: replicator
--

ALTER TABLE ONLY public.reactions
    ADD CONSTRAINT reactions_fid_type_target_cast_hash_target_url_unique UNIQUE NULLS NOT DISTINCT (fid, type, target_cast_hash, target_url);


--
-- TOC entry 3591 (class 2606 OID 16602)
-- Name: reactions reactions_hash_unique; Type: CONSTRAINT; Schema: public; Owner: replicator
--

ALTER TABLE ONLY public.reactions
    ADD CONSTRAINT reactions_hash_unique UNIQUE (hash);


--
-- TOC entry 3593 (class 2606 OID 16600)
-- Name: reactions reactions_pkey; Type: CONSTRAINT; Schema: public; Owner: replicator
--

ALTER TABLE ONLY public.reactions
    ADD CONSTRAINT reactions_pkey PRIMARY KEY (id);


--
-- TOC entry 3556 (class 2606 OID 16476)
-- Name: signers signers_fid_key_unique; Type: CONSTRAINT; Schema: public; Owner: replicator
--

ALTER TABLE ONLY public.signers
    ADD CONSTRAINT signers_fid_key_unique UNIQUE (fid, key);


--
-- TOC entry 3637 (class 2606 OID 39166)
-- Name: signers_new signers_new_fid_key_key; Type: CONSTRAINT; Schema: public; Owner: replicator
--

ALTER TABLE ONLY public.signers_new
    ADD CONSTRAINT signers_new_fid_key_key UNIQUE (fid, key);


--
-- TOC entry 3639 (class 2606 OID 39164)
-- Name: signers_new signers_new_pkey; Type: CONSTRAINT; Schema: public; Owner: replicator
--

ALTER TABLE ONLY public.signers_new
    ADD CONSTRAINT signers_new_pkey PRIMARY KEY (id);


--
-- TOC entry 3558 (class 2606 OID 16474)
-- Name: signers signers_pkey; Type: CONSTRAINT; Schema: public; Owner: replicator
--

ALTER TABLE ONLY public.signers
    ADD CONSTRAINT signers_pkey PRIMARY KEY (id);


--
-- TOC entry 3614 (class 2606 OID 16702)
-- Name: storage_allocations storage_allocations_pkey; Type: CONSTRAINT; Schema: public; Owner: replicator
--

ALTER TABLE ONLY public.storage_allocations
    ADD CONSTRAINT storage_allocations_pkey PRIMARY KEY (id);


--
-- TOC entry 3616 (class 2606 OID 16704)
-- Name: storage_allocations storage_chain_event_id_fid_unique; Type: CONSTRAINT; Schema: public; Owner: replicator
--

ALTER TABLE ONLY public.storage_allocations
    ADD CONSTRAINT storage_chain_event_id_fid_unique UNIQUE (chain_event_id, fid);


--
-- TOC entry 3607 (class 2606 OID 16680)
-- Name: user_data user_data_fid_type_unique; Type: CONSTRAINT; Schema: public; Owner: replicator
--

ALTER TABLE ONLY public.user_data
    ADD CONSTRAINT user_data_fid_type_unique UNIQUE (fid, type);


--
-- TOC entry 3609 (class 2606 OID 16682)
-- Name: user_data user_data_hash_unique; Type: CONSTRAINT; Schema: public; Owner: replicator
--

ALTER TABLE ONLY public.user_data
    ADD CONSTRAINT user_data_hash_unique UNIQUE (hash);


--
-- TOC entry 3611 (class 2606 OID 16678)
-- Name: user_data user_data_pkey; Type: CONSTRAINT; Schema: public; Owner: replicator
--

ALTER TABLE ONLY public.user_data
    ADD CONSTRAINT user_data_pkey PRIMARY KEY (id);


--
-- TOC entry 3561 (class 2606 OID 16508)
-- Name: username_proofs username_proofs_pkey; Type: CONSTRAINT; Schema: public; Owner: replicator
--

ALTER TABLE ONLY public.username_proofs
    ADD CONSTRAINT username_proofs_pkey PRIMARY KEY (id);


--
-- TOC entry 3563 (class 2606 OID 16510)
-- Name: username_proofs username_proofs_username_timestamp_unique; Type: CONSTRAINT; Schema: public; Owner: replicator
--

ALTER TABLE ONLY public.username_proofs
    ADD CONSTRAINT username_proofs_username_timestamp_unique UNIQUE (username, "timestamp");


--
-- TOC entry 3603 (class 2606 OID 16655)
-- Name: verifications verifications_pkey; Type: CONSTRAINT; Schema: public; Owner: replicator
--

ALTER TABLE ONLY public.verifications
    ADD CONSTRAINT verifications_pkey PRIMARY KEY (id);


--
-- TOC entry 3605 (class 2606 OID 16657)
-- Name: verifications verifications_signer_address_fid_unique; Type: CONSTRAINT; Schema: public; Owner: replicator
--

ALTER TABLE ONLY public.verifications
    ADD CONSTRAINT verifications_signer_address_fid_unique UNIQUE (signer_address, fid);


--
-- TOC entry 3577 (class 1259 OID 16585)
-- Name: casts_active_fid_timestamp_index; Type: INDEX; Schema: public; Owner: replicator
--

CREATE INDEX casts_active_fid_timestamp_index ON public.casts USING btree (fid, "timestamp") WHERE (deleted_at IS NULL);


--
-- TOC entry 3580 (class 1259 OID 16587)
-- Name: casts_parent_hash_index; Type: INDEX; Schema: public; Owner: replicator
--

CREATE INDEX casts_parent_hash_index ON public.casts USING btree (parent_hash) WHERE (parent_hash IS NOT NULL);


--
-- TOC entry 3581 (class 1259 OID 16589)
-- Name: casts_parent_url_index; Type: INDEX; Schema: public; Owner: replicator
--

CREATE INDEX casts_parent_url_index ON public.casts USING btree (parent_url) WHERE (parent_url IS NOT NULL);


--
-- TOC entry 3584 (class 1259 OID 16588)
-- Name: casts_root_parent_hash_index; Type: INDEX; Schema: public; Owner: replicator
--

CREATE INDEX casts_root_parent_hash_index ON public.casts USING btree (root_parent_hash) WHERE (root_parent_hash IS NOT NULL);


--
-- TOC entry 3585 (class 1259 OID 16590)
-- Name: casts_root_parent_url_index; Type: INDEX; Schema: public; Owner: replicator
--

CREATE INDEX casts_root_parent_url_index ON public.casts USING btree (root_parent_url) WHERE (root_parent_url IS NOT NULL);


--
-- TOC entry 3586 (class 1259 OID 16586)
-- Name: casts_timestamp_index; Type: INDEX; Schema: public; Owner: replicator
--

CREATE INDEX casts_timestamp_index ON public.casts USING btree ("timestamp");


--
-- TOC entry 3544 (class 1259 OID 16448)
-- Name: chain_events_block_hash_index; Type: INDEX; Schema: public; Owner: replicator
--

CREATE INDEX chain_events_block_hash_index ON public.chain_events USING hash (block_hash);


--
-- TOC entry 3547 (class 1259 OID 16449)
-- Name: chain_events_block_timestamp_index; Type: INDEX; Schema: public; Owner: replicator
--

CREATE INDEX chain_events_block_timestamp_index ON public.chain_events USING btree (block_timestamp);


--
-- TOC entry 3548 (class 1259 OID 16447)
-- Name: chain_events_fid_index; Type: INDEX; Schema: public; Owner: replicator
--

CREATE INDEX chain_events_fid_index ON public.chain_events USING btree (fid);


--
-- TOC entry 3551 (class 1259 OID 16450)
-- Name: chain_events_transaction_hash_index; Type: INDEX; Schema: public; Owner: replicator
--

CREATE INDEX chain_events_transaction_hash_index ON public.chain_events USING hash (transaction_hash);


--
-- TOC entry 3617 (class 1259 OID 16798)
-- Name: globaltrust_id_idx; Type: INDEX; Schema: public; Owner: replicator
--

CREATE INDEX globaltrust_id_idx ON public.globaltrust USING btree (strategy_id);


--
-- TOC entry 3626 (class 1259 OID 16799)
-- Name: k3l_frame_interaction_fid_action_type_url_idunique; Type: INDEX; Schema: public; Owner: replicator
--

CREATE UNIQUE INDEX k3l_frame_interaction_fid_action_type_url_idunique ON public.k3l_frame_interaction USING btree (fid, action_type, url_id) NULLS NOT DISTINCT;


--
-- TOC entry 3627 (class 1259 OID 16800)
-- Name: k3l_rank_idx; Type: INDEX; Schema: public; Owner: replicator
--

CREATE UNIQUE INDEX k3l_rank_idx ON public.k3l_rank USING btree (pseudo_id);


--
-- TOC entry 3596 (class 1259 OID 16645)
-- Name: links_fid_target_fid_type_unique; Type: INDEX; Schema: public; Owner: replicator
--

CREATE UNIQUE INDEX links_fid_target_fid_type_unique ON public.links USING btree (fid, target_fid, type) NULLS NOT DISTINCT;


--
-- TOC entry 3570 (class 1259 OID 16558)
-- Name: messages_fid_index; Type: INDEX; Schema: public; Owner: replicator
--

CREATE INDEX messages_fid_index ON public.messages USING btree (fid);


--
-- TOC entry 3575 (class 1259 OID 16559)
-- Name: messages_signer_index; Type: INDEX; Schema: public; Owner: replicator
--

CREATE INDEX messages_signer_index ON public.messages USING btree (signer);


--
-- TOC entry 3576 (class 1259 OID 16557)
-- Name: messages_timestamp_index; Type: INDEX; Schema: public; Owner: replicator
--

CREATE INDEX messages_timestamp_index ON public.messages USING btree ("timestamp");


--
-- TOC entry 3630 (class 1259 OID 23281)
-- Name: mv_channel_channel_idx; Type: INDEX; Schema: public; Owner: replicator
--

CREATE INDEX mv_channel_channel_idx ON public.mv_channel_stats USING btree (channel);


--
-- TOC entry 3634 (class 1259 OID 23545)
-- Name: mv_channel_fids_all_channel_fid_idx; Type: INDEX; Schema: public; Owner: replicator
--

CREATE INDEX mv_channel_fids_all_channel_fid_idx ON public.mv_channel_fids_all USING btree (channel, fid);


--
-- TOC entry 3631 (class 1259 OID 23356)
-- Name: mv_channel_fids_channel_fid_idx; Type: INDEX; Schema: public; Owner: replicator
--

CREATE INDEX mv_channel_fids_channel_fid_idx ON public.mv_channel_fids USING btree (channel, fid);


--
-- TOC entry 3632 (class 1259 OID 23354)
-- Name: mv_channel_fids_channel_idx; Type: INDEX; Schema: public; Owner: replicator
--

CREATE INDEX mv_channel_fids_channel_idx ON public.mv_channel_fids USING btree (channel);


--
-- TOC entry 3633 (class 1259 OID 23355)
-- Name: mv_channel_fids_fid_idx; Type: INDEX; Schema: public; Owner: replicator
--

CREATE INDEX mv_channel_fids_fid_idx ON public.mv_channel_fids USING btree (fid);


--
-- TOC entry 3587 (class 1259 OID 16620)
-- Name: reactions_active_fid_timestamp_index; Type: INDEX; Schema: public; Owner: replicator
--

CREATE INDEX reactions_active_fid_timestamp_index ON public.reactions USING btree (fid, "timestamp") WHERE (deleted_at IS NULL);


--
-- TOC entry 3594 (class 1259 OID 16621)
-- Name: reactions_target_cast_hash_index; Type: INDEX; Schema: public; Owner: replicator
--

CREATE INDEX reactions_target_cast_hash_index ON public.reactions USING btree (target_cast_hash) WHERE (target_cast_hash IS NOT NULL);


--
-- TOC entry 3595 (class 1259 OID 16622)
-- Name: reactions_target_url_index; Type: INDEX; Schema: public; Owner: replicator
--

CREATE INDEX reactions_target_url_index ON public.reactions USING btree (target_url) WHERE (target_url IS NOT NULL);


--
-- TOC entry 3554 (class 1259 OID 16497)
-- Name: signers_fid_index; Type: INDEX; Schema: public; Owner: replicator
--

CREATE INDEX signers_fid_index ON public.signers USING btree (fid);


--
-- TOC entry 3635 (class 1259 OID 39167)
-- Name: signers_new_fid_idx; Type: INDEX; Schema: public; Owner: replicator
--

CREATE INDEX signers_new_fid_idx ON public.signers_new USING btree (fid);


--
-- TOC entry 3640 (class 1259 OID 39168)
-- Name: signers_new_requester_fid_idx; Type: INDEX; Schema: public; Owner: replicator
--

CREATE INDEX signers_new_requester_fid_idx ON public.signers_new USING btree (requester_fid);


--
-- TOC entry 3559 (class 1259 OID 16498)
-- Name: signers_requester_fid_index; Type: INDEX; Schema: public; Owner: replicator
--

CREATE INDEX signers_requester_fid_index ON public.signers USING btree (requester_fid);


--
-- TOC entry 3612 (class 1259 OID 16710)
-- Name: storage_allocations_fid_expires_at_index; Type: INDEX; Schema: public; Owner: replicator
--

CREATE INDEX storage_allocations_fid_expires_at_index ON public.storage_allocations USING btree (fid, expires_at);


--
-- TOC entry 3601 (class 1259 OID 16668)
-- Name: verifications_fid_timestamp_index; Type: INDEX; Schema: public; Owner: replicator
--

CREATE INDEX verifications_fid_timestamp_index ON public.verifications USING btree (fid, "timestamp");


--
-- TOC entry 3641 (class 2606 OID 16801)
-- Name: k3l_cast_embed_url_mapping k3l_cast_embed_url_mapping_cast_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: replicator
--

ALTER TABLE ONLY public.k3l_cast_embed_url_mapping
    ADD CONSTRAINT k3l_cast_embed_url_mapping_cast_id_fkey FOREIGN KEY (cast_id) REFERENCES public.casts(id);


--
-- TOC entry 3642 (class 2606 OID 16806)
-- Name: k3l_cast_embed_url_mapping k3l_cast_embed_url_mapping_url_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: replicator
--

ALTER TABLE ONLY public.k3l_cast_embed_url_mapping
    ADD CONSTRAINT k3l_cast_embed_url_mapping_url_id_fkey FOREIGN KEY (url_id) REFERENCES public.k3l_url_labels(url_id);


-- Completed on 2024-04-10 14:09:25 PDT

--
-- PostgreSQL database dump complete
--

