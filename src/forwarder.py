import socket
import logging
import time
import os

logger = logging.getLogger("aishub2nmea")

def stream_udp_realtime(nmea_list, host, port):
    """
    Streams NMEA sentences with pacing to prevent buffer overflow.
    Target rate: ~200 messages per second (adjustable via MSG_DELAY).
    """
    # Get pacing from environment (0.005s = 200 msg/sec)
    # If set to 0, it will 'blast' as before.
    delay = float(os.getenv("MSG_DELAY", 0.005))
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    total = len(nmea_list)

    if total == 0:
        logger.info("No messages to stream.")
        return

    logger.info(f"Streaming {total} messages to {host}:{port} (Pacing: {delay}s)")

    for msg in nmea_list:
        if not msg.endswith("\r\n"):
            msg += "\r\n"
        
        try:
            sock.sendto(msg.encode("ascii"), (host, port))
            # The 'Secret Sauce': Give the receiver time to breathe
            if delay > 0:
                time.sleep(delay)
        except Exception as e:
            logger.error(f"UDP send failed: {e}")
            break # Stop if the network is down

    logger.info(f"Stream complete.")
    sock.close()
