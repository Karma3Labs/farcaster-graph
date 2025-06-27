import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import urllib3

http = urllib3.PoolManager()


def download_csv(limit: int, offset: int, table_name: str):
    """
    Download CSV data from the backend server.

    Args:
        endpoint (str): The endpoint for the download.

    Returns:
        List[dict]: List of downloaded data.

    Example:
        data = et._download_csv('localtrust/123')
    """
    print(f"limt={limit}, offset={offset}")
    jitter = random.uniform(0.01, 1)
    time.sleep(jitter)

    response = http.request(
        "GET",
        f"https://api.dune.com/api/v1/query/3832819/results/csv?limit={limit}&offset={offset}",
        headers={
            "Accept": "text/csv",
            "Content-Type": "text/csv",
            "X-DUNE-API-KEY": "7QYqrqNvGVJJuwMybzxfh1sbR8qXFbDI",
        },
        preload_content=False,
    )
    if response.status != 200:
        raise Exception(f"Failed to download CSV: {response.data.decode('utf-8')}")

    # data = response.data.decode('utf-8')
    # print(data)
    filename = f"backup/{table_name}_offset_{offset}_limit_{limit}.csv"
    with open(filename, "wb") as out_file:
        # print(data)
        # data = response.read() # a `bytes` object
        out_file.write(response.data)

        # shutil.copyfileobj(response, out_file)
        # out_file.write(response)
        print(f"wrote {filename}")


limit = 30000
# next = limit
offset = 0

start = 0
stop = 382500000
step = limit
incremental_array = list(range(start, stop + step, step))

# print(incremental_array[:100])
num_workers = 25
table_name = "karma3-labs.dataset_k3l_cast_localtrust"
# Use ThreadPoolExecutor to make parallel HTTP requests
with ThreadPoolExecutor(max_workers=num_workers) as executor:
    future_to_value = {
        executor.submit(download_csv, limit, value, table_name): value
        for value in incremental_array
    }

    for future in as_completed(future_to_value):
        value = future_to_value[future]
        try:
            future.result()
        except Exception as exc:
            print(f"Value {value} generated an exception: {exc}")

print("All requests completed.")
