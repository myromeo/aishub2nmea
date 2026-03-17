import time
import logging

from config import Config
from aishub import fetch_ais_data
from parser import parse_aishub_xml
from encoder import vessels_to_nmea
from forwarder import stream_udp_realtime
from logger import setup_logging

logger = setup_logging()

def main():
    logger.info("AIS Streamer starting...")

    while True:
        try:
            logger.debug("Requesting AIS data from AISHub...")
            xml = fetch_ais_data()

            logger.debug("Parsing XML data...")
            vessels = parse_aishub_xml(xml)
            logger.info(f"Parsed {len(vessels)} vessel positions")

            if len(vessels) == 0:
                logger.warning("No vessels received! Check geofence / username / interval settings.")

            logger.debug("Encoding vessels to AIS NMEA sentences...")
            nmea = vessels_to_nmea(vessels)
            logger.info(f"Encoded {len(nmea)} AIS messages")

            mps = getattr(Config, "MESSAGES_PER_SECOND", 5)
            logger.info(f"Streaming in real‑time at {mps} messages/sec")

            stream_udp_realtime(
                nmea_list=nmea,
                host=Config.UDP_HOST,
                port=Config.UDP_PORT,
                mps=mps
            )

        except Exception as e:
            logger.error(f"Unhandled error occurred: {e}", exc_info=True)

        logger.info(f"Sleeping {Config.POLL_INTERVAL} seconds before next poll...")
        time.sleep(Config.POLL_INTERVAL)


if __name__ == "__main__":
    main()
