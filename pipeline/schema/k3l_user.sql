CREATE ROLE k3l_user LOGIN PASSWORD 'skoiYyORdzOygilQor';

GRANT SELECT ON ALL TABLES IN SCHEMA "public" TO k3l_user;

GRANT USAGE, CREATE ON SCHEMA public TO k3l_user;

-- below commands required only for an existing database
-- ALTER TABLE public.globaltrust OWNER TO k3l_user;
-- ALTER TABLE public.localtrust OWNER TO k3l_user;
-- ALTER TABLE public.globaltrust_config OWNER TO k3l_user;
-- ALTER TABLE public.pretrust OWNER TO k3l_user;
-- ALTER TABLE public.localtrust_stats OWNER TO k3l_user;