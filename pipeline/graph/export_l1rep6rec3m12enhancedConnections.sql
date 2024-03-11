select 
i,
j,
v
from 
localtrust
where 
strategy_id=3
and date=(select max(date) from localtrust where strategy_id=3)