import os
from urllib.parse import urlencode
from dotenv import load_dotenv

# IMPORTANT: do NOT override Portainer environment variables
load_dotenv(override=False)


class Config:

    # AISHub API parameters
    USERNAME = os.getenv("AIS_USERNAME")
    FORMAT = os.getenv("AIS_FORMAT", "0")     # MUST be 0 for raw encoded ints
    OUTPUT = os.getenv("AIS_OUTPUT", "xml")
    COMPRESS = os.getenv("AIS_COMPRESS", "0")

    LAT_MIN = os.getenv("LAT_MIN", "-90")
    LAT_MAX = os.getenv("LAT_MAX", "90")
    LON_MIN = os.getenv("LON_MIN", "-180")
    LON_MAX = os.getenv("LON_MAX", "180")

    MMSI = os.getenv("MMSI", "")
    IMO = os.getenv("IMO", "")
    INTERVAL = os.getenv("INTERVAL", "")

    # Streaming rate
    MESSAGES_PER_SECOND = float(os.getenv("MESSAGES_PER_SECOND", "5"))

    # Poll frequency
    POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "60"))

    # UDP target
    UDP_HOST = os.getenv("UDP_HOST", "127.0.0.1")
    UDP_PORT = int(os.getenv("UDP_PORT", "10110"))

    @staticmethod
    def build_url():
        base = "https://data.aishub.net/ws.php?"

        params = {
            "username": Config.USERNAME,
            "format": Config.FORMAT,
            "output": Config.OUTPUT,
            "compress": Config.COMPRESS,
            "latmin": Config.LAT_MIN,
            "latmax": Config.LAT_MAX,
            "lonmin": Config.LON_MIN,
            "lonmax": Config.LON_MAX,
            "mmsi": Config.MMSI,
            "imo": Config.IMO,
            "interval": Config.INTERVAL,
        }

        # Remove blanks
        clean_params = {k: v for k, v in params.items() if v not in ("", None, " ")}

        return base + urlencode(clean_params)
``
