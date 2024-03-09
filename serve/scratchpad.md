# Sample cURL commands to test locally based on the sample graphs in the samples folder

curl -X 'POST' 'http://localhost:8000/graph/neighbors/engagement/handles?k=1&limit=10' -H 'accept: application/json'   -H 'Content-Type: application/json'   -d '["mikjin"]'

curl -X 'POST' 'http://localhost:8000/graph/neighbors/engagement/addresses?limit=10' -H 'accept: application/json'   -H 'Content-Type: application/json'   -d '["0x9acf607fa580e5857efde4cc1462326e0a6ffe8d"]'

curl -X 'POST' 'http://localhost:8000/graph/neighbors/engagement/fids?limit=10' -H 'accept: application/json'   -H 'Content-Type: application/json'   -d '[225588]'


curl -X 'POST' 'http://localhost:8000/scores/personalized/engagement/handles?limit=10' -H 'accept: application/json'   -H 'Content-Type: application/json'   -d '["mikjin"]'

curl -X 'POST' 'http://localhost:8000/scores/personalized/engagement/addresses?limit=10' -H 'accept: application/json'   -H 'Content-Type: application/json'   -d '["0x9acf607fa580e5857efde4cc1462326e0a6ffe8d"]'

curl -X 'POST' 'http://localhost:8000/scores/personalized/engagement/fids?limit=10' -H 'accept: application/json'   -H 'Content-Type: application/json'   -d '[225588]'


curl -X 'POST' 'http://localhost:8000/graph/neighbors/following/handles?limit=10' -H 'accept: application/json'   -H 'Content-Type: application/json'   -d '["farcaster.eth"]'

curl -X 'POST' 'http://localhost:8000/graph/neighbors/following/addresses?limit=10' -H 'accept: application/json'   -H 'Content-Type: application/json'   -d '["0x86924c37a93734e8611eb081238928a9d18a63c0"]'

curl -X 'POST' 'http://localhost:8000/graph/neighbors/following/fids?limit=10' -H 'accept: application/json'   -H 'Content-Type: application/json'   -d '[1]'


curl -X 'POST' 'http://localhost:8000/scores/personalized/following/handles?limit=10' -H 'accept: application/json'   -H 'Content-Type: application/json'   -d '["farcaster.eth"]'

curl -X 'POST' 'http://localhost:8000/scores/personalized/following/addresses?limit=10' -H 'accept: application/json'   -H 'Content-Type: application/json'   -d '["0x86924c37a93734e8611eb081238928a9d18a63c0"]'

curl -X 'POST' 'http://localhost:8000/scores/personalized/following/fids?limit=10' -H 'accept: application/json'   -H 'Content-Type: application/json'   -d '[1]'


# Useful Dune Queries
### Farcaster users onchain activity
https://dune.com/queries/3026245/5027754

