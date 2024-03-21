--
-- PostgreSQL database dump
--

-- Dumped from database version 16.0
-- Dumped by pg_dump version 16.0

-- Started on 2024-03-20 20:31:20 PDT

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
-- TOC entry 286 (class 1259 OID 33486)
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
-- TOC entry 288 (class 1259 OID 33519)
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
-- TOC entry 293 (class 1259 OID 51553)
-- Name: k3l_cast_embed_url_mapping; Type: TABLE; Schema: public; Owner: replicator
--

CREATE TABLE public.k3l_cast_embed_url_mapping (
    url_id integer,
    cast_id uuid
);


ALTER TABLE public.k3l_cast_embed_url_mapping OWNER TO replicator;

--
-- TOC entry 292 (class 1259 OID 51543)
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
-- TOC entry 295 (class 1259 OID 52653)
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
-- TOC entry 294 (class 1259 OID 51932)
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
-- TOC entry 291 (class 1259 OID 51542)
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
-- TOC entry 296 (class 1259 OID 54063)
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
-- TOC entry 287 (class 1259 OID 33515)
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
-- TOC entry 3369 (class 2606 OID 33526)
-- Name: globaltrust_config globaltrust_config_pkey; Type: CONSTRAINT; Schema: public; Owner: replicator
--

ALTER TABLE ONLY public.globaltrust_config
    ADD CONSTRAINT globaltrust_config_pkey PRIMARY KEY (strategy_id, date);


--
-- TOC entry 3367 (class 2606 OID 33621)
-- Name: globaltrust globaltrust_strategy_name_date_i_unique; Type: CONSTRAINT; Schema: public; Owner: replicator
--

ALTER TABLE ONLY public.globaltrust
    ADD CONSTRAINT globaltrust_strategy_name_date_i_unique UNIQUE (strategy_id, date, i);


--
-- TOC entry 3371 (class 2606 OID 51550)
-- Name: k3l_url_labels k3l_url_labels_pkey; Type: CONSTRAINT; Schema: public; Owner: replicator
--

ALTER TABLE ONLY public.k3l_url_labels
    ADD CONSTRAINT k3l_url_labels_pkey PRIMARY KEY (url_id);


--
-- TOC entry 3373 (class 2606 OID 51552)
-- Name: k3l_url_labels k3l_url_labels_url_unique; Type: CONSTRAINT; Schema: public; Owner: replicator
--

ALTER TABLE ONLY public.k3l_url_labels
    ADD CONSTRAINT k3l_url_labels_url_unique UNIQUE (url);


--
-- TOC entry 3365 (class 1259 OID 33491)
-- Name: globaltrust_id_idx; Type: INDEX; Schema: public; Owner: replicator
--

CREATE INDEX globaltrust_id_idx ON public.globaltrust USING btree (strategy_id);


--
-- TOC entry 3375 (class 1259 OID 52660)
-- Name: k3l_frame_interaction_fid_action_type_url_idunique; Type: INDEX; Schema: public; Owner: replicator
--

CREATE UNIQUE INDEX k3l_frame_interaction_fid_action_type_url_idunique ON public.k3l_frame_interaction USING btree (fid, action_type, url_id) NULLS NOT DISTINCT;


--
-- TOC entry 3374 (class 1259 OID 51937)
-- Name: k3l_rank_idx; Type: INDEX; Schema: public; Owner: replicator
--

CREATE UNIQUE INDEX k3l_rank_idx ON public.k3l_rank USING btree (pseudo_id);


--
-- TOC entry 3376 (class 2606 OID 51561)
-- Name: k3l_cast_embed_url_mapping k3l_cast_embed_url_mapping_cast_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: replicator
--

ALTER TABLE ONLY public.k3l_cast_embed_url_mapping
    ADD CONSTRAINT k3l_cast_embed_url_mapping_cast_id_fkey FOREIGN KEY (cast_id) REFERENCES public.casts(id);


--
-- TOC entry 3377 (class 2606 OID 51556)
-- Name: k3l_cast_embed_url_mapping k3l_cast_embed_url_mapping_url_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: replicator
--

ALTER TABLE ONLY public.k3l_cast_embed_url_mapping
    ADD CONSTRAINT k3l_cast_embed_url_mapping_url_id_fkey FOREIGN KEY (url_id) REFERENCES public.k3l_url_labels(url_id);


-- Completed on 2024-03-20 20:31:40 PDT

--
-- PostgreSQL database dump complete
--

