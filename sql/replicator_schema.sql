--
-- PostgreSQL database dump
--

-- Dumped from database version 16.2
-- Dumped by pg_dump version 16.0

-- Started on 2024-03-20 22:35:05 PDT

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

ALTER TABLE IF EXISTS ONLY public.verifications DROP CONSTRAINT IF EXISTS verifications_hash_foreign;
ALTER TABLE IF EXISTS ONLY public.verifications DROP CONSTRAINT IF EXISTS verifications_fid_foreign;
ALTER TABLE IF EXISTS ONLY public.username_proofs DROP CONSTRAINT IF EXISTS username_proofs_fid_foreign;
ALTER TABLE IF EXISTS ONLY public.user_data DROP CONSTRAINT IF EXISTS user_data_hash_foreign;
ALTER TABLE IF EXISTS ONLY public.user_data DROP CONSTRAINT IF EXISTS user_data_fid_foreign;
ALTER TABLE IF EXISTS ONLY public.signers DROP CONSTRAINT IF EXISTS signers_requester_fid_foreign;
ALTER TABLE IF EXISTS ONLY public.signers DROP CONSTRAINT IF EXISTS signers_remove_chain_event_id_foreign;
ALTER TABLE IF EXISTS ONLY public.signers DROP CONSTRAINT IF EXISTS signers_fid_foreign;
ALTER TABLE IF EXISTS ONLY public.signers DROP CONSTRAINT IF EXISTS signers_add_chain_event_id_foreign;
ALTER TABLE IF EXISTS ONLY public.reactions DROP CONSTRAINT IF EXISTS reactions_target_hash_foreign;
ALTER TABLE IF EXISTS ONLY public.reactions DROP CONSTRAINT IF EXISTS reactions_hash_foreign;
ALTER TABLE IF EXISTS ONLY public.reactions DROP CONSTRAINT IF EXISTS reactions_fid_foreign;
ALTER TABLE IF EXISTS ONLY public.messages DROP CONSTRAINT IF EXISTS messages_signer_fid_foreign;
ALTER TABLE IF EXISTS ONLY public.messages DROP CONSTRAINT IF EXISTS messages_fid_foreign;
ALTER TABLE IF EXISTS ONLY public.links DROP CONSTRAINT IF EXISTS links_target_fid_foreign;
ALTER TABLE IF EXISTS ONLY public.links DROP CONSTRAINT IF EXISTS links_fid_foreign;
ALTER TABLE IF EXISTS ONLY public.fnames DROP CONSTRAINT IF EXISTS fnames_fid_foreign;
ALTER TABLE IF EXISTS ONLY public.storage_allocations DROP CONSTRAINT IF EXISTS fids_chain_event_id_foreign;
ALTER TABLE IF EXISTS ONLY public.fids DROP CONSTRAINT IF EXISTS fids_chain_event_id_foreign;
ALTER TABLE IF EXISTS ONLY public.casts DROP CONSTRAINT IF EXISTS casts_hash_foreign;
ALTER TABLE IF EXISTS ONLY public.casts DROP CONSTRAINT IF EXISTS casts_fid_foreign;
DROP INDEX IF EXISTS public.verifications_fid_timestamp_index;
DROP INDEX IF EXISTS public.storage_allocations_fid_expires_at_index;
DROP INDEX IF EXISTS public.signers_requester_fid_index;
DROP INDEX IF EXISTS public.signers_fid_index;
DROP INDEX IF EXISTS public.reactions_target_url_index;
DROP INDEX IF EXISTS public.reactions_target_cast_hash_index;
DROP INDEX IF EXISTS public.reactions_active_fid_timestamp_index;
DROP INDEX IF EXISTS public.messages_timestamp_index;
DROP INDEX IF EXISTS public.messages_signer_index;
DROP INDEX IF EXISTS public.messages_fid_index;
DROP INDEX IF EXISTS public.links_fid_target_fid_type_unique;
DROP INDEX IF EXISTS public.chain_events_transaction_hash_index;
DROP INDEX IF EXISTS public.chain_events_fid_index;
DROP INDEX IF EXISTS public.chain_events_block_timestamp_index;
DROP INDEX IF EXISTS public.chain_events_block_hash_index;
DROP INDEX IF EXISTS public.casts_timestamp_index;
DROP INDEX IF EXISTS public.casts_root_parent_url_index;
DROP INDEX IF EXISTS public.casts_root_parent_hash_index;
DROP INDEX IF EXISTS public.casts_parent_url_index;
DROP INDEX IF EXISTS public.casts_parent_hash_index;
DROP INDEX IF EXISTS public.casts_active_fid_timestamp_index;
ALTER TABLE IF EXISTS ONLY public.verifications DROP CONSTRAINT IF EXISTS verifications_signer_address_fid_unique;
ALTER TABLE IF EXISTS ONLY public.verifications DROP CONSTRAINT IF EXISTS verifications_pkey;
ALTER TABLE IF EXISTS ONLY public.username_proofs DROP CONSTRAINT IF EXISTS username_proofs_username_timestamp_unique;
ALTER TABLE IF EXISTS ONLY public.username_proofs DROP CONSTRAINT IF EXISTS username_proofs_pkey;
ALTER TABLE IF EXISTS ONLY public.user_data DROP CONSTRAINT IF EXISTS user_data_pkey;
ALTER TABLE IF EXISTS ONLY public.user_data DROP CONSTRAINT IF EXISTS user_data_hash_unique;
ALTER TABLE IF EXISTS ONLY public.user_data DROP CONSTRAINT IF EXISTS user_data_fid_type_unique;
ALTER TABLE IF EXISTS ONLY public.storage_allocations DROP CONSTRAINT IF EXISTS storage_chain_event_id_fid_unique;
ALTER TABLE IF EXISTS ONLY public.storage_allocations DROP CONSTRAINT IF EXISTS storage_allocations_pkey;
ALTER TABLE IF EXISTS ONLY public.signers DROP CONSTRAINT IF EXISTS signers_pkey;
ALTER TABLE IF EXISTS ONLY public.signers DROP CONSTRAINT IF EXISTS signers_fid_key_unique;
ALTER TABLE IF EXISTS ONLY public.reactions DROP CONSTRAINT IF EXISTS reactions_pkey;
ALTER TABLE IF EXISTS ONLY public.reactions DROP CONSTRAINT IF EXISTS reactions_hash_unique;
ALTER TABLE IF EXISTS ONLY public.reactions DROP CONSTRAINT IF EXISTS reactions_fid_type_target_cast_hash_target_url_unique;
ALTER TABLE IF EXISTS ONLY public.messages DROP CONSTRAINT IF EXISTS messages_pkey;
ALTER TABLE IF EXISTS ONLY public.messages DROP CONSTRAINT IF EXISTS messages_hash_unique;
ALTER TABLE IF EXISTS ONLY public.links DROP CONSTRAINT IF EXISTS links_pkey;
ALTER TABLE IF EXISTS ONLY public.links DROP CONSTRAINT IF EXISTS links_hash_unique;
ALTER TABLE IF EXISTS ONLY public.kysely_migration DROP CONSTRAINT IF EXISTS kysely_migration_pkey;
ALTER TABLE IF EXISTS ONLY public.kysely_migration_lock DROP CONSTRAINT IF EXISTS kysely_migration_lock_pkey;
ALTER TABLE IF EXISTS ONLY public.fnames DROP CONSTRAINT IF EXISTS fnames_username_unique;
ALTER TABLE IF EXISTS ONLY public.fnames DROP CONSTRAINT IF EXISTS fnames_pkey;
ALTER TABLE IF EXISTS ONLY public.fnames DROP CONSTRAINT IF EXISTS fnames_fid_unique;
ALTER TABLE IF EXISTS ONLY public.fids DROP CONSTRAINT IF EXISTS fids_pkey;
ALTER TABLE IF EXISTS ONLY public.chain_events DROP CONSTRAINT IF EXISTS chain_events_pkey;
ALTER TABLE IF EXISTS ONLY public.chain_events DROP CONSTRAINT IF EXISTS chain_events_block_number_log_index_unique;
ALTER TABLE IF EXISTS ONLY public.casts DROP CONSTRAINT IF EXISTS casts_pkey;
ALTER TABLE IF EXISTS ONLY public.casts DROP CONSTRAINT IF EXISTS casts_hash_unique;
DROP TABLE IF EXISTS public.verifications;
DROP TABLE IF EXISTS public.username_proofs;
DROP TABLE IF EXISTS public.user_data;
DROP TABLE IF EXISTS public.storage_allocations;
DROP TABLE IF EXISTS public.signers;
DROP TABLE IF EXISTS public.reactions;
DROP TABLE IF EXISTS public.messages;
DROP TABLE IF EXISTS public.links;
DROP TABLE IF EXISTS public.kysely_migration_lock;
DROP TABLE IF EXISTS public.kysely_migration;
DROP TABLE IF EXISTS public.fnames;
DROP TABLE IF EXISTS public.fids;
DROP TABLE IF EXISTS public.chain_events;
DROP TABLE IF EXISTS public.casts;
DROP FUNCTION IF EXISTS public.generate_ulid();
DROP SCHEMA IF EXISTS public;
--
-- TOC entry 5 (class 2615 OID 2200)
-- Name: public; Type: SCHEMA; Schema: -; Owner: pg_database_owner
--

