import time
import logging

from logger import setup_logging
from config import Config
from aishub import fetch_ais_data
from parser import parse_aishub_xml
from encoder import vessels_to_nmea
from forwarder import stream_udp_realtime

logger = setup_logging()


def main():
    logger.info("AIS Streamer starting...")

    while True:
        try:
            logger.info("Requesting AIS data...")
            xml = fetch_ais_data()

            logger.info("Parsing AIS XML...")
            vessels = parse_aishub_xml(xml)
            logger.info(f"Parsed {len(vessels)} vessels")

            # Debug sample vessel
            if vessels:
                v = vessels[0]
                logger.warning(
                    f"SAMPLE RAW: lat={v['lat']} lon={v['lon']} sog={v['sog']} cog={v['cog']} "
                    f"navstat={v['navstat']} rot={v['rot']}"
                )

            logger.info("Encoding vessels...")
            nmea = vessels_to_nmea(vessels)
            logger.info(f"Encoded {len(nmea)} AIS messages")

            stream_udp_realtime(
                nmea_list=nmea,
                host=Config.UDP_HOST,
                port=Config.UDP_PORT,
                mps=Config.MESSAGES_PER_SECOND
            )

        except Exception as e:
            logger.error("Unhandled error in main loop", exc_info=True)

        logger.info(f"Sleeping {Config.POLL_INTERVAL} seconds before next poll…")
        time.sleep(Config.POLL_INTERVAL)


if __name__ == "__main__":
    main()
