--
-- PostgreSQL database dump
--

-- Dumped from database version 17.2 (Ubuntu 17.2-1.pgdg24.04+1)
-- Dumped by pg_dump version 17.4 (Ubuntu 17.4-1.pgdg24.10+2)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: public; Type: SCHEMA; Schema: -; Owner: pg_database_owner
--

CREATE SCHEMA public;


ALTER SCHEMA public OWNER TO pg_database_owner;

--
-- Name: SCHEMA public; Type: COMMENT; Schema: -; Owner: pg_database_owner
--

COMMENT ON SCHEMA public IS 'standard public schema';


--
-- Name: channel_rank_status; Type: TYPE; Schema: public; Owner: k3l_user
--

CREATE TYPE public.channel_rank_status AS ENUM (
    'pending',
    'inprogress',
    'completed',
    'errored',
    'terminated'
);


ALTER TYPE public.channel_rank_status OWNER TO k3l_user;

--
-- Name: tokens_dist_status; Type: TYPE; Schema: public; Owner: k3l_user
--

CREATE TYPE public.tokens_dist_status AS ENUM (
    'submitted',
    'success',
    'failure'
);


ALTER TYPE public.tokens_dist_status OWNER TO k3l_user;

--
-- Name: end_week_9amoffset(timestamp without time zone, interval); Type: FUNCTION; Schema: public; Owner: k3l_user
--

CREATE FUNCTION public.end_week_9amoffset(timestamp without time zone, interval) RETURNS timestamp with time zone
    LANGUAGE sql IMMUTABLE
    AS $_$ 
    SELECT 
            date_trunc('week', $1 + $2 - '9 hours'::interval)  -- force to monday 9am
            - $2 + '9 hours'::interval -- revert force
            + '7 days'::interval - '1 seconds'::interval -- end of week
    $_$;


ALTER FUNCTION public.end_week_9amoffset(timestamp without time zone, interval) OWNER TO k3l_user;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: k3l_user
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


ALTER TABLE public.alembic_version OWNER TO k3l_user;

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
-- Name: balances; Type: TABLE; Schema: public; Owner: k3l_user
--

CREATE TABLE public.balances (
    chain_id integer NOT NULL,
    token_address bytea NOT NULL,
    wallet_address bytea NOT NULL,
    value numeric(62,0),
    block_number bigint,
    log_index bigint
);


ALTER TABLE public.balances OWNER TO k3l_user;

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

--
-- Name: globaltrust; Type: TABLE; Schema: public; Owner: k3l_user
--

