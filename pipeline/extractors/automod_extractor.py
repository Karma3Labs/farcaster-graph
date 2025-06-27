import io
import sys
from datetime import date

import pandas as pd
import requests
from loguru import logger
from sqlalchemy import create_engine, text


def fetch_data_from_api(api_key, db_user, db_password, db_endpoint):
    params = {"start": "2024-01-01", "end": "2024-12-31"}
    headers = {"api-key": f"{api_key}"}
    df_automod = pd.DataFrame()
    for channel in ["degen", "dev", "memes"]:
        initial_url = (
            f"https://automod.sh/api/partners/channels/{channel}/activity/export?"
        )
        response = requests.get(initial_url, params=params, headers=headers)
        print(response.url)
        if response.status_code == 200:
            # Read the response content into a pandas DataFrame
            data = pd.read_csv(io.StringIO(response.content.decode("utf-8")))
            data["channel_id"] = channel
            print(len(data))
            df_automod = pd.concat([df_automod, data], axis=0)
        else:
            raise Exception(
                f"Failed to fetch data from automod. Status code: {response.status_code}"
            )

    if len(df_automod) == 0:
        raise Exception("Failed to fetch data from automod. No data found.")

    rename_dict = {
        "createdAt": "created_at",
        "affectedUsername": "affected_username",
        "affectedUserFid": "affected_userid",
        "castHash": "cast_hash",
        "castText": "cast_text",
    }

    df_automod.rename(columns=rename_dict, inplace=True)
    df_automod = df_automod[
        [
            "created_at",
            "action",
            "actor",
            "affected_username",
            "affected_userid",
            "cast_hash",
            "channel_id",
        ]
    ]
    df_automod["created_at"] = pd.to_datetime(df_automod["created_at"], unit="ms")
    df_automod["date_iso"] = date.today()

    logger.info(df_automod.head())
    engine_string = "postgresql+psycopg2://%s:%s@%s:%d/%s" % (
        db_user,
        db_password,
        db_endpoint,
        9541,
        "farcaster",
    )

    postgres_engine = create_engine(
        engine_string, connect_args={"connect_timeout": 1000}
    )
    with postgres_engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE automod_data"))
        df_automod.to_sql("automod_data", con=conn, if_exists="append", index=False)
    return None


if __name__ == "__main__":
    # Get the parameters from the command line arguments
    if len(sys.argv) != 5:
        raise ValueError(
            "Please provide db_user, db_password, and db_endpoint as arguments."
        )

    api_key = sys.argv[1]
    db_user = sys.argv[2]
    db_password = sys.argv[3]
    db_endpoint = sys.argv[4]

    fetch_data_from_api(api_key, db_user, db_password, db_endpoint)
