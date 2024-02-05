curl -X 'POST' \
  'http://127.0.0.1:8000/graph/neighbors/engagement' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{"addresses": ["0x4114e33eb831858649ea3702e1c9a2db3f626446", "0x8773442740c17c9d0f0b87022c722f9a136206ed"]}'

curl -X 'GET' \
  'http://127.0.0.1:8000/graph/neighbors/engagement' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '["0x4114e33eb831858649ea3702e1c9a2db3f626446", "0x8773442740c17c9d0f0b87022c722f9a136206ed"]' \
  -s -o /tmp/fc_engagement_out.json -w "\ndnslookup: %{time_namelookup} | connect: %{time_connect} | appconnect: %{time_appconnect} | pretransfer: %{time_pretransfer} | redirect: %{time_redirect} | starttransfer: %{time_starttransfer} | total: %{time_total} | size: %{size_download}\n"

curl -X 'GET' \
  'http://127.0.0.1:8000/graph/neighbors/following' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '["0x4114e33eb831858649ea3702e1c9a2db3f626446", "0x8773442740c17c9d0f0b87022c722f9a136206ed"]' \
  -s -o /tmp/fc_following_out.json -w "\ndnslookup: %{time_namelookup} | connect: %{time_connect} | appconnect: %{time_appconnect} | pretransfer: %{time_pretransfer} | redirect: %{time_redirect} | starttransfer: %{time_starttransfer} | total: %{time_total} | size: %{size_download}\n"

curl -X 'GET' \
  'http://127.0.0.1:8000/metadata/handles' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '["0x4114e33eb831858649ea3702e1c9a2db3f626446", "0x8773442740c17c9d0f0b87022c722f9a136206ed"]' \
  -s -o /tmp/fc_handles.json -w "\ndnslookup: %{time_namelookup} | connect: %{time_connect} | appconnect: %{time_appconnect} | pretransfer: %{time_pretransfer} | redirect: %{time_redirect} | starttransfer: %{time_starttransfer} | total: %{time_total} | size: %{size_download}\n"


curl -X 'GET' \
  'http://127.0.0.1:8000/metadata/addresses' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '["dwr.eth", "v", "vitalik.eth"]' \
  -s -o /tmp/fc_handle_addresses.json -w "\ndnslookup: %{time_namelookup} | connect: %{time_connect} | appconnect: %{time_appconnect} | pretransfer: %{time_pretransfer} | redirect: %{time_redirect} | starttransfer: %{time_starttransfer} | total: %{time_total} | size: %{size_download}\n"

https://dune.com/queries/3026245/5027754