CREATE SCHEMA public;


ALTER SCHEMA public OWNER TO pg_database_owner;

--
-- TOC entry 3619 (class 0 OID 0)
-- Dependencies: 5
-- Name: SCHEMA public; Type: COMMENT; Schema: -; Owner: pg_database_owner
--

COMMENT ON SCHEMA public IS 'standard public schema';


--
-- TOC entry 277 (class 1255 OID 16435)
-- Name: generate_ulid(); Type: FUNCTION; Schema: public; Owner: replicator
--

CREATE FUNCTION public.generate_ulid() RETURNS uuid
    LANGUAGE sql STRICT PARALLEL SAFE
    RETURN ((lpad(to_hex((floor((EXTRACT(epoch FROM clock_timestamp()) * (1000)::numeric)))::bigint), 12, '0'::text) || encode(public.gen_random_bytes(10), 'hex'::text)))::uuid;


ALTER FUNCTION public.generate_ulid() OWNER TO replicator;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- TOC entry 224 (class 1259 OID 16560)
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
-- TOC entry 218 (class 1259 OID 16436)
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
-- TOC entry 219 (class 1259 OID 16451)
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
-- TOC entry 222 (class 1259 OID 16516)
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
-- TOC entry 216 (class 1259 OID 16385)
-- Name: kysely_migration; Type: TABLE; Schema: public; Owner: replicator
--

