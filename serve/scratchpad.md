curl -X 'POST' \
  'http://127.0.0.1:8000/graph/neighbors/engagement' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{"addresses": ["0x4114e33eb831858649ea3702e1c9a2db3f626446", "0x8773442740c17c9d0f0b87022c722f9a136206ed"]}'

curl -X 'GET' \
  'http://127.0.0.1:8000/graph/neighbors/engagement' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '["0x4114e33eb831858649ea3702e1c9a2db3f626446", "0x8773442740c17c9d0f0b87022c722f9a136206ed"]'


https://dune.com/queries/3026245/5027754

