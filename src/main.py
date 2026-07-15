import time
import logging

from logger import setup_logging
from config import Config
from aishub import fetch_ais_data
from parser import parse_aishub_xml
from encoder import vessels_to_nmea
from forwarder import stream_udp_realtime, get_udp_socket
from cache import VesselCache

logger = setup_logging()


def main():
    logger.info("AIS Streamer starting...")
    cache = VesselCache()
    sock = get_udp_socket()

    while True:
        cycle_start = time.monotonic()

        try:
            logger.info("Requesting AIS data...")
            xml = fetch_ais_data()

            if xml is None:
                logger.warning("No data received this poll, skipping")
            else:
                vessels = parse_aishub_xml(xml)
                logger.info(f"Parsed {len(vessels)} vessels")

                type1_vessels, type5_vessels = cache.filter_changed(vessels)
                logger.info(
                    f"{len(type1_vessels)} position updates, "
                    f"{len(type5_vessels)} static updates (of {len(vessels)} total)"
                )

                nmea = vessels_to_nmea(type1_vessels, type5_vessels)
                logger.info(f"Encoded {len(nmea)} AIS messages")

                stream_udp_realtime(
                    sock=sock,
                    nmea_list=nmea,
                    host=Config.UDP_HOST,
                    port=Config.UDP_PORT,
                    target_seconds=Config.STREAM_BUDGET_SECONDS
                )

                cache.prune()

        except Exception:
            logger.error("Unhandled error in main loop", exc_info=True)

        elapsed = time.monotonic() - cycle_start
        remaining = Config.POLL_INTERVAL - elapsed

        if remaining > 0:
            logger.info(f"Cycle took {elapsed:.1f}s, sleeping {remaining:.1f}s to hold {Config.POLL_INTERVAL}s cadence")
            time.sleep(remaining)
        else:
            logger.warning(
                f"Cycle took {elapsed:.1f}s, longer than POLL_INTERVAL ({Config.POLL_INTERVAL}s) — polling immediately"
            )


if __name__ == "__main__":
    main()