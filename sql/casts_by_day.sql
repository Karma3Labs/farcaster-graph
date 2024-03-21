SELECT DATE_TRUNC('day', timestamp) AS day, COUNT(*) AS row_count
FROM casts
GROUP BY DATE_TRUNC('day', timestamp)
ORDER BY day ASC
LIMIT 1000;
