# Pre-requisites
1. Generate graph artifacts by running the [pipeline](../pipeline/Readme.md) from the `pipeline` sub-project in the parent folder. *Note: if you are in a rush, you can try the sample artifacts found in the `samples` folder of this sub-project*
2. An instance of Postgres DB with data from Farcaster (installed locally or on a remote server)  - for example, a database instance of [Farcaster Replicator](https://github.com/farcasterxyz/hub-monorepo/tree/main/apps/replicator) 
3. Copy/rename `.env.sample` to `.env` and udpate the properties.
4. Install [Python 3.12](https://www.python.org/downloads/)
5. Install [Poetry](https://python-poetry.org) for depenedency management:
`curl -sSL https://install.python-poetry.org | python3 -`
6. Create a [virtualenv](https://docs.python.org/3/library/venv.html) somewhere on your machine - for example,`python3 -m venv .venv` will create a virtualenv in your current directory.

## Setup virtual environment
1. Activate the virtual environment that your created in the steps above: `source .venv/bin/activate`
2. Install dependencies `poetry install`

# Start the server
1. Activate the virtual environment if it is not already active.
2. Start the server

	- local machine for development: `uvicorn app.main:app --reload`
	- production: `uvicorn app.main:app --host 0.0.0.0 --port 8080 > /tmp/uvicorn.log 2>&1 &`

# Try the API

Query the engagement-based graph:

**NOTE: the server supports both GET and POST methods work but since we use a request body, most http clients prefer POST**

```
curl -X 'POST' \
  'http://127.0.0.1:8000/graph/neighbors/engagement' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '["0x4114e33eb831858649ea3702e1c9a2db3f626446", "0x86924c37a93734e8611eb081238928a9d18a63c0"]' \
  -s -o /tmp/fc_engagement_out.json -w "\ndnslookup: %{time_namelookup} | connect: %{time_connect} | appconnect: %{time_appconnect} | pretransfer: %{time_pretransfer} | redirect: %{time_redirect} | starttransfer: %{time_starttransfer} | total: %{time_total} | size: %{size_download}\n"
```

Query the following-based graph:

```
curl -X 'POST' \
  'http://127.0.0.1:8000/graph/neighbors/following' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '["0x460af11e497dc273fc163414943c6fd95d17b1fd", "0x86924c37a93734e8611eb081238928a9d18a63c0"]' \
  -s -o /tmp/fc_following_out.json -w "\ndnslookup: %{time_namelookup} | connect: %{time_connect} | appconnect: %{time_appconnect} | pretransfer: %{time_pretransfer} | redirect: %{time_redirect} | starttransfer: %{time_starttransfer} | total: %{time_total} | size: %{size_download}\n"
```

Get handles for eth addresses:

```
curl -X 'POST' \
  'http://127.0.0.1:8000/metadata/handles' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '["0x86924c37a93734e8611eb081238928a9d18a63c0", "0x8773442740c17c9d0f0b87022c722f9a136206ed", "0x91031dcfdea024b4d51e775486111d2b2a715871", "0x4114e33eb831858649ea3702e1c9a2db3f626446", "0x182327170fc284caaa5b1bc3e3878233f529d741", "0x460af11e497dc273fc163414943c6fd95d17b1fd", "0x5466de5329eb506376ea5c10b996e580e3a9ca25", "0xdbcc3f8f6831bd83dadb6a59b432ee1d1da76940"]' \
  -s -o /tmp/fc_handles_out.json -w "\ndnslookup: %{time_namelookup} | connect: %{time_connect} | appconnect: %{time_appconnect} | pretransfer: %{time_pretransfer} | redirect: %{time_redirect} | starttransfer: %{time_starttransfer} | total: %{time_total} | size: %{size_download}\n"
```
	
Get eth addresses for handles:

```
curl -X 'POST' \
  'http://127.0.0.1:8000/metadata/addresses' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '["farcaster.eth", "varunsrin.eth", "farcaster", "v", "luisc", "grumbly"]' \
  -s -o /tmp/fc_addresses_out.json -w "\ndnslookup: %{time_namelookup} | connect: %{time_connect} | appconnect: %{time_appconnect} | pretransfer: %{time_pretransfer} | redirect: %{time_redirect} | starttransfer: %{time_starttransfer} | total: %{time_total} | size: %{size_download}\n"
```

Personalized ranking based on the engagement-based graph:

```
curl -X 'POST' \
  'http://127.0.0.1:8000/scores/personalized/engagement/addresses' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '["0x4114e33eb831858649ea3702e1c9a2db3f626446", "0x86924c37a93734e8611eb081238928a9d18a63c0"]' \
  -s -o /tmp/fc_personal_engagement_addresses_out.json -w "\ndnslookup: %{time_namelookup} | connect: %{time_connect} | appconnect: %{time_appconnect} | pretransfer: %{time_pretransfer} | redirect: %{time_redirect} | starttransfer: %{time_starttransfer} | total: %{time_total} | size: %{size_download}\n"
```

```
curl -X 'POST' \
  'http://127.0.0.1:8000/scores/personalized/engagement/handles' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '["farcaster.eth", "varunsrin.eth", "farcaster", "v"]' \
  -s -o /tmp/fc_personal_engagement_handles_out.json -w "\ndnslookup: %{time_namelookup} | connect: %{time_connect} | appconnect: %{time_appconnect} | pretransfer: %{time_pretransfer} | redirect: %{time_redirect} | starttransfer: %{time_starttransfer} | total: %{time_total} | size: %{size_download}\n"
```

Personalized ranking based on the following-based graph:

```
curl -X 'POST' \
  'http://127.0.0.1:8000/scores/personalized/following/addresses' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '["0x460af11e497dc273fc163414943c6fd95d17b1fd", "0x5466de5329eb506376ea5c10b996e580e3a9ca25", "0xdbcc3f8f6831bd83dadb6a59b432ee1d1da76940"]' \
  -s -o /tmp/fc_personal_following_addresses_out.json -w "\ndnslookup: %{time_namelookup} | connect: %{time_connect} | appconnect: %{time_appconnect} | pretransfer: %{time_pretransfer} | redirect: %{time_redirect} | starttransfer: %{time_starttransfer} | total: %{time_total} | size: %{size_download}\n"
```

```
curl -X 'POST' \
  'http://127.0.0.1:8000/scores/personalized/following/handles' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '["luisc", "grumbly"]' \
  -s -o /tmp/fc_personal_following_handles_out.json -w "\ndnslookup: %{time_namelookup} | connect: %{time_connect} | appconnect: %{time_appconnect} | pretransfer: %{time_pretransfer} | redirect: %{time_redirect} | starttransfer: %{time_starttransfer} | total: %{time_total} | size: %{size_download}\n"
```