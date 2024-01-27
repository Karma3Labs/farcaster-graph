SELECT 
	'0x'||encode(f1.custody_address,'hex') as i,
 	'0x'||encode(f2.custody_address,'hex') as j, 
  lt.v
FROM localtrust as lt
INNER JOIN fids as f1 on (f1.fid = cast(lt.i as int8))
INNER JOIN fids as f2 on (f2.fid = cast(lt.j as int8))
WHERE 
  lt.strategy_id=3
  AND lt.date=(select max(date) from localtrust where strategy_id=3)