--
-- PostgreSQL database dump
--

-- Dumped from database version 16.2
-- Dumped by pg_dump version 16.2 (Ubuntu 16.2-1.pgdg22.04+1)

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
-- Name: automod_data; Type: TABLE; Schema: public; Owner: k3l_user
--

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


ALTER TABLE public.automod_data OWNER TO k3l_user;

--
-- Name: cura_hidden_fids; Type: TABLE; Schema: public; Owner: k3l_user
--

CREATE TABLE public.cura_hidden_fids (
    channel_id text NOT NULL,
    hidden_fid bigint NOT NULL,
    hider_fid bigint NOT NULL,
    is_active boolean NOT NULL,
    created_at timestamp with time zone,
    updated_at timestamp with time zone,
    insert_ts timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    update_ts timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.cura_hidden_fids OWNER TO k3l_user;

SET default_tablespace = morespace;

--
-- Name: globaltrust; Type: TABLE; Schema: public; Owner: k3l_user; Tablespace: morespace
--

CREATE UNLOGGED TABLE public.globaltrust (
    strategy_id integer,
    i bigint,
    v real,
    date date DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.globaltrust OWNER TO k3l_user;

SET default_tablespace = '';

--
-- Name: globaltrust_config; Type: TABLE; Schema: public; Owner: k3l_user
--

CREATE TABLE public.globaltrust_config (
    strategy_id integer NOT NULL,
    strategy_name character varying(255) NOT NULL,
    pretrust text,
    localtrust text,
    alpha real,
    date date DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE public.globaltrust_config OWNER TO k3l_user;

--
-- Name: k3l_cast_action; Type: TABLE; Schema: public; Owner: k3l_user
--

CREATE TABLE public.k3l_cast_action (
    fid bigint NOT NULL,
    cast_hash bytea NOT NULL,
    casted integer NOT NULL,
    replied integer NOT NULL,
    recasted integer NOT NULL,
    liked integer NOT NULL,
    action_ts timestamp without time zone NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
)
PARTITION BY RANGE (action_ts);


ALTER TABLE public.k3l_cast_action OWNER TO k3l_user;

--
-- Name: k3l_cast_action_y2024m12; Type: TABLE; Schema: public; Owner: k3l_user
--

CREATE TABLE public.k3l_cast_action_y2024m12 (
    fid bigint NOT NULL,
    cast_hash bytea NOT NULL,
    casted integer NOT NULL,
    replied integer NOT NULL,
    recasted integer NOT NULL,
    liked integer NOT NULL,
    action_ts timestamp without time zone NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE public.k3l_cast_action_y2024m12 OWNER TO k3l_user;

--
-- Name: k3l_cast_action_y2025m01; Type: TABLE; Schema: public; Owner: k3l_user
--

CREATE TABLE public.k3l_cast_action_y2025m01 (
    fid bigint NOT NULL,
    cast_hash bytea NOT NULL,
    casted integer NOT NULL,
    replied integer NOT NULL,
    recasted integer NOT NULL,
    liked integer NOT NULL,
    action_ts timestamp without time zone NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE public.k3l_cast_action_y2025m01 OWNER TO k3l_user;

--
-- Name: k3l_cast_action_y2025m02; Type: TABLE; Schema: public; Owner: k3l_user
--

CREATE TABLE public.k3l_cast_action_y2025m02 (
    fid bigint NOT NULL,
    cast_hash bytea NOT NULL,
    casted integer NOT NULL,
    replied integer NOT NULL,
    recasted integer NOT NULL,
    liked integer NOT NULL,
    action_ts timestamp without time zone NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE public.k3l_cast_action_y2025m02 OWNER TO k3l_user;

--
-- Name: k3l_cast_action_y2025m03; Type: TABLE; Schema: public; Owner: k3l_user
--

CREATE TABLE public.k3l_cast_action_y2025m03 (
    fid bigint NOT NULL,
    cast_hash bytea NOT NULL,
    casted integer NOT NULL,
    replied integer NOT NULL,
    recasted integer NOT NULL,
    liked integer NOT NULL,
    action_ts timestamp without time zone NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE public.k3l_cast_action_y2025m03 OWNER TO k3l_user;

--
-- Name: k3l_cast_embed_url_mapping; Type: TABLE; Schema: public; Owner: k3l_user
--

CREATE TABLE public.k3l_cast_embed_url_mapping (
    url_id bigint,
    cast_id bigint
);


ALTER TABLE public.k3l_cast_embed_url_mapping OWNER TO k3l_user;

--
-- Name: k3l_channel_domains; Type: TABLE; Schema: public; Owner: k3l_user
--

CREATE TABLE public.k3l_channel_domains (
    id integer NOT NULL,
    channel_id text NOT NULL,
    interval_days smallint NOT NULL,
    domain integer NOT NULL,
    category text NOT NULL,
    insert_ts timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.k3l_channel_domains OWNER TO k3l_user;

--
-- Name: k3l_channel_domains_id_seq; Type: SEQUENCE; Schema: public; Owner: k3l_user
--

ALTER TABLE public.k3l_channel_domains ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.k3l_channel_domains_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: k3l_channel_fids; Type: TABLE; Schema: public; Owner: k3l_user
--

CREATE UNLOGGED TABLE public.k3l_channel_fids (
    channel_id text NOT NULL,
    fid bigint NOT NULL,
    score real NOT NULL,
    rank bigint NOT NULL,
    compute_ts timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    strategy_name text NOT NULL
);


ALTER TABLE public.k3l_channel_fids OWNER TO k3l_user;

--
-- Name: k3l_channel_fids_old; Type: TABLE; Schema: public; Owner: k3l_user
--

CREATE UNLOGGED TABLE public.k3l_channel_fids_old (
    channel_id text,
    fid bigint,
    score real,
    rank bigint,
    compute_ts timestamp without time zone,
    strategy_name text
);


ALTER TABLE public.k3l_channel_fids_old OWNER TO k3l_user;

--
-- Name: k3l_channel_openrank_results; Type: TABLE; Schema: public; Owner: k3l_user
--

CREATE TABLE public.k3l_channel_openrank_results (
    channel_domain_id integer NOT NULL,
    fid bigint NOT NULL,
    channel_id text NOT NULL,
    req_id text NOT NULL,
    score real NOT NULL,
    rank bigint NOT NULL,
    insert_ts timestamp without time zone DEFAULT CURRENT_TIMESTAMP
)
PARTITION BY RANGE (insert_ts);


ALTER TABLE public.k3l_channel_openrank_results OWNER TO k3l_user;

--
-- Name: k3l_channel_openrank_results_y2024m11; Type: TABLE; Schema: public; Owner: k3l_user
--

CREATE TABLE public.k3l_channel_openrank_results_y2024m11 (
    channel_domain_id integer NOT NULL,
    fid bigint NOT NULL,
    channel_id text NOT NULL,
    req_id text NOT NULL,
    score real NOT NULL,
    rank bigint NOT NULL,
    insert_ts timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.k3l_channel_openrank_results_y2024m11 OWNER TO k3l_user;

--
-- Name: k3l_channel_openrank_results_y2024m12; Type: TABLE; Schema: public; Owner: k3l_user
--

CREATE TABLE public.k3l_channel_openrank_results_y2024m12 (
    channel_domain_id integer NOT NULL,
    fid bigint NOT NULL,
    channel_id text NOT NULL,
    req_id text NOT NULL,
    score real NOT NULL,
    rank bigint NOT NULL,
    insert_ts timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.k3l_channel_openrank_results_y2024m12 OWNER TO k3l_user;

--
-- Name: k3l_channel_openrank_results_y2025m01; Type: TABLE; Schema: public; Owner: k3l_user
--

CREATE TABLE public.k3l_channel_openrank_results_y2025m01 (
    channel_domain_id integer NOT NULL,
    fid bigint NOT NULL,
    channel_id text NOT NULL,
    req_id text NOT NULL,
    score real NOT NULL,
    rank bigint NOT NULL,
    insert_ts timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.k3l_channel_openrank_results_y2025m01 OWNER TO k3l_user;

--
-- Name: k3l_channel_openrank_results_y2025m02; Type: TABLE; Schema: public; Owner: k3l_user
--

CREATE TABLE public.k3l_channel_openrank_results_y2025m02 (
    channel_domain_id integer NOT NULL,
    fid bigint NOT NULL,
    channel_id text NOT NULL,
    req_id text NOT NULL,
    score real NOT NULL,
    rank bigint NOT NULL,
    insert_ts timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.k3l_channel_openrank_results_y2025m02 OWNER TO k3l_user;

--
-- Name: k3l_channel_openrank_results_y2025m03; Type: TABLE; Schema: public; Owner: k3l_user
--

CREATE TABLE public.k3l_channel_openrank_results_y2025m03 (
    channel_domain_id integer NOT NULL,
    fid bigint NOT NULL,
    channel_id text NOT NULL,
    req_id text NOT NULL,
    score real NOT NULL,
    rank bigint NOT NULL,
    insert_ts timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.k3l_channel_openrank_results_y2025m03 OWNER TO k3l_user;

--
-- Name: k3l_channel_points_allowlist; Type: TABLE; Schema: public; Owner: k3l_user
--

CREATE TABLE public.k3l_channel_points_allowlist (
    channel_id text NOT NULL,
    is_allowed boolean DEFAULT true NOT NULL,
    insert_ts timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.k3l_channel_points_allowlist OWNER TO k3l_user;

--
-- Name: k3l_channel_points_bal; Type: TABLE; Schema: public; Owner: k3l_user
--

CREATE TABLE public.k3l_channel_points_bal (
    fid bigint NOT NULL,
    channel_id text NOT NULL,
    balance numeric NOT NULL,
    latest_earnings numeric NOT NULL,
    insert_ts timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    update_ts timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    latest_score real NOT NULL,
    latest_adj_score real NOT NULL
);


ALTER TABLE public.k3l_channel_points_bal OWNER TO k3l_user;

--
-- Name: k3l_channel_points_bal_old; Type: TABLE; Schema: public; Owner: k3l_user
--

CREATE TABLE public.k3l_channel_points_bal_old (
    fid bigint NOT NULL,
    channel_id text NOT NULL,
    balance numeric NOT NULL,
    latest_earnings numeric NOT NULL,
    insert_ts timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    update_ts timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    latest_score real NOT NULL,
    latest_adj_score real NOT NULL
);


ALTER TABLE public.k3l_channel_points_bal_old OWNER TO k3l_user;

--
-- Name: k3l_channel_points_log; Type: TABLE; Schema: public; Owner: k3l_user
--

CREATE TABLE public.k3l_channel_points_log (
    fid bigint NOT NULL,
    channel_id text NOT NULL,
    earnings numeric NOT NULL,
    model_name text NOT NULL,
    insert_ts timestamp with time zone DEFAULT CURRENT_TIMESTAMP
)
PARTITION BY RANGE (insert_ts);


ALTER TABLE public.k3l_channel_points_log OWNER TO k3l_user;

--
-- Name: k3l_channel_points_log_y2024m12; Type: TABLE; Schema: public; Owner: k3l_user
--

CREATE TABLE public.k3l_channel_points_log_y2024m12 (
    fid bigint NOT NULL,
    channel_id text NOT NULL,
    earnings numeric NOT NULL,
    model_name text NOT NULL,
    insert_ts timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.k3l_channel_points_log_y2024m12 OWNER TO k3l_user;

--
-- Name: k3l_channel_points_log_y2025m01; Type: TABLE; Schema: public; Owner: k3l_user
--

CREATE TABLE public.k3l_channel_points_log_y2025m01 (
    fid bigint NOT NULL,
    channel_id text NOT NULL,
    earnings numeric NOT NULL,
    model_name text NOT NULL,
    insert_ts timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.k3l_channel_points_log_y2025m01 OWNER TO k3l_user;

--
-- Name: k3l_channel_points_log_y2025m02; Type: TABLE; Schema: public; Owner: k3l_user
--

CREATE TABLE public.k3l_channel_points_log_y2025m02 (
    fid bigint NOT NULL,
    channel_id text NOT NULL,
    earnings numeric NOT NULL,
    model_name text NOT NULL,
    insert_ts timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.k3l_channel_points_log_y2025m02 OWNER TO k3l_user;

--
-- Name: k3l_channel_points_log_y2025m03; Type: TABLE; Schema: public; Owner: k3l_user
--

CREATE TABLE public.k3l_channel_points_log_y2025m03 (
    fid bigint NOT NULL,
    channel_id text NOT NULL,
    earnings numeric NOT NULL,
    model_name text NOT NULL,
    insert_ts timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.k3l_channel_points_log_y2025m03 OWNER TO k3l_user;

--
-- Name: k3l_channel_rank; Type: MATERIALIZED VIEW; Schema: public; Owner: k3l_user
--

CREATE MATERIALIZED VIEW public.k3l_channel_rank AS
 SELECT row_number() OVER () AS pseudo_id,
    channel_id,
    fid,
    score,
    rank,
    compute_ts,
    strategy_name
   FROM public.k3l_channel_fids cfids
  WITH NO DATA;


ALTER MATERIALIZED VIEW public.k3l_channel_rank OWNER TO k3l_user;

--
-- Name: k3l_channel_rewards_config; Type: TABLE; Schema: public; Owner: k3l_user
--

CREATE TABLE public.k3l_channel_rewards_config (
    channel_id text NOT NULL,
    is_ranked boolean DEFAULT true NOT NULL,
    is_points boolean DEFAULT false NOT NULL,
    is_tokens boolean DEFAULT false NOT NULL,
    token_airdrop_budget bigint DEFAULT 25000000 NOT NULL,
    token_daily_budget bigint DEFAULT 434981 NOT NULL,
    token_tax_pct numeric DEFAULT 0.02 NOT NULL,
    insert_ts timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    update_ts timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    total_supply bigint DEFAULT 1000000000 NOT NULL,
    creator_cut smallint DEFAULT 500 NOT NULL,
    vesting_months smallint DEFAULT 36 NOT NULL,
    airdrop_pmil smallint DEFAULT 50 NOT NULL,
    community_supply bigint DEFAULT 500000000 NOT NULL,
    symbol text
);


ALTER TABLE public.k3l_channel_rewards_config OWNER TO k3l_user;

--
-- Name: k3l_channel_tokens_bal; Type: TABLE; Schema: public; Owner: k3l_user
--

CREATE TABLE public.k3l_channel_tokens_bal (
    fid bigint NOT NULL,
    channel_id text NOT NULL,
    balance bigint NOT NULL,
    latest_earnings bigint NOT NULL,
    insert_ts timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    update_ts timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.k3l_channel_tokens_bal OWNER TO k3l_user;

--
-- Name: k3l_channel_tokens_log; Type: TABLE; Schema: public; Owner: k3l_user
--

CREATE TABLE public.k3l_channel_tokens_log (
    fid bigint NOT NULL,
    channel_id text NOT NULL,
    amt bigint NOT NULL,
    latest_points real NOT NULL,
    points_ts timestamp without time zone NOT NULL,
    dist_id integer NOT NULL,
    dist_status public.tokens_dist_status,
    insert_ts timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    update_ts timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    fid_address text,
    dist_reason text,
    txn_hash text,
    batch_id smallint NOT NULL
)
PARTITION BY RANGE (points_ts);


ALTER TABLE public.k3l_channel_tokens_log OWNER TO k3l_user;

--
-- Name: k3l_channel_tokens_log_y2024m12; Type: TABLE; Schema: public; Owner: k3l_user
--

CREATE TABLE public.k3l_channel_tokens_log_y2024m12 (
    fid bigint NOT NULL,
    channel_id text NOT NULL,
    amt bigint NOT NULL,
    latest_points real NOT NULL,
    points_ts timestamp without time zone NOT NULL,
    dist_id integer NOT NULL,
    dist_status public.tokens_dist_status,
    insert_ts timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    update_ts timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    fid_address text,
    dist_reason text,
    txn_hash text,
    batch_id smallint NOT NULL
);


ALTER TABLE public.k3l_channel_tokens_log_y2024m12 OWNER TO k3l_user;

--
-- Name: k3l_channel_tokens_log_y2025m01; Type: TABLE; Schema: public; Owner: k3l_user
--

CREATE TABLE public.k3l_channel_tokens_log_y2025m01 (
    fid bigint NOT NULL,
    channel_id text NOT NULL,
    amt bigint NOT NULL,
    latest_points real NOT NULL,
    points_ts timestamp without time zone NOT NULL,
    dist_id integer NOT NULL,
    dist_status public.tokens_dist_status,
    insert_ts timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    update_ts timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    fid_address text,
    dist_reason text,
    txn_hash text,
    batch_id smallint NOT NULL
);


ALTER TABLE public.k3l_channel_tokens_log_y2025m01 OWNER TO k3l_user;

--
-- Name: k3l_channel_tokens_log_y2025m02; Type: TABLE; Schema: public; Owner: k3l_user
--

CREATE TABLE public.k3l_channel_tokens_log_y2025m02 (
    fid bigint NOT NULL,
    channel_id text NOT NULL,
    amt bigint NOT NULL,
    latest_points real NOT NULL,
    points_ts timestamp without time zone NOT NULL,
    dist_id integer NOT NULL,
    dist_status public.tokens_dist_status,
    insert_ts timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    update_ts timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    fid_address text,
    dist_reason text,
    txn_hash text,
    batch_id smallint NOT NULL
);


ALTER TABLE public.k3l_channel_tokens_log_y2025m02 OWNER TO k3l_user;

--
-- Name: k3l_channel_tokens_log_y2025m03; Type: TABLE; Schema: public; Owner: k3l_user
--

CREATE TABLE public.k3l_channel_tokens_log_y2025m03 (
    fid bigint NOT NULL,
    channel_id text NOT NULL,
    amt bigint NOT NULL,
    latest_points real NOT NULL,
    points_ts timestamp without time zone NOT NULL,
    dist_id integer NOT NULL,
    dist_status public.tokens_dist_status,
    insert_ts timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    update_ts timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    fid_address text,
    dist_reason text,
    txn_hash text,
    batch_id smallint NOT NULL
);


ALTER TABLE public.k3l_channel_tokens_log_y2025m03 OWNER TO k3l_user;

--
-- Name: k3l_degen_tips; Type: TABLE; Schema: public; Owner: k3l_user
--

CREATE TABLE public.k3l_degen_tips (
    id integer NOT NULL,
    cast_hash bytea NOT NULL,
    parent_hash bytea NOT NULL,
    fid bigint NOT NULL,
    parent_fid bigint NOT NULL,
    degen_amount numeric NOT NULL,
    parsed_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    "timestamp" timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    parent_timestamp timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE public.k3l_degen_tips OWNER TO k3l_user;

--
-- Name: k3l_degen_tips_id_seq; Type: SEQUENCE; Schema: public; Owner: k3l_user
--

CREATE SEQUENCE public.k3l_degen_tips_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.k3l_degen_tips_id_seq OWNER TO k3l_user;

--
-- Name: k3l_degen_tips_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: k3l_user
--

ALTER SEQUENCE public.k3l_degen_tips_id_seq OWNED BY public.k3l_degen_tips.id;


--
-- Name: k3l_url_labels; Type: TABLE; Schema: public; Owner: k3l_user
--

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


ALTER TABLE public.k3l_url_labels OWNER TO k3l_user;

SET default_tablespace = morespace;

--
-- Name: k3l_frame_interaction; Type: MATERIALIZED VIEW; Schema: public; Owner: k3l_user; Tablespace: morespace
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
     JOIN public.k3l_cast_embed_url_mapping url_map ON (((url_map.cast_id = casts.id) AND (casts.deleted_at IS NULL))))
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
     JOIN public.reactions ON (((reactions.target_hash = casts.hash) AND (reactions.reaction_type = 2) AND (casts.deleted_at IS NULL))))
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
     JOIN public.reactions ON (((reactions.target_hash = casts.hash) AND (reactions.reaction_type = 1) AND (casts.deleted_at IS NULL))))
     JOIN public.k3l_cast_embed_url_mapping url_map ON ((casts.id = url_map.cast_id)))
     JOIN public.k3l_url_labels urls ON (((urls.url_id = url_map.url_id) AND ((urls.category)::text = 'frame'::text))))
  GROUP BY reactions.fid, 'like'::text, urls.url_id, ((((((urls.scheme || '://'::text) ||
        CASE
            WHEN (urls.subdomain <> ''::text) THEN (urls.subdomain || '.'::text)
            ELSE ''::text
        END) || urls.domain) || '.'::text) || (urls.tld)::text) || urls.path)
  WITH NO DATA;


ALTER MATERIALIZED VIEW public.k3l_frame_interaction OWNER TO k3l_user;

SET default_tablespace = '';

--
-- Name: k3l_rank; Type: MATERIALIZED VIEW; Schema: public; Owner: k3l_user
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


ALTER MATERIALIZED VIEW public.k3l_rank OWNER TO k3l_user;

--
-- Name: k3l_recent_frame_interaction; Type: MATERIALIZED VIEW; Schema: public; Owner: k3l_user
--

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
     JOIN public.k3l_cast_embed_url_mapping url_map ON (((url_map.cast_id = casts.id) AND (casts.deleted_at IS NULL))))
     JOIN public.k3l_url_labels urls ON (((urls.url_id = url_map.url_id) AND ((urls.category)::text = 'frame'::text))))
  WHERE ((casts."timestamp" >= (now() - '30 days'::interval)) AND (casts."timestamp" <= now()))
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
     JOIN public.reactions ON (((reactions.target_hash = casts.hash) AND (reactions.reaction_type = 2) AND (casts.deleted_at IS NULL))))
     JOIN public.k3l_cast_embed_url_mapping url_map ON ((casts.id = url_map.cast_id)))
     JOIN public.k3l_url_labels urls ON (((urls.url_id = url_map.url_id) AND ((urls.category)::text = 'frame'::text))))
  WHERE ((casts."timestamp" >= (now() - '30 days'::interval)) AND (casts."timestamp" <= now()))
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
     JOIN public.reactions ON (((reactions.target_hash = casts.hash) AND (reactions.reaction_type = 1) AND (casts.deleted_at IS NULL))))
     JOIN public.k3l_cast_embed_url_mapping url_map ON ((casts.id = url_map.cast_id)))
     JOIN public.k3l_url_labels urls ON (((urls.url_id = url_map.url_id) AND ((urls.category)::text = 'frame'::text))))
  WHERE ((casts."timestamp" >= (now() - '30 days'::interval)) AND (casts."timestamp" <= now()))
  GROUP BY reactions.fid, 'like'::text, urls.url_id, ((((((urls.scheme || '://'::text) ||
        CASE
            WHEN (urls.subdomain <> ''::text) THEN (urls.subdomain || '.'::text)
            ELSE ''::text
        END) || urls.domain) || '.'::text) || (urls.tld)::text) || urls.path)
  WITH NO DATA;


ALTER MATERIALIZED VIEW public.k3l_recent_frame_interaction OWNER TO k3l_user;

--
-- Name: k3l_recent_parent_casts; Type: MATERIALIZED VIEW; Schema: public; Owner: k3l_user
--

CREATE MATERIALIZED VIEW public.k3l_recent_parent_casts AS
 SELECT id,
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
   FROM public.casts
  WHERE ((parent_hash IS NULL) AND (deleted_at IS NULL) AND (("timestamp" >= (now() - '30 days'::interval)) AND ("timestamp" <= now())))
  WITH NO DATA;


ALTER MATERIALIZED VIEW public.k3l_recent_parent_casts OWNER TO k3l_user;

--
-- Name: k3l_recent_parent_casts_old; Type: MATERIALIZED VIEW; Schema: public; Owner: k3l_user
--

CREATE MATERIALIZED VIEW public.k3l_recent_parent_casts_old AS
 SELECT id,
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
   FROM public.casts
  WHERE ((parent_hash IS NULL) AND (deleted_at IS NULL) AND (("timestamp" >= (now() - '5 days'::interval)) AND ("timestamp" <= now())))
  WITH NO DATA;


ALTER MATERIALIZED VIEW public.k3l_recent_parent_casts_old OWNER TO k3l_user;

--
-- Name: k3l_top_casters; Type: TABLE; Schema: public; Owner: k3l_user
--

CREATE TABLE public.k3l_top_casters (
    i bigint NOT NULL,
    v double precision NOT NULL,
    date_iso date NOT NULL,
    cast_hash bytea
);


ALTER TABLE public.k3l_top_casters OWNER TO k3l_user;

--
-- Name: k3l_top_spammers; Type: TABLE; Schema: public; Owner: k3l_user
--

CREATE TABLE public.k3l_top_spammers (
    fid bigint NOT NULL,
    display_name text NOT NULL,
    total_outgoing bigint NOT NULL,
    spammer_score double precision NOT NULL,
    total_parent_casts bigint NOT NULL,
    total_replies_with_parent_hash bigint NOT NULL,
    global_openrank_score double precision NOT NULL,
    global_rank bigint NOT NULL,
    total_global_rank_rows bigint NOT NULL,
    date_iso date NOT NULL
);


ALTER TABLE public.k3l_top_spammers OWNER TO k3l_user;

--
-- Name: k3l_url_labels_url_id_seq; Type: SEQUENCE; Schema: public; Owner: k3l_user
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
-- Name: localtrust_stats_v2; Type: TABLE; Schema: public; Owner: k3l_user
--

CREATE TABLE public.localtrust_stats_v2 (
    date date,
    strategy_id_row_count bigint,
    strategy_id_mean double precision,
    strategy_id_stddev double precision,
    strategy_id_range double precision,
    strategy_id integer,
    insert_ts timestamp without time zone
);


ALTER TABLE public.localtrust_stats_v2 OWNER TO k3l_user;

--
-- Name: pretrust; Type: TABLE; Schema: public; Owner: k3l_user
--

CREATE TABLE public.pretrust (
    fid bigint NOT NULL,
    fname text NOT NULL,
    fid_active_tier integer NOT NULL,
    fid_active_tier_name text NOT NULL,
    data_source character varying(32) DEFAULT 'Dune'::character varying,
    insert_ts timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.pretrust OWNER TO k3l_user;

--
-- Name: pretrust_v2; Type: TABLE; Schema: public; Owner: k3l_user
--

CREATE TABLE public.pretrust_v2 (
    fid bigint,
    fname text,
    fid_active_tier integer,
    fid_active_tier_name text,
    data_source character varying(32),
    insert_ts timestamp without time zone,
    strategy_id bigint
);


ALTER TABLE public.pretrust_v2 OWNER TO k3l_user;

--
-- Name: tmp_globaltrust_v2; Type: TABLE; Schema: public; Owner: k3l_user
--

CREATE UNLOGGED TABLE public.tmp_globaltrust_v2 (
    strategy_id integer,
    i bigint,
    v real,
    date date
);


ALTER TABLE public.tmp_globaltrust_v2 OWNER TO k3l_user;

--
-- Name: k3l_cast_action_y2024m12; Type: TABLE ATTACH; Schema: public; Owner: k3l_user
--

ALTER TABLE ONLY public.k3l_cast_action ATTACH PARTITION public.k3l_cast_action_y2024m12 FOR VALUES FROM ('2024-12-01 00:00:00') TO ('2025-01-01 00:00:00');


--
-- Name: k3l_cast_action_y2025m01; Type: TABLE ATTACH; Schema: public; Owner: k3l_user
--

ALTER TABLE ONLY public.k3l_cast_action ATTACH PARTITION public.k3l_cast_action_y2025m01 FOR VALUES FROM ('2025-01-01 00:00:00') TO ('2025-02-01 00:00:00');


--
-- Name: k3l_cast_action_y2025m02; Type: TABLE ATTACH; Schema: public; Owner: k3l_user
--

ALTER TABLE ONLY public.k3l_cast_action ATTACH PARTITION public.k3l_cast_action_y2025m02 FOR VALUES FROM ('2025-02-01 00:00:00') TO ('2025-03-01 00:00:00');


--
-- Name: k3l_cast_action_y2025m03; Type: TABLE ATTACH; Schema: public; Owner: k3l_user
--

ALTER TABLE ONLY public.k3l_cast_action ATTACH PARTITION public.k3l_cast_action_y2025m03 FOR VALUES FROM ('2025-03-01 00:00:00') TO ('2025-04-01 00:00:00');


--
-- Name: k3l_channel_openrank_results_y2024m11; Type: TABLE ATTACH; Schema: public; Owner: k3l_user
--

ALTER TABLE ONLY public.k3l_channel_openrank_results ATTACH PARTITION public.k3l_channel_openrank_results_y2024m11 FOR VALUES FROM ('2024-11-01 00:00:00') TO ('2024-12-01 00:00:00');


--
-- Name: k3l_channel_openrank_results_y2024m12; Type: TABLE ATTACH; Schema: public; Owner: k3l_user
--

ALTER TABLE ONLY public.k3l_channel_openrank_results ATTACH PARTITION public.k3l_channel_openrank_results_y2024m12 FOR VALUES FROM ('2024-12-01 00:00:00') TO ('2025-01-01 00:00:00');


--
-- Name: k3l_channel_openrank_results_y2025m01; Type: TABLE ATTACH; Schema: public; Owner: k3l_user
--

ALTER TABLE ONLY public.k3l_channel_openrank_results ATTACH PARTITION public.k3l_channel_openrank_results_y2025m01 FOR VALUES FROM ('2025-01-01 00:00:00') TO ('2025-02-01 00:00:00');


--
-- Name: k3l_channel_openrank_results_y2025m02; Type: TABLE ATTACH; Schema: public; Owner: k3l_user
--

ALTER TABLE ONLY public.k3l_channel_openrank_results ATTACH PARTITION public.k3l_channel_openrank_results_y2025m02 FOR VALUES FROM ('2025-02-01 00:00:00') TO ('2025-03-01 00:00:00');


--
-- Name: k3l_channel_openrank_results_y2025m03; Type: TABLE ATTACH; Schema: public; Owner: k3l_user
--

ALTER TABLE ONLY public.k3l_channel_openrank_results ATTACH PARTITION public.k3l_channel_openrank_results_y2025m03 FOR VALUES FROM ('2025-03-01 00:00:00') TO ('2025-04-01 00:00:00');


--
-- Name: k3l_channel_points_log_y2024m12; Type: TABLE ATTACH; Schema: public; Owner: k3l_user
--

ALTER TABLE ONLY public.k3l_channel_points_log ATTACH PARTITION public.k3l_channel_points_log_y2024m12 FOR VALUES FROM ('2024-12-01 00:00:00+00') TO ('2025-01-01 00:00:00+00');


--
-- Name: k3l_channel_points_log_y2025m01; Type: TABLE ATTACH; Schema: public; Owner: k3l_user
--

ALTER TABLE ONLY public.k3l_channel_points_log ATTACH PARTITION public.k3l_channel_points_log_y2025m01 FOR VALUES FROM ('2025-01-01 00:00:00+00') TO ('2025-02-01 00:00:00+00');


--
-- Name: k3l_channel_points_log_y2025m02; Type: TABLE ATTACH; Schema: public; Owner: k3l_user
--

ALTER TABLE ONLY public.k3l_channel_points_log ATTACH PARTITION public.k3l_channel_points_log_y2025m02 FOR VALUES FROM ('2025-02-01 00:00:00+00') TO ('2025-03-01 00:00:00+00');


--
-- Name: k3l_channel_points_log_y2025m03; Type: TABLE ATTACH; Schema: public; Owner: k3l_user
--

ALTER TABLE ONLY public.k3l_channel_points_log ATTACH PARTITION public.k3l_channel_points_log_y2025m03 FOR VALUES FROM ('2025-03-01 00:00:00+00') TO ('2025-04-01 00:00:00+00');


--
-- Name: k3l_channel_tokens_log_y2024m12; Type: TABLE ATTACH; Schema: public; Owner: k3l_user
--

ALTER TABLE ONLY public.k3l_channel_tokens_log ATTACH PARTITION public.k3l_channel_tokens_log_y2024m12 FOR VALUES FROM ('2024-12-01 00:00:00') TO ('2025-01-01 00:00:00');


--
-- Name: k3l_channel_tokens_log_y2025m01; Type: TABLE ATTACH; Schema: public; Owner: k3l_user
--

ALTER TABLE ONLY public.k3l_channel_tokens_log ATTACH PARTITION public.k3l_channel_tokens_log_y2025m01 FOR VALUES FROM ('2025-01-01 00:00:00') TO ('2025-02-01 00:00:00');


--
-- Name: k3l_channel_tokens_log_y2025m02; Type: TABLE ATTACH; Schema: public; Owner: k3l_user
--

ALTER TABLE ONLY public.k3l_channel_tokens_log ATTACH PARTITION public.k3l_channel_tokens_log_y2025m02 FOR VALUES FROM ('2025-02-01 00:00:00') TO ('2025-03-01 00:00:00');


--
-- Name: k3l_channel_tokens_log_y2025m03; Type: TABLE ATTACH; Schema: public; Owner: k3l_user
--

ALTER TABLE ONLY public.k3l_channel_tokens_log ATTACH PARTITION public.k3l_channel_tokens_log_y2025m03 FOR VALUES FROM ('2025-03-01 00:00:00') TO ('2025-04-01 00:00:00');


--
-- Name: k3l_degen_tips id; Type: DEFAULT; Schema: public; Owner: k3l_user
--

ALTER TABLE ONLY public.k3l_degen_tips ALTER COLUMN id SET DEFAULT nextval('public.k3l_degen_tips_id_seq'::regclass);


--
-- Name: pretrust fid_insert_ts_unique; Type: CONSTRAINT; Schema: public; Owner: k3l_user
--

ALTER TABLE ONLY public.pretrust
    ADD CONSTRAINT fid_insert_ts_unique UNIQUE (fid, insert_ts);


--
-- Name: globaltrust_config globaltrust_config_pkey; Type: CONSTRAINT; Schema: public; Owner: k3l_user
--

ALTER TABLE ONLY public.globaltrust_config
    ADD CONSTRAINT globaltrust_config_pkey PRIMARY KEY (strategy_id, date);


SET default_tablespace = morespace;

--
-- Name: globaltrust globaltrust_strategy_name_date_i_unique; Type: CONSTRAINT; Schema: public; Owner: k3l_user; Tablespace: morespace
--

ALTER TABLE ONLY public.globaltrust
    ADD CONSTRAINT globaltrust_strategy_name_date_i_unique UNIQUE (strategy_id, date, i);


SET default_tablespace = '';

--
-- Name: k3l_channel_domains k3l_channel_domains_channel_id_category_key; Type: CONSTRAINT; Schema: public; Owner: k3l_user
--

ALTER TABLE ONLY public.k3l_channel_domains
    ADD CONSTRAINT k3l_channel_domains_channel_id_category_key UNIQUE (channel_id, category);


--
-- Name: k3l_channel_domains k3l_channel_domains_domain_key; Type: CONSTRAINT; Schema: public; Owner: k3l_user
--

ALTER TABLE ONLY public.k3l_channel_domains
    ADD CONSTRAINT k3l_channel_domains_domain_key UNIQUE (domain);


--
-- Name: k3l_channel_points_allowlist k3l_channel_points_allowlist_ch_uniq; Type: CONSTRAINT; Schema: public; Owner: k3l_user
--

ALTER TABLE ONLY public.k3l_channel_points_allowlist
    ADD CONSTRAINT k3l_channel_points_allowlist_ch_uniq UNIQUE (channel_id);


--
-- Name: k3l_channel_rewards_config k3l_channel_rewards_config_ch_unq; Type: CONSTRAINT; Schema: public; Owner: k3l_user
--

ALTER TABLE ONLY public.k3l_channel_rewards_config
    ADD CONSTRAINT k3l_channel_rewards_config_ch_unq UNIQUE (channel_id);


--
-- Name: k3l_degen_tips k3l_degen_tips_pkey; Type: CONSTRAINT; Schema: public; Owner: k3l_user
--

ALTER TABLE ONLY public.k3l_degen_tips
    ADD CONSTRAINT k3l_degen_tips_pkey PRIMARY KEY (id);


--
-- Name: k3l_url_labels k3l_url_labels_pkey; Type: CONSTRAINT; Schema: public; Owner: k3l_user
--

ALTER TABLE ONLY public.k3l_url_labels
    ADD CONSTRAINT k3l_url_labels_pkey PRIMARY KEY (url_id);


--
-- Name: k3l_url_labels k3l_url_labels_url_unique; Type: CONSTRAINT; Schema: public; Owner: k3l_user
--

ALTER TABLE ONLY public.k3l_url_labels
    ADD CONSTRAINT k3l_url_labels_url_unique UNIQUE (url);


--
-- Name: k3l_channel_domains openrank_reqs_pkey; Type: CONSTRAINT; Schema: public; Owner: k3l_user
--

ALTER TABLE ONLY public.k3l_channel_domains
    ADD CONSTRAINT openrank_reqs_pkey PRIMARY KEY (id);


--
-- Name: k3l_degen_tips unique_cast_hash; Type: CONSTRAINT; Schema: public; Owner: k3l_user
--

ALTER TABLE ONLY public.k3l_degen_tips
    ADD CONSTRAINT unique_cast_hash UNIQUE (cast_hash);


--
-- Name: cura_hidden_fids_ch_fid_act_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX cura_hidden_fids_ch_fid_act_idx ON public.cura_hidden_fids USING btree (channel_id, hidden_fid, is_active);


SET default_tablespace = morespace;

--
-- Name: globaltrust_id_idx; Type: INDEX; Schema: public; Owner: k3l_user; Tablespace: morespace
--

CREATE INDEX globaltrust_id_idx ON public.globaltrust USING btree (strategy_id);


SET default_tablespace = '';

--
-- Name: idx_automod_data_action_ch_userid; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX idx_automod_data_action_ch_userid ON public.automod_data USING btree (action, channel_id, affected_userid);


--
-- Name: idx_degen_tips_fid; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX idx_degen_tips_fid ON public.k3l_degen_tips USING btree (fid);


--
-- Name: idx_degen_tips_parent_fid; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX idx_degen_tips_parent_fid ON public.k3l_degen_tips USING btree (parent_fid);


--
-- Name: idx_degen_tips_parent_hash; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX idx_degen_tips_parent_hash ON public.k3l_degen_tips USING btree (parent_hash);


--
-- Name: idx_degen_tips_parent_timestamp; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX idx_degen_tips_parent_timestamp ON public.k3l_degen_tips USING btree (parent_timestamp);


--
-- Name: idx_degen_tips_timestamp; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX idx_degen_tips_timestamp ON public.k3l_degen_tips USING btree ("timestamp");


--
-- Name: idx_k3l_cast_action_cast_hash_action_ts; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX idx_k3l_cast_action_cast_hash_action_ts ON ONLY public.k3l_cast_action USING btree (cast_hash, action_ts);


--
-- Name: idx_k3l_cast_action_covering; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX idx_k3l_cast_action_covering ON ONLY public.k3l_cast_action USING btree (cast_hash, action_ts, fid) INCLUDE (casted, replied, recasted, liked);


--
-- Name: idx_k3l_degen_tips_parent_hash_fid; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX idx_k3l_degen_tips_parent_hash_fid ON public.k3l_degen_tips USING btree (parent_hash, fid);


--
-- Name: k3l_cast_action_cast_hash_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_cast_hash_idx ON ONLY public.k3l_cast_action USING btree (cast_hash);


--
-- Name: k3l_cast_action_fid_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_fid_idx ON ONLY public.k3l_cast_action USING btree (fid);


--
-- Name: k3l_cast_action_fid_ts_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_fid_ts_idx ON ONLY public.k3l_cast_action USING btree (fid, action_ts);


--
-- Name: k3l_cast_action_timestamp_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_timestamp_idx ON ONLY public.k3l_cast_action USING btree (action_ts);


--
-- Name: k3l_cast_action_unique_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE UNIQUE INDEX k3l_cast_action_unique_idx ON ONLY public.k3l_cast_action USING btree (cast_hash, fid, action_ts);


--
-- Name: k3l_cast_action_y2024m12_action_ts_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_y2024m12_action_ts_idx ON public.k3l_cast_action_y2024m12 USING btree (action_ts);


--
-- Name: k3l_cast_action_y2024m12_cast_hash_action_ts_fid_casted_rep_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_y2024m12_cast_hash_action_ts_fid_casted_rep_idx ON public.k3l_cast_action_y2024m12 USING btree (cast_hash, action_ts, fid) INCLUDE (casted, replied, recasted, liked);


--
-- Name: k3l_cast_action_y2024m12_cast_hash_action_ts_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_y2024m12_cast_hash_action_ts_idx ON public.k3l_cast_action_y2024m12 USING btree (cast_hash, action_ts);


--
-- Name: k3l_cast_action_y2024m12_cast_hash_fid_action_ts_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE UNIQUE INDEX k3l_cast_action_y2024m12_cast_hash_fid_action_ts_idx ON public.k3l_cast_action_y2024m12 USING btree (cast_hash, fid, action_ts);


--
-- Name: k3l_cast_action_y2024m12_cast_hash_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_y2024m12_cast_hash_idx ON public.k3l_cast_action_y2024m12 USING btree (cast_hash);


--
-- Name: k3l_cast_action_y2024m12_fid_action_ts_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_y2024m12_fid_action_ts_idx ON public.k3l_cast_action_y2024m12 USING btree (fid, action_ts);


--
-- Name: k3l_cast_action_y2024m12_fid_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_y2024m12_fid_idx ON public.k3l_cast_action_y2024m12 USING btree (fid);


--
-- Name: k3l_cast_action_y2025m01_action_ts_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_y2025m01_action_ts_idx ON public.k3l_cast_action_y2025m01 USING btree (action_ts);


--
-- Name: k3l_cast_action_y2025m01_cast_hash_action_ts_fid_casted_rep_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_y2025m01_cast_hash_action_ts_fid_casted_rep_idx ON public.k3l_cast_action_y2025m01 USING btree (cast_hash, action_ts, fid) INCLUDE (casted, replied, recasted, liked);


--
-- Name: k3l_cast_action_y2025m01_cast_hash_action_ts_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_y2025m01_cast_hash_action_ts_idx ON public.k3l_cast_action_y2025m01 USING btree (cast_hash, action_ts);


--
-- Name: k3l_cast_action_y2025m01_cast_hash_fid_action_ts_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE UNIQUE INDEX k3l_cast_action_y2025m01_cast_hash_fid_action_ts_idx ON public.k3l_cast_action_y2025m01 USING btree (cast_hash, fid, action_ts);


--
-- Name: k3l_cast_action_y2025m01_cast_hash_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_y2025m01_cast_hash_idx ON public.k3l_cast_action_y2025m01 USING btree (cast_hash);


--
-- Name: k3l_cast_action_y2025m01_fid_action_ts_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_y2025m01_fid_action_ts_idx ON public.k3l_cast_action_y2025m01 USING btree (fid, action_ts);


--
-- Name: k3l_cast_action_y2025m01_fid_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_y2025m01_fid_idx ON public.k3l_cast_action_y2025m01 USING btree (fid);


--
-- Name: k3l_cast_action_y2025m02_action_ts_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_y2025m02_action_ts_idx ON public.k3l_cast_action_y2025m02 USING btree (action_ts);


--
-- Name: k3l_cast_action_y2025m02_cast_hash_action_ts_fid_casted_rep_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_y2025m02_cast_hash_action_ts_fid_casted_rep_idx ON public.k3l_cast_action_y2025m02 USING btree (cast_hash, action_ts, fid) INCLUDE (casted, replied, recasted, liked);


--
-- Name: k3l_cast_action_y2025m02_cast_hash_action_ts_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_y2025m02_cast_hash_action_ts_idx ON public.k3l_cast_action_y2025m02 USING btree (cast_hash, action_ts);


--
-- Name: k3l_cast_action_y2025m02_cast_hash_fid_action_ts_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE UNIQUE INDEX k3l_cast_action_y2025m02_cast_hash_fid_action_ts_idx ON public.k3l_cast_action_y2025m02 USING btree (cast_hash, fid, action_ts);


--
-- Name: k3l_cast_action_y2025m02_cast_hash_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_y2025m02_cast_hash_idx ON public.k3l_cast_action_y2025m02 USING btree (cast_hash);


--
-- Name: k3l_cast_action_y2025m02_fid_action_ts_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_y2025m02_fid_action_ts_idx ON public.k3l_cast_action_y2025m02 USING btree (fid, action_ts);


--
-- Name: k3l_cast_action_y2025m02_fid_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_y2025m02_fid_idx ON public.k3l_cast_action_y2025m02 USING btree (fid);


--
-- Name: k3l_cast_action_y2025m03_action_ts_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_y2025m03_action_ts_idx ON public.k3l_cast_action_y2025m03 USING btree (action_ts);


--
-- Name: k3l_cast_action_y2025m03_cast_hash_action_ts_fid_casted_rep_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_y2025m03_cast_hash_action_ts_fid_casted_rep_idx ON public.k3l_cast_action_y2025m03 USING btree (cast_hash, action_ts, fid) INCLUDE (casted, replied, recasted, liked);


--
-- Name: k3l_cast_action_y2025m03_cast_hash_action_ts_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_y2025m03_cast_hash_action_ts_idx ON public.k3l_cast_action_y2025m03 USING btree (cast_hash, action_ts);


--
-- Name: k3l_cast_action_y2025m03_cast_hash_fid_action_ts_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE UNIQUE INDEX k3l_cast_action_y2025m03_cast_hash_fid_action_ts_idx ON public.k3l_cast_action_y2025m03 USING btree (cast_hash, fid, action_ts);


--
-- Name: k3l_cast_action_y2025m03_cast_hash_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_y2025m03_cast_hash_idx ON public.k3l_cast_action_y2025m03 USING btree (cast_hash);


--
-- Name: k3l_cast_action_y2025m03_fid_action_ts_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_y2025m03_fid_action_ts_idx ON public.k3l_cast_action_y2025m03 USING btree (fid, action_ts);


--
-- Name: k3l_cast_action_y2025m03_fid_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_y2025m03_fid_idx ON public.k3l_cast_action_y2025m03 USING btree (fid);


--
-- Name: k3l_cast_embed_url_mapping_cast_id_index; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_embed_url_mapping_cast_id_index ON public.k3l_cast_embed_url_mapping USING btree (cast_id);


--
-- Name: k3l_cast_embed_url_mapping_url_id_index; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_embed_url_mapping_url_id_index ON public.k3l_cast_embed_url_mapping USING btree (url_id);


--
-- Name: k3l_ch_or_results_ch_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_ch_or_results_ch_idx ON ONLY public.k3l_channel_openrank_results USING btree (channel_id);


--
-- Name: k3l_ch_or_results_fid_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_ch_or_results_fid_idx ON ONLY public.k3l_channel_openrank_results USING btree (fid);


--
-- Name: k3l_channel_openrank_results_y2024m11_channel_id_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_channel_openrank_results_y2024m11_channel_id_idx ON public.k3l_channel_openrank_results_y2024m11 USING btree (channel_id);


--
-- Name: k3l_channel_openrank_results_y2024m11_fid_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_channel_openrank_results_y2024m11_fid_idx ON public.k3l_channel_openrank_results_y2024m11 USING btree (fid);


--
-- Name: k3l_channel_openrank_results_y2024m12_channel_id_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_channel_openrank_results_y2024m12_channel_id_idx ON public.k3l_channel_openrank_results_y2024m12 USING btree (channel_id);


--
-- Name: k3l_channel_openrank_results_y2024m12_fid_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_channel_openrank_results_y2024m12_fid_idx ON public.k3l_channel_openrank_results_y2024m12 USING btree (fid);


--
-- Name: k3l_channel_openrank_results_y2025m01_channel_id_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_channel_openrank_results_y2025m01_channel_id_idx ON public.k3l_channel_openrank_results_y2025m01 USING btree (channel_id);


--
-- Name: k3l_channel_openrank_results_y2025m01_fid_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_channel_openrank_results_y2025m01_fid_idx ON public.k3l_channel_openrank_results_y2025m01 USING btree (fid);


--
-- Name: k3l_channel_openrank_results_y2025m02_channel_id_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_channel_openrank_results_y2025m02_channel_id_idx ON public.k3l_channel_openrank_results_y2025m02 USING btree (channel_id);


--
-- Name: k3l_channel_openrank_results_y2025m02_fid_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_channel_openrank_results_y2025m02_fid_idx ON public.k3l_channel_openrank_results_y2025m02 USING btree (fid);


--
-- Name: k3l_channel_openrank_results_y2025m03_channel_id_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_channel_openrank_results_y2025m03_channel_id_idx ON public.k3l_channel_openrank_results_y2025m03 USING btree (channel_id);


--
-- Name: k3l_channel_openrank_results_y2025m03_fid_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_channel_openrank_results_y2025m03_fid_idx ON public.k3l_channel_openrank_results_y2025m03 USING btree (fid);


--
-- Name: k3l_channel_points_bal_new_channel_id_balance_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_channel_points_bal_new_channel_id_balance_idx ON public.k3l_channel_points_bal USING btree (channel_id, balance);


--
-- Name: k3l_channel_points_bal_new_channel_id_balance_idx1; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_channel_points_bal_new_channel_id_balance_idx1 ON public.k3l_channel_points_bal_old USING btree (channel_id, balance);


--
-- Name: k3l_channel_points_bal_new_channel_id_fid_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_channel_points_bal_new_channel_id_fid_idx ON public.k3l_channel_points_bal USING btree (channel_id, fid);


--
-- Name: k3l_channel_points_bal_new_channel_id_fid_idx1; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_channel_points_bal_new_channel_id_fid_idx1 ON public.k3l_channel_points_bal_old USING btree (channel_id, fid);


--
-- Name: k3l_channel_points_log_ch_fid_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_channel_points_log_ch_fid_idx ON ONLY public.k3l_channel_points_log USING btree (channel_id, fid);


--
-- Name: k3l_channel_points_log_ch_mdl_fid_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_channel_points_log_ch_mdl_fid_idx ON ONLY public.k3l_channel_points_log USING btree (channel_id, model_name, fid);


--
-- Name: k3l_channel_points_log_ch_mdl_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_channel_points_log_ch_mdl_idx ON ONLY public.k3l_channel_points_log USING btree (channel_id, model_name);


--
-- Name: k3l_channel_points_log_y2024m12_channel_id_fid_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_channel_points_log_y2024m12_channel_id_fid_idx ON public.k3l_channel_points_log_y2024m12 USING btree (channel_id, fid);


--
-- Name: k3l_channel_points_log_y2024m12_channel_id_model_name_fid_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_channel_points_log_y2024m12_channel_id_model_name_fid_idx ON public.k3l_channel_points_log_y2024m12 USING btree (channel_id, model_name, fid);


--
-- Name: k3l_channel_points_log_y2024m12_channel_id_model_name_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_channel_points_log_y2024m12_channel_id_model_name_idx ON public.k3l_channel_points_log_y2024m12 USING btree (channel_id, model_name);


--
-- Name: k3l_channel_points_log_y2025m01_channel_id_fid_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_channel_points_log_y2025m01_channel_id_fid_idx ON public.k3l_channel_points_log_y2025m01 USING btree (channel_id, fid);


--
-- Name: k3l_channel_points_log_y2025m01_channel_id_model_name_fid_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_channel_points_log_y2025m01_channel_id_model_name_fid_idx ON public.k3l_channel_points_log_y2025m01 USING btree (channel_id, model_name, fid);


--
-- Name: k3l_channel_points_log_y2025m01_channel_id_model_name_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_channel_points_log_y2025m01_channel_id_model_name_idx ON public.k3l_channel_points_log_y2025m01 USING btree (channel_id, model_name);


--
-- Name: k3l_channel_points_log_y2025m02_channel_id_fid_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_channel_points_log_y2025m02_channel_id_fid_idx ON public.k3l_channel_points_log_y2025m02 USING btree (channel_id, fid);


--
-- Name: k3l_channel_points_log_y2025m02_channel_id_model_name_fid_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_channel_points_log_y2025m02_channel_id_model_name_fid_idx ON public.k3l_channel_points_log_y2025m02 USING btree (channel_id, model_name, fid);


--
-- Name: k3l_channel_points_log_y2025m02_channel_id_model_name_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_channel_points_log_y2025m02_channel_id_model_name_idx ON public.k3l_channel_points_log_y2025m02 USING btree (channel_id, model_name);


--
-- Name: k3l_channel_points_log_y2025m03_channel_id_fid_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_channel_points_log_y2025m03_channel_id_fid_idx ON public.k3l_channel_points_log_y2025m03 USING btree (channel_id, fid);


--
-- Name: k3l_channel_points_log_y2025m03_channel_id_model_name_fid_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_channel_points_log_y2025m03_channel_id_model_name_fid_idx ON public.k3l_channel_points_log_y2025m03 USING btree (channel_id, model_name, fid);


--
-- Name: k3l_channel_points_log_y2025m03_channel_id_model_name_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_channel_points_log_y2025m03_channel_id_model_name_idx ON public.k3l_channel_points_log_y2025m03 USING btree (channel_id, model_name);


--
-- Name: k3l_channel_rank_ch_fid_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_channel_rank_ch_fid_idx ON public.k3l_channel_rank USING btree (channel_id, fid);


--
-- Name: k3l_channel_rank_ch_strat_fid_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_channel_rank_ch_strat_fid_idx ON public.k3l_channel_rank USING btree (channel_id, strategy_name, fid);


--
-- Name: k3l_channel_rank_ch_strat_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_channel_rank_ch_strat_idx ON public.k3l_channel_rank USING btree (channel_id, strategy_name);


--
-- Name: k3l_channel_rank_fid_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_channel_rank_fid_idx ON public.k3l_channel_rank USING btree (fid);


--
-- Name: k3l_channel_rank_rank_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_channel_rank_rank_idx ON public.k3l_channel_rank USING btree (rank);


--
-- Name: k3l_channel_rank_unq_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE UNIQUE INDEX k3l_channel_rank_unq_idx ON public.k3l_channel_rank USING btree (pseudo_id);


--
-- Name: k3l_channel_rewards_config_ch_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_channel_rewards_config_ch_idx ON public.k3l_channel_rewards_config USING btree (channel_id);


--
-- Name: k3l_channel_tokens_bal_ch_fid_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE UNIQUE INDEX k3l_channel_tokens_bal_ch_fid_idx ON public.k3l_channel_tokens_bal USING btree (channel_id, fid);


--
-- Name: k3l_channel_tokens_log_ch_fid_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_channel_tokens_log_ch_fid_idx ON ONLY public.k3l_channel_tokens_log USING btree (channel_id, fid);


--
-- Name: k3l_channel_tokens_log_dist_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_channel_tokens_log_dist_idx ON ONLY public.k3l_channel_tokens_log USING btree (dist_id);


--
-- Name: k3l_channel_tokens_log_pending_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_channel_tokens_log_pending_idx ON ONLY public.k3l_channel_tokens_log USING btree (dist_status) WHERE (dist_status <> 'success'::public.tokens_dist_status);


--
-- Name: k3l_channel_tokens_log_y2024m12_channel_id_fid_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_channel_tokens_log_y2024m12_channel_id_fid_idx ON public.k3l_channel_tokens_log_y2024m12 USING btree (channel_id, fid);


--
-- Name: k3l_channel_tokens_log_y2024m12_req_id_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_channel_tokens_log_y2024m12_req_id_idx ON public.k3l_channel_tokens_log_y2024m12 USING btree (dist_id);


--
-- Name: k3l_channel_tokens_log_y2024m12_req_status_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_channel_tokens_log_y2024m12_req_status_idx ON public.k3l_channel_tokens_log_y2024m12 USING btree (dist_status) WHERE (dist_status <> 'success'::public.tokens_dist_status);


--
-- Name: k3l_channel_tokens_log_y2025m01_channel_id_fid_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_channel_tokens_log_y2025m01_channel_id_fid_idx ON public.k3l_channel_tokens_log_y2025m01 USING btree (channel_id, fid);


--
-- Name: k3l_channel_tokens_log_y2025m01_req_id_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_channel_tokens_log_y2025m01_req_id_idx ON public.k3l_channel_tokens_log_y2025m01 USING btree (dist_id);


--
-- Name: k3l_channel_tokens_log_y2025m01_req_status_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_channel_tokens_log_y2025m01_req_status_idx ON public.k3l_channel_tokens_log_y2025m01 USING btree (dist_status) WHERE (dist_status <> 'success'::public.tokens_dist_status);


--
-- Name: k3l_channel_tokens_log_y2025m02_channel_id_fid_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_channel_tokens_log_y2025m02_channel_id_fid_idx ON public.k3l_channel_tokens_log_y2025m02 USING btree (channel_id, fid);


--
-- Name: k3l_channel_tokens_log_y2025m02_req_id_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_channel_tokens_log_y2025m02_req_id_idx ON public.k3l_channel_tokens_log_y2025m02 USING btree (dist_id);


--
-- Name: k3l_channel_tokens_log_y2025m02_req_status_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_channel_tokens_log_y2025m02_req_status_idx ON public.k3l_channel_tokens_log_y2025m02 USING btree (dist_status) WHERE (dist_status <> 'success'::public.tokens_dist_status);


--
-- Name: k3l_channel_tokens_log_y2025m03_channel_id_fid_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_channel_tokens_log_y2025m03_channel_id_fid_idx ON public.k3l_channel_tokens_log_y2025m03 USING btree (channel_id, fid);


--
-- Name: k3l_channel_tokens_log_y2025m03_req_id_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_channel_tokens_log_y2025m03_req_id_idx ON public.k3l_channel_tokens_log_y2025m03 USING btree (dist_id);


--
-- Name: k3l_channel_tokens_log_y2025m03_req_status_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_channel_tokens_log_y2025m03_req_status_idx ON public.k3l_channel_tokens_log_y2025m03 USING btree (dist_status) WHERE (dist_status <> 'success'::public.tokens_dist_status);


SET default_tablespace = morespace;

--
-- Name: k3l_frame_interaction_fid_action_type_url_idunique; Type: INDEX; Schema: public; Owner: k3l_user; Tablespace: morespace
--

CREATE UNIQUE INDEX k3l_frame_interaction_fid_action_type_url_idunique ON public.k3l_frame_interaction USING btree (fid, action_type, url_id) NULLS NOT DISTINCT;


--
-- Name: k3l_frame_interaction_fid_index; Type: INDEX; Schema: public; Owner: k3l_user; Tablespace: morespace
--

CREATE INDEX k3l_frame_interaction_fid_index ON public.k3l_frame_interaction USING btree (fid);


--
-- Name: k3l_frame_interaction_url_id_index; Type: INDEX; Schema: public; Owner: k3l_user; Tablespace: morespace
--

CREATE INDEX k3l_frame_interaction_url_id_index ON public.k3l_frame_interaction USING btree (url_id);


--
-- Name: k3l_frame_interaction_url_index; Type: INDEX; Schema: public; Owner: k3l_user; Tablespace: morespace
--

CREATE INDEX k3l_frame_interaction_url_index ON public.k3l_frame_interaction USING btree (url);


SET default_tablespace = '';

--
-- Name: k3l_rank_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE UNIQUE INDEX k3l_rank_idx ON public.k3l_rank USING btree (pseudo_id);


--
-- Name: k3l_rank_profile_id_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_rank_profile_id_idx ON public.k3l_rank USING btree (profile_id);


--
-- Name: k3l_rank_profile_id_strategy_id_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_rank_profile_id_strategy_id_idx ON public.k3l_rank USING btree (profile_id, strategy_id);


--
-- Name: k3l_rank_strategy_id_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_rank_strategy_id_idx ON public.k3l_rank USING btree (strategy_id);


--
-- Name: k3l_recent_frame_interaction_fid_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_recent_frame_interaction_fid_idx ON public.k3l_recent_frame_interaction USING btree (fid);


--
-- Name: k3l_recent_frame_interaction_fid_type_url_unq; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE UNIQUE INDEX k3l_recent_frame_interaction_fid_type_url_unq ON public.k3l_recent_frame_interaction USING btree (fid, action_type, url_id) NULLS NOT DISTINCT;


--
-- Name: k3l_recent_frame_interaction_url_id_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_recent_frame_interaction_url_id_idx ON public.k3l_recent_frame_interaction USING btree (url_id);


--
-- Name: k3l_recent_frame_interaction_url_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_recent_frame_interaction_url_idx ON public.k3l_recent_frame_interaction USING btree (url);


--
-- Name: k3l_recent_parent_casts_hash_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_recent_parent_casts_hash_idx ON public.k3l_recent_parent_casts USING btree (hash);


--
-- Name: k3l_recent_parent_casts_hash_idx_old; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_recent_parent_casts_hash_idx_old ON public.k3l_recent_parent_casts_old USING btree (hash);


--
-- Name: k3l_recent_parent_casts_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE UNIQUE INDEX k3l_recent_parent_casts_idx ON public.k3l_recent_parent_casts USING btree (id);


--
-- Name: k3l_recent_parent_casts_idx_old; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE UNIQUE INDEX k3l_recent_parent_casts_idx_old ON public.k3l_recent_parent_casts_old USING btree (id);


--
-- Name: k3l_url_labels_earliest_cast_dt_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_url_labels_earliest_cast_dt_idx ON public.k3l_url_labels USING btree (earliest_cast_dt);


--
-- Name: k3l_url_labels_latest_cast_dt_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_url_labels_latest_cast_dt_idx ON public.k3l_url_labels USING btree (latest_cast_dt);


--
-- Name: k3l_cast_action_y2024m12_action_ts_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_timestamp_idx ATTACH PARTITION public.k3l_cast_action_y2024m12_action_ts_idx;


--
-- Name: k3l_cast_action_y2024m12_cast_hash_action_ts_fid_casted_rep_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.idx_k3l_cast_action_covering ATTACH PARTITION public.k3l_cast_action_y2024m12_cast_hash_action_ts_fid_casted_rep_idx;


--
-- Name: k3l_cast_action_y2024m12_cast_hash_action_ts_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.idx_k3l_cast_action_cast_hash_action_ts ATTACH PARTITION public.k3l_cast_action_y2024m12_cast_hash_action_ts_idx;


--
-- Name: k3l_cast_action_y2024m12_cast_hash_fid_action_ts_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_unique_idx ATTACH PARTITION public.k3l_cast_action_y2024m12_cast_hash_fid_action_ts_idx;


--
-- Name: k3l_cast_action_y2024m12_cast_hash_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_cast_hash_idx ATTACH PARTITION public.k3l_cast_action_y2024m12_cast_hash_idx;


--
-- Name: k3l_cast_action_y2024m12_fid_action_ts_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_fid_ts_idx ATTACH PARTITION public.k3l_cast_action_y2024m12_fid_action_ts_idx;


--
-- Name: k3l_cast_action_y2024m12_fid_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_fid_idx ATTACH PARTITION public.k3l_cast_action_y2024m12_fid_idx;


--
-- Name: k3l_cast_action_y2025m01_action_ts_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_timestamp_idx ATTACH PARTITION public.k3l_cast_action_y2025m01_action_ts_idx;


--
-- Name: k3l_cast_action_y2025m01_cast_hash_action_ts_fid_casted_rep_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.idx_k3l_cast_action_covering ATTACH PARTITION public.k3l_cast_action_y2025m01_cast_hash_action_ts_fid_casted_rep_idx;


--
-- Name: k3l_cast_action_y2025m01_cast_hash_action_ts_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.idx_k3l_cast_action_cast_hash_action_ts ATTACH PARTITION public.k3l_cast_action_y2025m01_cast_hash_action_ts_idx;


--
-- Name: k3l_cast_action_y2025m01_cast_hash_fid_action_ts_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_unique_idx ATTACH PARTITION public.k3l_cast_action_y2025m01_cast_hash_fid_action_ts_idx;


--
-- Name: k3l_cast_action_y2025m01_cast_hash_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_cast_hash_idx ATTACH PARTITION public.k3l_cast_action_y2025m01_cast_hash_idx;


--
-- Name: k3l_cast_action_y2025m01_fid_action_ts_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_fid_ts_idx ATTACH PARTITION public.k3l_cast_action_y2025m01_fid_action_ts_idx;


--
-- Name: k3l_cast_action_y2025m01_fid_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_fid_idx ATTACH PARTITION public.k3l_cast_action_y2025m01_fid_idx;


--
-- Name: k3l_cast_action_y2025m02_action_ts_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_timestamp_idx ATTACH PARTITION public.k3l_cast_action_y2025m02_action_ts_idx;


--
-- Name: k3l_cast_action_y2025m02_cast_hash_action_ts_fid_casted_rep_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.idx_k3l_cast_action_covering ATTACH PARTITION public.k3l_cast_action_y2025m02_cast_hash_action_ts_fid_casted_rep_idx;


--
-- Name: k3l_cast_action_y2025m02_cast_hash_action_ts_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.idx_k3l_cast_action_cast_hash_action_ts ATTACH PARTITION public.k3l_cast_action_y2025m02_cast_hash_action_ts_idx;


--
-- Name: k3l_cast_action_y2025m02_cast_hash_fid_action_ts_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_unique_idx ATTACH PARTITION public.k3l_cast_action_y2025m02_cast_hash_fid_action_ts_idx;


--
-- Name: k3l_cast_action_y2025m02_cast_hash_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_cast_hash_idx ATTACH PARTITION public.k3l_cast_action_y2025m02_cast_hash_idx;


--
-- Name: k3l_cast_action_y2025m02_fid_action_ts_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_fid_ts_idx ATTACH PARTITION public.k3l_cast_action_y2025m02_fid_action_ts_idx;


--
-- Name: k3l_cast_action_y2025m02_fid_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_fid_idx ATTACH PARTITION public.k3l_cast_action_y2025m02_fid_idx;


--
-- Name: k3l_cast_action_y2025m03_action_ts_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_timestamp_idx ATTACH PARTITION public.k3l_cast_action_y2025m03_action_ts_idx;


--
-- Name: k3l_cast_action_y2025m03_cast_hash_action_ts_fid_casted_rep_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.idx_k3l_cast_action_covering ATTACH PARTITION public.k3l_cast_action_y2025m03_cast_hash_action_ts_fid_casted_rep_idx;


--
-- Name: k3l_cast_action_y2025m03_cast_hash_action_ts_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.idx_k3l_cast_action_cast_hash_action_ts ATTACH PARTITION public.k3l_cast_action_y2025m03_cast_hash_action_ts_idx;


--
-- Name: k3l_cast_action_y2025m03_cast_hash_fid_action_ts_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_unique_idx ATTACH PARTITION public.k3l_cast_action_y2025m03_cast_hash_fid_action_ts_idx;


--
-- Name: k3l_cast_action_y2025m03_cast_hash_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_cast_hash_idx ATTACH PARTITION public.k3l_cast_action_y2025m03_cast_hash_idx;


--
-- Name: k3l_cast_action_y2025m03_fid_action_ts_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_fid_ts_idx ATTACH PARTITION public.k3l_cast_action_y2025m03_fid_action_ts_idx;


--
-- Name: k3l_cast_action_y2025m03_fid_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_fid_idx ATTACH PARTITION public.k3l_cast_action_y2025m03_fid_idx;


--
-- Name: k3l_channel_openrank_results_y2024m11_channel_id_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_ch_or_results_ch_idx ATTACH PARTITION public.k3l_channel_openrank_results_y2024m11_channel_id_idx;


--
-- Name: k3l_channel_openrank_results_y2024m11_fid_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_ch_or_results_fid_idx ATTACH PARTITION public.k3l_channel_openrank_results_y2024m11_fid_idx;


--
-- Name: k3l_channel_openrank_results_y2024m12_channel_id_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_ch_or_results_ch_idx ATTACH PARTITION public.k3l_channel_openrank_results_y2024m12_channel_id_idx;


--
-- Name: k3l_channel_openrank_results_y2024m12_fid_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_ch_or_results_fid_idx ATTACH PARTITION public.k3l_channel_openrank_results_y2024m12_fid_idx;


--
-- Name: k3l_channel_openrank_results_y2025m01_channel_id_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_ch_or_results_ch_idx ATTACH PARTITION public.k3l_channel_openrank_results_y2025m01_channel_id_idx;


--
-- Name: k3l_channel_openrank_results_y2025m01_fid_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_ch_or_results_fid_idx ATTACH PARTITION public.k3l_channel_openrank_results_y2025m01_fid_idx;


--
-- Name: k3l_channel_openrank_results_y2025m02_channel_id_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_ch_or_results_ch_idx ATTACH PARTITION public.k3l_channel_openrank_results_y2025m02_channel_id_idx;


--
-- Name: k3l_channel_openrank_results_y2025m02_fid_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_ch_or_results_fid_idx ATTACH PARTITION public.k3l_channel_openrank_results_y2025m02_fid_idx;


--
-- Name: k3l_channel_openrank_results_y2025m03_channel_id_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_ch_or_results_ch_idx ATTACH PARTITION public.k3l_channel_openrank_results_y2025m03_channel_id_idx;


--
-- Name: k3l_channel_openrank_results_y2025m03_fid_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_ch_or_results_fid_idx ATTACH PARTITION public.k3l_channel_openrank_results_y2025m03_fid_idx;


--
-- Name: k3l_channel_points_log_y2024m12_channel_id_fid_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_channel_points_log_ch_fid_idx ATTACH PARTITION public.k3l_channel_points_log_y2024m12_channel_id_fid_idx;


--
-- Name: k3l_channel_points_log_y2024m12_channel_id_model_name_fid_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_channel_points_log_ch_mdl_fid_idx ATTACH PARTITION public.k3l_channel_points_log_y2024m12_channel_id_model_name_fid_idx;


--
-- Name: k3l_channel_points_log_y2024m12_channel_id_model_name_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_channel_points_log_ch_mdl_idx ATTACH PARTITION public.k3l_channel_points_log_y2024m12_channel_id_model_name_idx;


--
-- Name: k3l_channel_points_log_y2025m01_channel_id_fid_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_channel_points_log_ch_fid_idx ATTACH PARTITION public.k3l_channel_points_log_y2025m01_channel_id_fid_idx;


--
-- Name: k3l_channel_points_log_y2025m01_channel_id_model_name_fid_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_channel_points_log_ch_mdl_fid_idx ATTACH PARTITION public.k3l_channel_points_log_y2025m01_channel_id_model_name_fid_idx;


--
-- Name: k3l_channel_points_log_y2025m01_channel_id_model_name_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_channel_points_log_ch_mdl_idx ATTACH PARTITION public.k3l_channel_points_log_y2025m01_channel_id_model_name_idx;


--
-- Name: k3l_channel_points_log_y2025m02_channel_id_fid_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_channel_points_log_ch_fid_idx ATTACH PARTITION public.k3l_channel_points_log_y2025m02_channel_id_fid_idx;


--
-- Name: k3l_channel_points_log_y2025m02_channel_id_model_name_fid_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_channel_points_log_ch_mdl_fid_idx ATTACH PARTITION public.k3l_channel_points_log_y2025m02_channel_id_model_name_fid_idx;


--
-- Name: k3l_channel_points_log_y2025m02_channel_id_model_name_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_channel_points_log_ch_mdl_idx ATTACH PARTITION public.k3l_channel_points_log_y2025m02_channel_id_model_name_idx;


--
-- Name: k3l_channel_points_log_y2025m03_channel_id_fid_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_channel_points_log_ch_fid_idx ATTACH PARTITION public.k3l_channel_points_log_y2025m03_channel_id_fid_idx;


--
-- Name: k3l_channel_points_log_y2025m03_channel_id_model_name_fid_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_channel_points_log_ch_mdl_fid_idx ATTACH PARTITION public.k3l_channel_points_log_y2025m03_channel_id_model_name_fid_idx;


--
-- Name: k3l_channel_points_log_y2025m03_channel_id_model_name_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_channel_points_log_ch_mdl_idx ATTACH PARTITION public.k3l_channel_points_log_y2025m03_channel_id_model_name_idx;


--
-- Name: k3l_channel_tokens_log_y2024m12_channel_id_fid_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_channel_tokens_log_ch_fid_idx ATTACH PARTITION public.k3l_channel_tokens_log_y2024m12_channel_id_fid_idx;


--
-- Name: k3l_channel_tokens_log_y2024m12_req_id_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_channel_tokens_log_dist_idx ATTACH PARTITION public.k3l_channel_tokens_log_y2024m12_req_id_idx;


--
-- Name: k3l_channel_tokens_log_y2024m12_req_status_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_channel_tokens_log_pending_idx ATTACH PARTITION public.k3l_channel_tokens_log_y2024m12_req_status_idx;


--
-- Name: k3l_channel_tokens_log_y2025m01_channel_id_fid_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_channel_tokens_log_ch_fid_idx ATTACH PARTITION public.k3l_channel_tokens_log_y2025m01_channel_id_fid_idx;


--
-- Name: k3l_channel_tokens_log_y2025m01_req_id_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_channel_tokens_log_dist_idx ATTACH PARTITION public.k3l_channel_tokens_log_y2025m01_req_id_idx;


--
-- Name: k3l_channel_tokens_log_y2025m01_req_status_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_channel_tokens_log_pending_idx ATTACH PARTITION public.k3l_channel_tokens_log_y2025m01_req_status_idx;


--
-- Name: k3l_channel_tokens_log_y2025m02_channel_id_fid_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_channel_tokens_log_ch_fid_idx ATTACH PARTITION public.k3l_channel_tokens_log_y2025m02_channel_id_fid_idx;


--
-- Name: k3l_channel_tokens_log_y2025m02_req_id_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_channel_tokens_log_dist_idx ATTACH PARTITION public.k3l_channel_tokens_log_y2025m02_req_id_idx;


--
-- Name: k3l_channel_tokens_log_y2025m02_req_status_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_channel_tokens_log_pending_idx ATTACH PARTITION public.k3l_channel_tokens_log_y2025m02_req_status_idx;


--
-- Name: k3l_channel_tokens_log_y2025m03_channel_id_fid_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_channel_tokens_log_ch_fid_idx ATTACH PARTITION public.k3l_channel_tokens_log_y2025m03_channel_id_fid_idx;


--
-- Name: k3l_channel_tokens_log_y2025m03_req_id_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_channel_tokens_log_dist_idx ATTACH PARTITION public.k3l_channel_tokens_log_y2025m03_req_id_idx;


--
-- Name: k3l_channel_tokens_log_y2025m03_req_status_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_channel_tokens_log_pending_idx ATTACH PARTITION public.k3l_channel_tokens_log_y2025m03_req_status_idx;


--
-- Name: k3l_cast_embed_url_mapping k3l_cast_embed_url_mapping_cast_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: k3l_user
--

ALTER TABLE ONLY public.k3l_cast_embed_url_mapping
    ADD CONSTRAINT k3l_cast_embed_url_mapping_cast_id_fkey FOREIGN KEY (cast_id) REFERENCES public.casts(id) ON DELETE CASCADE;


--
-- Name: k3l_cast_embed_url_mapping k3l_cast_embed_url_mapping_url_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: k3l_user
--

ALTER TABLE ONLY public.k3l_cast_embed_url_mapping
    ADD CONSTRAINT k3l_cast_embed_url_mapping_url_id_fkey FOREIGN KEY (url_id) REFERENCES public.k3l_url_labels(url_id);


--
-- Name: k3l_channel_openrank_results k3l_channel_openrank_results_fkey; Type: FK CONSTRAINT; Schema: public; Owner: k3l_user
--

ALTER TABLE public.k3l_channel_openrank_results
    ADD CONSTRAINT k3l_channel_openrank_results_fkey FOREIGN KEY (channel_domain_id) REFERENCES public.k3l_channel_domains(id);


--
-- Name: TABLE automod_data; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.automod_data TO k3l_readonly;


--
-- Name: TABLE cura_hidden_fids; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.cura_hidden_fids TO k3l_readonly;


--
-- Name: TABLE globaltrust; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.globaltrust TO k3l_readonly;


--
-- Name: TABLE globaltrust_config; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.globaltrust_config TO k3l_readonly;


--
-- Name: TABLE k3l_cast_action; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.k3l_cast_action TO k3l_readonly;


--
-- Name: TABLE k3l_cast_action_y2025m02; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.k3l_cast_action_y2025m02 TO k3l_readonly;


--
-- Name: TABLE k3l_cast_action_y2025m03; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.k3l_cast_action_y2025m03 TO k3l_readonly;


--
-- Name: TABLE k3l_cast_embed_url_mapping; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.k3l_cast_embed_url_mapping TO k3l_readonly;


--
-- Name: TABLE k3l_channel_domains; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.k3l_channel_domains TO k3l_readonly;


--
-- Name: TABLE k3l_channel_fids_old; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.k3l_channel_fids_old TO k3l_readonly;


--
-- Name: TABLE k3l_channel_openrank_results; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.k3l_channel_openrank_results TO k3l_readonly;


--
-- Name: TABLE k3l_channel_openrank_results_y2024m11; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.k3l_channel_openrank_results_y2024m11 TO k3l_readonly;


--
-- Name: TABLE k3l_channel_openrank_results_y2024m12; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.k3l_channel_openrank_results_y2024m12 TO k3l_readonly;


--
-- Name: TABLE k3l_channel_openrank_results_y2025m01; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.k3l_channel_openrank_results_y2025m01 TO k3l_readonly;


--
-- Name: TABLE k3l_channel_openrank_results_y2025m02; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.k3l_channel_openrank_results_y2025m02 TO k3l_readonly;


--
-- Name: TABLE k3l_channel_openrank_results_y2025m03; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.k3l_channel_openrank_results_y2025m03 TO k3l_readonly;


--
-- Name: TABLE k3l_channel_points_allowlist; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.k3l_channel_points_allowlist TO k3l_readonly;


--
-- Name: TABLE k3l_channel_points_bal; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.k3l_channel_points_bal TO k3l_readonly;


--
-- Name: TABLE k3l_channel_points_bal_old; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.k3l_channel_points_bal_old TO k3l_readonly;


--
-- Name: TABLE k3l_channel_points_log; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.k3l_channel_points_log TO k3l_readonly;


--
-- Name: TABLE k3l_channel_points_log_y2024m12; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.k3l_channel_points_log_y2024m12 TO k3l_readonly;


--
-- Name: TABLE k3l_channel_points_log_y2025m01; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.k3l_channel_points_log_y2025m01 TO k3l_readonly;


--
-- Name: TABLE k3l_channel_points_log_y2025m02; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.k3l_channel_points_log_y2025m02 TO k3l_readonly;


--
-- Name: TABLE k3l_channel_points_log_y2025m03; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.k3l_channel_points_log_y2025m03 TO k3l_readonly;


--
-- Name: TABLE k3l_channel_rank; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.k3l_channel_rank TO k3l_readonly;


--
-- Name: TABLE k3l_channel_rewards_config; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.k3l_channel_rewards_config TO k3l_readonly;


--
-- Name: TABLE k3l_channel_tokens_bal; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.k3l_channel_tokens_bal TO k3l_readonly;


--
-- Name: TABLE k3l_channel_tokens_log; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.k3l_channel_tokens_log TO k3l_readonly;


--
-- Name: TABLE k3l_channel_tokens_log_y2024m12; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.k3l_channel_tokens_log_y2024m12 TO k3l_readonly;


--
-- Name: TABLE k3l_channel_tokens_log_y2025m01; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.k3l_channel_tokens_log_y2025m01 TO k3l_readonly;


--
-- Name: TABLE k3l_channel_tokens_log_y2025m02; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.k3l_channel_tokens_log_y2025m02 TO k3l_readonly;


--
-- Name: TABLE k3l_channel_tokens_log_y2025m03; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.k3l_channel_tokens_log_y2025m03 TO k3l_readonly;


--
-- Name: TABLE k3l_degen_tips; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT ON TABLE public.k3l_degen_tips TO PUBLIC;


--
-- Name: TABLE k3l_url_labels; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.k3l_url_labels TO k3l_readonly;


--
-- Name: TABLE k3l_frame_interaction; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.k3l_frame_interaction TO k3l_readonly;


--
-- Name: TABLE k3l_rank; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.k3l_rank TO k3l_readonly;


--
-- Name: TABLE k3l_recent_frame_interaction; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.k3l_recent_frame_interaction TO k3l_readonly;


--
-- Name: TABLE k3l_recent_parent_casts; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.k3l_recent_parent_casts TO k3l_readonly;


--
-- Name: TABLE k3l_recent_parent_casts_old; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.k3l_recent_parent_casts_old TO k3l_readonly;


--
-- Name: TABLE k3l_top_casters; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT ALL ON TABLE public.k3l_top_casters TO k3l_readonly;


--
-- Name: TABLE k3l_top_spammers; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT ALL ON TABLE public.k3l_top_spammers TO k3l_readonly;


--
-- Name: TABLE localtrust_stats_v2; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT ALL ON TABLE public.localtrust_stats_v2 TO k3l_readonly;


--
-- Name: TABLE pretrust; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.pretrust TO k3l_readonly;


--
-- Name: TABLE pretrust_v2; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT ALL ON TABLE public.pretrust_v2 TO k3l_readonly;


--
-- Name: TABLE tmp_globaltrust_v2; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.tmp_globaltrust_v2 TO k3l_readonly;


--
-- PostgreSQL database dump complete
--

