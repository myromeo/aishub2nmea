import socket
import time
import logging
import random

logger = logging.getLogger("aishub2nmea")


def stream_udp_realtime(nmea_list, host, port, mps=5):
    """
    Stream AIS messages in a real-time manner.
    mps = messages per second (default 5)
    """

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    if mps <= 0:
        mps = 1

    delay = 1.0 / float(mps)
    total = len(nmea_list)

    logger.info(f"Starting real-time AIS stream: {total} messages @ ~{mps} msg/s")

    # Shuffle to simulate natural timing
    random.shuffle(nmea_list)

    MAX_DEBUG = 5
    debug_count = 0

    for msg in nmea_list:

        # Debug truncated message
        if debug_count < MAX_DEBUG:
            preview = msg[:80] + ("..." if len(msg) > 80 else "")
            logger.debug(f"UDP → {host}:{port} :: {preview}")
            debug_count += 1

        try:
            sock.sendto(msg.encode("utf-8"), (host, port))
        except Exception as e:
            logger.error(f"UDP send failed to {host}:{port}", exc_info=True)

        time.sleep(delay)

    logger.info(f"Completed streaming {total} AIS messages.")
    sock.close()
