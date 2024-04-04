--
-- Name: k3l_channels; Type: TABLE; Schema: public; Owner: replicator
--

CREATE TABLE public.k3l_channels (
    id text not null,
    project_url text NOT NULL,
    name text,
    description text,
    image_url text,
    lead_fid bigint,
    host_fids bigint[],
    created_at_ts timestamp without t time zone,
    follower_count bigintime zone NOT NULL,
    processed_ts timestamp without
);


ALTER TABLE public.k3l_channels OWNER TO replicator;

CREATE INDEX channel_id_idx ON public.k3l_channels USING btree (id);


ALTER TABLE ONLY public.k3l_channels
    ADD CONSTRAINT k3l_channels_pkey PRIMARY KEY (id);