CREATE TABLE public.kysely_migration (
    name character varying(255) NOT NULL,
    "timestamp" character varying(255) NOT NULL
);


ALTER TABLE public.kysely_migration OWNER TO replicator;

--
-- TOC entry 217 (class 1259 OID 16392)
-- Name: kysely_migration_lock; Type: TABLE; Schema: public; Owner: replicator
--

CREATE TABLE public.kysely_migration_lock (
    id character varying(255) NOT NULL,
    is_locked integer DEFAULT 0 NOT NULL
);


ALTER TABLE public.kysely_migration_lock OWNER TO replicator;

--
-- TOC entry 226 (class 1259 OID 16623)
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
-- TOC entry 223 (class 1259 OID 16535)
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
-- TOC entry 225 (class 1259 OID 16591)
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
-- TOC entry 220 (class 1259 OID 16465)
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
-- TOC entry 229 (class 1259 OID 16693)
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
-- TOC entry 228 (class 1259 OID 16669)
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
-- TOC entry 221 (class 1259 OID 16499)
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
-- TOC entry 227 (class 1259 OID 16646)
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
-- TOC entry 3412 (class 2606 OID 16574)
-- Name: casts casts_hash_unique; Type: CONSTRAINT; Schema: public; Owner: replicator
--

ALTER TABLE ONLY public.casts
    ADD CONSTRAINT casts_hash_unique UNIQUE (hash);


--
-- TOC entry 3416 (class 2606 OID 16572)
-- Name: casts casts_pkey; Type: CONSTRAINT; Schema: public; Owner: replicator
--

ALTER TABLE ONLY public.casts
    ADD CONSTRAINT casts_pkey PRIMARY KEY (id);


--
-- TOC entry 3379 (class 2606 OID 16446)
-- Name: chain_events chain_events_block_number_log_index_unique; Type: CONSTRAINT; Schema: public; Owner: replicator
--

ALTER TABLE ONLY public.chain_events
    ADD CONSTRAINT chain_events_block_number_log_index_unique UNIQUE (block_number, log_index);


--
-- TOC entry 3383 (class 2606 OID 16444)
-- Name: chain_events chain_events_pkey; Type: CONSTRAINT; Schema: public; Owner: replicator
--

ALTER TABLE ONLY public.chain_events
    ADD CONSTRAINT chain_events_pkey PRIMARY KEY (id);


