import requests
import logging
from config import Config

logger = logging.getLogger("aishub2nmea")


def fetch_ais_data():
    url = Config.build_url()
    logger.info(f"Using URL: {url}")

    try:
        resp = requests.get(url, timeout=10)
    except requests.RequestException as e:
        logger.error(f"AISHub request failed: {e}")
        return None

    logger.debug(f"AISHub HTTP status: {resp.status_code}")

    if resp.status_code != 200:
        logger.error(f"AISHub Error {resp.status_code}: {resp.text}")
        return None

    return resp.text