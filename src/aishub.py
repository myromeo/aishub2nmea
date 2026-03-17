import requests
from config import Config
import logging
logger = logging.getLogger("aishub2nmea")

def fetch_ais_data():
    url = Config.build_url()
    logger.debug(f"Fetching from URL: {url}")

    resp = requests.get(url, timeout=10)

    logger.debug(f"AISHub response status: {resp.status_code}")
    if resp.status_code != 200:
        logger.error(f"AISHub returned status {resp.status_code}: {resp.text}")

    resp.raise_for_status()
    return resp.text
