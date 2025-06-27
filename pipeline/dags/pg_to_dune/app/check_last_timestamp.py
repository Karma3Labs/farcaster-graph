import json
import os

from dune_client.client import DuneClient
from dune_client.query import QueryBase
from dune_client.types import QueryParameter

# change the current working directory where .env file lives
# os.chdir("/Users/abc/local-Workspace/python-notebook-examples")
# load .env file
# dotenv.load_dotenv(".env")
# setup Dune Python client
dune = DuneClient(os.environ["DUNE_API_KEY"])

query = QueryBase(
    name="fetch last date of globaltrust_v2",
    query_id=int(os.environ["QUERY_ID"]),
)

result = dune.run_query(
    query=query,
    # performance = 'large' # optionally define which tier to run the execution on (default is "medium")
)

if len(result.result.rows) != 1:
    raise "not one"

last_date = result.result.rows[0][os.environ["FILTER_COLUMN"]]
print(last_date)
# # go over the results returned
# for row in result.result.rows:
#     print('hell')
#     print (row) # as an example we print the rows