--
-- TOC entry 3386 (class 2606 OID 16459)
-- Name: fids fids_pkey; Type: CONSTRAINT; Schema: public; Owner: replicator
--

ALTER TABLE ONLY public.fids
    ADD CONSTRAINT fids_pkey PRIMARY KEY (fid);


--
-- TOC entry 3398 (class 2606 OID 16527)
-- Name: fnames fnames_fid_unique; Type: CONSTRAINT; Schema: public; Owner: replicator
--

ALTER TABLE ONLY public.fnames
    ADD CONSTRAINT fnames_fid_unique UNIQUE (fid);


--
-- TOC entry 3400 (class 2606 OID 16525)
-- Name: fnames fnames_pkey; Type: CONSTRAINT; Schema: public; Owner: replicator
--

ALTER TABLE ONLY public.fnames
    ADD CONSTRAINT fnames_pkey PRIMARY KEY (id);


--
-- TOC entry 3402 (class 2606 OID 16529)
-- Name: fnames fnames_username_unique; Type: CONSTRAINT; Schema: public; Owner: replicator
--

ALTER TABLE ONLY public.fnames
    ADD CONSTRAINT fnames_username_unique UNIQUE (username);


--
-- TOC entry 3376 (class 2606 OID 16397)
-- Name: kysely_migration_lock kysely_migration_lock_pkey; Type: CONSTRAINT; Schema: public; Owner: replicator
--

ALTER TABLE ONLY public.kysely_migration_lock
    ADD CONSTRAINT kysely_migration_lock_pkey PRIMARY KEY (id);


--
-- TOC entry 3374 (class 2606 OID 16391)
-- Name: kysely_migration kysely_migration_pkey; Type: CONSTRAINT; Schema: public; Owner: replicator
--

ALTER TABLE ONLY public.kysely_migration
    ADD CONSTRAINT kysely_migration_pkey PRIMARY KEY (name);


--
-- TOC entry 3431 (class 2606 OID 16634)
-- Name: links links_hash_unique; Type: CONSTRAINT; Schema: public; Owner: replicator
--

ALTER TABLE ONLY public.links
    ADD CONSTRAINT links_hash_unique UNIQUE (hash);


--
-- TOC entry 3433 (class 2606 OID 16632)
-- Name: links links_pkey; Type: CONSTRAINT; Schema: public; Owner: replicator
--

ALTER TABLE ONLY public.links
    ADD CONSTRAINT links_pkey PRIMARY KEY (id);


--
-- TOC entry 3405 (class 2606 OID 16546)
-- Name: messages messages_hash_unique; Type: CONSTRAINT; Schema: public; Owner: replicator
--

ALTER TABLE ONLY public.messages
    ADD CONSTRAINT messages_hash_unique UNIQUE (hash);


--
-- TOC entry 3407 (class 2606 OID 16544)
-- Name: messages messages_pkey; Type: CONSTRAINT; Schema: public; Owner: replicator
--

ALTER TABLE ONLY public.messages
    ADD CONSTRAINT messages_pkey PRIMARY KEY (id);


--
-- TOC entry 3422 (class 2606 OID 16619)
-- Name: reactions reactions_fid_type_target_cast_hash_target_url_unique; Type: CONSTRAINT; Schema: public; Owner: replicator
--

ALTER TABLE ONLY public.reactions
    ADD CONSTRAINT reactions_fid_type_target_cast_hash_target_url_unique UNIQUE NULLS NOT DISTINCT (fid, type, target_cast_hash, target_url);


--
-- TOC entry 3424 (class 2606 OID 16602)
-- Name: reactions reactions_hash_unique; Type: CONSTRAINT; Schema: public; Owner: replicator
--

ALTER TABLE ONLY public.reactions
    ADD CONSTRAINT reactions_hash_unique UNIQUE (hash);


--
-- TOC entry 3426 (class 2606 OID 16600)
-- Name: reactions reactions_pkey; Type: CONSTRAINT; Schema: public; Owner: replicator
--

ALTER TABLE ONLY public.reactions
    ADD CONSTRAINT reactions_pkey PRIMARY KEY (id);


--
-- TOC entry 3389 (class 2606 OID 16476)
-- Name: signers signers_fid_key_unique; Type: CONSTRAINT; Schema: public; Owner: replicator
--

