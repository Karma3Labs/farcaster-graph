# Sample cURL commands to test locally based on the sample graphs in the samples folder

curl -X 'POST' 'http://localhost:8000/graph/neighbors/engagement/handles?k=1' -H 'accept: application/json'   -H 'Content-Type: application/json'   -d '["mikjin"]'

curl -X 'POST' 'http://localhost:8000/graph/neighbors/following/handles' -H 'accept: application/json'   -H 'Content-Type: application/json'   -d '["farcaster.eth"]'

curl -X 'POST' 'http://localhost:8000/graph/neighbors/engagement/addresses' -H 'accept: application/json'   -H 'Content-Type: application/json'   -d '["0x9acf607fa580e5857efde4cc1462326e0a6ffe8d"]'

curl -X 'POST' 'http://localhost:8000/graph/neighbors/following/addresses' -H 'accept: application/json'   -H 'Content-Type: application/json'   -d '["0x86924c37a93734e8611eb081238928a9d18a63c0"]'

curl -X 'POST' 'http://localhost:8000/scores/personalized/engagement/addresses' -H 'accept: application/json'   -H 'Content-Type: application/json'   -d '["0x9acf607fa580e5857efde4cc1462326e0a6ffe8d"]'

curl -X 'POST' 'http://localhost:8000/scores/personalized/following/addresses' -H 'accept: application/json'   -H 'Content-Type: application/json'   -d '["0x86924c37a93734e8611eb081238928a9d18a63c0"]'


# Useful Dune Queries
### Farcaster users onchain activity
https://dune.com/queries/3026245/5027754

