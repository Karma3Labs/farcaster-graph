select 
i,
j,
v
from 
localtrust
where 
strategy_id=1
and date=(select max(date) from localtrust where strategy_id=1)
-- comment out below code for local testing
-- AND i::integer < 10
-- ORDER BY random()
-- LIMIT 1000