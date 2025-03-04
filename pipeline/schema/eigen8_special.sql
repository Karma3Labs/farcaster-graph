CREATE VIEW warpcast_channels_data AS
SELECT
	channel_id as id,
  url,
--   name, -- in Eigen2 but not available in Eigen8
  description,
  image_url as imageurl,
--   headerimageurl, -- in Eigen2 but not available in Eigen8
	lead_fid as leadfid,
  moderator_fids as moderatorfids,
  created_at as createdat,
  follower_count as followercount,
--   membercount, -- in Eigen2 but not available in Eigen8
--   pinedcasthash, -- in Eigen2 but not available in Eigen8
	timestamp as insert_ts
FROM channels