ALTER TABLE ONLY public.signers
    ADD CONSTRAINT signers_fid_key_unique UNIQUE (fid, key);


--
-- TOC entry 3391 (class 2606 OID 16474)
-- Name: signers signers_pkey; Type: CONSTRAINT; Schema: public; Owner: replicator
--

ALTER TABLE ONLY public.signers
    ADD CONSTRAINT signers_pkey PRIMARY KEY (id);


--
-- TOC entry 3447 (class 2606 OID 16702)
-- Name: storage_allocations storage_allocations_pkey; Type: CONSTRAINT; Schema: public; Owner: replicator
--

ALTER TABLE ONLY public.storage_allocations
    ADD CONSTRAINT storage_allocations_pkey PRIMARY KEY (id);


--
-- TOC entry 3449 (class 2606 OID 16704)
-- Name: storage_allocations storage_chain_event_id_fid_unique; Type: CONSTRAINT; Schema: public; Owner: replicator
--

ALTER TABLE ONLY public.storage_allocations
    ADD CONSTRAINT storage_chain_event_id_fid_unique UNIQUE (chain_event_id, fid);


--
-- TOC entry 3440 (class 2606 OID 16680)
-- Name: user_data user_data_fid_type_unique; Type: CONSTRAINT; Schema: public; Owner: replicator
--

ALTER TABLE ONLY public.user_data
    ADD CONSTRAINT user_data_fid_type_unique UNIQUE (fid, type);


--
-- TOC entry 3442 (class 2606 OID 16682)
-- Name: user_data user_data_hash_unique; Type: CONSTRAINT; Schema: public; Owner: replicator
--

ALTER TABLE ONLY public.user_data
    ADD CONSTRAINT user_data_hash_unique UNIQUE (hash);


--
-- TOC entry 3444 (class 2606 OID 16678)
-- Name: user_data user_data_pkey; Type: CONSTRAINT; Schema: public; Owner: replicator
--

ALTER TABLE ONLY public.user_data
    ADD CONSTRAINT user_data_pkey PRIMARY KEY (id);


--
-- TOC entry 3394 (class 2606 OID 16508)
-- Name: username_proofs username_proofs_pkey; Type: CONSTRAINT; Schema: public; Owner: replicator
--

ALTER TABLE ONLY public.username_proofs
    ADD CONSTRAINT username_proofs_pkey PRIMARY KEY (id);


--
-- TOC entry 3396 (class 2606 OID 16510)
-- Name: username_proofs username_proofs_username_timestamp_unique; Type: CONSTRAINT; Schema: public; Owner: replicator
--

ALTER TABLE ONLY public.username_proofs
    ADD CONSTRAINT username_proofs_username_timestamp_unique UNIQUE (username, "timestamp");


--
-- TOC entry 3436 (class 2606 OID 16655)
-- Name: verifications verifications_pkey; Type: CONSTRAINT; Schema: public; Owner: replicator
--

ALTER TABLE ONLY public.verifications
    ADD CONSTRAINT verifications_pkey PRIMARY KEY (id);


--
-- TOC entry 3438 (class 2606 OID 16657)
-- Name: verifications verifications_signer_address_fid_unique; Type: CONSTRAINT; Schema: public; Owner: replicator
--

ALTER TABLE ONLY public.verifications
    ADD CONSTRAINT verifications_signer_address_fid_unique UNIQUE (signer_address, fid);


--
-- TOC entry 3410 (class 1259 OID 16585)
-- Name: casts_active_fid_timestamp_index; Type: INDEX; Schema: public; Owner: replicator
--

CREATE INDEX casts_active_fid_timestamp_index ON public.casts USING btree (fid, "timestamp") WHERE (deleted_at IS NULL);


--
-- TOC entry 3413 (class 1259 OID 16587)
-- Name: casts_parent_hash_index; Type: INDEX; Schema: public; Owner: replicator
--

CREATE INDEX casts_parent_hash_index ON public.casts USING btree (parent_hash) WHERE (parent_hash IS NOT NULL);


--
-- TOC entry 3414 (class 1259 OID 16589)
-- Name: casts_parent_url_index; Type: INDEX; Schema: public; Owner: replicator
--

CREATE INDEX casts_parent_url_index ON public.casts USING btree (parent_url) WHERE (parent_url IS NOT NULL);


--
-- TOC entry 3417 (class 1259 OID 16588)
-- Name: casts_root_parent_hash_index; Type: INDEX; Schema: public; Owner: replicator
--

