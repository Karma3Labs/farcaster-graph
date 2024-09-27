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

SET default_tablespace = '';

SET default_table_access_method = heap;

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
-- Data for Name: globaltrust_config; Type: TABLE DATA; Schema: public; Owner: k3l_user
--

COPY public.globaltrust_config (strategy_id, strategy_name, pretrust, localtrust, alpha, date) FROM stdin;
1	follows	pretrustAllEqually	existingConnections	0.5	2023-12-07
3	engagement	pretrustAllEqually	l1rep6rec3m12enhancedConnections	0.5	2023-12-07
5	activity	pretrustAllEqually	l1rep1rec1m1enhancedConnections	0.5	2023-12-07
7	OG circles	pretrustSpecificUsernames	existingConnections	0.5	2023-12-07
9	OG engagement	pretrustSpecificUsernames	l1rep6rec3m12enhancedConnections	0.5	2023-12-07
11	OG activity	pretrustSpecificUsernames	l1rep1rec1m1enhancedConnections	0.5	2023-12-07
1	follows	pretrustTopTier	existingConnections	0.5	2024-03-14
3	engagement	pretrustTopTier	l1rep6rec3m12enhancedConnections	0.5	2024-03-14
1	follows	pretrustTopTier	existingConnections	0.5	2024-09-27
3	engagement	pretrustTopTier	l1rep6rec3m12enhancedConnections	0.5	2024-09-27
9	v3engagement	v2pretrustTopTier	followsboostedl1rep3rec6m12	0.5	2024-09-27
\.


--
-- Name: globaltrust_config globaltrust_config_pkey; Type: CONSTRAINT; Schema: public; Owner: k3l_user
--

ALTER TABLE ONLY public.globaltrust_config
    ADD CONSTRAINT globaltrust_config_pkey PRIMARY KEY (strategy_id, date);


--
-- Name: TABLE globaltrust_config; Type: ACL; Schema: public; Owner: k3l_user
--

GRANT SELECT,REFERENCES ON TABLE public.globaltrust_config TO k3l_readonly;


--
-- PostgreSQL database dump complete
--

