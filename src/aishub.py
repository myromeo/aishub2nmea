import requests
from config import Config

def fetch_ais_data():
    url = Config.build_url()
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    return resp.text
