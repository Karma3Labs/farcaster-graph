INSERT INTO k3l_cast_embed_url_mapping(url_id, cast_id)
WITH max_cast_dt AS (
  select 
  	max(latest_cast_dt) as dt
	from k3l_url_labels as labels
	inner join k3l_cast_embed_url_mapping as url_map on (labels.url_id = url_map.url_id)
)
  SELECT 
      labels.url_id as url_id,
      casts.id as cast_id
  FROM casts 
    cross join lateral json_array_elements(casts.embeds) as ems
    inner join max_cast_dt on (casts.created_at >= max_cast_dt.dt)
     inner join 
     	k3l_url_labels as labels 
      	on (labels.url = ems->>'url'
            AND json_array_length(embeds) > 0
    				AND ems->'url' IS NOT NULL
    				AND ems->>'url' NOT LIKE ALL(ARRAY[
                          'https://i.imgur.com/%',
                          'https://youtu.be/%',
                          'https://www.youtube.com/%',
                          'https://imagedelivery.net/%',
                          '%.png', '%.gif', '%.pdf', '%.jpg', '%.jpeg', '%.mp4', '%.m3u8'])  
    				AND created_at >= max_cast_dt.dt
            )