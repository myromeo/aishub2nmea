import socket
import time
import logging
import random

logger = logging.getLogger("aishub2nmea")

def stream_udp_realtime(nmea_list, host, port, mps=5):
    """
    Stream AIS messages in real-time-like fashion.
    
    mps = messages per second (default = 5)
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    delay = 1.0 / mps
    total = len(nmea_list)

    logger.info(f"Starting real-time AIS stream: {total} messages at ~{mps} msg/sec")

    # Shuffle messages so they don't always appear in the same order
    random.shuffle(nmea_list)

    # Limit debug output
    MAX_DEBUG = 5  
    debug_count = 0

    for msg in nmea_list:
        try:
            preview = msg[:60] + ("..." if len(msg) > 60 else "")

            if debug_count < MAX_DEBUG:
                logger.debug(f"REALTIME UDP → {host}:{port} :: {preview}")
                debug_count += 1

            sock.sendto(msg.encode(), (host, port))
            time.sleep(delay)

        except Exception as e:
            logger.error(f"UDP send failed to {host}:{port}", exc_info=True)

    logger.info(f"Real-time AIS stream complete: {total} messages streamed @ {mps}/sec")
    sock.close()
