import socket
import time
import logging
import random

logger = logging.getLogger("aishub2nmea")

def stream_udp_fast(nmea_list, host, port):
    """
    Blasts AIS messages as fast as the CPU/Network allows.
    No shuffling, no delays.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    total = len(nmea_list)

    logger.info(f"Blasting {total} AIS messages to {host}:{port}")

    # Process sequentially (Important for Type 5 Part 1 & 2 to stay together)
    for msg in nmea_list:
        if not msg.endswith("\r\n"):
            msg += "\r\n"
        
        try:
            # We send each sentence in its own UDP packet, but with 0 delay.
            sock.sendto(msg.encode("ascii"), (host, port))
        except Exception as e:
            logger.error(f"UDP send failed: {e}")

    logger.info(f"Blast complete.")
    sock.close()
