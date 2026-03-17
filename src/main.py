import time
from config import Config
from aishub import fetch_ais_data
from parser import parse_aishub_xml
from encoder import vessels_to_nmea
from forwarder import send_udp
from logger import setup_logging

logger = setup_logging()
import os
logger.info("ACTIVE ENVIRONMENT VARIABLES:")
for key in os.environ:
    if key.startswith("AIS_") or key in ("LAT_MIN", "LAT_MAX", "LON_MIN", "LON_MAX", "UDP_HOST", "UDP_PORT"):
        logger.info(f"  {key} = {os.environ[key]}")

def main():
    logger.info("AIS Streamer starting...")

    while True:
        try:
            logger.debug("Requesting AIS data...")
            xml = fetch_ais_data()

            logger.debug("Parsing XML data...")
            vessels = parse_aishub_xml(xml)

            logger.info(f"Parsed {len(vessels)} vessel positions")

            if len(vessels) == 0:
                logger.warning("No vessels received! Check .env parameters and AISHub account.")

            logger.debug("Encoding vessels to AIS NMEA sentences...")
            nmea = vessels_to_nmea(vessels)

            logger.info(f"Encoded {len(nmea)} AIS NMEA sentences")

            logger.debug("Sending AIS messages via UDP…")
            send_udp(nmea, Config.UDP_HOST, Config.UDP_PORT)

            logger.info(f"Sent {len(nmea)} AIS messages to {Config.UDP_HOST}:{Config.UDP_PORT}")

        except Exception as e:
            logger.error(f"Unhandled error occurred: {e}", exc_info=True)

        time.sleep(Config.POLL_INTERVAL)

if __name__ == "__main__":
    main()
