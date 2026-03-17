import socket
import logging

logger = logging.getLogger("aishub2nmea")

def send_udp(nmea_list, host, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Limit debug output to prevent flooding logs
    MAX_DEBUG = 5  
    count = 0

    for msg in nmea_list:
        try:
            # Truncate message for debug readability
            preview = msg[:60] + ("..." if len(msg) > 60 else "")

            if count < MAX_DEBUG:
                logger.debug(f"UDP SEND → {host}:{port} :: {preview}")

            sock.sendto(msg.encode(), (host, port))
            count += 1

        except Exception as e:
            logger.error(f"UDP send failed to {host}:{port}", exc_info=True)

    sock.close()

    logger.info(f"UDP send complete: {len(nmea_list)} messages sent → {host}:{port}")
