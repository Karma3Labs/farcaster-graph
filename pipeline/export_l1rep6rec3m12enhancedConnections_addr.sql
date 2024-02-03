SELECT 
	'0x'||encode(coalesce(v1.signer_address, f1.custody_address),'hex') as i,
 	'0x'||encode(coalesce(v2.signer_address, f2.custody_address),'hex') as j, 
  lt.v
FROM localtrust as lt
INNER JOIN fids as f1 on (f1.fid = cast(lt.i as int8))
INNER JOIN fids as f2 on (f2.fid = cast(lt.j as int8))
LEFT JOIN verifications as v1 on (v1.fid = f1.fid)
LEFT JOIN verifications as v2 on (v2.fid = f2.fid)
WHERE 
  lt.strategy_id=3
  AND lt.date=(select max(date) from localtrust where strategy_id=3)