import os
from urllib.parse import urlencode
from dotenv import load_dotenv

# Do not overwrite environment variables provided by Docker/Portainer
load_dotenv(override=False)

class Config:
    # --- AISHub parameters (Defaults aligned with your working Compose) ---
    USERNAME = os.getenv("AIS_USERNAME")
    FORMAT   = os.getenv("AIS_FORMAT", "1")   # Default to Human Readable
    OUTPUT   = os.getenv("AIS_OUTPUT", "xml") # Always XML
    COMPRESS = os.getenv("AIS_COMPRESS", "0") # No compression

    # --- Bounding Box (Default: English Channel Focus) ---
    LAT_MIN = os.getenv("LAT_MIN", "48.5")
    LAT_MAX = os.getenv("LAT_MAX", "51.5")
    LON_MIN = os.getenv("LON_MIN", "-6.5")
    LON_MAX = os.getenv("LON_MAX", "2.5")

    # --- Filtering (Usually empty) ---
    MMSI = os.getenv("MMSI", "")
    IMO  = os.getenv("IMO", "")
    
    # --- Polling (Default to 60s) ---
    POLL_INTERVAL = int(os.getenv("INTERVAL", "60"))

    # --- UDP Output (Default to your shipfeeder setup) ---
    UDP_HOST = os.getenv("UDP_HOST", "shipfeeder")
    UDP_PORT = int(os.getenv("UDP_PORT", "50001"))

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
            # We use interval=60 for the API call to match the poll rate
            "interval": Config.POLL_INTERVAL, 
        }

        # Remove empty or whitespace params to keep the URL clean
        clean = {k: v for k, v in params.items() if str(v).strip()}

        return base + urlencode(clean)