CREATE INDEX casts_root_parent_hash_index ON public.casts USING btree (root_parent_hash) WHERE (root_parent_hash IS NOT NULL);


--
-- TOC entry 3418 (class 1259 OID 16590)
-- Name: casts_root_parent_url_index; Type: INDEX; Schema: public; Owner: replicator
--

CREATE INDEX casts_root_parent_url_index ON public.casts USING btree (root_parent_url) WHERE (root_parent_url IS NOT NULL);


--
-- TOC entry 3419 (class 1259 OID 16586)
-- Name: casts_timestamp_index; Type: INDEX; Schema: public; Owner: replicator
--

CREATE INDEX casts_timestamp_index ON public.casts USING btree ("timestamp");


--
-- TOC entry 3377 (class 1259 OID 16448)
-- Name: chain_events_block_hash_index; Type: INDEX; Schema: public; Owner: replicator
--

CREATE INDEX chain_events_block_hash_index ON public.chain_events USING hash (block_hash);


--
-- TOC entry 3380 (class 1259 OID 16449)
-- Name: chain_events_block_timestamp_index; Type: INDEX; Schema: public; Owner: replicator
--

CREATE INDEX chain_events_block_timestamp_index ON public.chain_events USING btree (block_timestamp);


--
-- TOC entry 3381 (class 1259 OID 16447)
-- Name: chain_events_fid_index; Type: INDEX; Schema: public; Owner: replicator
--

CREATE INDEX chain_events_fid_index ON public.chain_events USING btree (fid);


--
-- TOC entry 3384 (class 1259 OID 16450)
-- Name: chain_events_transaction_hash_index; Type: INDEX; Schema: public; Owner: replicator
--

CREATE INDEX chain_events_transaction_hash_index ON public.chain_events USING hash (transaction_hash);


--
-- TOC entry 3429 (class 1259 OID 16645)
-- Name: links_fid_target_fid_type_unique; Type: INDEX; Schema: public; Owner: replicator
--

CREATE UNIQUE INDEX links_fid_target_fid_type_unique ON public.links USING btree (fid, target_fid, type) NULLS NOT DISTINCT;


--
-- TOC entry 3403 (class 1259 OID 16558)
-- Name: messages_fid_index; Type: INDEX; Schema: public; Owner: replicator
--

CREATE INDEX messages_fid_index ON public.messages USING btree (fid);


--
-- TOC entry 3408 (class 1259 OID 16559)
-- Name: messages_signer_index; Type: INDEX; Schema: public; Owner: replicator
--

CREATE INDEX messages_signer_index ON public.messages USING btree (signer);


--
-- TOC entry 3409 (class 1259 OID 16557)
-- Name: messages_timestamp_index; Type: INDEX; Schema: public; Owner: replicator
--

CREATE INDEX messages_timestamp_index ON public.messages USING btree ("timestamp");


--
-- TOC entry 3420 (class 1259 OID 16620)
-- Name: reactions_active_fid_timestamp_index; Type: INDEX; Schema: public; Owner: replicator
--

CREATE INDEX reactions_active_fid_timestamp_index ON public.reactions USING btree (fid, "timestamp") WHERE (deleted_at IS NULL);


--
-- TOC entry 3427 (class 1259 OID 16621)
-- Name: reactions_target_cast_hash_index; Type: INDEX; Schema: public; Owner: replicator
--

CREATE INDEX reactions_target_cast_hash_index ON public.reactions USING btree (target_cast_hash) WHERE (target_cast_hash IS NOT NULL);


--
-- TOC entry 3428 (class 1259 OID 16622)
-- Name: reactions_target_url_index; Type: INDEX; Schema: public; Owner: replicator
--

CREATE INDEX reactions_target_url_index ON public.reactions USING btree (target_url) WHERE (target_url IS NOT NULL);


--
-- TOC entry 3387 (class 1259 OID 16497)
-- Name: signers_fid_index; Type: INDEX; Schema: public; Owner: replicator
--

CREATE INDEX signers_fid_index ON public.signers USING btree (fid);


--
-- TOC entry 3392 (class 1259 OID 16498)
-- Name: signers_requester_fid_index; Type: INDEX; Schema: public; Owner: replicator
--

CREATE INDEX signers_requester_fid_index ON public.signers USING btree (requester_fid);


