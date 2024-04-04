class Channel():
  def __init__(self, channel):
    self.id: str = channel.get('id')
    self.project_url: str = channel.get('url')
    self.name: str = channel.get('name')
    self.description: str = channel.get('description')
    self.image_url: str = channel.get('imageUrl')
    self.lead_fid: int = channel.get('leadFid')
    self.host_fids: list[int] = channel.get('hostFids')
    self.created_at_ts: int = channel.get('createdAt')
    self.follower_count: int = channel.get('followerCount')
