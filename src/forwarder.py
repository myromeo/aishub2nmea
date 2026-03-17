import socket
import logging
import time
import os

logger = logging.getLogger("aishub2nmea")

def stream_udp_realtime(nmea_list, host, port, mps=None):
    """
    Paced UDP streamer. 
    Accepts 'mps' (Messages Per Second) from main.py to prevent TypeError.
    """
    # Use mps if provided, otherwise check environment, otherwise default to 200
    if mps:
        delay = 1.0 / float(mps)
    else:
        delay = float(os.getenv("MSG_DELAY", 0.005))
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    total = len(nmea_list)

    if total == 0:
        logger.info("No vessels found in this poll. Skipping stream.")
        return

    logger.info(f"Streaming {total} messages to {host}:{port} (Pacing: {delay:.4f}s)")

    for msg in nmea_list:
        if not msg.endswith("\r\n"):
            msg += "\r\n"
        
        try:
            sock.sendto(msg.encode("ascii"), (host, port))
            if delay > 0:
                time.sleep(delay)
        except Exception as e:
            logger.error(f"UDP send failed: {e}")
            break

    logger.info(f"Stream complete.")
    sock.close()
