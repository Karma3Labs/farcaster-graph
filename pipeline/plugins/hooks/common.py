from urllib.parse import urlparse, urlunparse

from airflow.models import Variable


def convert_hostname(url: str):
    # Parse the original URL
    parsed_url = urlparse(url)

    # Replace the scheme and netloc with the new hostname
    new_netloc = Variable.get("airflow_hostname")
    new_scheme = "https"

    # Construct the new URL
    return urlunparse((new_scheme, new_netloc) + parsed_url[2:])
