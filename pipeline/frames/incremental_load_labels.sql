INSERT INTO k3l_url_labels(url, latest_cast_dt, earliest_cast_dt)
WITH max_cast_dt AS (
  select 
  	coalesce(max(latest_cast_dt),'1/26/24') as dt
	from k3l_url_labels as labels
	inner join k3l_cast_embed_url_mapping as url_map on (labels.url_id = url_map.url_id)
)
SELECT 
    ems->>'url' as url, 
    max(created_at) as latest_cast_dt,
   	min(created_at) as earliest_cast_dt
FROM
		casts
  		cross join lateral jsonb_array_elements(casts.embeds) as ems
   inner join max_cast_dt on (casts.created_at >= max_cast_dt.dt AND casts.deleted_at IS NOT NULL)
   left join 
   	k3l_url_labels as labels 
    	on (labels.url = ems->>'url' 
          and casts.created_at >= max_cast_dt.dt
          )
WHERE 
  labels.url_id IS NULL
	AND jsonb_array_length(embeds) > 0
  AND ems->'url' IS NOT NULL
  AND ems->>'url' NOT LIKE ALL(ARRAY[
                          'https://i.imgur.com/%',
                          'https://youtu.be/%',
                          'https://www.youtube.com/%',
                          'https://imagedelivery.net/%',
                          '%.png', '%.gif', '%.pdf', '%.jpg', '%.jpeg', '%.mp4', '%.m3u8'])
GROUP BY ems->>'url'