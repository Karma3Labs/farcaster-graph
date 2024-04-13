WITH casts_counts AS (
  SELECT DATE_TRUNC('day', timestamp) AS day, COUNT(*) AS casts_count
  FROM casts
  GROUP BY DATE_TRUNC('day', timestamp)
),
links_counts AS (
  SELECT DATE_TRUNC('day', timestamp) AS day, COUNT(*) AS links_count
  FROM links
  GROUP BY DATE_TRUNC('day', timestamp)
),
messages_counts AS (
  SELECT DATE_TRUNC('day', timestamp) AS day, COUNT(*) AS messages_count
  FROM messages
  GROUP BY DATE_TRUNC('day', timestamp)
),
reactions_counts AS (
  SELECT DATE_TRUNC('day', timestamp) AS day, COUNT(*) AS reactions_count
  FROM reactions
  GROUP BY DATE_TRUNC('day', timestamp)
),
user_data_counts AS (
  SELECT DATE_TRUNC('day', timestamp) AS day, COUNT(*) AS user_data_count
  FROM user_data
  GROUP BY DATE_TRUNC('day', timestamp)
),
verifications_counts AS (
  SELECT DATE_TRUNC('day', timestamp) AS day, COUNT(*) AS verifications_count
  FROM verifications
  GROUP BY DATE_TRUNC('day', timestamp)
)
SELECT 
  COALESCE(casts.day, links.day, messages.day, reactions.day, user_data.day, verifications.day) AS day,
  COALESCE(casts_count, 0) AS casts_count,
  COALESCE(links_count, 0) AS links_count,
  COALESCE(messages_count, 0) AS messages_count,
  COALESCE(reactions_count, 0) AS reactions_count,
  COALESCE(user_data_count, 0) AS user_data_count,
  COALESCE(verifications_count, 0) AS verifications_count
FROM casts_counts casts
FULL OUTER JOIN links_counts links ON casts.day = links.day
FULL OUTER JOIN reactions_counts reactions ON COALESCE(casts.day, links.day) = reactions.day
FULL OUTER JOIN verifications_counts verifications ON COALESCE(casts.day, links.day, reactions.day) = verifications.day
FULL OUTER JOIN messages_counts messages ON COALESCE(casts.day, links.day, reactions.day, verifications.day) = messages.day
FULL OUTER JOIN user_data_counts user_data ON COALESCE(casts.day, links.day, reactions.day, verifications.day, messages.day) = user_data.day
ORDER BY day DESC
LIMIT 1000;
