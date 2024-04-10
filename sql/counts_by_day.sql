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
reactions_counts AS (
  SELECT DATE_TRUNC('day', timestamp) AS day, COUNT(*) AS reactions_count
  FROM reactions
  GROUP BY DATE_TRUNC('day', timestamp)
),
verifications_counts AS (
  SELECT DATE_TRUNC('day', timestamp) AS day, COUNT(*) AS verifications_count
  FROM verifications
  GROUP BY DATE_TRUNC('day', timestamp)
)
SELECT 
  COALESCE(casts.day, links.day, reactions.day, verifications.day) AS day,
  COALESCE(casts_count, 0) AS casts_count,
  COALESCE(links_count, 0) AS links_count,
  COALESCE(reactions_count, 0) AS reactions_count,
  COALESCE(verifications_count, 0) AS verifications_count
FROM casts_counts casts
FULL OUTER JOIN links_counts links ON casts.day = links.day
FULL OUTER JOIN reactions_counts reactions ON COALESCE(casts.day, links.day) = reactions.day
FULL OUTER JOIN verifications_counts verifications ON COALESCE(casts.day, links.day, reactions.day) = verifications.day
ORDER BY day DESC
LIMIT 1000;
