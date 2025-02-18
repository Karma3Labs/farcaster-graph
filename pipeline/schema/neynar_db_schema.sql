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

--
-- Name: pg_stat_statements; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pg_stat_statements WITH SCHEMA public;


--
-- Name: EXTENSION pg_stat_statements; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION pg_stat_statements IS 'track planning and execution statistics of all SQL statements executed';


--
-- Name: pgcrypto; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA public;


--
-- Name: EXTENSION pgcrypto; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION pgcrypto IS 'cryptographic functions';


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
-- Name: backfill_root_parent_hash(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.backfill_root_parent_hash() RETURNS void
    LANGUAGE plpgsql
    AS $$
DECLARE
    current_hash bytea;
    ancestor_hash bytea;
    row_hash bytea;
    row_parent_hash bytea;
BEGIN
    FOR row_hash, row_parent_hash IN SELECT hash, parent_hash FROM casts LOOP
        current_hash := row_hash;
        ancestor_hash := current_hash; -- Initialize with the current hash

        -- Loop to find the oldest ancestor
        WHILE current_hash IS NOT NULL LOOP
            SELECT parent_hash INTO current_hash FROM casts WHERE hash = current_hash;

            -- Update ancestor_hash if a parent is found
            IF current_hash IS NOT NULL THEN
                ancestor_hash := current_hash;
            END IF;
        END LOOP;

        -- Update the root_parent_hash for the current row
        UPDATE casts SET root_parent_hash = ancestor_hash WHERE hash = row_hash;
    END LOOP;
END;
$$;


ALTER FUNCTION public.backfill_root_parent_hash() OWNER TO postgres;

--
-- Name: generate_ulid(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.generate_ulid() RETURNS uuid
    LANGUAGE sql STRICT PARALLEL SAFE
    RETURN ((lpad(to_hex((floor((EXTRACT(epoch FROM clock_timestamp()) * (1000)::numeric)))::bigint), 12, '0'::text) || encode(public.gen_random_bytes(10), 'hex'::text)))::uuid;


ALTER FUNCTION public.generate_ulid() OWNER TO postgres;

--
-- Name: mark_object_deletions(text); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.mark_object_deletions(object_table_name text) RETURNS TABLE(hash bytea, deleted_at timestamp without time zone)
    LANGUAGE plpgsql
    AS $$
BEGIN
    -- Create a temporary table to store the results
    CREATE TEMP TABLE temp_updated_hashes (hash BYTEA, deleted_at TIMESTAMP);

    -- Perform the update and insert the results into the temporary table
    EXECUTE format('
        WITH updated AS (
            UPDATE %I obj
            SET deleted_at = COALESCE(m.revoked_at, m.pruned_at, m.deleted_at)
            FROM messages m
            WHERE obj.hash = m.hash
            AND obj.deleted_at IS NULL
            AND (m.revoked_at IS NOT NULL OR m.pruned_at IS NOT NULL OR m.deleted_at IS NOT NULL)
            RETURNING obj.hash, obj.deleted_at
        )
        INSERT INTO temp_updated_hashes (hash, deleted_at)
        SELECT hash, deleted_at FROM updated', object_table_name);

    -- Return the results from the temporary table
    RETURN QUERY SELECT * FROM temp_updated_hashes;

    -- Drop the temporary table
    DROP TABLE temp_updated_hashes;
END;
$$;


ALTER FUNCTION public.mark_object_deletions(object_table_name text) OWNER TO postgres;

--
-- Name: terminate_stuck_processes(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.terminate_stuck_processes() RETURNS void
    LANGUAGE plpgsql
    AS $$
DECLARE
	r record;
BEGIN
FOR r IN 
  SELECT pid 
  FROM pg_stat_activity 
  WHERE 
    (state = 'active' or state like 'idle%')
    AND 
    query like '%globaltrust%'
    AND datname = 'farcaster' and usename='postgres'
    and query_start < now() - interval '1 days'
  ORDER BY query_start asc
LOOP
  -- Attempt to terminate the backend
  PERFORM pg_terminate_backend(r.pid);
END LOOP;
END;
$$;


ALTER FUNCTION public.terminate_stuck_processes() OWNER TO postgres;

--
-- Name: update_root_parent_hash(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.update_root_parent_hash() RETURNS trigger
    LANGUAGE plpgsql
    AS $$DECLARE
    current_hash bytea;
    last_non_null_parent_hash bytea;
    root_parent_url text;
BEGIN
    -- Initialize current_hash with the parent hash of the new cast
    current_hash := NEW.parent_hash;
    last_non_null_parent_hash := NEW.parent_hash; -- Keep track of the last non-null parent hash

    -- If the inserted cast has no parent, it is its own root
    IF current_hash IS NULL THEN
        NEW.root_parent_hash := NEW.hash;
        NEW.root_parent_url := NEW.parent_url; -- Also set the root_parent_url as the cast's own parent_url
    ELSE
        -- Loop to find the furthest non-null parent hash
        LOOP
            SELECT parent_hash, parent_url INTO current_hash, root_parent_url
            FROM casts
            WHERE hash = current_hash;

            -- Exit the loop if we've reached a cast without a parent
            EXIT WHEN current_hash IS NULL;

            -- Update last_non_null_parent_hash since we've found a non-null parent hash
            last_non_null_parent_hash := current_hash;
        END LOOP;

        -- Set root_parent_hash to the furthest found non-null parent_hash
        NEW.root_parent_hash := last_non_null_parent_hash;
        -- Set root_parent_url to the parent_url of the root cast
        NEW.root_parent_url := root_parent_url;
    END IF;

    RETURN NEW;
END;$$;


ALTER FUNCTION public.update_root_parent_hash() OWNER TO postgres;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: account_verifications; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.account_verifications (
    id bigint NOT NULL,
    created_at timestamp without time zone DEFAULT '2024-10-19 09:12:00.763074'::timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone,
    fid bigint NOT NULL,
    platform character varying(20),
    platform_id text NOT NULL,
    platform_username text NOT NULL,
    verified_at timestamp without time zone,
    CONSTRAINT platform_name_check CHECK (((platform)::text = 'x'::text))
);


ALTER TABLE public.account_verifications OWNER TO postgres;

--
-- Name: account_verifications_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.account_verifications_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.account_verifications_id_seq OWNER TO postgres;

--
-- Name: account_verifications_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.account_verifications_id_seq OWNED BY public.account_verifications.id;


--
-- Name: automod_daily_data; Type: TABLE; Schema: public; Owner: k3l_user
--

CREATE TABLE public.automod_daily_data (
    created_at timestamp without time zone,
    action text,
    actor text,
    affected_username text,
    affected_userid bigint,
    cast_hash text,
    channel_id text,
    date_iso date
);


ALTER TABLE public.automod_daily_data OWNER TO k3l_user;

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
-- Name: blocks; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.blocks (
    id bigint NOT NULL,
    created_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone,
    blocker_fid bigint NOT NULL,
    blocked_fid bigint NOT NULL,
    updated_at timestamp with time zone
);


ALTER TABLE public.blocks OWNER TO postgres;

--
-- Name: blocks_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.blocks_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.blocks_id_seq OWNER TO postgres;

--
-- Name: blocks_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.blocks_id_seq OWNED BY public.blocks.id;


--
-- Name: casts; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.casts (
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


ALTER TABLE public.casts OWNER TO postgres;

--
-- Name: casts_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.casts ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.casts_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: channel_follows; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.channel_follows (
    id integer NOT NULL,
    created_at timestamp without time zone DEFAULT '2024-09-18 17:31:31.98102'::timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone,
    fid bigint NOT NULL,
    channel_id text NOT NULL,
    "timestamp" timestamp without time zone NOT NULL
);


ALTER TABLE public.channel_follows OWNER TO postgres;

--
-- Name: channel_follows_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.channel_follows_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.channel_follows_id_seq OWNER TO postgres;

--
-- Name: channel_follows_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.channel_follows_id_seq OWNED BY public.channel_follows.id;


--
-- Name: channel_members; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.channel_members (
    id integer NOT NULL,
    created_at timestamp without time zone DEFAULT '2024-09-26 21:44:23.43287'::timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone,
    fid bigint NOT NULL,
    channel_id text NOT NULL,
    "timestamp" timestamp without time zone NOT NULL
);


ALTER TABLE public.channel_members OWNER TO postgres;

--
-- Name: channel_members_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.channel_members_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.channel_members_id_seq OWNER TO postgres;

--
-- Name: channel_members_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.channel_members_id_seq OWNED BY public.channel_members.id;


--
-- Name: channels; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.channels (
    id bigint NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone,
    channel_id text NOT NULL,
    url text NOT NULL,
    description text NOT NULL,
    image_url text NOT NULL,
    lead_fid bigint NOT NULL,
    moderator_fids bigint[] NOT NULL,
    follower_count integer NOT NULL,
    "timestamp" timestamp without time zone NOT NULL
);


ALTER TABLE public.channels OWNER TO postgres;

--
-- Name: channels_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.channels_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.channels_id_seq OWNER TO postgres;

--
-- Name: channels_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.channels_id_seq OWNED BY public.channels.id;


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
-- Name: degen_tip_allowance_pretrust_received_amount_top_100_alpha_0_1; Type: TABLE; Schema: public; Owner: k3l_user
--

CREATE TABLE public.degen_tip_allowance_pretrust_received_amount_top_100_alpha_0_1 (
    i bigint NOT NULL,
    v real,
    date date DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.degen_tip_allowance_pretrust_received_amount_top_100_alpha_0_1 OWNER TO k3l_user;

--
-- Name: dist_id; Type: TABLE; Schema: public; Owner: k3l_user
--

CREATE TABLE public.dist_id (
    nextval bigint
);


ALTER TABLE public.dist_id OWNER TO k3l_user;

--
-- Name: fids; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.fids (
    fid bigint NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    custody_address bytea NOT NULL,
    registered_at timestamp with time zone
);


ALTER TABLE public.fids OWNER TO postgres;

--
-- Name: fnames; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.fnames (
    fname text NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    custody_address bytea,
    expires_at timestamp without time zone,
    fid bigint,
    deleted_at timestamp without time zone
);


ALTER TABLE public.fnames OWNER TO postgres;

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
-- Name: hub_subscriptions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.hub_subscriptions (
    host text NOT NULL,
    last_event_id bigint
);


ALTER TABLE public.hub_subscriptions OWNER TO postgres;

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

--
-- Name: reactions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.reactions (
    id bigint NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at timestamp without time zone,
    "timestamp" timestamp without time zone NOT NULL,
    reaction_type smallint NOT NULL,
    fid bigint NOT NULL,
    hash bytea NOT NULL,
    target_hash bytea,
    target_fid bigint,
    target_url text
);


ALTER TABLE public.reactions OWNER TO postgres;

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
-- Name: kysely_migration; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.kysely_migration (
    name character varying(255) NOT NULL,
    "timestamp" character varying(255) NOT NULL
);


ALTER TABLE public.kysely_migration OWNER TO postgres;

--
-- Name: kysely_migration_lock; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.kysely_migration_lock (
    id character varying(255) NOT NULL,
    is_locked integer DEFAULT 0 NOT NULL
);


ALTER TABLE public.kysely_migration_lock OWNER TO postgres;

--
-- Name: links; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.links (
    id bigint NOT NULL,
    fid bigint,
    target_fid bigint,
    hash bytea NOT NULL,
    "timestamp" timestamp without time zone NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at timestamp without time zone,
    type text,
    display_timestamp timestamp without time zone
);


ALTER TABLE public.links OWNER TO postgres;

--
-- Name: links_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.links ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.links_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: localtrust_stats; Type: TABLE; Schema: public; Owner: k3l_user
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


ALTER TABLE public.localtrust_stats OWNER TO k3l_user;

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
-- Name: messages; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.messages (
    id bigint NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at timestamp without time zone,
    pruned_at timestamp without time zone,
    revoked_at timestamp without time zone,
    "timestamp" timestamp without time zone NOT NULL,
    message_type smallint NOT NULL,
    fid bigint NOT NULL,
    hash bytea NOT NULL,
    hash_scheme smallint NOT NULL,
    signature bytea NOT NULL,
    signature_scheme smallint NOT NULL,
    signer bytea NOT NULL
);


ALTER TABLE public.messages OWNER TO postgres;

--
-- Name: messages_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.messages ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.messages_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: power_users; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.power_users (
    fid bigint NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone,
    status character varying(20),
    seed_at timestamp without time zone,
    CONSTRAINT power_users_status_enum_check CHECK (((status)::text = ANY ((ARRAY['pending'::character varying, 'power'::character varying, 'revoked'::character varying])::text[])))
);


ALTER TABLE public.power_users OWNER TO postgres;

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
-- Name: user_data; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.user_data (
    id bigint NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at timestamp without time zone,
    "timestamp" timestamp without time zone NOT NULL,
    fid bigint NOT NULL,
    hash bytea NOT NULL,
    type smallint NOT NULL,
    value text NOT NULL
);


ALTER TABLE public.user_data OWNER TO postgres;

--
-- Name: verifications; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.verifications (
    id bigint NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at timestamp without time zone,
    "timestamp" timestamp without time zone NOT NULL,
    fid bigint NOT NULL,
    hash bytea NOT NULL,
    claim jsonb NOT NULL
);


ALTER TABLE public.verifications OWNER TO postgres;

--
-- Name: profile_with_addresses; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.profile_with_addresses AS
 SELECT main.fid,
    COALESCE(NULLIF(main.fname, ''::text), main.fname_noproof) AS fname,
    main.display_name,
    main.avatar_url,
    main.bio,
    COALESCE(addr.addresses, '[]'::jsonb) AS verified_addresses
   FROM (( SELECT f.fid,
            fn.fname AS fname_noproof,
            encode(f.custody_address, 'hex'::text) AS custody_address_hex,
            max(
                CASE
                    WHEN (ud.type = 6) THEN ud.value
                    ELSE NULL::text
                END) AS fname,
            max(
                CASE
                    WHEN (ud.type = 2) THEN ud.value
                    ELSE NULL::text
                END) AS display_name,
            max(
                CASE
                    WHEN (ud.type = 1) THEN ud.value
                    ELSE NULL::text
                END) AS avatar_url,
            max(
                CASE
                    WHEN (ud.type = 3) THEN ud.value
                    ELSE NULL::text
                END) AS bio
           FROM ((public.fids f
             LEFT JOIN public.fnames fn ON ((f.custody_address = fn.custody_address)))
             LEFT JOIN public.user_data ud ON ((f.fid = ud.fid)))
          GROUP BY f.fid, fn.fname, f.custody_address) main
     LEFT JOIN ( SELECT verifications.fid,
            jsonb_agg((verifications.claim ->> 'address'::text) ORDER BY verifications."timestamp") AS addresses
           FROM public.verifications
          GROUP BY verifications.fid) addr ON ((main.fid = addr.fid)));


ALTER VIEW public.profile_with_addresses OWNER TO postgres;

--
-- Name: reactions_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.reactions ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.reactions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: signers; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.signers (
    id bigint NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at timestamp without time zone,
    "timestamp" timestamp without time zone NOT NULL,
    fid bigint NOT NULL,
    hash bytea,
    custody_address bytea,
    signer bytea NOT NULL,
    name text,
    app_fid bigint
);


ALTER TABLE public.signers OWNER TO postgres;

--
-- Name: signers_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.signers ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.signers_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: storage; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.storage (
    id bigint NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at timestamp without time zone,
    "timestamp" timestamp without time zone NOT NULL,
    fid bigint NOT NULL,
    units bigint NOT NULL,
    expiry timestamp without time zone NOT NULL
);


ALTER TABLE public.storage OWNER TO postgres;

--
-- Name: storage_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.storage ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.storage_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: tmp_globaltrust; Type: TABLE; Schema: public; Owner: k3l_user
--

CREATE UNLOGGED TABLE public.tmp_globaltrust (
    strategy_id integer,
    i bigint,
    v real,
    date date
);


ALTER TABLE public.tmp_globaltrust OWNER TO k3l_user;

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
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tokens_dist_seq OWNER TO k3l_user;

--
-- Name: top_channel_casters; Type: TABLE; Schema: public; Owner: k3l_user
--

CREATE TABLE public.top_channel_casters (
    cast_hash character varying NOT NULL,
    fid bigint NOT NULL,
    cast_score double precision NOT NULL,
    reaction_count bigint NOT NULL,
    global_rank bigint NOT NULL,
    channel_rank bigint NOT NULL,
    cast_hour timestamp without time zone NOT NULL,
    cast_ts timestamp without time zone NOT NULL,
    cast_text text NOT NULL,
    channel_id text NOT NULL,
    date_iso date NOT NULL
);


ALTER TABLE public.top_channel_casters OWNER TO k3l_user;

--
-- Name: user_data_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.user_data ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.user_data_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: user_labels; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.user_labels (
    id bigint NOT NULL,
    source text NOT NULL,
    provider_fid bigint NOT NULL,
    target_fid bigint NOT NULL,
    label_type text NOT NULL,
    label_value text NOT NULL,
    "timestamp" timestamp without time zone NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE public.user_labels OWNER TO postgres;

--
-- Name: user_labels_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.user_labels_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.user_labels_id_seq OWNER TO postgres;

--
-- Name: user_labels_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.user_labels_id_seq OWNED BY public.user_labels.id;


--
-- Name: verifications_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.verifications ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.verifications_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: warpcast_channels_data; Type: TABLE; Schema: public; Owner: k3l_user
--

CREATE TABLE public.warpcast_channels_data (
    id text NOT NULL,
    url text NOT NULL,
    name text NOT NULL,
    description text,
    imageurl text,
    headerimageurl text,
    leadfid bigint,
    moderatorfids bigint[],
    createdat timestamp without time zone,
    followercount integer NOT NULL,
    membercount integer NOT NULL,
    pinnedcasthash text,
    insert_ts timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.warpcast_channels_data OWNER TO k3l_user;

--
-- Name: warpcast_followers; Type: TABLE; Schema: public; Owner: k3l_user
--

CREATE TABLE public.warpcast_followers (
    fid bigint NOT NULL,
    followedat bigint NOT NULL,
    insert_ts timestamp without time zone NOT NULL,
    channel_id text NOT NULL
);


ALTER TABLE public.warpcast_followers OWNER TO k3l_user;

--
-- Name: warpcast_followers_bkup_20241210; Type: TABLE; Schema: public; Owner: k3l_user
--

CREATE TABLE public.warpcast_followers_bkup_20241210 (
    fid bigint NOT NULL,
    followedat bigint NOT NULL,
    insert_ts timestamp without time zone NOT NULL,
    channel_id text NOT NULL
);


ALTER TABLE public.warpcast_followers_bkup_20241210 OWNER TO k3l_user;

--
-- Name: warpcast_members; Type: TABLE; Schema: public; Owner: k3l_user
--

CREATE TABLE public.warpcast_members (
    fid bigint NOT NULL,
    memberat bigint NOT NULL,
    insert_ts timestamp without time zone NOT NULL,
    channel_id text NOT NULL
);


ALTER TABLE public.warpcast_members OWNER TO k3l_user;

--
-- Name: warpcast_members_old; Type: TABLE; Schema: public; Owner: k3l_user
--

CREATE TABLE public.warpcast_members_old (
    fid bigint NOT NULL,
    memberat bigint NOT NULL,
    insert_ts timestamp without time zone NOT NULL,
    channel_id text NOT NULL
);


ALTER TABLE public.warpcast_members_old OWNER TO k3l_user;

--
-- Name: warpcast_power_users; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.warpcast_power_users (
    fid bigint NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


ALTER TABLE public.warpcast_power_users OWNER TO postgres;

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
-- Name: account_verifications id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.account_verifications ALTER COLUMN id SET DEFAULT nextval('public.account_verifications_id_seq'::regclass);


--
-- Name: blocks id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.blocks ALTER COLUMN id SET DEFAULT nextval('public.blocks_id_seq'::regclass);


--
-- Name: channel_follows id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.channel_follows ALTER COLUMN id SET DEFAULT nextval('public.channel_follows_id_seq'::regclass);


--
-- Name: channel_members id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.channel_members ALTER COLUMN id SET DEFAULT nextval('public.channel_members_id_seq'::regclass);


--
-- Name: channels id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.channels ALTER COLUMN id SET DEFAULT nextval('public.channels_id_seq'::regclass);


--
-- Name: k3l_degen_tips id; Type: DEFAULT; Schema: public; Owner: k3l_user
--

ALTER TABLE ONLY public.k3l_degen_tips ALTER COLUMN id SET DEFAULT nextval('public.k3l_degen_tips_id_seq'::regclass);


--
-- Name: user_labels id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_labels ALTER COLUMN id SET DEFAULT nextval('public.user_labels_id_seq'::regclass);


--
-- Name: account_verifications account_verifications_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.account_verifications
    ADD CONSTRAINT account_verifications_pkey PRIMARY KEY (id);


--
-- Name: blocks blocks_blocker_blocked; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.blocks
    ADD CONSTRAINT blocks_blocker_blocked UNIQUE (blocker_fid, blocked_fid);


--
-- Name: blocks blocks_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.blocks
    ADD CONSTRAINT blocks_pkey PRIMARY KEY (id);


--
-- Name: casts casts_hash_unique; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.casts
    ADD CONSTRAINT casts_hash_unique UNIQUE (hash);


--
-- Name: casts casts_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.casts
    ADD CONSTRAINT casts_pkey PRIMARY KEY (id);


--
-- Name: channel_follows channel_follows_fid_channel_id_unique; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.channel_follows
    ADD CONSTRAINT channel_follows_fid_channel_id_unique UNIQUE (fid, channel_id);


--
-- Name: channel_follows channel_follows_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.channel_follows
    ADD CONSTRAINT channel_follows_pkey PRIMARY KEY (id);


--
-- Name: channel_members channel_members_fid_channel_id_unique; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.channel_members
    ADD CONSTRAINT channel_members_fid_channel_id_unique UNIQUE (fid, channel_id);


--
-- Name: channel_members channel_members_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.channel_members
    ADD CONSTRAINT channel_members_pkey PRIMARY KEY (id);


--
-- Name: channels channels_channel_id_unique; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.channels
    ADD CONSTRAINT channels_channel_id_unique UNIQUE (channel_id);


--
-- Name: channels channels_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.channels
    ADD CONSTRAINT channels_pkey PRIMARY KEY (id);


--
-- Name: degen_tip_allowance_pretrust_received_amount_top_100_alpha_0_1 degen_tip_allowance_pretrust_received_amount_top_100_alpha_pkey; Type: CONSTRAINT; Schema: public; Owner: k3l_user
--

ALTER TABLE ONLY public.degen_tip_allowance_pretrust_received_amount_top_100_alpha_0_1
    ADD CONSTRAINT degen_tip_allowance_pretrust_received_amount_top_100_alpha_pkey PRIMARY KEY (i);


--
-- Name: pretrust fid_insert_ts_unique; Type: CONSTRAINT; Schema: public; Owner: k3l_user
--

ALTER TABLE ONLY public.pretrust
    ADD CONSTRAINT fid_insert_ts_unique UNIQUE (fid, insert_ts);


--
-- Name: fids fids_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.fids
    ADD CONSTRAINT fids_pkey PRIMARY KEY (fid);


--
-- Name: fnames fnames_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.fnames
    ADD CONSTRAINT fnames_pkey PRIMARY KEY (fname);


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
-- Name: hub_subscriptions hub_subscriptions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.hub_subscriptions
    ADD CONSTRAINT hub_subscriptions_pkey PRIMARY KEY (host);


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
-- Name: kysely_migration_lock kysely_migration_lock_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.kysely_migration_lock
    ADD CONSTRAINT kysely_migration_lock_pkey PRIMARY KEY (id);


--
-- Name: kysely_migration kysely_migration_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.kysely_migration
    ADD CONSTRAINT kysely_migration_pkey PRIMARY KEY (name);


--
-- Name: links links_fid_target_fid_type_unique; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.links
    ADD CONSTRAINT links_fid_target_fid_type_unique UNIQUE (fid, target_fid, type);


--
-- Name: links links_hash_unique; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.links
    ADD CONSTRAINT links_hash_unique UNIQUE (hash);


--
-- Name: links links_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.links
    ADD CONSTRAINT links_pkey PRIMARY KEY (id);


--
-- Name: messages messages_hash_unique; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.messages
    ADD CONSTRAINT messages_hash_unique UNIQUE (hash);


--
-- Name: messages messages_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.messages
    ADD CONSTRAINT messages_pkey PRIMARY KEY (id);


--
-- Name: k3l_channel_domains openrank_reqs_pkey; Type: CONSTRAINT; Schema: public; Owner: k3l_user
--

ALTER TABLE ONLY public.k3l_channel_domains
    ADD CONSTRAINT openrank_reqs_pkey PRIMARY KEY (id);


--
-- Name: power_users power_users_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.power_users
    ADD CONSTRAINT power_users_pkey PRIMARY KEY (fid);


--
-- Name: reactions reactions_hash_unique; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.reactions
    ADD CONSTRAINT reactions_hash_unique UNIQUE (hash);


--
-- Name: reactions reactions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.reactions
    ADD CONSTRAINT reactions_pkey PRIMARY KEY (id);


--
-- Name: signers signers_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.signers
    ADD CONSTRAINT signers_pkey PRIMARY KEY (id);


--
-- Name: storage storage_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.storage
    ADD CONSTRAINT storage_pkey PRIMARY KEY (id);


--
-- Name: k3l_degen_tips unique_cast_hash; Type: CONSTRAINT; Schema: public; Owner: k3l_user
--

ALTER TABLE ONLY public.k3l_degen_tips
    ADD CONSTRAINT unique_cast_hash UNIQUE (cast_hash);


--
-- Name: storage unique_fid_units_expiry; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.storage
    ADD CONSTRAINT unique_fid_units_expiry UNIQUE (fid, units, expiry);


--
-- Name: signers unique_timestamp_fid_signer; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.signers
    ADD CONSTRAINT unique_timestamp_fid_signer UNIQUE ("timestamp", fid, signer);


--
-- Name: user_data user_data_fid_type_unique; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_data
    ADD CONSTRAINT user_data_fid_type_unique UNIQUE (fid, type);


--
-- Name: user_data user_data_hash_unique; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_data
    ADD CONSTRAINT user_data_hash_unique UNIQUE (hash);


--
-- Name: user_data user_data_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_data
    ADD CONSTRAINT user_data_pkey PRIMARY KEY (id);


--
-- Name: user_labels user_labels_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_labels
    ADD CONSTRAINT user_labels_pkey PRIMARY KEY (id);


--
-- Name: user_labels user_labels_unique_idx; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_labels
    ADD CONSTRAINT user_labels_unique_idx UNIQUE (provider_fid, source, target_fid, label_type);


--
-- Name: verifications verifications_hash_unique; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.verifications
    ADD CONSTRAINT verifications_hash_unique UNIQUE (hash);


--
-- Name: verifications verifications_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.verifications
    ADD CONSTRAINT verifications_pkey PRIMARY KEY (id);


--
-- Name: warpcast_power_users warpcast_power_users_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.warpcast_power_users
    ADD CONSTRAINT warpcast_power_users_pkey PRIMARY KEY (fid);


--
-- Name: account_verifications_fid_deleted_at_is_null_index; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX account_verifications_fid_deleted_at_is_null_index ON public.account_verifications USING btree (fid) WHERE (deleted_at IS NULL);


--
-- Name: blocks_blocked_fid_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX blocks_blocked_fid_deleted_at ON public.blocks USING btree (blocked_fid, deleted_at) WHERE (deleted_at IS NULL);


--
-- Name: blocks_blocker_fid_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX blocks_blocker_fid_deleted_at ON public.blocks USING btree (blocker_fid, deleted_at) WHERE (deleted_at IS NULL);


--
-- Name: casts_created_at_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX casts_created_at_idx ON public.casts USING btree (created_at);


--
-- Name: casts_deleted_at_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX casts_deleted_at_idx ON public.casts USING btree (deleted_at);


--
-- Name: casts_fid_timestamp_index; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX casts_fid_timestamp_index ON public.casts USING btree (fid, "timestamp");


--
-- Name: casts_parent_hash_parent_fid_index; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX casts_parent_hash_parent_fid_index ON public.casts USING btree (parent_hash, parent_fid) WHERE ((parent_hash IS NOT NULL) AND (parent_fid IS NOT NULL));


--
-- Name: casts_parent_url_index; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX casts_parent_url_index ON public.casts USING btree (parent_url) WHERE (parent_url IS NOT NULL);


--
-- Name: casts_timestamp_index; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX casts_timestamp_index ON public.casts USING btree ("timestamp");


--
-- Name: casts_updated_at_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX casts_updated_at_idx ON public.casts USING btree (updated_at);


--
-- Name: channel_follows_channel_id_deleted_at_is_null_timestamp_index; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX channel_follows_channel_id_deleted_at_is_null_timestamp_index ON public.channel_follows USING btree (channel_id, deleted_at, "timestamp") WHERE (deleted_at IS NULL);


--
-- Name: channel_follows_deleted_at_index; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX channel_follows_deleted_at_index ON public.channel_follows USING btree (deleted_at);


--
-- Name: channel_follows_fid_deleted_at_is_null_timestamp_index; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX channel_follows_fid_deleted_at_is_null_timestamp_index ON public.channel_follows USING btree (fid, deleted_at, "timestamp") WHERE (deleted_at IS NULL);


--
-- Name: channel_members_channel_id_deleted_at_is_null_timestamp_index; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX channel_members_channel_id_deleted_at_is_null_timestamp_index ON public.channel_members USING btree (channel_id, deleted_at, "timestamp") WHERE (deleted_at IS NULL);


--
-- Name: channel_members_deleted_at_index; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX channel_members_deleted_at_index ON public.channel_members USING btree (deleted_at);


--
-- Name: channel_members_fid_deleted_at_is_null_timestamp_index; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX channel_members_fid_deleted_at_is_null_timestamp_index ON public.channel_members USING btree (fid, deleted_at, "timestamp") WHERE (deleted_at IS NULL);


--
-- Name: channels_channel_id_deleted_at_is_null_timestamp_index; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX channels_channel_id_deleted_at_is_null_timestamp_index ON public.channels USING btree (channel_id, deleted_at, "timestamp") WHERE (deleted_at IS NULL);


--
-- Name: channels_deleted_at_index; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX channels_deleted_at_index ON public.channels USING btree (deleted_at);


--
-- Name: channels_url_deleted_at_is_null_timestamp_index; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX channels_url_deleted_at_is_null_timestamp_index ON public.channels USING btree (url, deleted_at, "timestamp") WHERE (deleted_at IS NULL);


--
-- Name: cura_hidden_fids_ch_fid_act_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX cura_hidden_fids_ch_fid_act_idx ON public.cura_hidden_fids USING btree (channel_id, hidden_fid, is_active);


--
-- Name: fids_created_at_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX fids_created_at_idx ON public.fids USING btree (created_at);


--
-- Name: fids_updated_at_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX fids_updated_at_idx ON public.fids USING btree (updated_at);


--
-- Name: fnames_created_at_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX fnames_created_at_idx ON public.fnames USING btree (created_at);


--
-- Name: fnames_deleted_at_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX fnames_deleted_at_idx ON public.fnames USING btree (deleted_at);


--
-- Name: fnames_expires_at_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX fnames_expires_at_idx ON public.fnames USING btree (expires_at);


--
-- Name: fnames_updated_at_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX fnames_updated_at_idx ON public.fnames USING btree (updated_at);


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
-- Name: idx_casts_hash_timestamp; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_casts_hash_timestamp ON public.casts USING btree (hash, "timestamp");


--
-- Name: idx_casts_mentions; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_casts_mentions ON public.casts USING gin (mentions);


--
-- Name: idx_casts_root_parent_url; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_casts_root_parent_url ON public.casts USING btree (root_parent_url);


--
-- Name: idx_casts_root_parent_url_parent_hash_fid; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_casts_root_parent_url_parent_hash_fid ON public.casts USING btree (root_parent_url, parent_hash, fid);


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
-- Name: idx_links_fid_target_fid_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_links_fid_target_fid_type ON public.links USING btree (fid, target_fid, type);


--
-- Name: idx_parent_fid; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_parent_fid ON public.casts USING btree (parent_fid);


--
-- Name: idx_parent_hash; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_parent_hash ON public.casts USING btree (parent_hash) WITH (deduplicate_items='false');


--
-- Name: idx_reactions_target_fid_timestamp; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_reactions_target_fid_timestamp ON public.reactions USING btree (target_fid, "timestamp");


--
-- Name: idx_reactions_target_hash_deleted_at_timestamp; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_reactions_target_hash_deleted_at_timestamp ON public.reactions USING btree (target_hash, deleted_at, "timestamp" DESC) WITH (deduplicate_items='false');


--
-- Name: idx_reactions_target_hash_fid_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_reactions_target_hash_fid_type ON public.reactions USING btree (target_hash, target_fid, reaction_type);


--
-- Name: idx_user_data_fid_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_data_fid_type ON public.user_data USING btree (fid, type) WITH (deduplicate_items='false');


--
-- Name: idx_user_data_type_lower_value_text; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_data_type_lower_value_text ON public.user_data USING btree (type, lower(value) text_pattern_ops) WHERE (type = ANY (ARRAY[2, 6]));


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
-- Name: links_created_at_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX links_created_at_idx ON public.links USING btree (created_at);


--
-- Name: links_deleted_at_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX links_deleted_at_idx ON public.links USING btree (deleted_at);


--
-- Name: links_updated_at_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX links_updated_at_idx ON public.links USING btree (updated_at);


--
-- Name: messages_created_at_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX messages_created_at_idx ON public.messages USING btree (created_at);


--
-- Name: messages_deleted_at_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX messages_deleted_at_idx ON public.messages USING btree (deleted_at);


--
-- Name: messages_pruned_at_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX messages_pruned_at_idx ON public.messages USING btree (pruned_at);


--
-- Name: messages_revoked_at_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX messages_revoked_at_idx ON public.messages USING btree (revoked_at);


--
-- Name: messages_timestamp_index; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX messages_timestamp_index ON public.messages USING btree ("timestamp");


--
-- Name: messages_updated_at_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX messages_updated_at_idx ON public.messages USING btree (updated_at);


--
-- Name: reactions_created_at_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX reactions_created_at_idx ON public.reactions USING btree (created_at);


--
-- Name: reactions_fid_timestamp_index; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX reactions_fid_timestamp_index ON public.reactions USING btree (fid, "timestamp");


--
-- Name: reactions_target_hash_target_fid_index; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX reactions_target_hash_target_fid_index ON public.reactions USING btree (target_hash, target_fid) WHERE ((target_hash IS NOT NULL) AND (target_fid IS NOT NULL));


--
-- Name: reactions_target_url_index; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX reactions_target_url_index ON public.reactions USING btree (target_url) WHERE (target_url IS NOT NULL);


--
-- Name: reactions_updated_at_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX reactions_updated_at_idx ON public.reactions USING btree (updated_at);


--
-- Name: root_parent_hash_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX root_parent_hash_idx ON public.casts USING btree (root_parent_hash);


--
-- Name: signers_created_at_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX signers_created_at_idx ON public.signers USING btree (created_at);


--
-- Name: signers_deleted_at_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX signers_deleted_at_idx ON public.signers USING btree (deleted_at);


--
-- Name: signers_fid_timestamp_index; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX signers_fid_timestamp_index ON public.signers USING btree (fid, "timestamp");


--
-- Name: signers_updated_at_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX signers_updated_at_idx ON public.signers USING btree (updated_at);


--
-- Name: storage_created_at_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX storage_created_at_idx ON public.storage USING btree (created_at);


--
-- Name: storage_deleted_at_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX storage_deleted_at_idx ON public.storage USING btree (deleted_at);


--
-- Name: storage_updated_at_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX storage_updated_at_idx ON public.storage USING btree (updated_at);


--
-- Name: timestamp_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX timestamp_idx ON public.reactions USING btree ("timestamp");


--
-- Name: user_data_created_at_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX user_data_created_at_idx ON public.user_data USING btree (created_at);


--
-- Name: user_data_deleted_at_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX user_data_deleted_at_idx ON public.user_data USING btree (deleted_at);


--
-- Name: user_data_fid_index; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX user_data_fid_index ON public.user_data USING btree (fid);


--
-- Name: user_data_updated_at_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX user_data_updated_at_idx ON public.user_data USING btree (updated_at);


--
-- Name: user_labels_timestamp_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX user_labels_timestamp_idx ON public.user_labels USING btree ("timestamp");


--
-- Name: verifications_claim_address_index; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX verifications_claim_address_index ON public.verifications USING btree (((claim ->> 'address'::text)));


--
-- Name: verifications_created_at_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX verifications_created_at_idx ON public.verifications USING btree (created_at);


--
-- Name: verifications_deleted_at_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX verifications_deleted_at_idx ON public.verifications USING btree (deleted_at);


--
-- Name: verifications_fid_timestamp_index; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX verifications_fid_timestamp_index ON public.verifications USING btree (fid, "timestamp");


--
-- Name: verifications_updated_at_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX verifications_updated_at_idx ON public.verifications USING btree (updated_at);


--
-- Name: warpcast_followers_bkup_20241210_channel_id_fid_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX warpcast_followers_bkup_20241210_channel_id_fid_idx ON public.warpcast_followers_bkup_20241210 USING btree (channel_id, fid);


--
-- Name: warpcast_followers_bkup_20241210_channel_id_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX warpcast_followers_bkup_20241210_channel_id_idx ON public.warpcast_followers_bkup_20241210 USING btree (channel_id);


--
-- Name: warpcast_followers_bkup_20241210_fid_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX warpcast_followers_bkup_20241210_fid_idx ON public.warpcast_followers_bkup_20241210 USING btree (fid);


--
-- Name: warpcast_followers_bkup_20241210_insert_ts_channel_id_fid_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX warpcast_followers_bkup_20241210_insert_ts_channel_id_fid_idx ON public.warpcast_followers_bkup_20241210 USING btree (insert_ts, channel_id, fid);


--
-- Name: warpcast_followers_new_channel_id_fid_idx1; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX warpcast_followers_new_channel_id_fid_idx1 ON public.warpcast_followers USING btree (channel_id, fid);


--
-- Name: warpcast_followers_new_channel_id_idx1; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX warpcast_followers_new_channel_id_idx1 ON public.warpcast_followers USING btree (channel_id);


--
-- Name: warpcast_followers_new_fid_idx1; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX warpcast_followers_new_fid_idx1 ON public.warpcast_followers USING btree (fid);


--
-- Name: warpcast_followers_new_insert_ts_channel_id_fid_idx1; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX warpcast_followers_new_insert_ts_channel_id_fid_idx1 ON public.warpcast_followers USING btree (insert_ts, channel_id, fid);


--
-- Name: warpcast_members_new_channel_id_fid_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX warpcast_members_new_channel_id_fid_idx ON public.warpcast_members_old USING btree (channel_id, fid);


--
-- Name: warpcast_members_new_channel_id_fid_idx1; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX warpcast_members_new_channel_id_fid_idx1 ON public.warpcast_members USING btree (channel_id, fid);


--
-- Name: warpcast_members_new_channel_id_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX warpcast_members_new_channel_id_idx ON public.warpcast_members_old USING btree (channel_id);


--
-- Name: warpcast_members_new_channel_id_idx1; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX warpcast_members_new_channel_id_idx1 ON public.warpcast_members USING btree (channel_id);


--
-- Name: warpcast_members_new_fid_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX warpcast_members_new_fid_idx ON public.warpcast_members_old USING btree (fid);


--
-- Name: warpcast_members_new_fid_idx1; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX warpcast_members_new_fid_idx1 ON public.warpcast_members USING btree (fid);


--
-- Name: warpcast_members_new_insert_ts_channel_id_fid_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX warpcast_members_new_insert_ts_channel_id_fid_idx ON public.warpcast_members_old USING btree (insert_ts, channel_id, fid);


--
-- Name: warpcast_members_new_insert_ts_channel_id_fid_idx1; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX warpcast_members_new_insert_ts_channel_id_fid_idx1 ON public.warpcast_members USING btree (insert_ts, channel_id, fid);


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
-- Name: casts trigger_update_root_parent_hash; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trigger_update_root_parent_hash BEFORE INSERT ON public.casts FOR EACH ROW EXECUTE FUNCTION public.update_root_parent_hash();


--
-- Name: casts casts_hash_foreign; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.casts
    ADD CONSTRAINT casts_hash_foreign FOREIGN KEY (hash) REFERENCES public.messages(hash);


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
-- Name: reactions reactions_hash_foreign; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.reactions
    ADD CONSTRAINT reactions_hash_foreign FOREIGN KEY (hash) REFERENCES public.messages(hash);


--
-- Name: user_data user_data_hash_foreign; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_data
    ADD CONSTRAINT user_data_hash_foreign FOREIGN KEY (hash) REFERENCES public.messages(hash);


--
-- Name: verifications verifications_hash_foreign; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.verifications
    ADD CONSTRAINT verifications_hash_foreign FOREIGN KEY (hash) REFERENCES public.messages(hash);


--
-- Name: SCHEMA public; Type: ACL; Schema: -; Owner: pg_database_owner
--

GRANT ALL ON SCHEMA public TO k3l_user;
GRANT USAGE ON SCHEMA public TO k3l_readonly;
GRANT USAGE ON SCHEMA public TO airbyte_user;


--
-- Name: TABLE automod_data; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.automod_data TO k3l_readonly;


--
-- Name: TABLE casts; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,REFERENCES ON TABLE public.casts TO k3l_user;
GRANT SELECT,REFERENCES ON TABLE public.casts TO k3l_readonly;


--
-- Name: TABLE cura_hidden_fids; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.cura_hidden_fids TO k3l_readonly;


--
-- Name: TABLE degen_tip_allowance_pretrust_received_amount_top_100_alpha_0_1; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.degen_tip_allowance_pretrust_received_amount_top_100_alpha_0_1 TO k3l_readonly;


--
-- Name: TABLE dist_id; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.dist_id TO k3l_readonly;


--
-- Name: TABLE fids; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,REFERENCES ON TABLE public.fids TO k3l_user;
GRANT SELECT,REFERENCES ON TABLE public.fids TO k3l_readonly;


--
-- Name: TABLE fnames; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,REFERENCES ON TABLE public.fnames TO k3l_user;
GRANT SELECT,REFERENCES ON TABLE public.fnames TO k3l_readonly;


--
-- Name: TABLE globaltrust; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.globaltrust TO k3l_readonly;


--
-- Name: TABLE globaltrust_config; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.globaltrust_config TO k3l_readonly;


--
-- Name: TABLE hub_subscriptions; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,REFERENCES ON TABLE public.hub_subscriptions TO k3l_user;
GRANT SELECT,REFERENCES ON TABLE public.hub_subscriptions TO k3l_readonly;


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
-- Name: TABLE reactions; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,REFERENCES ON TABLE public.reactions TO k3l_user;
GRANT SELECT,REFERENCES ON TABLE public.reactions TO k3l_readonly;


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
-- Name: TABLE kysely_migration; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,REFERENCES ON TABLE public.kysely_migration TO k3l_user;
GRANT SELECT,REFERENCES ON TABLE public.kysely_migration TO k3l_readonly;


--
-- Name: TABLE kysely_migration_lock; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,REFERENCES ON TABLE public.kysely_migration_lock TO k3l_user;
GRANT SELECT,REFERENCES ON TABLE public.kysely_migration_lock TO k3l_readonly;


--
-- Name: TABLE links; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,REFERENCES ON TABLE public.links TO k3l_user;
GRANT SELECT,REFERENCES ON TABLE public.links TO k3l_readonly;


--
-- Name: TABLE localtrust_stats; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.localtrust_stats TO k3l_readonly;


--
-- Name: TABLE localtrust_stats_v2; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT ALL ON TABLE public.localtrust_stats_v2 TO k3l_readonly;


--
-- Name: TABLE messages; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,REFERENCES ON TABLE public.messages TO k3l_user;
GRANT SELECT,REFERENCES ON TABLE public.messages TO k3l_readonly;


--
-- Name: TABLE pretrust; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.pretrust TO k3l_readonly;


--
-- Name: TABLE pretrust_v2; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT ALL ON TABLE public.pretrust_v2 TO k3l_readonly;


--
-- Name: TABLE user_data; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,REFERENCES ON TABLE public.user_data TO k3l_user;
GRANT SELECT,REFERENCES ON TABLE public.user_data TO k3l_readonly;


--
-- Name: TABLE verifications; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,REFERENCES ON TABLE public.verifications TO k3l_user;
GRANT SELECT,REFERENCES ON TABLE public.verifications TO k3l_readonly;


--
-- Name: TABLE profile_with_addresses; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,REFERENCES ON TABLE public.profile_with_addresses TO k3l_user;
GRANT SELECT,REFERENCES ON TABLE public.profile_with_addresses TO k3l_readonly;


--
-- Name: TABLE signers; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,REFERENCES ON TABLE public.signers TO k3l_user;
GRANT SELECT,REFERENCES ON TABLE public.signers TO k3l_readonly;


--
-- Name: TABLE storage; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,REFERENCES ON TABLE public.storage TO k3l_user;
GRANT SELECT,REFERENCES ON TABLE public.storage TO k3l_readonly;


--
-- Name: TABLE tmp_globaltrust_v2; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.tmp_globaltrust_v2 TO k3l_readonly;


--
-- Name: TABLE warpcast_channels_data; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.warpcast_channels_data TO k3l_readonly;


--
-- Name: TABLE warpcast_followers; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.warpcast_followers TO k3l_readonly;


--
-- Name: TABLE warpcast_followers_bkup_20241210; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.warpcast_followers_bkup_20241210 TO k3l_readonly;


--
-- Name: TABLE warpcast_members; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.warpcast_members TO k3l_readonly;


--
-- Name: TABLE warpcast_members_old; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.warpcast_members_old TO k3l_readonly;


--
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: public; Owner: k3l_user
--

ALTER DEFAULT PRIVILEGES FOR ROLE k3l_user IN SCHEMA public GRANT SELECT,REFERENCES ON TABLES TO k3l_readonly;


--
-- PostgreSQL database dump complete
--

