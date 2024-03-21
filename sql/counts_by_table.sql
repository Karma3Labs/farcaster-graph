WITH 
    q_fids AS (SELECT COUNT(1) AS fids_count FROM fids),
    q_fnames AS (SELECT COUNT(1) AS fnames_count FROM fnames),
    q_reactions AS (SELECT COUNT(1) AS reactions_count FROM reactions),
    q_casts AS (SELECT COUNT(1) AS casts_count FROM casts),
    q_links AS (SELECT COUNT(1) AS links_count FROM links),
    q_messages AS (SELECT COUNT(1) AS messages_count FROM messages)
    
SELECT 
    q_fids.fids_count, 
    q_fnames.fnames_count, 
    q_reactions.reactions_count, 
    q_casts.casts_count, 
    q_links.links_count, 
    q_messages.messages_count
FROM
    q_fids, q_fnames, q_reactions, q_casts, q_links, q_messages;
