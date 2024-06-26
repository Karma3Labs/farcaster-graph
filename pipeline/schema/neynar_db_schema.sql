--
-- PostgreSQL database dump
--

-- Dumped from database version 16.2
-- Dumped by pg_dump version 16.2

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
-- Name: pgcrypto; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA public;


--
-- Name: EXTENSION pgcrypto; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION pgcrypto IS 'cryptographic functions';


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
-- Name: fids; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.fids (
    fid bigint NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    custody_address bytea NOT NULL
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
-- Name: k3l_cast_action_y2024m04; Type: TABLE; Schema: public; Owner: k3l_user
--

CREATE TABLE public.k3l_cast_action_y2024m04 (
    fid bigint NOT NULL,
    cast_hash bytea NOT NULL,
    casted integer NOT NULL,
    replied integer NOT NULL,
    recasted integer NOT NULL,
    liked integer NOT NULL,
    action_ts timestamp without time zone NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE public.k3l_cast_action_y2024m04 OWNER TO k3l_user;

--
-- Name: k3l_cast_action_y2024m05; Type: TABLE; Schema: public; Owner: k3l_user
--

CREATE TABLE public.k3l_cast_action_y2024m05 (
    fid bigint NOT NULL,
    cast_hash bytea NOT NULL,
    casted integer NOT NULL,
    replied integer NOT NULL,
    recasted integer NOT NULL,
    liked integer NOT NULL,
    action_ts timestamp without time zone NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE public.k3l_cast_action_y2024m05 OWNER TO k3l_user;

--
-- Name: k3l_cast_action_y2024m06; Type: TABLE; Schema: public; Owner: k3l_user
--

CREATE TABLE public.k3l_cast_action_y2024m06 (
    fid bigint NOT NULL,
    cast_hash bytea NOT NULL,
    casted integer NOT NULL,
    replied integer NOT NULL,
    recasted integer NOT NULL,
    liked integer NOT NULL,
    action_ts timestamp without time zone NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE public.k3l_cast_action_y2024m06 OWNER TO k3l_user;

--
-- Name: k3l_cast_action_y2024m07; Type: TABLE; Schema: public; Owner: k3l_user
--

CREATE TABLE public.k3l_cast_action_y2024m07 (
    fid bigint NOT NULL,
    cast_hash bytea NOT NULL,
    casted integer NOT NULL,
    replied integer NOT NULL,
    recasted integer NOT NULL,
    liked integer NOT NULL,
    action_ts timestamp without time zone NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE public.k3l_cast_action_y2024m07 OWNER TO k3l_user;

--
-- Name: k3l_cast_action_y2024m08; Type: TABLE; Schema: public; Owner: k3l_user
--

CREATE TABLE public.k3l_cast_action_y2024m08 (
    fid bigint NOT NULL,
    cast_hash bytea NOT NULL,
    casted integer NOT NULL,
    replied integer NOT NULL,
    recasted integer NOT NULL,
    liked integer NOT NULL,
    action_ts timestamp without time zone NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE public.k3l_cast_action_y2024m08 OWNER TO k3l_user;

--
-- Name: k3l_cast_action_y2024m09; Type: TABLE; Schema: public; Owner: k3l_user
--

CREATE TABLE public.k3l_cast_action_y2024m09 (
    fid bigint NOT NULL,
    cast_hash bytea NOT NULL,
    casted integer NOT NULL,
    replied integer NOT NULL,
    recasted integer NOT NULL,
    liked integer NOT NULL,
    action_ts timestamp without time zone NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE public.k3l_cast_action_y2024m09 OWNER TO k3l_user;

--
-- Name: k3l_cast_embed_url_mapping; Type: TABLE; Schema: public; Owner: k3l_user
--

CREATE TABLE public.k3l_cast_embed_url_mapping (
    url_id bigint,
    cast_id bigint
);


ALTER TABLE public.k3l_cast_embed_url_mapping OWNER TO k3l_user;

--
-- Name: k3l_channel_fids; Type: TABLE; Schema: public; Owner: k3l_user
--

CREATE TABLE public.k3l_channel_fids (
    channel_id text NOT NULL,
    fid bigint NOT NULL,
    score real NOT NULL,
    rank bigint NOT NULL,
    compute_ts timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    strategy_name text NOT NULL
);


ALTER TABLE public.k3l_channel_fids OWNER TO k3l_user;

--
-- Name: k3l_channel_rank; Type: MATERIALIZED VIEW; Schema: public; Owner: k3l_user
--

CREATE MATERIALIZED VIEW public.k3l_channel_rank AS
 WITH latest_compute AS (
         SELECT max(k3l_channel_fids.compute_ts) AS max_ts,
            k3l_channel_fids.channel_id
           FROM public.k3l_channel_fids
          GROUP BY k3l_channel_fids.channel_id
        )
 SELECT row_number() OVER () AS pseudo_id,
    cfids.channel_id,
    cfids.fid,
    cfids.score,
    cfids.rank,
    cfids.compute_ts,
    cfids.strategy_name
   FROM (public.k3l_channel_fids cfids
     JOIN latest_compute ON (((cfids.compute_ts = latest_compute.max_ts) AND (cfids.channel_id = latest_compute.channel_id))))
  WITH NO DATA;


ALTER MATERIALIZED VIEW public.k3l_channel_rank OWNER TO k3l_user;

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

--
-- Name: k3l_frame_interaction; Type: MATERIALIZED VIEW; Schema: public; Owner: k3l_user
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
   FROM public.casts
  WHERE ((parent_hash IS NULL) AND (deleted_at IS NULL) AND (("timestamp" >= (now() - '5 days'::interval)) AND ("timestamp" <= now())))
  WITH NO DATA;


ALTER MATERIALIZED VIEW public.k3l_recent_parent_casts OWNER TO k3l_user;

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
-- Name: localtrust; Type: TABLE; Schema: public; Owner: k3l_user
--

CREATE UNLOGGED TABLE public.localtrust (
    strategy_id integer,
    i character varying(255),
    j character varying(255),
    v double precision,
    date date
);


ALTER TABLE public.localtrust OWNER TO k3l_user;

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
    signer bytea NOT NULL,
    raw bytea NOT NULL
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
-- Name: k3l_cast_action_y2024m04; Type: TABLE ATTACH; Schema: public; Owner: k3l_user
--

ALTER TABLE ONLY public.k3l_cast_action ATTACH PARTITION public.k3l_cast_action_y2024m04 FOR VALUES FROM ('2024-04-01 00:00:00') TO ('2024-05-01 00:00:00');


--
-- Name: k3l_cast_action_y2024m05; Type: TABLE ATTACH; Schema: public; Owner: k3l_user
--

ALTER TABLE ONLY public.k3l_cast_action ATTACH PARTITION public.k3l_cast_action_y2024m05 FOR VALUES FROM ('2024-05-01 00:00:00') TO ('2024-06-01 00:00:00');


--
-- Name: k3l_cast_action_y2024m06; Type: TABLE ATTACH; Schema: public; Owner: k3l_user
--

ALTER TABLE ONLY public.k3l_cast_action ATTACH PARTITION public.k3l_cast_action_y2024m06 FOR VALUES FROM ('2024-06-01 00:00:00') TO ('2024-07-01 00:00:00');


--
-- Name: k3l_cast_action_y2024m07; Type: TABLE ATTACH; Schema: public; Owner: k3l_user
--

ALTER TABLE ONLY public.k3l_cast_action ATTACH PARTITION public.k3l_cast_action_y2024m07 FOR VALUES FROM ('2024-07-01 00:00:00') TO ('2024-08-01 00:00:00');


--
-- Name: k3l_cast_action_y2024m08; Type: TABLE ATTACH; Schema: public; Owner: k3l_user
--

ALTER TABLE ONLY public.k3l_cast_action ATTACH PARTITION public.k3l_cast_action_y2024m08 FOR VALUES FROM ('2024-08-01 00:00:00') TO ('2024-09-01 00:00:00');


--
-- Name: k3l_cast_action_y2024m09; Type: TABLE ATTACH; Schema: public; Owner: k3l_user
--

ALTER TABLE ONLY public.k3l_cast_action ATTACH PARTITION public.k3l_cast_action_y2024m09 FOR VALUES FROM ('2024-09-01 00:00:00') TO ('2024-10-01 00:00:00');


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


--
-- Name: globaltrust globaltrust_strategy_name_date_i_unique; Type: CONSTRAINT; Schema: public; Owner: k3l_user
--

ALTER TABLE ONLY public.globaltrust
    ADD CONSTRAINT globaltrust_strategy_name_date_i_unique UNIQUE (strategy_id, date, i);


--
-- Name: hub_subscriptions hub_subscriptions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.hub_subscriptions
    ADD CONSTRAINT hub_subscriptions_pkey PRIMARY KEY (host);


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


--
-- Name: globaltrust_id_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX globaltrust_id_idx ON public.globaltrust USING btree (strategy_id);


--
-- Name: idx_links_fid; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_links_fid ON public.links USING btree (fid);


--
-- Name: idx_links_target_fid; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_links_target_fid ON public.links USING btree (target_fid);


--
-- Name: idx_parent_fid_timestamp; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_parent_fid_timestamp ON public.casts USING btree (parent_fid, "timestamp");


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
-- Name: idx_user_data_fid_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_data_fid_type ON public.user_data USING btree (fid, type) WITH (deduplicate_items='false');


--
-- Name: k3l_cast_action_cast_hash_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_cast_hash_idx ON ONLY public.k3l_cast_action USING btree (cast_hash);


--
-- Name: k3l_cast_action_fid_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_fid_idx ON ONLY public.k3l_cast_action USING btree (fid);


--
-- Name: k3l_cast_action_timestamp_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_timestamp_idx ON ONLY public.k3l_cast_action USING btree (action_ts);


--
-- Name: k3l_cast_action_unique_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE UNIQUE INDEX k3l_cast_action_unique_idx ON ONLY public.k3l_cast_action USING btree (cast_hash, fid, action_ts);


--
-- Name: k3l_cast_action_y2024m04_action_ts_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_y2024m04_action_ts_idx ON public.k3l_cast_action_y2024m04 USING btree (action_ts);


--
-- Name: k3l_cast_action_y2024m04_cast_hash_fid_action_ts_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE UNIQUE INDEX k3l_cast_action_y2024m04_cast_hash_fid_action_ts_idx ON public.k3l_cast_action_y2024m04 USING btree (cast_hash, fid, action_ts);


--
-- Name: k3l_cast_action_y2024m04_cast_hash_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_y2024m04_cast_hash_idx ON public.k3l_cast_action_y2024m04 USING btree (cast_hash);


--
-- Name: k3l_cast_action_y2024m04_fid_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_y2024m04_fid_idx ON public.k3l_cast_action_y2024m04 USING btree (fid);


--
-- Name: k3l_cast_action_y2024m05_action_ts_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_y2024m05_action_ts_idx ON public.k3l_cast_action_y2024m05 USING btree (action_ts);


--
-- Name: k3l_cast_action_y2024m05_cast_hash_fid_action_ts_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE UNIQUE INDEX k3l_cast_action_y2024m05_cast_hash_fid_action_ts_idx ON public.k3l_cast_action_y2024m05 USING btree (cast_hash, fid, action_ts);


--
-- Name: k3l_cast_action_y2024m05_cast_hash_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_y2024m05_cast_hash_idx ON public.k3l_cast_action_y2024m05 USING btree (cast_hash);


--
-- Name: k3l_cast_action_y2024m05_fid_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_y2024m05_fid_idx ON public.k3l_cast_action_y2024m05 USING btree (fid);


--
-- Name: k3l_cast_action_y2024m06_action_ts_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_y2024m06_action_ts_idx ON public.k3l_cast_action_y2024m06 USING btree (action_ts);


--
-- Name: k3l_cast_action_y2024m06_cast_hash_fid_action_ts_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE UNIQUE INDEX k3l_cast_action_y2024m06_cast_hash_fid_action_ts_idx ON public.k3l_cast_action_y2024m06 USING btree (cast_hash, fid, action_ts);


--
-- Name: k3l_cast_action_y2024m06_cast_hash_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_y2024m06_cast_hash_idx ON public.k3l_cast_action_y2024m06 USING btree (cast_hash);


--
-- Name: k3l_cast_action_y2024m06_fid_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_y2024m06_fid_idx ON public.k3l_cast_action_y2024m06 USING btree (fid);


--
-- Name: k3l_cast_action_y2024m07_action_ts_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_y2024m07_action_ts_idx ON public.k3l_cast_action_y2024m07 USING btree (action_ts);


--
-- Name: k3l_cast_action_y2024m07_cast_hash_fid_action_ts_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE UNIQUE INDEX k3l_cast_action_y2024m07_cast_hash_fid_action_ts_idx ON public.k3l_cast_action_y2024m07 USING btree (cast_hash, fid, action_ts);


--
-- Name: k3l_cast_action_y2024m07_cast_hash_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_y2024m07_cast_hash_idx ON public.k3l_cast_action_y2024m07 USING btree (cast_hash);


--
-- Name: k3l_cast_action_y2024m07_fid_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_y2024m07_fid_idx ON public.k3l_cast_action_y2024m07 USING btree (fid);


--
-- Name: k3l_cast_action_y2024m08_action_ts_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_y2024m08_action_ts_idx ON public.k3l_cast_action_y2024m08 USING btree (action_ts);


--
-- Name: k3l_cast_action_y2024m08_cast_hash_fid_action_ts_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE UNIQUE INDEX k3l_cast_action_y2024m08_cast_hash_fid_action_ts_idx ON public.k3l_cast_action_y2024m08 USING btree (cast_hash, fid, action_ts);


--
-- Name: k3l_cast_action_y2024m08_cast_hash_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_y2024m08_cast_hash_idx ON public.k3l_cast_action_y2024m08 USING btree (cast_hash);


--
-- Name: k3l_cast_action_y2024m08_fid_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_y2024m08_fid_idx ON public.k3l_cast_action_y2024m08 USING btree (fid);


--
-- Name: k3l_cast_action_y2024m09_action_ts_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_y2024m09_action_ts_idx ON public.k3l_cast_action_y2024m09 USING btree (action_ts);


--
-- Name: k3l_cast_action_y2024m09_cast_hash_fid_action_ts_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE UNIQUE INDEX k3l_cast_action_y2024m09_cast_hash_fid_action_ts_idx ON public.k3l_cast_action_y2024m09 USING btree (cast_hash, fid, action_ts);


--
-- Name: k3l_cast_action_y2024m09_cast_hash_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_y2024m09_cast_hash_idx ON public.k3l_cast_action_y2024m09 USING btree (cast_hash);


--
-- Name: k3l_cast_action_y2024m09_fid_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_action_y2024m09_fid_idx ON public.k3l_cast_action_y2024m09 USING btree (fid);


--
-- Name: k3l_cast_embed_url_mapping_cast_id_index; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_embed_url_mapping_cast_id_index ON public.k3l_cast_embed_url_mapping USING btree (cast_id);


--
-- Name: k3l_cast_embed_url_mapping_url_id_index; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_cast_embed_url_mapping_url_id_index ON public.k3l_cast_embed_url_mapping USING btree (url_id);


--
-- Name: k3l_channel_fids_id_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_channel_fids_id_idx ON public.k3l_channel_fids USING btree (channel_id, compute_ts, fid);


--
-- Name: k3l_channel_fids_rank_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_channel_fids_rank_idx ON public.k3l_channel_fids USING btree (channel_id, rank);


--
-- Name: k3l_channel_fids_ts_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_channel_fids_ts_idx ON public.k3l_channel_fids USING btree (channel_id, compute_ts);


--
-- Name: k3l_channel_rank_ch_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_channel_rank_ch_idx ON public.k3l_channel_rank USING btree (channel_id);


--
-- Name: k3l_channel_rank_fid_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_channel_rank_fid_idx ON public.k3l_channel_rank USING btree (fid);


--
-- Name: k3l_channel_rank_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE UNIQUE INDEX k3l_channel_rank_idx ON public.k3l_channel_rank USING btree (pseudo_id);


--
-- Name: k3l_channel_rank_rank_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_channel_rank_rank_idx ON public.k3l_channel_rank USING btree (rank);


--
-- Name: k3l_frame_interaction_fid_action_type_url_idunique; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE UNIQUE INDEX k3l_frame_interaction_fid_action_type_url_idunique ON public.k3l_frame_interaction USING btree (fid, action_type, url_id) NULLS NOT DISTINCT;


--
-- Name: k3l_frame_interaction_fid_index; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_frame_interaction_fid_index ON public.k3l_frame_interaction USING btree (fid);


--
-- Name: k3l_frame_interaction_url_id_index; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_frame_interaction_url_id_index ON public.k3l_frame_interaction USING btree (url_id);


--
-- Name: k3l_frame_interaction_url_index; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_frame_interaction_url_index ON public.k3l_frame_interaction USING btree (url);


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
-- Name: k3l_recent_parent_casts_hash_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE INDEX k3l_recent_parent_casts_hash_idx ON public.k3l_recent_parent_casts USING btree (hash);


--
-- Name: k3l_recent_parent_casts_idx; Type: INDEX; Schema: public; Owner: k3l_user
--

CREATE UNIQUE INDEX k3l_recent_parent_casts_idx ON public.k3l_recent_parent_casts USING btree (id);


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
-- Name: k3l_cast_action_y2024m04_action_ts_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_timestamp_idx ATTACH PARTITION public.k3l_cast_action_y2024m04_action_ts_idx;


--
-- Name: k3l_cast_action_y2024m04_cast_hash_fid_action_ts_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_unique_idx ATTACH PARTITION public.k3l_cast_action_y2024m04_cast_hash_fid_action_ts_idx;


--
-- Name: k3l_cast_action_y2024m04_cast_hash_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_cast_hash_idx ATTACH PARTITION public.k3l_cast_action_y2024m04_cast_hash_idx;


--
-- Name: k3l_cast_action_y2024m04_fid_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_fid_idx ATTACH PARTITION public.k3l_cast_action_y2024m04_fid_idx;


--
-- Name: k3l_cast_action_y2024m05_action_ts_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_timestamp_idx ATTACH PARTITION public.k3l_cast_action_y2024m05_action_ts_idx;


--
-- Name: k3l_cast_action_y2024m05_cast_hash_fid_action_ts_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_unique_idx ATTACH PARTITION public.k3l_cast_action_y2024m05_cast_hash_fid_action_ts_idx;


--
-- Name: k3l_cast_action_y2024m05_cast_hash_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_cast_hash_idx ATTACH PARTITION public.k3l_cast_action_y2024m05_cast_hash_idx;


--
-- Name: k3l_cast_action_y2024m05_fid_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_fid_idx ATTACH PARTITION public.k3l_cast_action_y2024m05_fid_idx;


--
-- Name: k3l_cast_action_y2024m06_action_ts_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_timestamp_idx ATTACH PARTITION public.k3l_cast_action_y2024m06_action_ts_idx;


--
-- Name: k3l_cast_action_y2024m06_cast_hash_fid_action_ts_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_unique_idx ATTACH PARTITION public.k3l_cast_action_y2024m06_cast_hash_fid_action_ts_idx;


--
-- Name: k3l_cast_action_y2024m06_cast_hash_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_cast_hash_idx ATTACH PARTITION public.k3l_cast_action_y2024m06_cast_hash_idx;


--
-- Name: k3l_cast_action_y2024m06_fid_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_fid_idx ATTACH PARTITION public.k3l_cast_action_y2024m06_fid_idx;


--
-- Name: k3l_cast_action_y2024m07_action_ts_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_timestamp_idx ATTACH PARTITION public.k3l_cast_action_y2024m07_action_ts_idx;


--
-- Name: k3l_cast_action_y2024m07_cast_hash_fid_action_ts_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_unique_idx ATTACH PARTITION public.k3l_cast_action_y2024m07_cast_hash_fid_action_ts_idx;


--
-- Name: k3l_cast_action_y2024m07_cast_hash_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_cast_hash_idx ATTACH PARTITION public.k3l_cast_action_y2024m07_cast_hash_idx;


--
-- Name: k3l_cast_action_y2024m07_fid_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_fid_idx ATTACH PARTITION public.k3l_cast_action_y2024m07_fid_idx;


--
-- Name: k3l_cast_action_y2024m08_action_ts_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_timestamp_idx ATTACH PARTITION public.k3l_cast_action_y2024m08_action_ts_idx;


--
-- Name: k3l_cast_action_y2024m08_cast_hash_fid_action_ts_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_unique_idx ATTACH PARTITION public.k3l_cast_action_y2024m08_cast_hash_fid_action_ts_idx;


--
-- Name: k3l_cast_action_y2024m08_cast_hash_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_cast_hash_idx ATTACH PARTITION public.k3l_cast_action_y2024m08_cast_hash_idx;


--
-- Name: k3l_cast_action_y2024m08_fid_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_fid_idx ATTACH PARTITION public.k3l_cast_action_y2024m08_fid_idx;


--
-- Name: k3l_cast_action_y2024m09_action_ts_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_timestamp_idx ATTACH PARTITION public.k3l_cast_action_y2024m09_action_ts_idx;


--
-- Name: k3l_cast_action_y2024m09_cast_hash_fid_action_ts_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_unique_idx ATTACH PARTITION public.k3l_cast_action_y2024m09_cast_hash_fid_action_ts_idx;


--
-- Name: k3l_cast_action_y2024m09_cast_hash_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_cast_hash_idx ATTACH PARTITION public.k3l_cast_action_y2024m09_cast_hash_idx;


--
-- Name: k3l_cast_action_y2024m09_fid_idx; Type: INDEX ATTACH; Schema: public; Owner: k3l_user
--

ALTER INDEX public.k3l_cast_action_fid_idx ATTACH PARTITION public.k3l_cast_action_y2024m09_fid_idx;


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
    ADD CONSTRAINT k3l_cast_embed_url_mapping_cast_id_fkey FOREIGN KEY (cast_id) REFERENCES public.casts(id);


--
-- Name: k3l_cast_embed_url_mapping k3l_cast_embed_url_mapping_url_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: k3l_user
--

ALTER TABLE ONLY public.k3l_cast_embed_url_mapping
    ADD CONSTRAINT k3l_cast_embed_url_mapping_url_id_fkey FOREIGN KEY (url_id) REFERENCES public.k3l_url_labels(url_id);


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


--
-- Name: TABLE casts; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,REFERENCES ON TABLE public.casts TO k3l_user;


--
-- Name: TABLE fids; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,REFERENCES ON TABLE public.fids TO k3l_user;


--
-- Name: TABLE fnames; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,REFERENCES ON TABLE public.fnames TO k3l_user;


--
-- Name: TABLE hub_subscriptions; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,REFERENCES ON TABLE public.hub_subscriptions TO k3l_user;


--
-- Name: TABLE reactions; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,REFERENCES ON TABLE public.reactions TO k3l_user;


--
-- Name: TABLE kysely_migration; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,REFERENCES ON TABLE public.kysely_migration TO k3l_user;


--
-- Name: TABLE kysely_migration_lock; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,REFERENCES ON TABLE public.kysely_migration_lock TO k3l_user;


--
-- Name: TABLE links; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,REFERENCES ON TABLE public.links TO k3l_user;


--
-- Name: TABLE messages; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,REFERENCES ON TABLE public.messages TO k3l_user;


--
-- Name: TABLE user_data; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,REFERENCES ON TABLE public.user_data TO k3l_user;


--
-- Name: TABLE verifications; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,REFERENCES ON TABLE public.verifications TO k3l_user;


--
-- Name: TABLE profile_with_addresses; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,REFERENCES ON TABLE public.profile_with_addresses TO k3l_user;


--
-- Name: TABLE signers; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,REFERENCES ON TABLE public.signers TO k3l_user;


--
-- Name: TABLE storage; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,REFERENCES ON TABLE public.storage TO k3l_user;


--
-- PostgreSQL database dump complete
--

