select 
i,
j,
v
from 
localtrust
where 
strategy_id=1
and date=(select max(date) from localtrust where strategy_id=1)