--
-- TOC entry 3445 (class 1259 OID 16710)
-- Name: storage_allocations_fid_expires_at_index; Type: INDEX; Schema: public; Owner: replicator
--

CREATE INDEX storage_allocations_fid_expires_at_index ON public.storage_allocations USING btree (fid, expires_at);


--
-- TOC entry 3434 (class 1259 OID 16668)
-- Name: verifications_fid_timestamp_index; Type: INDEX; Schema: public; Owner: replicator
--

CREATE INDEX verifications_fid_timestamp_index ON public.verifications USING btree (fid, "timestamp");


--
-- TOC entry 3459 (class 2606 OID 16575)
-- Name: casts casts_fid_foreign; Type: FK CONSTRAINT; Schema: public; Owner: replicator
--

ALTER TABLE ONLY public.casts
    ADD CONSTRAINT casts_fid_foreign FOREIGN KEY (fid) REFERENCES public.fids(fid) ON DELETE CASCADE;


--
-- TOC entry 3460 (class 2606 OID 16580)
-- Name: casts casts_hash_foreign; Type: FK CONSTRAINT; Schema: public; Owner: replicator
--

ALTER TABLE ONLY public.casts
    ADD CONSTRAINT casts_hash_foreign FOREIGN KEY (hash) REFERENCES public.messages(hash) ON DELETE CASCADE;


--
-- TOC entry 3450 (class 2606 OID 16460)
-- Name: fids fids_chain_event_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: replicator
--

ALTER TABLE ONLY public.fids
    ADD CONSTRAINT fids_chain_event_id_foreign FOREIGN KEY (chain_event_id) REFERENCES public.chain_events(id) ON DELETE CASCADE;


--
-- TOC entry 3470 (class 2606 OID 16705)
-- Name: storage_allocations fids_chain_event_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: replicator
--

ALTER TABLE ONLY public.storage_allocations
    ADD CONSTRAINT fids_chain_event_id_foreign FOREIGN KEY (chain_event_id) REFERENCES public.chain_events(id) ON DELETE CASCADE;


--
-- TOC entry 3456 (class 2606 OID 16530)
-- Name: fnames fnames_fid_foreign; Type: FK CONSTRAINT; Schema: public; Owner: replicator
--

ALTER TABLE ONLY public.fnames
    ADD CONSTRAINT fnames_fid_foreign FOREIGN KEY (fid) REFERENCES public.fids(fid) ON DELETE CASCADE;


--
-- TOC entry 3464 (class 2606 OID 16635)
-- Name: links links_fid_foreign; Type: FK CONSTRAINT; Schema: public; Owner: replicator
--

ALTER TABLE ONLY public.links
    ADD CONSTRAINT links_fid_foreign FOREIGN KEY (fid) REFERENCES public.fids(fid) ON DELETE CASCADE;


--
-- TOC entry 3465 (class 2606 OID 16640)
-- Name: links links_target_fid_foreign; Type: FK CONSTRAINT; Schema: public; Owner: replicator
--

ALTER TABLE ONLY public.links
    ADD CONSTRAINT links_target_fid_foreign FOREIGN KEY (target_fid) REFERENCES public.fids(fid) ON DELETE CASCADE;


--
-- TOC entry 3457 (class 2606 OID 16547)
-- Name: messages messages_fid_foreign; Type: FK CONSTRAINT; Schema: public; Owner: replicator
--

ALTER TABLE ONLY public.messages
    ADD CONSTRAINT messages_fid_foreign FOREIGN KEY (fid) REFERENCES public.fids(fid) ON DELETE CASCADE;


--
-- TOC entry 3458 (class 2606 OID 16552)
-- Name: messages messages_signer_fid_foreign; Type: FK CONSTRAINT; Schema: public; Owner: replicator
--

ALTER TABLE ONLY public.messages
    ADD CONSTRAINT messages_signer_fid_foreign FOREIGN KEY (fid, signer) REFERENCES public.signers(fid, key) ON DELETE CASCADE;


--
-- TOC entry 3461 (class 2606 OID 16603)
-- Name: reactions reactions_fid_foreign; Type: FK CONSTRAINT; Schema: public; Owner: replicator
--

ALTER TABLE ONLY public.reactions
    ADD CONSTRAINT reactions_fid_foreign FOREIGN KEY (fid) REFERENCES public.fids(fid) ON DELETE CASCADE;


