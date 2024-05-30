# Sample cURL commands to test locally based on the sample graphs in the samples folder

## For YOU Feed
curl -X 'GET' 'http://localhost:8000/casts/personalized/popular/3'

curl -X 'GET' 'http://localhost:8000/casts/personalized/popular/3?agg=sumsquare&weights=L1C10R5Y7&k=2&offset=25&limit=25&lite=false'


## (Coming Soon) 
### (Coming Soon) Global Profile Rankings

curl -X 'GET' 'http://localhost:8000/scores/global/engagement/rankings?offset=10&limit=10' -H 'accept: application/json'   -H 'Content-Type: application/json'

curl -X 'POST' 'http://localhost:8000/scores/global/engagement/fids' -H 'accept: application/json'   -H 'Content-Type: application/json' -d '[2,3]'

curl -X 'GET' 'http://localhost:8000/scores/global/following/rankings?offset=10&limit=10' -H 'accept: application/json'   -H 'Content-Type: application/json'

curl -X 'POST' 'http://localhost:8000/scores/global/following/fids' -H 'accept: application/json'   -H 'Content-Type: application/json' -d '[2,3]'


### (Coming Soon) Personalized Profile Rankings

curl -X 'POST' 'http://localhost:8000/scores/personalized/engagement/fids?limit=10' -H 'accept: application/json'   -H 'Content-Type: application/json'   -d '[2,3]'




