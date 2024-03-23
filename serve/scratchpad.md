# Sample cURL commands to test locally based on the sample graphs in the samples folder

## Direct

curl -X 'POST' 'http://localhost:8000/direct/following/handles?limit=10' -H 'accept: application/json'   -H 'Content-Type: application/json'   -d '["v", "danromero.eth"]'

curl -X 'POST' 'http://localhost:8000/direct/following/fids?limit=10' -H 'accept: application/json'   -H 'Content-Type: application/json'   -d '[2,3]'

curl -X 'POST' 'http://localhost:8000/direct/engagement/handles?limit=10' -H 'accept: application/json'   -H 'Content-Type: application/json'   -d '["v", "dwr.eth"]'

curl -X 'POST' 'http://localhost:8000/direct/engagement/handles?limit=10' -H 'accept: application/json'   -H 'Content-Type: application/json'   -d '["vijaypm"]'

## Neighbors

curl -X 'POST' 'http://localhost:8000/graph/neighbors/engagement/handles?k=1&limit=10' -H 'accept: application/json'   -H 'Content-Type: application/json'   -d '["v", "danromero.eth"]'

curl -X 'POST' 'http://localhost:8000/graph/neighbors/engagement/addresses?limit=10' -H 'accept: application/json'   -H 'Content-Type: application/json'   -d '["0x91031dcfdea024b4d51e775486111d2b2a715871", "0x8fc5d6afe572fefc4ec153587b63ce543f6fa2ea"]'

curl -X 'POST' 'http://localhost:8000/graph/neighbors/engagement/fids?limit=10' -H 'accept: application/json'   -H 'Content-Type: application/json'   -d '[2,3]'

curl -X 'POST' 'http://localhost:8000/graph/neighbors/following/handles?limit=10' -H 'accept: application/json'   -H 'Content-Type: application/json'   -d '["v", "danromero.eth"]'

curl -X 'POST' 'http://localhost:8000/graph/neighbors/following/addresses?limit=10' -H 'accept: application/json'   -H 'Content-Type: application/json'   -d '["0x91031dcfdea024b4d51e775486111d2b2a715871", "0x8fc5d6afe572fefc4ec153587b63ce543f6fa2ea"]'

curl -X 'POST' 'http://localhost:8000/graph/neighbors/following/fids?limit=10' -H 'accept: application/json'   -H 'Content-Type: application/json'   -d '[2,3]'

## Personalized Profile Rankings

curl -X 'POST' 'http://localhost:8000/scores/personalized/engagement/handles?limit=10' -H 'accept: application/json'   -H 'Content-Type: application/json'   -d '["v", "danromero.eth"]'

curl -X 'POST' 'http://localhost:8000/scores/personalized/engagement/addresses?limit=10' -H 'accept: application/json'   -H 'Content-Type: application/json'   -d '["0x91031dcfdea024b4d51e775486111d2b2a715871", "0x8fc5d6afe572fefc4ec153587b63ce543f6fa2ea"]'

curl -X 'POST' 'http://localhost:8000/scores/personalized/engagement/fids?limit=10' -H 'accept: application/json'   -H 'Content-Type: application/json'   -d '[2,3]'

curl -X 'POST' 'http://localhost:8000/scores/personalized/following/handles?limit=10' -H 'accept: application/json'   -H 'Content-Type: application/json'   -d '["v", "danromero.eth"]'

curl -X 'POST' 'http://localhost:8000/scores/personalized/following/addresses?limit=10' -H 'accept: application/json'   -H 'Content-Type: application/json'   -d '["0x91031dcfdea024b4d51e775486111d2b2a715871", "0x8fc5d6afe572fefc4ec153587b63ce543f6fa2ea"]'

curl -X 'POST' 'http://localhost:8000/scores/personalized/following/fids?limit=10' -H 'accept: application/json'   -H 'Content-Type: application/json'   -d '[2,3]'

## Global Profile Rankings

curl -X 'GET' 'http://localhost:8000/scores/global/engagement/rankings?offset=10&limit=10' -H 'accept: application/json'   -H 'Content-Type: application/json'

curl -X 'POST' 'http://localhost:8000/scores/global/engagement/fids' -H 'accept: application/json'   -H 'Content-Type: application/json' -d '[2,3]'

curl -X 'POST' 'http://localhost:8000/scores/global/engagement/handles' -H 'accept: application/json'   -H 'Content-Type: application/json' -d '["v", "danromero.eth"]'

curl -X 'GET' 'http://localhost:8000/scores/global/following/rankings?offset=10&limit=10' -H 'accept: application/json'   -H 'Content-Type: application/json'

curl -X 'POST' 'http://localhost:8000/scores/global/following/fids' -H 'accept: application/json'   -H 'Content-Type: application/json' -d '[2,3]'

curl -X 'POST' 'http://localhost:8000/scores/global/following/handles' -H 'accept: application/json'   -H 'Content-Type: application/json' -d '["v", "danromero.eth"]'

## Farcaster Fid <-> Handles <-> Addresses lookup

curl -X 'POST' 'http://localhost:8000/metadata/handles' -H 'accept: application/json'   -H 'Content-Type: application/json'   -d '["0x91031dcfdea024b4d51e775486111d2b2a715871", "0x8fc5d6afe572fefc4ec153587b63ce543f6fa2ea"]'

curl -X 'POST' 'http://localhost:8000/metadata/fids' -H 'accept: application/json'   -H 'Content-Type: application/json'   -d '["0x91031dcfdea024b4d51e775486111d2b2a715871", "0x8fc5d6afe572fefc4ec153587b63ce543f6fa2ea"]'

curl -X 'POST' 'http://localhost:8000/metadata/addresses' -H 'accept: application/json'   -H 'Content-Type: application/json'   -d '["v", "danromero.eth"]' 

curl -X 'POST' 'http://localhost:8000/metadata/addresses/handles' -H 'accept: application/json'   -H 'Content-Type: application/json'   -d '["v", "danromero.eth"]' 

curl -X 'POST' 'http://localhost:8000/metadata/addresses/fids' -H 'accept: application/json'   -H 'Content-Type: application/json'   -d '[2,3]' 

## Global Frames Rankings

curl -X 'GET' 'http://localhost:8000/frames/global/rankings' -H 'accept: application/json'   -H 'Content-Type: application/json'

curl -X 'GET' 'http://localhost:8000/frames/global/rankings?details=True&agg=sumsquare&weights=L1C10R5&offset=10&limit=10' -H 'accept: application/json'   -H 'Content-Type: application/json'

## Personalized Frames Rankings

curl -X 'POST' 'http://localhost:8000/frames/personalized/rankings/fids' -H 'accept: application/json'   -H 'Content-Type: application/json' -d '[2,3]'

curl -X 'POST' 'http://localhost:8000/frames/personalized/rankings/fids?agg=sumsquare&weights=L1C10R5&voting=single&k=2&limit=10' -H 'accept: application/json'   -H 'Content-Type: application/json' -d '[2,3]'



# Useful Dune Queries
### Farcaster users onchain activity
https://dune.com/queries/3026245/5027754

