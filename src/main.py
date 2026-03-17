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
            logger.info("Requesting AIS data...")
            xml = fetch_ais_data()

            logger.info("Parsing AIS XML...")
            vessels = parse_aishub_xml(xml)
            logger.info(f"Parsed {len(vessels)} vessels")

            if len(vessels) == 0:
                logger.warning("No vessels returned — check geofence or AISHub parameters.")

            # Debug: sample raw vessel
            if len(vessels) > 0:
                v = vessels[0]
                logger.warning(
                    f"SAMPLE RAW: lat={v['lat']} lon={v['lon']} sog={v['sog']} cog={v['cog']} navstat={v['navstat']} rot={v['rot']}"
                )

            logger.info("Encoding vessels into AIS NMEA...")
            nmea = vessels_to_nmea(vessels)
            logger.info(f"Encoded {len(nmea)} AIS messages.")

            # Real-time AIS streaming
            mps = getattr(Config, "MESSAGES_PER_SECOND", 5)
            logger.info(f"Streaming AIS messages at {mps} msg/sec")

            stream_udp_realtime(
                nmea_list=nmea,
                host=Config.UDP_HOST,
                port=Config.UDP_PORT,
                mps=mps,
            )

        except Exception as e:
            logger.error("Fatal error in main loop", exc_info=True)

        logger.info(f"Sleeping {Config.POLL_INTERVAL} seconds before next poll…")
        time.sleep(Config.POLL_INTERVAL)


if __name__ == "__main__":
    main()