CREATE UNLOGGED TABLE public.globaltrust (
    strategy_id integer,
    i bigint,
    v real,
    date date DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.globaltrust OWNER TO k3l_user;

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
-- Name: k3l_cast_action_v1; Type: TABLE; Schema: public; Owner: k3l_user
--

CREATE TABLE public.k3l_cast_action_v1 (
    channel_id text,
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


ALTER TABLE public.k3l_cast_action_v1 OWNER TO k3l_user;

--
-- Name: k3l_cast_action; Type: VIEW; Schema: public; Owner: k3l_user
--

CREATE VIEW public.k3l_cast_action AS
 SELECT channel_id,
    fid,
    cast_hash,
    casted,
    replied,
    recasted,
    liked,
    action_ts,
    created_at
   FROM public.k3l_cast_action_v1;


ALTER VIEW public.k3l_cast_action OWNER TO k3l_user;

--
-- Name: k3l_cast_action_v1_y2024m09; Type: TABLE; Schema: public; Owner: k3l_user
--

CREATE TABLE public.k3l_cast_action_v1_y2024m09 (
    channel_id text,
    fid bigint NOT NULL,
    cast_hash bytea NOT NULL,
    casted integer NOT NULL,
    replied integer NOT NULL,
    recasted integer NOT NULL,
    liked integer NOT NULL,
    action_ts timestamp without time zone NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE public.k3l_cast_action_v1_y2024m09 OWNER TO k3l_user;

--
-- Name: k3l_cast_action_v1_y2024m10; Type: TABLE; Schema: public; Owner: k3l_user
--

CREATE TABLE public.k3l_cast_action_v1_y2024m10 (
    channel_id text,
    fid bigint NOT NULL,
    cast_hash bytea NOT NULL,
    casted integer NOT NULL,
    replied integer NOT NULL,
    recasted integer NOT NULL,
    liked integer NOT NULL,
    action_ts timestamp without time zone NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE public.k3l_cast_action_v1_y2024m10 OWNER TO k3l_user;

--
-- Name: k3l_cast_action_v1_y2024m11; Type: TABLE; Schema: public; Owner: k3l_user
--

CREATE TABLE public.k3l_cast_action_v1_y2024m11 (
    channel_id text,
    fid bigint NOT NULL,
    cast_hash bytea NOT NULL,
    casted integer NOT NULL,
    replied integer NOT NULL,
    recasted integer NOT NULL,
    liked integer NOT NULL,
    action_ts timestamp without time zone NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE public.k3l_cast_action_v1_y2024m11 OWNER TO k3l_user;

--
-- Name: k3l_cast_action_v1_y2024m12; Type: TABLE; Schema: public; Owner: k3l_user
--

CREATE TABLE public.k3l_cast_action_v1_y2024m12 (
    channel_id text,
    fid bigint NOT NULL,
    cast_hash bytea NOT NULL,
    casted integer NOT NULL,
    replied integer NOT NULL,
    recasted integer NOT NULL,
    liked integer NOT NULL,
    action_ts timestamp without time zone NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE public.k3l_cast_action_v1_y2024m12 OWNER TO k3l_user;

--
-- Name: k3l_cast_action_v1_y2025m01; Type: TABLE; Schema: public; Owner: k3l_user
--

CREATE TABLE public.k3l_cast_action_v1_y2025m01 (
    channel_id text,
    fid bigint NOT NULL,
    cast_hash bytea NOT NULL,
    casted integer NOT NULL,
    replied integer NOT NULL,
    recasted integer NOT NULL,
    liked integer NOT NULL,
    action_ts timestamp without time zone NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE public.k3l_cast_action_v1_y2025m01 OWNER TO k3l_user;

--
-- Name: k3l_cast_action_v1_y2025m02; Type: TABLE; Schema: public; Owner: k3l_user
--

CREATE TABLE public.k3l_cast_action_v1_y2025m02 (
    channel_id text,
    fid bigint NOT NULL,
    cast_hash bytea NOT NULL,
    casted integer NOT NULL,
    replied integer NOT NULL,
    recasted integer NOT NULL,
    liked integer NOT NULL,
    action_ts timestamp without time zone NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE public.k3l_cast_action_v1_y2025m02 OWNER TO k3l_user;

--
-- Name: k3l_cast_action_v1_y2025m03; Type: TABLE; Schema: public; Owner: k3l_user
--

CREATE TABLE public.k3l_cast_action_v1_y2025m03 (
    channel_id text,
    fid bigint NOT NULL,
    cast_hash bytea NOT NULL,
    casted integer NOT NULL,
    replied integer NOT NULL,
    recasted integer NOT NULL,
    liked integer NOT NULL,
    action_ts timestamp without time zone NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE public.k3l_cast_action_v1_y2025m03 OWNER TO k3l_user;

--
-- Name: k3l_cast_action_v1_y2025m04; Type: TABLE; Schema: public; Owner: k3l_user
--

CREATE TABLE public.k3l_cast_action_v1_y2025m04 (
    channel_id text,
    fid bigint NOT NULL,
    cast_hash bytea NOT NULL,
    casted integer NOT NULL,
    replied integer NOT NULL,
    recasted integer NOT NULL,
    liked integer NOT NULL,
    action_ts timestamp without time zone NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE public.k3l_cast_action_v1_y2025m04 OWNER TO k3l_user;

--
-- Name: k3l_cast_action_v1_y2025m05; Type: TABLE; Schema: public; Owner: k3l_user
--

CREATE TABLE public.k3l_cast_action_v1_y2025m05 (
    channel_id text,
    fid bigint NOT NULL,
    cast_hash bytea NOT NULL,
    casted integer NOT NULL,
    replied integer NOT NULL,
    recasted integer NOT NULL,
    liked integer NOT NULL,
    action_ts timestamp without time zone NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE public.k3l_cast_action_v1_y2025m05 OWNER TO k3l_user;

--
-- Name: k3l_cast_action_v1_y2025m06; Type: TABLE; Schema: public; Owner: k3l_user
--

CREATE TABLE public.k3l_cast_action_v1_y2025m06 (
    channel_id text,
    fid bigint NOT NULL,
    cast_hash bytea NOT NULL,
    casted integer NOT NULL,
    replied integer NOT NULL,
    recasted integer NOT NULL,
    liked integer NOT NULL,
    action_ts timestamp without time zone NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE public.k3l_cast_action_v1_y2025m06 OWNER TO k3l_user;

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
-- Name: k3l_channel_metrics; Type: TABLE; Schema: public; Owner: k3l_user
--

CREATE TABLE public.k3l_channel_metrics (
    metric_ts timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    channel_id text NOT NULL,
    metric text NOT NULL,
    int_value bigint,
    float_value numeric,
    insert_ts timestamp with time zone DEFAULT CURRENT_TIMESTAMP
)
PARTITION BY RANGE (metric_ts);


ALTER TABLE public.k3l_channel_metrics OWNER TO k3l_user;

--
-- Name: k3l_channel_metrics_y2025m01; Type: TABLE; Schema: public; Owner: k3l_user
--

CREATE TABLE public.k3l_channel_metrics_y2025m01 (
    metric_ts timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    channel_id text NOT NULL,
    metric text NOT NULL,
    int_value bigint,
    float_value numeric,
    insert_ts timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.k3l_channel_metrics_y2025m01 OWNER TO k3l_user;

--
-- Name: k3l_channel_metrics_y2025m02; Type: TABLE; Schema: public; Owner: k3l_user
--

CREATE TABLE public.k3l_channel_metrics_y2025m02 (
    metric_ts timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    channel_id text NOT NULL,
    metric text NOT NULL,
    int_value bigint,
    float_value numeric,
    insert_ts timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.k3l_channel_metrics_y2025m02 OWNER TO k3l_user;

--
-- Name: k3l_channel_metrics_y2025m03; Type: TABLE; Schema: public; Owner: k3l_user
--

CREATE TABLE public.k3l_channel_metrics_y2025m03 (
    metric_ts timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    channel_id text NOT NULL,
    metric text NOT NULL,
    int_value bigint,
    float_value numeric,
    insert_ts timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.k3l_channel_metrics_y2025m03 OWNER TO k3l_user;

--
-- Name: k3l_channel_metrics_y2025m04; Type: TABLE; Schema: public; Owner: k3l_user
--

CREATE TABLE public.k3l_channel_metrics_y2025m04 (
    metric_ts timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    channel_id text NOT NULL,
    metric text NOT NULL,
    int_value bigint,
    float_value numeric,
    insert_ts timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.k3l_channel_metrics_y2025m04 OWNER TO k3l_user;

--
-- Name: k3l_channel_metrics_y2025m05; Type: TABLE; Schema: public; Owner: k3l_user
--

CREATE TABLE public.k3l_channel_metrics_y2025m05 (
    metric_ts timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    channel_id text NOT NULL,
    metric text NOT NULL,
    int_value bigint,
    float_value numeric,
    insert_ts timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.k3l_channel_metrics_y2025m05 OWNER TO k3l_user;

--
-- Name: k3l_channel_metrics_y2025m06; Type: TABLE; Schema: public; Owner: k3l_user
--

CREATE TABLE public.k3l_channel_metrics_y2025m06 (
    metric_ts timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    channel_id text NOT NULL,
    metric text NOT NULL,
    int_value bigint,
    float_value numeric,
    insert_ts timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.k3l_channel_metrics_y2025m06 OWNER TO k3l_user;

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
    insert_ts timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    notes text
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
    insert_ts timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    notes text
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
    insert_ts timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    notes text
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
    insert_ts timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    notes text
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
    insert_ts timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    notes text
);


ALTER TABLE public.k3l_channel_points_log_y2025m03 OWNER TO k3l_user;

--
-- Name: k3l_channel_points_log_y2025m04; Type: TABLE; Schema: public; Owner: k3l_user
--

CREATE TABLE public.k3l_channel_points_log_y2025m04 (
    fid bigint NOT NULL,
    channel_id text NOT NULL,
    earnings numeric NOT NULL,
    model_name text NOT NULL,
    insert_ts timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    notes text
);


ALTER TABLE public.k3l_channel_points_log_y2025m04 OWNER TO k3l_user;

--
-- Name: k3l_channel_points_log_y2025m05; Type: TABLE; Schema: public; Owner: k3l_user
--

CREATE TABLE public.k3l_channel_points_log_y2025m05 (
    fid bigint NOT NULL,
    channel_id text NOT NULL,
    earnings numeric NOT NULL,
    model_name text NOT NULL,
    insert_ts timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    notes text
);


ALTER TABLE public.k3l_channel_points_log_y2025m05 OWNER TO k3l_user;

--
-- Name: k3l_channel_points_log_y2025m06; Type: TABLE; Schema: public; Owner: k3l_user
--

CREATE TABLE public.k3l_channel_points_log_y2025m06 (
    fid bigint NOT NULL,
    channel_id text NOT NULL,
    earnings numeric NOT NULL,
    model_name text NOT NULL,
    insert_ts timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    notes text
);


ALTER TABLE public.k3l_channel_points_log_y2025m06 OWNER TO k3l_user;

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
-- Name: k3l_channel_rank_log; Type: TABLE; Schema: public; Owner: k3l_user
--

CREATE TABLE public.k3l_channel_rank_log (
    run_id text NOT NULL,
    num_days smallint NOT NULL,
    channel_id text NOT NULL,
    batch_id smallint NOT NULL,
    rank_status public.channel_rank_status DEFAULT 'pending'::public.channel_rank_status,
    num_fids integer,
    elapsed_time_ms bigint,
    run_ts timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    inactive_seeds bigint[]
)
PARTITION BY RANGE (run_ts);


ALTER TABLE public.k3l_channel_rank_log OWNER TO k3l_user;

--
-- Name: k3l_channel_rank_log_y2025m03; Type: TABLE; Schema: public; Owner: k3l_user
--

CREATE TABLE public.k3l_channel_rank_log_y2025m03 (
    run_id text NOT NULL,
    num_days smallint NOT NULL,
    channel_id text NOT NULL,
    batch_id smallint NOT NULL,
    rank_status public.channel_rank_status DEFAULT 'pending'::public.channel_rank_status,
    num_fids integer,
    elapsed_time_ms bigint,
    run_ts timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    inactive_seeds bigint[]
);


ALTER TABLE public.k3l_channel_rank_log_y2025m03 OWNER TO k3l_user;

--
-- Name: k3l_channel_rank_log_y2025m04; Type: TABLE; Schema: public; Owner: k3l_user
--

CREATE TABLE public.k3l_channel_rank_log_y2025m04 (
    run_id text NOT NULL,
    num_days smallint NOT NULL,
    channel_id text NOT NULL,
    batch_id smallint NOT NULL,
    rank_status public.channel_rank_status DEFAULT 'pending'::public.channel_rank_status,
    num_fids integer,
    elapsed_time_ms bigint,
    run_ts timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    inactive_seeds bigint[]
);


ALTER TABLE public.k3l_channel_rank_log_y2025m04 OWNER TO k3l_user;

--
-- Name: k3l_channel_rank_log_y2025m05; Type: TABLE; Schema: public; Owner: k3l_user
--

CREATE TABLE public.k3l_channel_rank_log_y2025m05 (
    run_id text NOT NULL,
    num_days smallint NOT NULL,
    channel_id text NOT NULL,
    batch_id smallint NOT NULL,
    rank_status public.channel_rank_status DEFAULT 'pending'::public.channel_rank_status,
    num_fids integer,
    elapsed_time_ms bigint,
    run_ts timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    inactive_seeds bigint[]
);


ALTER TABLE public.k3l_channel_rank_log_y2025m05 OWNER TO k3l_user;

--
-- Name: k3l_channel_rank_log_y2025m06; Type: TABLE; Schema: public; Owner: k3l_user
--

CREATE TABLE public.k3l_channel_rank_log_y2025m06 (
    run_id text NOT NULL,
    num_days smallint NOT NULL,
    channel_id text NOT NULL,
    batch_id smallint NOT NULL,
    rank_status public.channel_rank_status DEFAULT 'pending'::public.channel_rank_status,
    num_fids integer,
    elapsed_time_ms bigint,
    run_ts timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    inactive_seeds bigint[]
);


ALTER TABLE public.k3l_channel_rank_log_y2025m06 OWNER TO k3l_user;

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
-- Name: k3l_channel_tokens_log_y2025m04; Type: TABLE; Schema: public; Owner: k3l_user
--

CREATE TABLE public.k3l_channel_tokens_log_y2025m04 (
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


ALTER TABLE public.k3l_channel_tokens_log_y2025m04 OWNER TO k3l_user;

--
-- Name: k3l_channel_tokens_log_y2025m05; Type: TABLE; Schema: public; Owner: k3l_user
--

CREATE TABLE public.k3l_channel_tokens_log_y2025m05 (
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


ALTER TABLE public.k3l_channel_tokens_log_y2025m05 OWNER TO k3l_user;

--
-- Name: k3l_channel_tokens_log_y2025m06; Type: TABLE; Schema: public; Owner: k3l_user
--

CREATE TABLE public.k3l_channel_tokens_log_y2025m06 (
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


ALTER TABLE public.k3l_channel_tokens_log_y2025m06 OWNER TO k3l_user;

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
   FROM neynarv2.casts
  WHERE ((parent_hash IS NULL) AND (deleted_at IS NULL) AND (("timestamp" >= (now() - '30 days'::interval)) AND ("timestamp" <= now())))
  WITH NO DATA;


ALTER MATERIALIZED VIEW public.k3l_recent_parent_casts OWNER TO k3l_user;

--
-- Name: verified_addresses; Type: VIEW; Schema: public; Owner: k3l_user
--

CREATE VIEW public.verified_addresses AS
 SELECT fid,
    "timestamp",
    address
   FROM neynarv3.verifications
  WHERE (deleted_at IS NULL);


ALTER VIEW public.verified_addresses OWNER TO k3l_user;

--
-- Name: k3l_token_holding_fids; Type: MATERIALIZED VIEW; Schema: public; Owner: k3l_user
--

CREATE MATERIALIZED VIEW public.k3l_token_holding_fids AS
 SELECT va.fid,
    b.token_address,
    sum(b.value) AS value
   FROM (public.balances b
     JOIN public.verified_addresses va ON ((b.wallet_address = va.address)))
  GROUP BY va.fid, b.token_address
 HAVING (sum(b.value) > (0)::numeric)
  WITH NO DATA;


ALTER MATERIALIZED VIEW public.k3l_token_holding_fids OWNER TO k3l_user;

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
-- Name: links; Type: VIEW; Schema: public; Owner: k3l_user
--

CREATE VIEW public.links AS
 SELECT id,
    fid,
    target_fid,
    "timestamp",
    created_at,
    updated_at,
    deleted_at,
    'follow'::text AS type,
    display_timestamp
   FROM neynarv3.follows;


ALTER VIEW public.links OWNER TO k3l_user;

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
-- Name: tokens_dist_seq; Type: SEQUENCE; Schema: public; Owner: k3l_user
--

CREATE SEQUENCE public.tokens_dist_seq
    START WITH 1896
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tokens_dist_seq OWNER TO k3l_user;

--
-- Name: verifications; Type: VIEW; Schema: public; Owner: k3l_user
--

CREATE VIEW public.verifications AS
 SELECT id,
    created_at,
    updated_at,
    deleted_at,
    "timestamp",
    fid,
    json_build_object('address', ('0x'::text || encode(address, 'hex'::text))) AS claim
   FROM neynarv3.verifications
  WHERE (deleted_at IS NULL);


ALTER VIEW public.verifications OWNER TO k3l_user;

--
-- Name: warpcast_channels_data; Type: VIEW; Schema: public; Owner: k3l_user
--

CREATE VIEW public.warpcast_channels_data AS
 SELECT channel_id AS id,
    url,
    description,
    image_url AS imageurl,
    lead_fid AS leadfid,
    moderator_fids AS moderatorfids,
    created_at AS createdat,
    follower_count AS followercount,
    "timestamp" AS insert_ts
   FROM neynarv2.channels;


ALTER VIEW public.warpcast_channels_data OWNER TO k3l_user;

--
-- Name: warpcast_followers; Type: VIEW; Schema: public; Owner: k3l_user
--

CREATE VIEW public.warpcast_followers AS
 SELECT fid,
    max(round(EXTRACT(epoch FROM "timestamp"), 0)) AS followedat,
    max("timestamp") AS insert_ts,
    channel_id
   FROM neynarv2.channel_follows
  WHERE (deleted_at IS NULL)
  GROUP BY fid, channel_id;


ALTER VIEW public.warpcast_followers OWNER TO k3l_user;

--
-- Name: warpcast_members; Type: VIEW; Schema: public; Owner: k3l_user
--

CREATE VIEW public.warpcast_members AS
 SELECT fid,
    max(round(EXTRACT(epoch FROM "timestamp"), 0)) AS memberat,
    max("timestamp") AS insert_ts,
    channel_id
   FROM neynarv2.channel_members
  WHERE (deleted_at IS NULL)
  GROUP BY fid, channel_id;


ALTER VIEW public.warpcast_members OWNER TO k3l_user;

--
-- Name: k3l_cast_action_v1_y2024m09; Type: TABLE ATTACH; Schema: public; Owner: k3l_user
--

ALTER TABLE ONLY public.k3l_cast_action_v1 ATTACH PARTITION public.k3l_cast_action_v1_y2024m09 FOR VALUES FROM ('2024-09-01 00:00:00') TO ('2024-10-01 00:00:00');


--
-- Name: k3l_cast_action_v1_y2024m10; Type: TABLE ATTACH; Schema: public; Owner: k3l_user
--

ALTER TABLE ONLY public.k3l_cast_action_v1 ATTACH PARTITION public.k3l_cast_action_v1_y2024m10 FOR VALUES FROM ('2024-10-01 00:00:00') TO ('2024-11-01 00:00:00');


--
-- Name: k3l_cast_action_v1_y2024m11; Type: TABLE ATTACH; Schema: public; Owner: k3l_user
--

ALTER TABLE ONLY public.k3l_cast_action_v1 ATTACH PARTITION public.k3l_cast_action_v1_y2024m11 FOR VALUES FROM ('2024-11-01 00:00:00') TO ('2024-12-01 00:00:00');


--
-- Name: k3l_cast_action_v1_y2024m12; Type: TABLE ATTACH; Schema: public; Owner: k3l_user
--

ALTER TABLE ONLY public.k3l_cast_action_v1 ATTACH PARTITION public.k3l_cast_action_v1_y2024m12 FOR VALUES FROM ('2024-12-01 00:00:00') TO ('2025-01-01 00:00:00');


--
-- Name: k3l_cast_action_v1_y2025m01; Type: TABLE ATTACH; Schema: public; Owner: k3l_user
--

ALTER TABLE ONLY public.k3l_cast_action_v1 ATTACH PARTITION public.k3l_cast_action_v1_y2025m01 FOR VALUES FROM ('2025-01-01 00:00:00') TO ('2025-02-01 00:00:00');


--
-- Name: k3l_cast_action_v1_y2025m02; Type: TABLE ATTACH; Schema: public; Owner: k3l_user
--

ALTER TABLE ONLY public.k3l_cast_action_v1 ATTACH PARTITION public.k3l_cast_action_v1_y2025m02 FOR VALUES FROM ('2025-02-01 00:00:00') TO ('2025-03-01 00:00:00');


--
-- Name: k3l_cast_action_v1_y2025m03; Type: TABLE ATTACH; Schema: public; Owner: k3l_user
--

ALTER TABLE ONLY public.k3l_cast_action_v1 ATTACH PARTITION public.k3l_cast_action_v1_y2025m03 FOR VALUES FROM ('2025-03-01 00:00:00') TO ('2025-04-01 00:00:00');


--
-- Name: k3l_cast_action_v1_y2025m04; Type: TABLE ATTACH; Schema: public; Owner: k3l_user
--

ALTER TABLE ONLY public.k3l_cast_action_v1 ATTACH PARTITION public.k3l_cast_action_v1_y2025m04 FOR VALUES FROM ('2025-04-01 00:00:00') TO ('2025-05-01 00:00:00');


--
-- Name: k3l_cast_action_v1_y2025m05; Type: TABLE ATTACH; Schema: public; Owner: k3l_user
--

ALTER TABLE ONLY public.k3l_cast_action_v1 ATTACH PARTITION public.k3l_cast_action_v1_y2025m05 FOR VALUES FROM ('2025-05-01 00:00:00') TO ('2025-06-01 00:00:00');


--
-- Name: k3l_cast_action_v1_y2025m06; Type: TABLE ATTACH; Schema: public; Owner: k3l_user
--

ALTER TABLE ONLY public.k3l_cast_action_v1 ATTACH PARTITION public.k3l_cast_action_v1_y2025m06 FOR VALUES FROM ('2025-06-01 00:00:00') TO ('2025-07-01 00:00:00');


--
-- Name: k3l_channel_metrics_y2025m01; Type: TABLE ATTACH; Schema: public; Owner: k3l_user
--

ALTER TABLE ONLY public.k3l_channel_metrics ATTACH PARTITION public.k3l_channel_metrics_y2025m01 FOR VALUES FROM ('2025-01-01 00:00:00+00') TO ('2025-02-01 00:00:00+00');


--
-- Name: k3l_channel_metrics_y2025m02; Type: TABLE ATTACH; Schema: public; Owner: k3l_user
--

ALTER TABLE ONLY public.k3l_channel_metrics ATTACH PARTITION public.k3l_channel_metrics_y2025m02 FOR VALUES FROM ('2025-02-01 00:00:00+00') TO ('2025-03-01 00:00:00+00');


--
-- Name: k3l_channel_metrics_y2025m03; Type: TABLE ATTACH; Schema: public; Owner: k3l_user
--

ALTER TABLE ONLY public.k3l_channel_metrics ATTACH PARTITION public.k3l_channel_metrics_y2025m03 FOR VALUES FROM ('2025-03-01 00:00:00+00') TO ('2025-04-01 00:00:00+00');


--
-- Name: k3l_channel_metrics_y2025m04; Type: TABLE ATTACH; Schema: public; Owner: k3l_user
--

ALTER TABLE ONLY public.k3l_channel_metrics ATTACH PARTITION public.k3l_channel_metrics_y2025m04 FOR VALUES FROM ('2025-04-01 00:00:00+00') TO ('2025-05-01 00:00:00+00');


--
-- Name: k3l_channel_metrics_y2025m05; Type: TABLE ATTACH; Schema: public; Owner: k3l_user
--

ALTER TABLE ONLY public.k3l_channel_metrics ATTACH PARTITION public.k3l_channel_metrics_y2025m05 FOR VALUES FROM ('2025-05-01 00:00:00+00') TO ('2025-06-01 00:00:00+00');


--
-- Name: k3l_channel_metrics_y2025m06; Type: TABLE ATTACH; Schema: public; Owner: k3l_user
--

ALTER TABLE ONLY public.k3l_channel_metrics ATTACH PARTITION public.k3l_channel_metrics_y2025m06 FOR VALUES FROM ('2025-06-01 00:00:00+00') TO ('2025-07-01 00:00:00+00');


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
-- Name: k3l_channel_points_log_y2025m04; Type: TABLE ATTACH; Schema: public; Owner: k3l_user
--

ALTER TABLE ONLY public.k3l_channel_points_log ATTACH PARTITION public.k3l_channel_points_log_y2025m04 FOR VALUES FROM ('2025-04-01 00:00:00+00') TO ('2025-05-01 00:00:00+00');


--
-- Name: k3l_channel_points_log_y2025m05; Type: TABLE ATTACH; Schema: public; Owner: k3l_user
--

ALTER TABLE ONLY public.k3l_channel_points_log ATTACH PARTITION public.k3l_channel_points_log_y2025m05 FOR VALUES FROM ('2025-05-01 00:00:00+00') TO ('2025-06-01 00:00:00+00');


--
-- Name: k3l_channel_points_log_y2025m06; Type: TABLE ATTACH; Schema: public; Owner: k3l_user
--

ALTER TABLE ONLY public.k3l_channel_points_log ATTACH PARTITION public.k3l_channel_points_log_y2025m06 FOR VALUES FROM ('2025-06-01 00:00:00+00') TO ('2025-07-01 00:00:00+00');


--
-- Name: k3l_channel_rank_log_y2025m03; Type: TABLE ATTACH; Schema: public; Owner: k3l_user
--

ALTER TABLE ONLY public.k3l_channel_rank_log ATTACH PARTITION public.k3l_channel_rank_log_y2025m03 FOR VALUES FROM ('2025-03-01 00:00:00+00') TO ('2025-04-01 00:00:00+00');


--
-- Name: k3l_channel_rank_log_y2025m04; Type: TABLE ATTACH; Schema: public; Owner: k3l_user
--

ALTER TABLE ONLY public.k3l_channel_rank_log ATTACH PARTITION public.k3l_channel_rank_log_y2025m04 FOR VALUES FROM ('2025-04-01 00:00:00+00') TO ('2025-05-01 00:00:00+00');


--
-- Name: k3l_channel_rank_log_y2025m05; Type: TABLE ATTACH; Schema: public; Owner: k3l_user
--

ALTER TABLE ONLY public.k3l_channel_rank_log ATTACH PARTITION public.k3l_channel_rank_log_y2025m05 FOR VALUES FROM ('2025-05-01 00:00:00+00') TO ('2025-06-01 00:00:00+00');


--
-- Name: k3l_channel_rank_log_y2025m06; Type: TABLE ATTACH; Schema: public; Owner: k3l_user
--

ALTER TABLE ONLY public.k3l_channel_rank_log ATTACH PARTITION public.k3l_channel_rank_log_y2025m06 FOR VALUES FROM ('2025-06-01 00:00:00+00') TO ('2025-07-01 00:00:00+00');


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
-- Name: k3l_channel_tokens_log_y2025m04; Type: TABLE ATTACH; Schema: public; Owner: k3l_user
--

ALTER TABLE ONLY public.k3l_channel_tokens_log ATTACH PARTITION public.k3l_channel_tokens_log_y2025m04 FOR VALUES FROM ('2025-04-01 00:00:00') TO ('2025-05-01 00:00:00');


--
-- Name: k3l_channel_tokens_log_y2025m05; Type: TABLE ATTACH; Schema: public; Owner: k3l_user
--

ALTER TABLE ONLY public.k3l_channel_tokens_log ATTACH PARTITION public.k3l_channel_tokens_log_y2025m05 FOR VALUES FROM ('2025-05-01 00:00:00') TO ('2025-06-01 00:00:00');


--
-- Name: k3l_channel_tokens_log_y2025m06; Type: TABLE ATTACH; Schema: public; Owner: k3l_user
--

ALTER TABLE ONLY public.k3l_channel_tokens_log ATTACH PARTITION public.k3l_channel_tokens_log_y2025m06 FOR VALUES FROM ('2025-06-01 00:00:00') TO ('2025-07-01 00:00:00');


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: k3l_user
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: balances balances_pkey; Type: CONSTRAINT; Schema: public; Owner: k3l_user
--

ALTER TABLE ONLY public.balances
    ADD CONSTRAINT balances_pkey PRIMARY KEY (chain_id, token_address, wallet_address);


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


--
-- Name: globaltrust globaltrust_strategy_name_date_i_unique; Type: CONSTRAINT; Schema: public; Owner: k3l_user
--

ALTER TABLE ONLY public.globaltrust
    ADD CONSTRAINT globaltrust_strategy_name_date_i_unique UNIQUE (strategy_id, date, i);


--
-- Name: k3l_cast_action_v1 k3l_cast_action_v1_unq; Type: CONSTRAINT; Schema: public; Owner: k3l_user
--

ALTER TABLE ONLY public.k3l_cast_action_v1
    ADD CONSTRAINT k3l_cast_action_v1_unq UNIQUE (cast_hash, fid, action_ts);


--
-- Name: k3l_cast_action_v1_y2024m09 k3l_cast_action_v1_y2024m09_cast_hash_fid_action_ts_key; Type: CONSTRAINT; Schema: public; Owner: k3l_user
--

ALTER TABLE ONLY public.k3l_cast_action_v1_y2024m09
    ADD CONSTRAINT k3l_cast_action_v1_y2024m09_cast_hash_fid_action_ts_key UNIQUE (cast_hash, fid, action_ts);


--
-- Name: k3l_cast_action_v1_y2024m10 k3l_cast_action_v1_y2024m10_cast_hash_fid_action_ts_key; Type: CONSTRAINT; Schema: public; Owner: k3l_user
--

ALTER TABLE ONLY public.k3l_cast_action_v1_y2024m10
    ADD CONSTRAINT k3l_cast_action_v1_y2024m10_cast_hash_fid_action_ts_key UNIQUE (cast_hash, fid, action_ts);


--
-- Name: k3l_cast_action_v1_y2024m11 k3l_cast_action_v1_y2024m11_cast_hash_fid_action_ts_key; Type: CONSTRAINT; Schema: public; Owner: k3l_user
--

ALTER TABLE ONLY public.k3l_cast_action_v1_y2024m11
    ADD CONSTRAINT k3l_cast_action_v1_y2024m11_cast_hash_fid_action_ts_key UNIQUE (cast_hash, fid, action_ts);


--
-- Name: k3l_cast_action_v1_y2024m12 k3l_cast_action_v1_y2024m12_cast_hash_fid_action_ts_key; Type: CONSTRAINT; Schema: public; Owner: k3l_user
--

ALTER TABLE ONLY public.k3l_cast_action_v1_y2024m12
    ADD CONSTRAINT k3l_cast_action_v1_y2024m12_cast_hash_fid_action_ts_key UNIQUE (cast_hash, fid, action_ts);


--
-- Name: k3l_cast_action_v1_y2025m01 k3l_cast_action_v1_y2025m01_cast_hash_fid_action_ts_key; Type: CONSTRAINT; Schema: public; Owner: k3l_user
--

ALTER TABLE ONLY public.k3l_cast_action_v1_y2025m01
    ADD CONSTRAINT k3l_cast_action_v1_y2025m01_cast_hash_fid_action_ts_key UNIQUE (cast_hash, fid, action_ts);


--
-- Name: k3l_cast_action_v1_y2025m02 k3l_cast_action_v1_y2025m02_cast_hash_fid_action_ts_key; Type: CONSTRAINT; Schema: public; Owner: k3l_user
--

ALTER TABLE ONLY public.k3l_cast_action_v1_y2025m02
    ADD CONSTRAINT k3l_cast_action_v1_y2025m02_cast_hash_fid_action_ts_key UNIQUE (cast_hash, fid, action_ts);


--
-- Name: k3l_cast_action_v1_y2025m03 k3l_cast_action_v1_y2025m03_cast_hash_fid_action_ts_key; Type: CONSTRAINT; Schema: public; Owner: k3l_user
--

ALTER TABLE ONLY public.k3l_cast_action_v1_y2025m03
    ADD CONSTRAINT k3l_cast_action_v1_y2025m03_cast_hash_fid_action_ts_key UNIQUE (cast_hash, fid, action_ts);


--
-- Name: k3l_cast_action_v1_y2025m04 k3l_cast_action_v1_y2025m04_cast_hash_fid_action_ts_key; Type: CONSTRAINT; Schema: public; Owner: k3l_user
--

ALTER TABLE ONLY public.k3l_cast_action_v1_y2025m04
    ADD CONSTRAINT k3l_cast_action_v1_y2025m04_cast_hash_fid_action_ts_key UNIQUE (cast_hash, fid, action_ts);


--
-- Name: k3l_cast_action_v1_y2025m05 k3l_cast_action_v1_y2025m05_cast_hash_fid_action_ts_key; Type: CONSTRAINT; Schema: public; Owner: k3l_user
--

ALTER TABLE ONLY public.k3l_cast_action_v1_y2025m05
    ADD CONSTRAINT k3l_cast_action_v1_y2025m05_cast_hash_fid_action_ts_key UNIQUE (cast_hash, fid, action_ts);


--
-- Name: k3l_cast_action_v1_y2025m06 k3l_cast_action_v1_y2025m06_cast_hash_fid_action_ts_key; Type: CONSTRAINT; Schema: public; Owner: k3l_user
--

ALTER TABLE ONLY public.k3l_cast_action_v1_y2025m06
    ADD CONSTRAINT k3l_cast_action_v1_y2025m06_cast_hash_fid_action_ts_key UNIQUE (cast_hash, fid, action_ts);


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
-- Name: k3l_channel_metrics k3l_channel_metrics_metric_ts_channel_id_metric_key; Type: CONSTRAINT; Schema: public; Owner: k3l_user
--

ALTER TABLE ONLY public.k3l_channel_metrics
    ADD CONSTRAINT k3l_channel_metrics_metric_ts_channel_id_metric_key UNIQUE (metric_ts, channel_id, metric);


--
-- Name: k3l_channel_metrics_y2025m01 k3l_channel_metrics_y2025m01_metric_ts_channel_id_metric_key; Type: CONSTRAINT; Schema: public; Owner: k3l_user
--

ALTER TABLE ONLY public.k3l_channel_metrics_y2025m01
    ADD CONSTRAINT k3l_channel_metrics_y2025m01_metric_ts_channel_id_metric_key UNIQUE (metric_ts, channel_id, metric);


--
-- Name: k3l_channel_metrics_y2025m02 k3l_channel_metrics_y2025m02_metric_ts_channel_id_metric_key; Type: CONSTRAINT; Schema: public; Owner: k3l_user
--

ALTER TABLE ONLY public.k3l_channel_metrics_y2025m02
    ADD CONSTRAINT k3l_channel_metrics_y2025m02_metric_ts_channel_id_metric_key UNIQUE (metric_ts, channel_id, metric);


--
-- Name: k3l_channel_metrics_y2025m03 k3l_channel_metrics_y2025m03_metric_ts_channel_id_metric_key; Type: CONSTRAINT; Schema: public; Owner: k3l_user
--

ALTER TABLE ONLY public.k3l_channel_metrics_y2025m03
    ADD CONSTRAINT k3l_channel_metrics_y2025m03_metric_ts_channel_id_metric_key UNIQUE (metric_ts, channel_id, metric);


--
-- Name: k3l_channel_metrics_y2025m04 k3l_channel_metrics_y2025m04_metric_ts_channel_id_metric_key; Type: CONSTRAINT; Schema: public; Owner: k3l_user
--

ALTER TABLE ONLY public.k3l_channel_metrics_y2025m04
    ADD CONSTRAINT k3l_channel_metrics_y2025m04_metric_ts_channel_id_metric_key UNIQUE (metric_ts, channel_id, metric);


--
-- Name: k3l_channel_metrics_y2025m05 k3l_channel_metrics_y2025m05_metric_ts_channel_id_metric_key; Type: CONSTRAINT; Schema: public; Owner: k3l_user
--

ALTER TABLE ONLY public.k3l_channel_metrics_y2025m05
    ADD CONSTRAINT k3l_channel_metrics_y2025m05_metric_ts_channel_id_metric_key UNIQUE (metric_ts, channel_id, metric);


--
-- Name: k3l_channel_metrics_y2025m06 k3l_channel_metrics_y2025m06_metric_ts_channel_id_metric_key; Type: CONSTRAINT; Schema: public; Owner: k3l_user
--

ALTER TABLE ONLY public.k3l_channel_metrics_y2025m06
    ADD CONSTRAINT k3l_channel_metrics_y2025m06_metric_ts_channel_id_metric_key UNIQUE (metric_ts, channel_id, metric);


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
-- Name: k3l_channel_domains openrank_reqs_pkey; Type: CONSTRAINT; Schema: public; Owner: k3l_user
--

ALTER TABLE ONLY public.k3l_channel_domains
    ADD CONSTRAINT openrank_reqs_pkey PRIMARY KEY (id);


--
-- Name: cura_hidden_fids_ch_fid_act_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX cura_hidden_fids_ch_fid_act_idx ON public.cura_hidden_fids USING btree (channel_id, hidden_fid, is_active);


--
-- Name: globaltrust_id_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX globaltrust_id_idx ON public.globaltrust USING btree (strategy_id);


--
-- Name: idx_automod_data_action_ch_userid; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX idx_automod_data_action_ch_userid ON public.automod_data USING btree (action, channel_id, affected_userid);


--
-- Name: k3l_cast_action_v1_ch_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_v1_ch_idx ON ONLY public.k3l_cast_action_v1 USING btree (channel_id);


--
-- Name: k3l_cast_action_v1_covering_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_v1_covering_idx ON ONLY public.k3l_cast_action_v1 USING btree (cast_hash, action_ts, fid) INCLUDE (casted, replied, recasted, liked);


--
-- Name: k3l_cast_action_v1_fid_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_v1_fid_idx ON ONLY public.k3l_cast_action_v1 USING btree (fid);


--
-- Name: k3l_cast_action_v1_fid_ts_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_v1_fid_ts_idx ON ONLY public.k3l_cast_action_v1 USING btree (fid, action_ts);


--
-- Name: k3l_cast_action_v1_timestamp_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_v1_timestamp_idx ON ONLY public.k3l_cast_action_v1 USING btree (action_ts);


--
-- Name: k3l_cast_action_v1_y2024m09_action_ts_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_v1_y2024m09_action_ts_idx ON public.k3l_cast_action_v1_y2024m09 USING btree (action_ts);


--
-- Name: k3l_cast_action_v1_y2024m09_cast_hash_action_ts_fid_casted__idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_v1_y2024m09_cast_hash_action_ts_fid_casted__idx ON public.k3l_cast_action_v1_y2024m09 USING btree (cast_hash, action_ts, fid) INCLUDE (casted, replied, recasted, liked);


--
-- Name: k3l_cast_action_v1_y2024m09_channel_id_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_v1_y2024m09_channel_id_idx ON public.k3l_cast_action_v1_y2024m09 USING btree (channel_id);


--
-- Name: k3l_cast_action_v1_y2024m09_fid_action_ts_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_v1_y2024m09_fid_action_ts_idx ON public.k3l_cast_action_v1_y2024m09 USING btree (fid, action_ts);


--
-- Name: k3l_cast_action_v1_y2024m09_fid_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_v1_y2024m09_fid_idx ON public.k3l_cast_action_v1_y2024m09 USING btree (fid);


--
-- Name: k3l_cast_action_v1_y2024m10_action_ts_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_v1_y2024m10_action_ts_idx ON public.k3l_cast_action_v1_y2024m10 USING btree (action_ts);


--
-- Name: k3l_cast_action_v1_y2024m10_cast_hash_action_ts_fid_casted__idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_v1_y2024m10_cast_hash_action_ts_fid_casted__idx ON public.k3l_cast_action_v1_y2024m10 USING btree (cast_hash, action_ts, fid) INCLUDE (casted, replied, recasted, liked);


--
-- Name: k3l_cast_action_v1_y2024m10_channel_id_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_v1_y2024m10_channel_id_idx ON public.k3l_cast_action_v1_y2024m10 USING btree (channel_id);


--
-- Name: k3l_cast_action_v1_y2024m10_fid_action_ts_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_v1_y2024m10_fid_action_ts_idx ON public.k3l_cast_action_v1_y2024m10 USING btree (fid, action_ts);


--
-- Name: k3l_cast_action_v1_y2024m10_fid_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_v1_y2024m10_fid_idx ON public.k3l_cast_action_v1_y2024m10 USING btree (fid);


--
-- Name: k3l_cast_action_v1_y2024m11_action_ts_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_v1_y2024m11_action_ts_idx ON public.k3l_cast_action_v1_y2024m11 USING btree (action_ts);


--
-- Name: k3l_cast_action_v1_y2024m11_cast_hash_action_ts_fid_casted__idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_v1_y2024m11_cast_hash_action_ts_fid_casted__idx ON public.k3l_cast_action_v1_y2024m11 USING btree (cast_hash, action_ts, fid) INCLUDE (casted, replied, recasted, liked);


--
-- Name: k3l_cast_action_v1_y2024m11_channel_id_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_v1_y2024m11_channel_id_idx ON public.k3l_cast_action_v1_y2024m11 USING btree (channel_id);


--
-- Name: k3l_cast_action_v1_y2024m11_fid_action_ts_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_v1_y2024m11_fid_action_ts_idx ON public.k3l_cast_action_v1_y2024m11 USING btree (fid, action_ts);


--
-- Name: k3l_cast_action_v1_y2024m11_fid_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_v1_y2024m11_fid_idx ON public.k3l_cast_action_v1_y2024m11 USING btree (fid);


--
-- Name: k3l_cast_action_v1_y2024m12_action_ts_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_v1_y2024m12_action_ts_idx ON public.k3l_cast_action_v1_y2024m12 USING btree (action_ts);


--
-- Name: k3l_cast_action_v1_y2024m12_cast_hash_action_ts_fid_casted__idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_v1_y2024m12_cast_hash_action_ts_fid_casted__idx ON public.k3l_cast_action_v1_y2024m12 USING btree (cast_hash, action_ts, fid) INCLUDE (casted, replied, recasted, liked);


--
-- Name: k3l_cast_action_v1_y2024m12_channel_id_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_v1_y2024m12_channel_id_idx ON public.k3l_cast_action_v1_y2024m12 USING btree (channel_id);


--
-- Name: k3l_cast_action_v1_y2024m12_fid_action_ts_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_v1_y2024m12_fid_action_ts_idx ON public.k3l_cast_action_v1_y2024m12 USING btree (fid, action_ts);


--
-- Name: k3l_cast_action_v1_y2024m12_fid_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_v1_y2024m12_fid_idx ON public.k3l_cast_action_v1_y2024m12 USING btree (fid);


--
-- Name: k3l_cast_action_v1_y2025m01_action_ts_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_v1_y2025m01_action_ts_idx ON public.k3l_cast_action_v1_y2025m01 USING btree (action_ts);


--
-- Name: k3l_cast_action_v1_y2025m01_cast_hash_action_ts_fid_casted__idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_v1_y2025m01_cast_hash_action_ts_fid_casted__idx ON public.k3l_cast_action_v1_y2025m01 USING btree (cast_hash, action_ts, fid) INCLUDE (casted, replied, recasted, liked);


--
-- Name: k3l_cast_action_v1_y2025m01_channel_id_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_v1_y2025m01_channel_id_idx ON public.k3l_cast_action_v1_y2025m01 USING btree (channel_id);


--
-- Name: k3l_cast_action_v1_y2025m01_fid_action_ts_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_v1_y2025m01_fid_action_ts_idx ON public.k3l_cast_action_v1_y2025m01 USING btree (fid, action_ts);


--
-- Name: k3l_cast_action_v1_y2025m01_fid_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_v1_y2025m01_fid_idx ON public.k3l_cast_action_v1_y2025m01 USING btree (fid);


--
-- Name: k3l_cast_action_v1_y2025m02_action_ts_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_v1_y2025m02_action_ts_idx ON public.k3l_cast_action_v1_y2025m02 USING btree (action_ts);


--
-- Name: k3l_cast_action_v1_y2025m02_cast_hash_action_ts_fid_casted__idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_v1_y2025m02_cast_hash_action_ts_fid_casted__idx ON public.k3l_cast_action_v1_y2025m02 USING btree (cast_hash, action_ts, fid) INCLUDE (casted, replied, recasted, liked);


--
-- Name: k3l_cast_action_v1_y2025m02_channel_id_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_v1_y2025m02_channel_id_idx ON public.k3l_cast_action_v1_y2025m02 USING btree (channel_id);


--
-- Name: k3l_cast_action_v1_y2025m02_fid_action_ts_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_v1_y2025m02_fid_action_ts_idx ON public.k3l_cast_action_v1_y2025m02 USING btree (fid, action_ts);


--
-- Name: k3l_cast_action_v1_y2025m02_fid_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_v1_y2025m02_fid_idx ON public.k3l_cast_action_v1_y2025m02 USING btree (fid);


--
-- Name: k3l_cast_action_v1_y2025m03_action_ts_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_v1_y2025m03_action_ts_idx ON public.k3l_cast_action_v1_y2025m03 USING btree (action_ts);


--
-- Name: k3l_cast_action_v1_y2025m03_cast_hash_action_ts_fid_casted__idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_v1_y2025m03_cast_hash_action_ts_fid_casted__idx ON public.k3l_cast_action_v1_y2025m03 USING btree (cast_hash, action_ts, fid) INCLUDE (casted, replied, recasted, liked);


--
-- Name: k3l_cast_action_v1_y2025m03_channel_id_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_v1_y2025m03_channel_id_idx ON public.k3l_cast_action_v1_y2025m03 USING btree (channel_id);


--
-- Name: k3l_cast_action_v1_y2025m03_fid_action_ts_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_v1_y2025m03_fid_action_ts_idx ON public.k3l_cast_action_v1_y2025m03 USING btree (fid, action_ts);


--
-- Name: k3l_cast_action_v1_y2025m03_fid_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_v1_y2025m03_fid_idx ON public.k3l_cast_action_v1_y2025m03 USING btree (fid);


--
-- Name: k3l_cast_action_v1_y2025m04_action_ts_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_v1_y2025m04_action_ts_idx ON public.k3l_cast_action_v1_y2025m04 USING btree (action_ts);


--
-- Name: k3l_cast_action_v1_y2025m04_cast_hash_action_ts_fid_casted__idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_v1_y2025m04_cast_hash_action_ts_fid_casted__idx ON public.k3l_cast_action_v1_y2025m04 USING btree (cast_hash, action_ts, fid) INCLUDE (casted, replied, recasted, liked);


--
-- Name: k3l_cast_action_v1_y2025m04_channel_id_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_v1_y2025m04_channel_id_idx ON public.k3l_cast_action_v1_y2025m04 USING btree (channel_id);


--
-- Name: k3l_cast_action_v1_y2025m04_fid_action_ts_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_v1_y2025m04_fid_action_ts_idx ON public.k3l_cast_action_v1_y2025m04 USING btree (fid, action_ts);


--
-- Name: k3l_cast_action_v1_y2025m04_fid_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_v1_y2025m04_fid_idx ON public.k3l_cast_action_v1_y2025m04 USING btree (fid);


--
-- Name: k3l_cast_action_v1_y2025m05_action_ts_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_v1_y2025m05_action_ts_idx ON public.k3l_cast_action_v1_y2025m05 USING btree (action_ts);


--
-- Name: k3l_cast_action_v1_y2025m05_cast_hash_action_ts_fid_casted__idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_v1_y2025m05_cast_hash_action_ts_fid_casted__idx ON public.k3l_cast_action_v1_y2025m05 USING btree (cast_hash, action_ts, fid) INCLUDE (casted, replied, recasted, liked);


--
-- Name: k3l_cast_action_v1_y2025m05_channel_id_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_v1_y2025m05_channel_id_idx ON public.k3l_cast_action_v1_y2025m05 USING btree (channel_id);


--
-- Name: k3l_cast_action_v1_y2025m05_fid_action_ts_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_v1_y2025m05_fid_action_ts_idx ON public.k3l_cast_action_v1_y2025m05 USING btree (fid, action_ts);


--
-- Name: k3l_cast_action_v1_y2025m05_fid_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_v1_y2025m05_fid_idx ON public.k3l_cast_action_v1_y2025m05 USING btree (fid);


--
-- Name: k3l_cast_action_v1_y2025m06_action_ts_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_v1_y2025m06_action_ts_idx ON public.k3l_cast_action_v1_y2025m06 USING btree (action_ts);


--
-- Name: k3l_cast_action_v1_y2025m06_cast_hash_action_ts_fid_casted__idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_v1_y2025m06_cast_hash_action_ts_fid_casted__idx ON public.k3l_cast_action_v1_y2025m06 USING btree (cast_hash, action_ts, fid) INCLUDE (casted, replied, recasted, liked);


--
-- Name: k3l_cast_action_v1_y2025m06_channel_id_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_v1_y2025m06_channel_id_idx ON public.k3l_cast_action_v1_y2025m06 USING btree (channel_id);


--
-- Name: k3l_cast_action_v1_y2025m06_fid_action_ts_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_v1_y2025m06_fid_action_ts_idx ON public.k3l_cast_action_v1_y2025m06 USING btree (fid, action_ts);


--
-- Name: k3l_cast_action_v1_y2025m06_fid_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_v1_y2025m06_fid_idx ON public.k3l_cast_action_v1_y2025m06 USING btree (fid);


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

CREATE INDEX k3l_channel_points_bal_new_channel_id_balance_idx ON public.k3l_channel_points_bal_old USING btree (channel_id, balance);


--
-- Name: k3l_channel_points_bal_new_channel_id_balance_idx1; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_channel_points_bal_new_channel_id_balance_idx1 ON public.k3l_channel_points_bal USING btree (channel_id, balance);


--
-- Name: k3l_channel_points_bal_new_channel_id_fid_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_channel_points_bal_new_channel_id_fid_idx ON public.k3l_channel_points_bal_old USING btree (channel_id, fid);


--
-- Name: k3l_channel_points_bal_new_channel_id_fid_idx1; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_channel_points_bal_new_channel_id_fid_idx1 ON public.k3l_channel_points_bal USING btree (channel_id, fid);


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
-- Name: k3l_channel_points_log_y2025m04_channel_id_fid_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_channel_points_log_y2025m04_channel_id_fid_idx ON public.k3l_channel_points_log_y2025m04 USING btree (channel_id, fid);


--
-- Name: k3l_channel_points_log_y2025m04_channel_id_model_name_fid_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_channel_points_log_y2025m04_channel_id_model_name_fid_idx ON public.k3l_channel_points_log_y2025m04 USING btree (channel_id, model_name, fid);


--
-- Name: k3l_channel_points_log_y2025m04_channel_id_model_name_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_channel_points_log_y2025m04_channel_id_model_name_idx ON public.k3l_channel_points_log_y2025m04 USING btree (channel_id, model_name);


--
-- Name: k3l_channel_points_log_y2025m05_channel_id_fid_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_channel_points_log_y2025m05_channel_id_fid_idx ON public.k3l_channel_points_log_y2025m05 USING btree (channel_id, fid);


--
-- Name: k3l_channel_points_log_y2025m05_channel_id_model_name_fid_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_channel_points_log_y2025m05_channel_id_model_name_fid_idx ON public.k3l_channel_points_log_y2025m05 USING btree (channel_id, model_name, fid);


--
-- Name: k3l_channel_points_log_y2025m05_channel_id_model_name_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_channel_points_log_y2025m05_channel_id_model_name_idx ON public.k3l_channel_points_log_y2025m05 USING btree (channel_id, model_name);


--
-- Name: k3l_channel_points_log_y2025m06_channel_id_fid_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_channel_points_log_y2025m06_channel_id_fid_idx ON public.k3l_channel_points_log_y2025m06 USING btree (channel_id, fid);


--
-- Name: k3l_channel_points_log_y2025m06_channel_id_model_name_fid_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_channel_points_log_y2025m06_channel_id_model_name_fid_idx ON public.k3l_channel_points_log_y2025m06 USING btree (channel_id, model_name, fid);


--
-- Name: k3l_channel_points_log_y2025m06_channel_id_model_name_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_channel_points_log_y2025m06_channel_id_model_name_idx ON public.k3l_channel_points_log_y2025m06 USING btree (channel_id, model_name);


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
-- Name: k3l_channel_rank_log_run_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_channel_rank_log_run_idx ON ONLY public.k3l_channel_rank_log USING btree (run_id);


--
-- Name: k3l_channel_rank_log_y2025m03_run_id_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_channel_rank_log_y2025m03_run_id_idx ON public.k3l_channel_rank_log_y2025m03 USING btree (run_id);


--
-- Name: k3l_channel_rank_log_y2025m04_run_id_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_channel_rank_log_y2025m04_run_id_idx ON public.k3l_channel_rank_log_y2025m04 USING btree (run_id);


--
-- Name: k3l_channel_rank_log_y2025m05_run_id_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_channel_rank_log_y2025m05_run_id_idx ON public.k3l_channel_rank_log_y2025m05 USING btree (run_id);


--
-- Name: k3l_channel_rank_log_y2025m06_run_id_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_channel_rank_log_y2025m06_run_id_idx ON public.k3l_channel_rank_log_y2025m06 USING btree (run_id);


--
-- Name: k3l_channel_rank_rank_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_channel_rank_rank_idx ON public.k3l_channel_rank USING btree (rank);


--
-- Name: k3l_channel_rank_strat_ch_ts_fid_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_channel_rank_strat_ch_ts_fid_idx ON public.k3l_channel_rank USING btree (strategy_name, channel_id, compute_ts, fid);


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


--
-- Name: k3l_channel_tokens_log_y2025m04_channel_id_fid_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_channel_tokens_log_y2025m04_channel_id_fid_idx ON public.k3l_channel_tokens_log_y2025m04 USING btree (channel_id, fid);


--
-- Name: k3l_channel_tokens_log_y2025m04_dist_id_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_channel_tokens_log_y2025m04_dist_id_idx ON public.k3l_channel_tokens_log_y2025m04 USING btree (dist_id);


--
-- Name: k3l_channel_tokens_log_y2025m04_dist_status_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_channel_tokens_log_y2025m04_dist_status_idx ON public.k3l_channel_tokens_log_y2025m04 USING btree (dist_status) WHERE (dist_status <> 'success'::public.tokens_dist_status);


--
-- Name: k3l_channel_tokens_log_y2025m05_channel_id_fid_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_channel_tokens_log_y2025m05_channel_id_fid_idx ON public.k3l_channel_tokens_log_y2025m05 USING btree (channel_id, fid);


--
-- Name: k3l_channel_tokens_log_y2025m05_dist_id_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_channel_tokens_log_y2025m05_dist_id_idx ON public.k3l_channel_tokens_log_y2025m05 USING btree (dist_id);


--
-- Name: k3l_channel_tokens_log_y2025m05_dist_status_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_channel_tokens_log_y2025m05_dist_status_idx ON public.k3l_channel_tokens_log_y2025m05 USING btree (dist_status) WHERE (dist_status <> 'success'::public.tokens_dist_status);


--
-- Name: k3l_channel_tokens_log_y2025m06_channel_id_fid_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_channel_tokens_log_y2025m06_channel_id_fid_idx ON public.k3l_channel_tokens_log_y2025m06 USING btree (channel_id, fid);


--
-- Name: k3l_channel_tokens_log_y2025m06_dist_id_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_channel_tokens_log_y2025m06_dist_id_idx ON public.k3l_channel_tokens_log_y2025m06 USING btree (dist_id);


--
-- Name: k3l_channel_tokens_log_y2025m06_dist_status_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_channel_tokens_log_y2025m06_dist_status_idx ON public.k3l_channel_tokens_log_y2025m06 USING btree (dist_status) WHERE (dist_status <> 'success'::public.tokens_dist_status);


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
-- Name: k3l_recent_parent_casts_fid_timestamp_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_recent_parent_casts_fid_timestamp_idx ON public.k3l_recent_parent_casts USING btree (fid, "timestamp");


--
-- Name: k3l_recent_parent_casts_hash_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_recent_parent_casts_hash_idx ON public.k3l_recent_parent_casts USING btree (hash);


--
-- Name: k3l_recent_parent_casts_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE UNIQUE INDEX k3l_recent_parent_casts_idx ON public.k3l_recent_parent_casts USING btree (id);


--
-- Name: k3l_token_holding_fids_fid_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_token_holding_fids_fid_idx ON public.k3l_token_holding_fids USING btree (fid, token_address);


--
-- Name: k3l_token_holding_fids_token_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_token_holding_fids_token_idx ON public.k3l_token_holding_fids USING btree (token_address, fid);


--
-- Name: k3l_cast_action_v1_y2024m09_action_ts_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_v1_timestamp_idx ATTACH PARTITION public.k3l_cast_action_v1_y2024m09_action_ts_idx;


--
-- Name: k3l_cast_action_v1_y2024m09_cast_hash_action_ts_fid_casted__idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_v1_covering_idx ATTACH PARTITION public.k3l_cast_action_v1_y2024m09_cast_hash_action_ts_fid_casted__idx;


--
-- Name: k3l_cast_action_v1_y2024m09_cast_hash_fid_action_ts_key; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_v1_unq ATTACH PARTITION public.k3l_cast_action_v1_y2024m09_cast_hash_fid_action_ts_key;


--
-- Name: k3l_cast_action_v1_y2024m09_channel_id_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_v1_ch_idx ATTACH PARTITION public.k3l_cast_action_v1_y2024m09_channel_id_idx;


--
-- Name: k3l_cast_action_v1_y2024m09_fid_action_ts_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_v1_fid_ts_idx ATTACH PARTITION public.k3l_cast_action_v1_y2024m09_fid_action_ts_idx;


--
-- Name: k3l_cast_action_v1_y2024m09_fid_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_v1_fid_idx ATTACH PARTITION public.k3l_cast_action_v1_y2024m09_fid_idx;


--
-- Name: k3l_cast_action_v1_y2024m10_action_ts_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_v1_timestamp_idx ATTACH PARTITION public.k3l_cast_action_v1_y2024m10_action_ts_idx;


--
-- Name: k3l_cast_action_v1_y2024m10_cast_hash_action_ts_fid_casted__idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_v1_covering_idx ATTACH PARTITION public.k3l_cast_action_v1_y2024m10_cast_hash_action_ts_fid_casted__idx;


--
-- Name: k3l_cast_action_v1_y2024m10_cast_hash_fid_action_ts_key; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_v1_unq ATTACH PARTITION public.k3l_cast_action_v1_y2024m10_cast_hash_fid_action_ts_key;


--
-- Name: k3l_cast_action_v1_y2024m10_channel_id_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_v1_ch_idx ATTACH PARTITION public.k3l_cast_action_v1_y2024m10_channel_id_idx;


--
-- Name: k3l_cast_action_v1_y2024m10_fid_action_ts_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_v1_fid_ts_idx ATTACH PARTITION public.k3l_cast_action_v1_y2024m10_fid_action_ts_idx;


--
-- Name: k3l_cast_action_v1_y2024m10_fid_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_v1_fid_idx ATTACH PARTITION public.k3l_cast_action_v1_y2024m10_fid_idx;


--
-- Name: k3l_cast_action_v1_y2024m11_action_ts_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_v1_timestamp_idx ATTACH PARTITION public.k3l_cast_action_v1_y2024m11_action_ts_idx;


--
-- Name: k3l_cast_action_v1_y2024m11_cast_hash_action_ts_fid_casted__idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_v1_covering_idx ATTACH PARTITION public.k3l_cast_action_v1_y2024m11_cast_hash_action_ts_fid_casted__idx;


--
-- Name: k3l_cast_action_v1_y2024m11_cast_hash_fid_action_ts_key; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_v1_unq ATTACH PARTITION public.k3l_cast_action_v1_y2024m11_cast_hash_fid_action_ts_key;


--
-- Name: k3l_cast_action_v1_y2024m11_channel_id_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_v1_ch_idx ATTACH PARTITION public.k3l_cast_action_v1_y2024m11_channel_id_idx;


--
-- Name: k3l_cast_action_v1_y2024m11_fid_action_ts_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_v1_fid_ts_idx ATTACH PARTITION public.k3l_cast_action_v1_y2024m11_fid_action_ts_idx;


--
-- Name: k3l_cast_action_v1_y2024m11_fid_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_v1_fid_idx ATTACH PARTITION public.k3l_cast_action_v1_y2024m11_fid_idx;


--
-- Name: k3l_cast_action_v1_y2024m12_action_ts_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_v1_timestamp_idx ATTACH PARTITION public.k3l_cast_action_v1_y2024m12_action_ts_idx;


--
-- Name: k3l_cast_action_v1_y2024m12_cast_hash_action_ts_fid_casted__idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_v1_covering_idx ATTACH PARTITION public.k3l_cast_action_v1_y2024m12_cast_hash_action_ts_fid_casted__idx;


--
-- Name: k3l_cast_action_v1_y2024m12_cast_hash_fid_action_ts_key; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_v1_unq ATTACH PARTITION public.k3l_cast_action_v1_y2024m12_cast_hash_fid_action_ts_key;


--
-- Name: k3l_cast_action_v1_y2024m12_channel_id_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_v1_ch_idx ATTACH PARTITION public.k3l_cast_action_v1_y2024m12_channel_id_idx;


--
-- Name: k3l_cast_action_v1_y2024m12_fid_action_ts_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_v1_fid_ts_idx ATTACH PARTITION public.k3l_cast_action_v1_y2024m12_fid_action_ts_idx;


--
-- Name: k3l_cast_action_v1_y2024m12_fid_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_v1_fid_idx ATTACH PARTITION public.k3l_cast_action_v1_y2024m12_fid_idx;


--
-- Name: k3l_cast_action_v1_y2025m01_action_ts_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_v1_timestamp_idx ATTACH PARTITION public.k3l_cast_action_v1_y2025m01_action_ts_idx;


--
-- Name: k3l_cast_action_v1_y2025m01_cast_hash_action_ts_fid_casted__idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_v1_covering_idx ATTACH PARTITION public.k3l_cast_action_v1_y2025m01_cast_hash_action_ts_fid_casted__idx;


--
-- Name: k3l_cast_action_v1_y2025m01_cast_hash_fid_action_ts_key; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_v1_unq ATTACH PARTITION public.k3l_cast_action_v1_y2025m01_cast_hash_fid_action_ts_key;


--
-- Name: k3l_cast_action_v1_y2025m01_channel_id_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_v1_ch_idx ATTACH PARTITION public.k3l_cast_action_v1_y2025m01_channel_id_idx;


--
-- Name: k3l_cast_action_v1_y2025m01_fid_action_ts_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_v1_fid_ts_idx ATTACH PARTITION public.k3l_cast_action_v1_y2025m01_fid_action_ts_idx;


--
-- Name: k3l_cast_action_v1_y2025m01_fid_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_v1_fid_idx ATTACH PARTITION public.k3l_cast_action_v1_y2025m01_fid_idx;


--
-- Name: k3l_cast_action_v1_y2025m02_action_ts_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_v1_timestamp_idx ATTACH PARTITION public.k3l_cast_action_v1_y2025m02_action_ts_idx;


--
-- Name: k3l_cast_action_v1_y2025m02_cast_hash_action_ts_fid_casted__idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_v1_covering_idx ATTACH PARTITION public.k3l_cast_action_v1_y2025m02_cast_hash_action_ts_fid_casted__idx;


--
-- Name: k3l_cast_action_v1_y2025m02_cast_hash_fid_action_ts_key; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_v1_unq ATTACH PARTITION public.k3l_cast_action_v1_y2025m02_cast_hash_fid_action_ts_key;


--
-- Name: k3l_cast_action_v1_y2025m02_channel_id_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_v1_ch_idx ATTACH PARTITION public.k3l_cast_action_v1_y2025m02_channel_id_idx;


--
-- Name: k3l_cast_action_v1_y2025m02_fid_action_ts_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_v1_fid_ts_idx ATTACH PARTITION public.k3l_cast_action_v1_y2025m02_fid_action_ts_idx;


--
-- Name: k3l_cast_action_v1_y2025m02_fid_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_v1_fid_idx ATTACH PARTITION public.k3l_cast_action_v1_y2025m02_fid_idx;


--
-- Name: k3l_cast_action_v1_y2025m03_action_ts_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_v1_timestamp_idx ATTACH PARTITION public.k3l_cast_action_v1_y2025m03_action_ts_idx;


--
-- Name: k3l_cast_action_v1_y2025m03_cast_hash_action_ts_fid_casted__idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_v1_covering_idx ATTACH PARTITION public.k3l_cast_action_v1_y2025m03_cast_hash_action_ts_fid_casted__idx;


--
-- Name: k3l_cast_action_v1_y2025m03_cast_hash_fid_action_ts_key; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_v1_unq ATTACH PARTITION public.k3l_cast_action_v1_y2025m03_cast_hash_fid_action_ts_key;


--
-- Name: k3l_cast_action_v1_y2025m03_channel_id_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_v1_ch_idx ATTACH PARTITION public.k3l_cast_action_v1_y2025m03_channel_id_idx;


--
-- Name: k3l_cast_action_v1_y2025m03_fid_action_ts_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_v1_fid_ts_idx ATTACH PARTITION public.k3l_cast_action_v1_y2025m03_fid_action_ts_idx;


--
-- Name: k3l_cast_action_v1_y2025m03_fid_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_v1_fid_idx ATTACH PARTITION public.k3l_cast_action_v1_y2025m03_fid_idx;


--
-- Name: k3l_cast_action_v1_y2025m04_action_ts_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_v1_timestamp_idx ATTACH PARTITION public.k3l_cast_action_v1_y2025m04_action_ts_idx;


--
-- Name: k3l_cast_action_v1_y2025m04_cast_hash_action_ts_fid_casted__idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_v1_covering_idx ATTACH PARTITION public.k3l_cast_action_v1_y2025m04_cast_hash_action_ts_fid_casted__idx;


--
-- Name: k3l_cast_action_v1_y2025m04_cast_hash_fid_action_ts_key; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_v1_unq ATTACH PARTITION public.k3l_cast_action_v1_y2025m04_cast_hash_fid_action_ts_key;


--
-- Name: k3l_cast_action_v1_y2025m04_channel_id_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_v1_ch_idx ATTACH PARTITION public.k3l_cast_action_v1_y2025m04_channel_id_idx;


--
-- Name: k3l_cast_action_v1_y2025m04_fid_action_ts_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_v1_fid_ts_idx ATTACH PARTITION public.k3l_cast_action_v1_y2025m04_fid_action_ts_idx;


--
-- Name: k3l_cast_action_v1_y2025m04_fid_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_v1_fid_idx ATTACH PARTITION public.k3l_cast_action_v1_y2025m04_fid_idx;


--
-- Name: k3l_cast_action_v1_y2025m05_action_ts_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_v1_timestamp_idx ATTACH PARTITION public.k3l_cast_action_v1_y2025m05_action_ts_idx;


--
-- Name: k3l_cast_action_v1_y2025m05_cast_hash_action_ts_fid_casted__idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_v1_covering_idx ATTACH PARTITION public.k3l_cast_action_v1_y2025m05_cast_hash_action_ts_fid_casted__idx;


--
-- Name: k3l_cast_action_v1_y2025m05_cast_hash_fid_action_ts_key; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_v1_unq ATTACH PARTITION public.k3l_cast_action_v1_y2025m05_cast_hash_fid_action_ts_key;


--
-- Name: k3l_cast_action_v1_y2025m05_channel_id_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_v1_ch_idx ATTACH PARTITION public.k3l_cast_action_v1_y2025m05_channel_id_idx;


--
-- Name: k3l_cast_action_v1_y2025m05_fid_action_ts_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_v1_fid_ts_idx ATTACH PARTITION public.k3l_cast_action_v1_y2025m05_fid_action_ts_idx;


--
-- Name: k3l_cast_action_v1_y2025m05_fid_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_v1_fid_idx ATTACH PARTITION public.k3l_cast_action_v1_y2025m05_fid_idx;


--
-- Name: k3l_cast_action_v1_y2025m06_action_ts_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_v1_timestamp_idx ATTACH PARTITION public.k3l_cast_action_v1_y2025m06_action_ts_idx;


--
-- Name: k3l_cast_action_v1_y2025m06_cast_hash_action_ts_fid_casted__idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_v1_covering_idx ATTACH PARTITION public.k3l_cast_action_v1_y2025m06_cast_hash_action_ts_fid_casted__idx;


--
-- Name: k3l_cast_action_v1_y2025m06_cast_hash_fid_action_ts_key; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_v1_unq ATTACH PARTITION public.k3l_cast_action_v1_y2025m06_cast_hash_fid_action_ts_key;


--
-- Name: k3l_cast_action_v1_y2025m06_channel_id_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_v1_ch_idx ATTACH PARTITION public.k3l_cast_action_v1_y2025m06_channel_id_idx;


--
-- Name: k3l_cast_action_v1_y2025m06_fid_action_ts_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_v1_fid_ts_idx ATTACH PARTITION public.k3l_cast_action_v1_y2025m06_fid_action_ts_idx;


--
-- Name: k3l_cast_action_v1_y2025m06_fid_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_v1_fid_idx ATTACH PARTITION public.k3l_cast_action_v1_y2025m06_fid_idx;


--
-- Name: k3l_channel_metrics_y2025m01_metric_ts_channel_id_metric_key; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_channel_metrics_metric_ts_channel_id_metric_key ATTACH PARTITION public.k3l_channel_metrics_y2025m01_metric_ts_channel_id_metric_key;


--
-- Name: k3l_channel_metrics_y2025m02_metric_ts_channel_id_metric_key; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_channel_metrics_metric_ts_channel_id_metric_key ATTACH PARTITION public.k3l_channel_metrics_y2025m02_metric_ts_channel_id_metric_key;


--
-- Name: k3l_channel_metrics_y2025m03_metric_ts_channel_id_metric_key; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_channel_metrics_metric_ts_channel_id_metric_key ATTACH PARTITION public.k3l_channel_metrics_y2025m03_metric_ts_channel_id_metric_key;


--
-- Name: k3l_channel_metrics_y2025m04_metric_ts_channel_id_metric_key; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_channel_metrics_metric_ts_channel_id_metric_key ATTACH PARTITION public.k3l_channel_metrics_y2025m04_metric_ts_channel_id_metric_key;


--
-- Name: k3l_channel_metrics_y2025m05_metric_ts_channel_id_metric_key; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_channel_metrics_metric_ts_channel_id_metric_key ATTACH PARTITION public.k3l_channel_metrics_y2025m05_metric_ts_channel_id_metric_key;


--
-- Name: k3l_channel_metrics_y2025m06_metric_ts_channel_id_metric_key; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_channel_metrics_metric_ts_channel_id_metric_key ATTACH PARTITION public.k3l_channel_metrics_y2025m06_metric_ts_channel_id_metric_key;


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
-- Name: k3l_channel_points_log_y2025m04_channel_id_fid_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_channel_points_log_ch_fid_idx ATTACH PARTITION public.k3l_channel_points_log_y2025m04_channel_id_fid_idx;


--
-- Name: k3l_channel_points_log_y2025m04_channel_id_model_name_fid_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_channel_points_log_ch_mdl_fid_idx ATTACH PARTITION public.k3l_channel_points_log_y2025m04_channel_id_model_name_fid_idx;


--
-- Name: k3l_channel_points_log_y2025m04_channel_id_model_name_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_channel_points_log_ch_mdl_idx ATTACH PARTITION public.k3l_channel_points_log_y2025m04_channel_id_model_name_idx;


--
-- Name: k3l_channel_points_log_y2025m05_channel_id_fid_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_channel_points_log_ch_fid_idx ATTACH PARTITION public.k3l_channel_points_log_y2025m05_channel_id_fid_idx;


--
-- Name: k3l_channel_points_log_y2025m05_channel_id_model_name_fid_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_channel_points_log_ch_mdl_fid_idx ATTACH PARTITION public.k3l_channel_points_log_y2025m05_channel_id_model_name_fid_idx;


--
-- Name: k3l_channel_points_log_y2025m05_channel_id_model_name_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_channel_points_log_ch_mdl_idx ATTACH PARTITION public.k3l_channel_points_log_y2025m05_channel_id_model_name_idx;


--
-- Name: k3l_channel_points_log_y2025m06_channel_id_fid_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_channel_points_log_ch_fid_idx ATTACH PARTITION public.k3l_channel_points_log_y2025m06_channel_id_fid_idx;


--
-- Name: k3l_channel_points_log_y2025m06_channel_id_model_name_fid_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_channel_points_log_ch_mdl_fid_idx ATTACH PARTITION public.k3l_channel_points_log_y2025m06_channel_id_model_name_fid_idx;


--
-- Name: k3l_channel_points_log_y2025m06_channel_id_model_name_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_channel_points_log_ch_mdl_idx ATTACH PARTITION public.k3l_channel_points_log_y2025m06_channel_id_model_name_idx;


--
-- Name: k3l_channel_rank_log_y2025m03_run_id_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_channel_rank_log_run_idx ATTACH PARTITION public.k3l_channel_rank_log_y2025m03_run_id_idx;


--
-- Name: k3l_channel_rank_log_y2025m04_run_id_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_channel_rank_log_run_idx ATTACH PARTITION public.k3l_channel_rank_log_y2025m04_run_id_idx;


--
-- Name: k3l_channel_rank_log_y2025m05_run_id_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_channel_rank_log_run_idx ATTACH PARTITION public.k3l_channel_rank_log_y2025m05_run_id_idx;


--
-- Name: k3l_channel_rank_log_y2025m06_run_id_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_channel_rank_log_run_idx ATTACH PARTITION public.k3l_channel_rank_log_y2025m06_run_id_idx;


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
-- Name: k3l_channel_tokens_log_y2025m04_channel_id_fid_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_channel_tokens_log_ch_fid_idx ATTACH PARTITION public.k3l_channel_tokens_log_y2025m04_channel_id_fid_idx;


--
-- Name: k3l_channel_tokens_log_y2025m04_dist_id_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_channel_tokens_log_dist_idx ATTACH PARTITION public.k3l_channel_tokens_log_y2025m04_dist_id_idx;


--
-- Name: k3l_channel_tokens_log_y2025m04_dist_status_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_channel_tokens_log_pending_idx ATTACH PARTITION public.k3l_channel_tokens_log_y2025m04_dist_status_idx;


--
-- Name: k3l_channel_tokens_log_y2025m05_channel_id_fid_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_channel_tokens_log_ch_fid_idx ATTACH PARTITION public.k3l_channel_tokens_log_y2025m05_channel_id_fid_idx;


--
-- Name: k3l_channel_tokens_log_y2025m05_dist_id_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_channel_tokens_log_dist_idx ATTACH PARTITION public.k3l_channel_tokens_log_y2025m05_dist_id_idx;


--
-- Name: k3l_channel_tokens_log_y2025m05_dist_status_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_channel_tokens_log_pending_idx ATTACH PARTITION public.k3l_channel_tokens_log_y2025m05_dist_status_idx;


--
-- Name: k3l_channel_tokens_log_y2025m06_channel_id_fid_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_channel_tokens_log_ch_fid_idx ATTACH PARTITION public.k3l_channel_tokens_log_y2025m06_channel_id_fid_idx;


--
-- Name: k3l_channel_tokens_log_y2025m06_dist_id_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_channel_tokens_log_dist_idx ATTACH PARTITION public.k3l_channel_tokens_log_y2025m06_dist_id_idx;


--
-- Name: k3l_channel_tokens_log_y2025m06_dist_status_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_channel_tokens_log_pending_idx ATTACH PARTITION public.k3l_channel_tokens_log_y2025m06_dist_status_idx;


--
-- Name: k3l_channel_openrank_results k3l_channel_openrank_results_fkey; Type: FK CONSTRAINT; Schema: public; Owner: k3l_user
--

ALTER TABLE public.k3l_channel_openrank_results
    ADD CONSTRAINT k3l_channel_openrank_results_fkey FOREIGN KEY (channel_domain_id) REFERENCES public.k3l_channel_domains(id);


--
-- Name: SCHEMA public; Type: ACL; Schema: -; Owner: pg_database_owner
--

GRANT ALL ON SCHEMA public TO k3l_user;
GRANT USAGE ON SCHEMA public TO k3l_readonly;


--
-- Name: FUNCTION end_week_9amoffset(timestamp without time zone, interval); Type: ACL; Schema: public; Owner: k3l_user
--

GRANT ALL ON FUNCTION public.end_week_9amoffset(timestamp without time zone, interval) TO k3l_readonly;


--
-- Name: TABLE alembic_version; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.alembic_version TO k3l_readonly;


--
-- Name: TABLE automod_data; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.automod_data TO k3l_readonly;


--
-- Name: TABLE balances; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.balances TO k3l_readonly;


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
-- Name: TABLE k3l_cast_action_v1; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.k3l_cast_action_v1 TO k3l_readonly;


--
-- Name: TABLE k3l_cast_action; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.k3l_cast_action TO k3l_readonly;


--
-- Name: TABLE k3l_cast_action_v1_y2024m09; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.k3l_cast_action_v1_y2024m09 TO k3l_readonly;


--
-- Name: TABLE k3l_cast_action_v1_y2024m10; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.k3l_cast_action_v1_y2024m10 TO k3l_readonly;


--
-- Name: TABLE k3l_cast_action_v1_y2024m11; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.k3l_cast_action_v1_y2024m11 TO k3l_readonly;


--
-- Name: TABLE k3l_cast_action_v1_y2024m12; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.k3l_cast_action_v1_y2024m12 TO k3l_readonly;


--
-- Name: TABLE k3l_cast_action_v1_y2025m01; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.k3l_cast_action_v1_y2025m01 TO k3l_readonly;


--
-- Name: TABLE k3l_cast_action_v1_y2025m02; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.k3l_cast_action_v1_y2025m02 TO k3l_readonly;


--
-- Name: TABLE k3l_cast_action_v1_y2025m03; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.k3l_cast_action_v1_y2025m03 TO k3l_readonly;


--
-- Name: TABLE k3l_cast_action_v1_y2025m04; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.k3l_cast_action_v1_y2025m04 TO k3l_readonly;


--
-- Name: TABLE k3l_cast_action_v1_y2025m05; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.k3l_cast_action_v1_y2025m05 TO k3l_readonly;


--
-- Name: TABLE k3l_cast_action_v1_y2025m06; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.k3l_cast_action_v1_y2025m06 TO k3l_readonly;


--
-- Name: TABLE k3l_channel_domains; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.k3l_channel_domains TO k3l_readonly;


--
-- Name: TABLE k3l_channel_fids_old; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.k3l_channel_fids_old TO k3l_readonly;


--
-- Name: TABLE k3l_channel_metrics; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.k3l_channel_metrics TO k3l_readonly;


--
-- Name: TABLE k3l_channel_metrics_y2025m01; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.k3l_channel_metrics_y2025m01 TO k3l_readonly;


--
-- Name: TABLE k3l_channel_metrics_y2025m02; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.k3l_channel_metrics_y2025m02 TO k3l_readonly;


--
-- Name: TABLE k3l_channel_metrics_y2025m03; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.k3l_channel_metrics_y2025m03 TO k3l_readonly;


--
-- Name: TABLE k3l_channel_metrics_y2025m04; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.k3l_channel_metrics_y2025m04 TO k3l_readonly;


--
-- Name: TABLE k3l_channel_metrics_y2025m05; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.k3l_channel_metrics_y2025m05 TO k3l_readonly;


--
-- Name: TABLE k3l_channel_metrics_y2025m06; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.k3l_channel_metrics_y2025m06 TO k3l_readonly;


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
-- Name: TABLE k3l_channel_points_log_y2025m04; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.k3l_channel_points_log_y2025m04 TO k3l_readonly;


--
-- Name: TABLE k3l_channel_points_log_y2025m05; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.k3l_channel_points_log_y2025m05 TO k3l_readonly;


--
-- Name: TABLE k3l_channel_points_log_y2025m06; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.k3l_channel_points_log_y2025m06 TO k3l_readonly;


--
-- Name: TABLE k3l_channel_rank; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.k3l_channel_rank TO k3l_readonly;


--
-- Name: TABLE k3l_channel_rank_log; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.k3l_channel_rank_log TO k3l_readonly;


--
-- Name: TABLE k3l_channel_rank_log_y2025m03; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.k3l_channel_rank_log_y2025m03 TO k3l_readonly;


--
-- Name: TABLE k3l_channel_rank_log_y2025m04; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.k3l_channel_rank_log_y2025m04 TO k3l_readonly;


--
-- Name: TABLE k3l_channel_rank_log_y2025m05; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.k3l_channel_rank_log_y2025m05 TO k3l_readonly;


--
-- Name: TABLE k3l_channel_rank_log_y2025m06; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.k3l_channel_rank_log_y2025m06 TO k3l_readonly;


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
-- Name: TABLE k3l_channel_tokens_log_y2025m04; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.k3l_channel_tokens_log_y2025m04 TO k3l_readonly;


--
-- Name: TABLE k3l_channel_tokens_log_y2025m05; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.k3l_channel_tokens_log_y2025m05 TO k3l_readonly;


--
-- Name: TABLE k3l_channel_tokens_log_y2025m06; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.k3l_channel_tokens_log_y2025m06 TO k3l_readonly;


--
-- Name: TABLE k3l_rank; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.k3l_rank TO k3l_readonly;


--
-- Name: TABLE k3l_recent_parent_casts; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.k3l_recent_parent_casts TO k3l_readonly;


--
-- Name: TABLE verified_addresses; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.verified_addresses TO k3l_readonly;


--
-- Name: TABLE k3l_token_holding_fids; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.k3l_token_holding_fids TO k3l_readonly;


--
-- Name: TABLE k3l_top_casters; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT ALL ON TABLE public.k3l_top_casters TO k3l_readonly;


--
-- Name: TABLE k3l_top_spammers; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT ALL ON TABLE public.k3l_top_spammers TO k3l_readonly;


--
-- Name: TABLE links; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.links TO k3l_readonly;


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
-- Name: TABLE verifications; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.verifications TO k3l_readonly;


--
-- Name: TABLE warpcast_channels_data; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.warpcast_channels_data TO k3l_readonly;


--
-- Name: TABLE warpcast_followers; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.warpcast_followers TO k3l_readonly;


--
-- Name: TABLE warpcast_members; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.warpcast_members TO k3l_readonly;


--
-- Name: DEFAULT PRIVILEGES FOR FUNCTIONS; Type: DEFAULT ACL; Schema: public; Owner: postgres
--

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON FUNCTIONS TO k3l_readonly;


--
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: public; Owner: postgres
--

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT SELECT,REFERENCES ON TABLES TO k3l_readonly;


--
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: public; Owner: k3l_user
--

ALTER DEFAULT PRIVILEGES FOR ROLE k3l_user IN SCHEMA public GRANT SELECT,REFERENCES ON TABLES TO k3l_readonly;


--
-- PostgreSQL database dump complete
--