--
-- TOC entry 3462 (class 2606 OID 16608)
-- Name: reactions reactions_hash_foreign; Type: FK CONSTRAINT; Schema: public; Owner: replicator
--

ALTER TABLE ONLY public.reactions
    ADD CONSTRAINT reactions_hash_foreign FOREIGN KEY (hash) REFERENCES public.messages(hash) ON DELETE CASCADE;


--
-- TOC entry 3463 (class 2606 OID 16613)
-- Name: reactions reactions_target_hash_foreign; Type: FK CONSTRAINT; Schema: public; Owner: replicator
--

ALTER TABLE ONLY public.reactions
    ADD CONSTRAINT reactions_target_hash_foreign FOREIGN KEY (target_cast_hash) REFERENCES public.casts(hash) ON DELETE CASCADE;


--
-- TOC entry 3451 (class 2606 OID 16487)
-- Name: signers signers_add_chain_event_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: replicator
--

ALTER TABLE ONLY public.signers
    ADD CONSTRAINT signers_add_chain_event_id_foreign FOREIGN KEY (add_chain_event_id) REFERENCES public.chain_events(id) ON DELETE CASCADE;


--
-- TOC entry 3452 (class 2606 OID 16477)
-- Name: signers signers_fid_foreign; Type: FK CONSTRAINT; Schema: public; Owner: replicator
--

ALTER TABLE ONLY public.signers
    ADD CONSTRAINT signers_fid_foreign FOREIGN KEY (fid) REFERENCES public.fids(fid) ON DELETE CASCADE;


--
-- TOC entry 3453 (class 2606 OID 16492)
-- Name: signers signers_remove_chain_event_id_foreign; Type: FK CONSTRAINT; Schema: public; Owner: replicator
--

ALTER TABLE ONLY public.signers
    ADD CONSTRAINT signers_remove_chain_event_id_foreign FOREIGN KEY (remove_chain_event_id) REFERENCES public.chain_events(id) ON DELETE CASCADE;


--
-- TOC entry 3454 (class 2606 OID 16482)
-- Name: signers signers_requester_fid_foreign; Type: FK CONSTRAINT; Schema: public; Owner: replicator
--

ALTER TABLE ONLY public.signers
    ADD CONSTRAINT signers_requester_fid_foreign FOREIGN KEY (requester_fid) REFERENCES public.fids(fid) ON DELETE CASCADE;


--
-- TOC entry 3468 (class 2606 OID 16683)
-- Name: user_data user_data_fid_foreign; Type: FK CONSTRAINT; Schema: public; Owner: replicator
--

ALTER TABLE ONLY public.user_data
    ADD CONSTRAINT user_data_fid_foreign FOREIGN KEY (fid) REFERENCES public.fids(fid) ON DELETE CASCADE;


--
-- TOC entry 3469 (class 2606 OID 16688)
-- Name: user_data user_data_hash_foreign; Type: FK CONSTRAINT; Schema: public; Owner: replicator
--

ALTER TABLE ONLY public.user_data
    ADD CONSTRAINT user_data_hash_foreign FOREIGN KEY (hash) REFERENCES public.messages(hash) ON DELETE CASCADE;


--
-- TOC entry 3455 (class 2606 OID 16511)
-- Name: username_proofs username_proofs_fid_foreign; Type: FK CONSTRAINT; Schema: public; Owner: replicator
--

ALTER TABLE ONLY public.username_proofs
    ADD CONSTRAINT username_proofs_fid_foreign FOREIGN KEY (fid) REFERENCES public.fids(fid) ON DELETE CASCADE;


--
-- TOC entry 3466 (class 2606 OID 16658)
-- Name: verifications verifications_fid_foreign; Type: FK CONSTRAINT; Schema: public; Owner: replicator
--

ALTER TABLE ONLY public.verifications
    ADD CONSTRAINT verifications_fid_foreign FOREIGN KEY (fid) REFERENCES public.fids(fid) ON DELETE CASCADE;


--
-- TOC entry 3467 (class 2606 OID 16663)
-- Name: verifications verifications_hash_foreign; Type: FK CONSTRAINT; Schema: public; Owner: replicator
--

ALTER TABLE ONLY public.verifications
    ADD CONSTRAINT verifications_hash_foreign FOREIGN KEY (hash) REFERENCES public.messages(hash) ON DELETE CASCADE;


-- Completed on 2024-03-20 22:35:20 PDT

--
-- PostgreSQL database dump complete
--

