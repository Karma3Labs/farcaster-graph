from datetime import datetime, timezone

class Channel():
  def __init__(self, channel):
    self.id: str = channel.get('id')
    self.project_url: str = channel.get('url')
    self.name: str = channel.get('name')
    self.description: str = channel.get('description')
    self.image_url: str = channel.get('imageurl')
    self.lead_fid: int = channel.get('leadfid')
    self.host_fids: list[int] = channel.get('hostfids')
    self.created_at_ts: str = channel.get('createdat')
    self.follower_count: int = channel.get('followercount')

  def __str__(self) -> str:
    dt = datetime.now()
    host_fids_str = "[" + ",".join(map(str, self.host_fids)) + "]" if self.host_fids and len(self.host_fids) > 0 else "[]"
    chan_str = "{" + f'''"id":"{self.id}","project_url":"{self.project_url}","name":"{self.name}","description":"{self.description}","image_url":"{self.image_url}","lead_fid":{self.lead_fid},"host_fids":{host_fids_str},"created_at_ts":"{self.created_at_ts}","follower_count":{self.follower_count},"processed_ts":"{dt}"''' + "}"
    return chan_str