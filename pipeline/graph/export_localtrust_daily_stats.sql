with stats_per_strategy_per_date as (SELECT
  max(date) AS date,
  COUNT(CASE WHEN strategy_id = 1 THEN 1 END) AS strategy_id_1_row_count,
  AVG(CASE WHEN strategy_id = 1 THEN v END) AS strategy_id_1_mean,
  STDDEV(CASE WHEN strategy_id = 1 THEN v END) AS strategy_id_1_stddev,
  MAX(CASE WHEN strategy_id = 1 THEN v END) - MIN(CASE WHEN strategy_id = 1 THEN v END) AS strategy_id_1_range,
  COUNT(CASE WHEN strategy_id = 3 THEN 1 END) AS strategy_id_3_row_count,
  AVG(CASE WHEN strategy_id = 3 THEN v END) AS strategy_id_3_mean,
  STDDEV(CASE WHEN strategy_id = 3 THEN v END) AS strategy_id_3_stddev,
  MAX(CASE WHEN strategy_id = 3 THEN v END) - MIN(CASE WHEN strategy_id = 3 THEN v END) AS strategy_id_3_range
FROM
  localtrust
-- GROUP BY
--   date
)
  
INSERT INTO localtrust_stats (
    date,
    strategy_id_1_row_count,
    strategy_id_1_mean,
    strategy_id_1_stddev,
    strategy_id_1_range,
    strategy_id_3_row_count,
    strategy_id_3_mean,
    strategy_id_3_stddev,
    strategy_id_3_range
)
SELECT
    date,
    strategy_id_1_row_count,
    strategy_id_1_mean,
    strategy_id_1_stddev,
    strategy_id_1_range,
    strategy_id_3_row_count,
    strategy_id_3_mean,
    strategy_id_3_stddev,
    strategy_id_3_range
FROM
    stats_per_strategy_per_date;
