import os
from urllib.parse import urlencode
from dotenv import load_dotenv

# Do not overwrite environment variables provided by Docker/Portainer
load_dotenv(override=False)

class Config:
    # --- AISHub parameters ---
    USERNAME = os.getenv("AIS_USERNAME")
    FORMAT   = os.getenv("AIS_FORMAT", "1")
    OUTPUT   = os.getenv("AIS_OUTPUT", "xml")
    COMPRESS = os.getenv("AIS_COMPRESS", "0")

    # --- Bounding Box (Default: English Channel) ---
    LAT_MIN = os.getenv("LAT_MIN", "48.5")
    LAT_MAX = os.getenv("LAT_MAX", "51.5")
    LON_MIN = os.getenv("LON_MIN", "-6.5")
    LON_MAX = os.getenv("LON_MAX", "2.5")

    # --- Filtering ---
    MMSI = os.getenv("MMSI", "")
    IMO  = os.getenv("IMO", "")
    
    # --- Timing Parameters (Separated) ---
    # INTERVAL: AISHub API 'interval' parameter (Minutes of signal age)
    INTERVAL = os.getenv("INTERVAL", "30") 
    
    # POLL_INTERVAL: How Long the script sleeps between updates (Seconds)
    POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "60"))

    # --- UDP Output ---
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
            "interval": Config.INTERVAL, # API parameter
        }

        clean = {k: v for k, v in params.items() if str(v).strip()}
        return base + urlencode(clean)
