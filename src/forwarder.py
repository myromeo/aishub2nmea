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
        if not msg.endswith("\r\n"):
            msg += "\r\n"
        
        try:
            sock.sendto(msg.encode("ascii"), (host, port)) # Use ascii for NMEA
        except Exception as e:
            logger.error(f"UDP send failed")

        time.sleep(delay)

    logger.info(f"Completed streaming {total} AIS messages.")
    sock.close()
