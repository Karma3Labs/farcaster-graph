select 
'0x' || encode(f1.custody_address::bytea, 'hex') as i,
'0x' || encode(f2.custody_address::bytea, 'hex') as j,
lt.v
from 
localtrust as lt
inner join fids as f1 on (cast(lt.i as int8) = f1.fid)
inner join fids as f2 on (cast(lt.j as int8) = f2.fid)
where 
strategy_id=1
and date=(select max(date) from localtrust where strategy_id=1)