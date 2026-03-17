import socket
import logging
logger = logging.getLogger("aishub2nmea")

def send_udp(nmea_list, host, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    for msg in nmea_list:
        try:
            sock.sendto(msg.encode(), (host, port))
        except Exception as e:
            logger.error(f"UDP send failed to {host}:{port}", exc_info=True)

    sock.close()
