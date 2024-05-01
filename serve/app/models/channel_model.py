from enum import Enum

class Channel(Enum):
  degen = 'degen'
  base = 'base'
  optimisim = 'optimisim'
  founders = 'founders'
  farcaster = 'farcaster'

channel_urls = dict()
channel_urls[Channel.degen] = 'chain://eip155:7777777/erc721:0x5d6a07d07354f8793d1ca06280c4adf04767ad7e'
channel_urls[Channel.base] = 'https://onchainsummer.xyz'
channel_urls[Channel.optimisim] = 'https://warpcast.com/~/channel/optimism'
channel_urls[Channel.founders] = 'https://farcaster.group/founders'
channel_urls[Channel.farcaster] = 'chain://eip155:7777777/erc721:0x4f86113fc3e9783cf3ec9a552cbb566716a57628'