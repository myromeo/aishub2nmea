import socket
import time
import logging
import random

logger = logging.getLogger("aishub2nmea")

def stream_udp_realtime(nmea_list, host, port, mps=5):
    """
    Stream AIS messages in a real-time-like fashion.
    Default mps = 5 messages per second.
    """

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    if mps <= 0:
        mps = 1

    delay = 1.0 / float(mps)
    total = len(nmea_list)

    logger.info(f"Starting AIS real‑time stream: {total} messages @ ~{mps} msg/sec")

    # Shuffle messages for more realistic stream order
    random.shuffle(nmea_list)

    # Limit debug to first few messages
    MAX_DEBUG = 5
    debug_count = 0

    for msg in nmea_list:
        try:
            preview = msg[:60] + ("..." if len(msg) > 60 else "")

            if debug_count < MAX_DEBUG:
                logger.debug(f"REALTIME UDP → {host}:{port} :: {preview}")
                debug_count += 1

            sock.sendto(msg.encode("utf-8"), (host, port))
            time.sleep(delay)

        except Exception as e:
            logger.error(f"UDP send failed to {host}:{port}", exc_info=True)

    logger.info(f"Completed real‑time AIS stream: {total} messages sent")
    sock.close()
